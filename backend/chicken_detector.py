import threading

from ultralytics import YOLO

import config
from db_controller import DbController
from tracker import Tracker
from bbox import BBox
from chicken_behaviour import chickenBehaviour
from chicken_analysis import chickenAnalysis


class chickenDetector:
    def __init__(self, device, dbController):
        # Initialize the YOLOv8 model
        self.model = YOLO("../model/topdownv4.pt")
        self.model.to(device)
        # Initialize the db
        self.dbController = dbController
        # Initialize the tracker
        self.tracker = Tracker(self.model, dbController)
        # Initialize the bbox
        self.bbox = BBox()
        # Get the class mapping from your YOLO model (assuming it provides a class_map attribute)
        self.class_mapping = self.model.names

        self.chickenAnalysis = chickenAnalysis(dbController)

        self.chickenBehaviour = chickenBehaviour(dbController)

        self.UPDATE_FRAME_THRESHOLD = 1 # frame
        self.last_frame_checked = 0

        # Create a Lock instance
        self.lock = threading.Lock()

    def detect_chicken(self, frame):
        self.chickenBehaviour.update_threshold()

        results = self.tracker.get_results(frame)
        self.bbox.set_frame(frame)

        # Get the boxes, track IDs, class names, and confidences
        boxes = results[0].boxes.xywh.cpu()
        track_ids = results[0].boxes.id.int().cpu().tolist()
        class_ids = results[0].boxes.cls.int().cpu().tolist()
        confidences = results[0].boxes.conf.cpu()

        # Check and update the status of track IDs
        self.tracker.check_missing_track_ids()

        # Create and start threads for maintaining id
        threads = []

        for box, track_id, class_id, confidence in zip(boxes, track_ids, class_ids, confidences):
            # Get the class name from the class mapping
            class_name = self.class_mapping[class_id]

            # Get the bbox position
            x, y, w, h = box

            if confidence > 0.5:
                # Create a new DbController instance for each thread
                db_controller_thread = DbController()
                db_controller_thread.connect()  # Connect to the db

                thread = threading.Thread(target=self.maintain_id_thread, args=(db_controller_thread, track_id, x, y, w, h, class_name, confidence))
                thread.start()
                threads.append(thread)

                # plot the track id history
                self.tracker.plot_track(x, y, track_id)

        # Wait for all threads to finish
        for thread in threads:
            thread.join()

        # draw bbox based on data saved in database
        # Fetch data from the database (assuming you have a method to fetch data)
        chicken_data = self.dbController.get_all_from_chicken_list()

        # Iterate through the fetched data and draw bboxes based on the database entries
        for data in chicken_data:
            id = data[0]
            x = data[4]
            y = data[5]
            w = data[6]
            h = data[7]
            confidence = data[9]

            # Draw bbox based on database data and based on user option
            if config.view_all:
                self.bbox.draw_chicken_bbox(id, confidence, x, y, w, h)
            else:
                if id == config.selected_chicken_id:

                    self.bbox.draw_chicken_bbox(id, confidence, x, y, w, h)

        # Create and start threads for action detection
        threads = []

        # detect action every few second to increase speed
        self.last_frame_checked += 1
        can_check_action = False
        if self.last_frame_checked > self.UPDATE_FRAME_THRESHOLD:
            self.last_frame_checked = 0
            can_check_action = True

        # Draw polyline outside the loop so that it appears on highest z-index
        # for box, track_id in zip(boxes, track_ids):
        for data in chicken_data:
            track_id = data[1]
            id = data[0]
            x = data[4]
            y = data[5]
            w = data[6]
            h = data[7]

            track = self.tracker.get_track_history(track_id)

            # Draw based on user option
            if config.view_all:
                self.bbox.draw_polyline(track)
                self.bbox.draw_circle(id, x, y)
            else:
                if id == config.selected_chicken_id:
                    self.bbox.draw_polyline(track)
                    self.bbox.draw_circle(id, x, y)

            if can_check_action:
                # Create a new DbController instance for each thread
                db_controller_thread = DbController()
                db_controller_thread.connect()  # Connect to the db

                if id is not None:
                    thread = threading.Thread(target=self.detect_chicken_action, args=(db_controller_thread, id, x, y, w, h))
                    thread.start()
                    threads.append(thread)

        # Wait for all threads to finish
        for thread in threads:
            thread.join()

        # update analysis
        self.chickenAnalysis.update_threshold()
        self.chickenAnalysis.update_analysis()

        # Draw the bbox for the feeder and drinker lastly
        """self.bbox.draw_bbox_feeder()
        self.bbox.draw_bbox_drinker1()
        self.bbox.draw_bbox_drinker2()"""

    def detect_chicken_action(self, db_controller_thread, id, x, y, w, h):
        # Acquire the Lock to ensure exclusive access to the track_id
        with self.lock:
            # use this condition because want each function to be execute
            action_detected = False

            # detect chicken behaviour
            move_a_bit, move_a_lot = self.chickenBehaviour.is_moving(db_controller_thread, id, x, y, w, h)

            if self.chickenBehaviour.detect_eating_or_drinking(db_controller_thread, id, x, y, w, h, move_a_bit):
                # insert lof is inside the detect
                action_detected = True
            if self.chickenBehaviour.detect_inactivity(db_controller_thread, id, move_a_lot) and not action_detected:
                self.dbController.insert_log(id, "inactivity")

    def maintain_id_thread(self, db_controller_thread, track_id, x, y, w, h, class_name, confidence):
        # Acquire the Lock to ensure that if the thread will need to wait to use the same resources(function) ensuring that clashing will not occurs
        with self.lock:
            self.tracker.maintain_id(db_controller_thread, track_id, x, y, w, h, class_name, confidence)
