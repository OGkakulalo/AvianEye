from ultralytics import YOLO
from video_capture import VideoCapture
from chicken_detection import ChickenDetection
from anomaly_detection import AnomalyDetection
import cv2
import time
import config

model = YOLO("../model/beta.pt")
videoCapture = VideoCapture("../data/test.mp4")
videoCapture.set_start_time(10) # second
chickenDetection = ChickenDetection()

classNames = ['chicken', 'chicken_head']

dIsPressed = True
chickenIsTracked = False
anomaly_last_tracked = 0
anomaly_is_tracked = True
ANOMALY_THRESHOLD = 50  # how many time

config.dbController.connect()
anomalyDetector = AnomalyDetection()

frame_processed = 10
while videoCapture.is_open():
    if dIsPressed:
        videoCapture.set_newFrameTime(time.time())
        img = videoCapture.read_frame()
        chickenDetection.set_frame(img)
        chickenDetection.draw_bounding_box_feeder()
        chickenDetection.set_current_timestamp(videoCapture.get_current_timestamp())
        results = model(img, stream=True)

        # process chicken
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Class id
                cls = int(box.cls[0])

                # Check confidence level
                if chickenDetection.conf_is_valid(box):
                    if cls == 0:  # Chicken
                        chickenDetection.set_positions(box)
                        chickenDetection.append_detection(box)

            # Tracking with deepsort
            chickenDetection.update_tracker()

            if frame_processed == 10:
                chickenDetection.detect_chicken_with_id()
            else:
                chickenDetection.draw_bbox()
            chickenIsTracked = True

        # test
        # add condition to check every 30 minutes or something later decide
        config.dbController.clear_table()
        config.dbController.insert_mock_data()
        anomalyDetector.detect_anomaly()

        results = model(img, stream=True)

        print("FPS: ", videoCapture.get_fps())
        videoCapture.display_frame(img)
        dIsPressed = False
    else:
        # Check for keyboard input
        key = cv2.waitKey(1)
        proceed = False

        if key == ord('q'):  # Exit when 'q' key is pressed
            break
        elif key == ord('d') or proceed:  # Move the frame 'd' is pressed
            videoCapture.forward_frame(10)
            dIsPressed = True
            """
            frame_processed += 1
            print("the frame processed is: ", frame_processed)
            if frame_processed == 11:
                frame_processed = 0
            """

        elif key == ord('a'):  # Move the frame back when 'a' key is pressed
            img = videoCapture.back_frame(10)
            videoCapture.display_frame(img)

videoCapture.release()
chickenDetection.reset()