from ultralytics import YOLO
from video_capture import VideoCapture
from chicken_detection import ChickenDetection
from anomaly_detection import AnomalyDetection
import cv2
import time
import config
import os

"""
# Replace 'rtsp://your_stream_url_here' with the actual RTSP stream URL
stream_url = 'rtsp://liang:liang@192.168.1.107/live'

# Create a VideoCapture object to connect to the RTSP stream
cap = cv2.VideoCapture(stream_url)

# Check if the VideoCapture object was successfully created
if not cap.isOpened():
    print("Error: Could not open video stream.")
    exit()

# Create a window to display the video
cv2.namedWindow('RTSP Stream', cv2.WINDOW_NORMAL)
cv2.resizeWindow('RTSP Stream', 1280, 720)

while True:
    # Read a frame from the video stream
    ret, frame = cap.read()

    if not ret:
        print("Error: Could not read frame.")
        break

    # Display the frame in the window
    cv2.imshow('RTSP Stream', frame)

    # Press 'q' to exit the loop and close the window
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the VideoCapture object and close the window
cap.release()
cv2.destroyAllWindows()
"""

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

hour = 9
minute = 0

while True:
    # Construct the path to the video file
    video_path = os.path.join("D:/record/20230826", str(hour).zfill(2), str(minute).zfill(2) + ".mp4")

    # Check if the video file exists
    if os.path.exists(video_path):
        cap = cv2.VideoCapture(video_path)

        while True:
            ret, frame = cap.read()

            if not ret:  # Check if we've reached the end of the video
                cap.release()  # Release the current video capture
                minute += 1  # Move to the next minute

                if minute >= 60:
                    minute = 0
                    hour += 1

                # Sleep for a while before opening the next video
                time.sleep(1)  # You can adjust the sleep duration as needed

                break  # Break out of the inner loop and open the next video
            else:
                # Process the frame here
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
                        videoCapture.release()
                        chickenDetection.reset()
                        cv2.destroyAllWindows()
                        cap.release()
                        exit()
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


    else:
        print(f"Video not found: {video_path}")

    # Check if we've reached the end of your desired time range (23:59)
    if hour == 24:
        break

# while videoCapture.is_open():
