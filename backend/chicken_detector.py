from ultralytics import YOLO
from tracker import Tracker
from bbox import BBox

class chickenDetector:
    def __init__(self, device, dbController):
        # Initialize the YOLOv8 model
        self.model = YOLO("../model/best.pt")
        self.model.to(device)
        # Initialize the db
        self.dbController = dbController
        # Initialize the tracker
        self.tracker = Tracker(self.model, dbController)
        # Initialize the bbox
        self.bbox = BBox()
        # Get the class mapping from your YOLO model (assuming it provides a class_map attribute)
        self.class_mapping = self.model.names

    def detect_chicken(self, frame):
        results = self.tracker.get_results(frame)
        self.bbox.set_frame(frame)

        # Get the boxes, track IDs, class names, and confidences
        boxes = results[0].boxes.xywh.cpu()
        track_ids = results[0].boxes.id.int().cpu().tolist()
        class_ids = results[0].boxes.cls.int().cpu().tolist()
        confidences = results[0].boxes.conf.cpu()

        # Check and update the status of track IDs
        self.tracker.check_missing_track_ids()

        for box, track_id, class_id, confidence in zip(boxes, track_ids, class_ids, confidences):
            # Get the class name from the class mapping
            class_name = self.class_mapping[class_id]

            # Get the bbox position
            x, y, w, h = box

            self.tracker.maintain_id(track_id, x, y, w, h, class_name, confidence)

            # plot the track id history
            self.tracker.plot_track(x, y, track_id)

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
            class_name = data[8]
            confidence = data[9]

            # Draw bbox based on database data
            self.bbox.draw_chicken_bbox(id, class_name, confidence, x, y, w, h)

        # Draw polyline outside the loop so that it appears on highest z-index
        for box, track_id in zip(boxes, track_ids):
            x, y, _, _ = box

            track = self.tracker.get_track_history(track_id)
            self.bbox.draw_polyline(track)
            self.bbox.draw_circle(x, y)
