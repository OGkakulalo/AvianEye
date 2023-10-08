import os
import cv2

from chicken_detector import chickenDetector
from torch.backends import cudnn
from video_capture import VideoCapture
from bbox import BBox
from db_controller import DbController
import torch

if __name__ == "__main__":
    # Check if CUDA (GPU) is available
    if torch.cuda.is_available():
        device = torch.device("cuda")
        cudnn.benchmark = True  # Enable CuDNN benchmark for faster training (if using CuDNN)
        print("CUDA is available")
    else:
        device = torch.device("cpu")
        print("CUDA is not available. Switching to CPU.")

    # Initialize the database
    dbController = DbController()
    dbController.connect()
    dbController.insert_chicken_id()

    # Initialize the chicken detector
    chicken_detector = chickenDetector(device, dbController)

    """
    # Initialize the custom VideoCapture object
    video_capture = VideoCapture("../data/alpha.mp4")
    video_capture.set_start_time(340)  # second
    """

    # Initialize the bbox object
    bbox = BBox()

    hour = 10
    minute = 33
    date = 20230903
    exit_video = False
    dIsPressed = True

    while not exit_video:
        # Construct the path to the video file
        video_path = os.path.join("D:/record/" + str(date), str(hour).zfill(2), str(minute).zfill(2) + ".mp4")

        # Check if the video file exists
        if os.path.exists(video_path):
            video_capture = VideoCapture(video_path)

            # Loop through the video frames
            while video_capture.is_open():
                if dIsPressed:
                    dIsPressed = False

                    # Read a frame from the video using your custom VideoCapture object
                    frame = video_capture.read_frame()

                    if frame is None:  # Check if we've reached the end of the video
                        video_capture.release()  # Release the current video capture
                        minute += 1  # Move to the next minute

                        if minute >= 60:
                            minute = 0
                            hour += 1
                        if hour == 24:
                            hour = 0
                            # Increment the date to the next day
                            date += 1
                        break  # Break out of the inner loop and open the next video
                    else:
                        bbox.set_frame(frame)

                        if frame is not None:
                            chicken_detector.detect_chicken(frame)
                            # Display the annotated frame
                            video_capture.display_frame(frame)
                            video_capture.forward_frame(1)
                else:
                    dIsPressed = True
                    # Break the loop if 'q' is pressed
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        exit_video = True
                        break
                    elif key == ord("d"):
                        dIsPressed = True
        else:
            print(f"Video not found: {video_path}")

    # Release the custom VideoCapture object
    video_capture.release()
    dbController.clear_table()
    dbController.close()


"""
videoCapture = VideoCapture("../data/test2.mp4")
videoCapture.set_start_time(340) # second
chickenDetection = ChickenDetection()

classNames = ['chicken']

dIsPressed = True
chickenIsTracked = False
anomaly_last_tracked = 0
anomaly_is_tracked = True
ANOMALY_THRESHOLD = 50  # how many time
CHICKEN_NUM = 10

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
        #config.dbController.clear_table()
        #config.dbController.insert_mock_data()
        #anomalyDetector.detect_anomaly()

        results = model(img, stream=True)

        print("FPS: ", videoCapture.get_fps())
        videoCapture.display_frame(img)
        dIsPressed = False
    else:
        # Check for keyboard input
        key = cv2.waitKey(1)
        proceed = True

        if key == ord('q'):  # Exit when 'q' key is pressed
            break
        elif key == ord('d') or proceed:  # Move the frame 'd' is pressed
            videoCapture.forward_frame(1)
            dIsPressed = True
        elif key == ord('a'):  # Move the frame back when 'a' key is pressed
            img = videoCapture.back_frame(10)
            videoCapture.display_frame(img)

videoCapture.release()
chickenDetection.reset()
"""
