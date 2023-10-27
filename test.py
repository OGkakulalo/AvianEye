import os
import time
import cv2
import config
from chicken_detector import chickenDetector
from torch.backends import cudnn
from video_capture import VideoCapture
from bbox import BBox
from db_controller import DbController
import torch
import threading
import time

from flask import Flask, render_template, Response
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

latest_frame = None  # Variable to store the latest frame


def start_process():
    global latest_frame  # Declare the variable as global

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
    dbController.insert_analysis()

    # Initialize the chicken detector
    chicken_detector = chickenDetector(device, dbController)

    # Initialize the bbox object
    bbox = BBox()

    hour = 10
    minute = 33
    date = 20230903
    exit_video = False
    dIsPressed = True
    sIsPressed = False

    while not exit_video:
        try:
            # Construct the path to the video file
            video_path = os.path.join("D:/record/" + str(date), str(hour).zfill(2), str(minute).zfill(2) + ".mp4")

            # Check if the video file exists
            if os.path.exists(video_path):
                video_capture = VideoCapture(video_path)

                # Loop through the video frames
                while video_capture.is_open():
                    if dIsPressed:
                        dIsPressed = False

                        start_time = time.time()

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

                                latest_frame = frame

                                cv2.imwrite("C:/Users/admin/Desktop/msu/degree/fyp/AvianEye/web/static/assets/test.jpg",
                                            frame)
                                # Display the annotated frame
                                video_capture.display_frame(frame)
                                video_capture.forward_frame(config.frame_skipped)

                                end_time = time.time()
                                processing_speed = round(end_time - start_time, 2)
                                config.speed_ratio = processing_speed / config.standard_speed
                                print(f"processing speed for 1 frame is {processing_speed}")
                    else:
                        if not sIsPressed:
                            dIsPressed = True
                        else:
                            dIsPressed = False

                        # Break the loop if 'q' is pressed
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord("q"):
                            exit_video = True
                            break
                        if key == ord("d"):
                            dIsPressed = True
                            sIsPressed = False
                        if key == ord("s"):
                            sIsPressed = True
                            print("System is paused")
            else:
                print(f"Video not found: {video_path}")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

    # Release the custom VideoCapture object
    video_capture.release()
    dbController.clear_table()
    dbController.close()


def gen_frames():
    while True:
        if latest_frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')
        time.sleep(1)


@app.route('/video')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    task = threading.Thread(target=start_process())
    task.start()

    app.run(debug=True, host="192.168.100.67", port=5000)
