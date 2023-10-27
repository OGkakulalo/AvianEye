import logging
import os

import cv2
import config
from chicken_detector import chickenDetector
from graph_drawer import graphDrawer
from torch.backends import cudnn
from video_capture import VideoCapture
from bbox import BBox
from db_controller import DbController
from anomaly_detection import anomalyDetector
import torch
import threading
import time

from flask import Flask, render_template, Response, send_file, request
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

latest_frame = None  # Variable to store the latest frame
last_frame_update_time = None  # Variable to store the time of the last frame update
last_graph_modified_time = None

# Define the day and night time
# for the real system
"""DAY_TIME = datetime.time(9, 0)  # 9 AM
NIGHT_TIME = datetime.time(18, 0)   # 6 PM"""
# for now based on the local video data
DAY_TIME = 9
NIGHT_TIME = 18

def start_process():
    global latest_frame  # Declare the variable as global
    global last_frame_update_time

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

    graph_drawer = graphDrawer()

    # Initialize the chicken detector
    chicken_detector = chickenDetector(device, dbController)
    anomaly_detector = anomalyDetector(dbController)
    # Initialize the bbox object
    bbox = BBox()

    hour = 17
    minute = 50
    date = 20230905
    exit_video = False
    anomaly_detection_start = False
    has_cleared = True

    analysis_start = time.time()
    analysis_start_no_anomaly = time.time()
    initial_graph_plot = time.time()
    ANALYSIS_THRESHOLD = 30  # second
    INITIAL_GRAPH_PLOT_NO_ANOMALY_THRESHOLD = 300  # second
    INITIAL_GRAPH_PLOT_THRESHOLD = 1800  # second

    while not exit_video:
        try:
            # Construct the path to the video file
            video_path = os.path.join("D:/record/" + str(date), str(hour).zfill(2), str(minute).zfill(2) + ".mp4")

            # Check if the video file exists
            if os.path.exists(video_path):
                video_capture = VideoCapture(video_path)
                # Loop through the video frames
                while video_capture.is_open():
                    # Read a frame from the video using your custom VideoCapture object
                    frame = video_capture.read_frame()

                    if frame is None:  # Check if we've reached the end of the video
                        video_capture.release()  # Release the current video capture
                        minute += 1  # Move to the next minute

                        if minute >= 60:
                            minute = 0
                            hour += 1

                            # periodically clear the action log
                            dbController.clear_action_log()
                        if hour == 24:
                            hour = 0
                            # Increment the date to the next day
                            date += 1
                        break  # Break out of the inner loop and open the next video
                    else:
                        bbox.set_frame(frame)

                        if frame is not None:
                            # detection start time
                            start_time = time.time()

                            # Get the current system time
                            # current_time = datetime.datetime.now().time()
                            # Check if it's day or night based on the current system time
                            # for the real system
                            # if DAY_TIME <= current_time < NIGHT_TIME:
                            # for now
                            # only perform anomaly detection during day time
                            if DAY_TIME <= hour < NIGHT_TIME:
                                if has_cleared:
                                    has_cleared = False
                                    # reset the objects when it day time again
                                    dbController = DbController()
                                    dbController.connect()
                                    dbController.insert_chicken_id()
                                    dbController.insert_analysis()
                                    graph_drawer = graphDrawer()
                                    chicken_detector = chickenDetector(device, dbController)
                                    anomaly_detector = anomalyDetector(dbController)

                                chicken_detector.detect_chicken(frame)

                                # perform anomaly after enough data is gathered
                                if time.time() - initial_graph_plot > INITIAL_GRAPH_PLOT_THRESHOLD:
                                    anomaly_detection_start = True
                                    # update the graph every threshold
                                    if time.time() - analysis_start > ANALYSIS_THRESHOLD:
                                        print("graph is updated")
                                        analysis_start = time.time()

                                        ids = dbController.get_distinct_id()

                                        # check for anomaly and draw the graph
                                        for id in ids:
                                            graph = anomaly_detector.detect_anomaly(id)
                                            if graph is not None:
                                                data, result, anomaly_colors, start_end_time_list, mahalanobis_dist = graph
                                                graph_drawer.save_graph(id, result, data, anomaly_colors, True,
                                                                        start_end_time_list, mahalanobis_dist)
                                                # send alert if chicken is detected as high possibility to be sick
                                                if anomaly_colors == "red":
                                                    anomaly_detector.send_alert(id,
                                                                                f"./static/assets/graph/chicken_{id}.png")

                                # save plain graph after enough data is gathered
                                if time.time() - initial_graph_plot > INITIAL_GRAPH_PLOT_NO_ANOMALY_THRESHOLD and not anomaly_detection_start:
                                    if time.time() - analysis_start_no_anomaly > ANALYSIS_THRESHOLD:
                                        analysis_start_no_anomaly = time.time()
                                        ids = dbController.get_distinct_id()

                                        for id in ids:
                                            # Fetch data for the current chicken ID
                                            result = dbController.get_analysis_data(id)
                                            if result:
                                                graph_drawer.save_graph(id, result)
                            else:
                                if not has_cleared:
                                    has_cleared = True

                                    ids = dbController.get_distinct_id()
                                    for id in ids:
                                        graph_drawer.delete_graph(id)

                                    dbController.clear_table()
                                    dbController.close()
                                pass

                            # to display to web
                            _, latest_frame = cv2.imencode('.jpg', frame)
                            latest_frame = latest_frame.tobytes()
                            # Update the last_frame_update_time to the current time
                            last_frame_update_time = time.time()

                            # Display the annotated frame
                            video_capture.display_frame(frame)
                            video_capture.forward_frame(config.frame_skipped)

                            end_time = time.time()
                            processing_speed = round(end_time - start_time, 2)
                            config.speed_ratio = processing_speed / config.standard_speed
                            print(f"processing speed for 1 frame is {processing_speed}")

                    # Break the loop if 'q' is pressed
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        exit_video = True
                        # Release the custom VideoCapture object
                        video_capture.release()
                        dbController.clear_table()
                        dbController.close()
                        break
            else:
                print(f"Video not found: {video_path}")
        except Exception as e:
            print(f"An error occurred: {str(e)}")


def gen_frames():
    while True:
        # Check if last_frame_update_time is None or if it's older than 5 seconds
        current_time = time.time()
        if last_frame_update_time is None or (current_time - last_frame_update_time) > 5:
            error_message = b'--frame\r\n' \
                            b'Content-Type: text/plain\r\n\r\n' \
                            b'Error: Image not updated for 5 seconds\r\n'
            yield error_message
        else:
            if latest_frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')

        # Add a short sleep here to avoid a high CPU load
        time.sleep(0.1)


@app.route('/video')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/graph')
def graph_image():
    selected_chicken_id = request.args.get('id')
    config.selected_chicken_id = int(selected_chicken_id)
    graph_image_path_png = f"./static/assets/graph/chicken_{selected_chicken_id}.png"

    global last_graph_modified_time

    graph_image_path = f"./static/assets/graph/chicken.gif"
    try:
        if os.path.exists(graph_image_path_png):
            graph_image_path = graph_image_path_png

        if last_graph_modified_time is None:
            last_graph_modified_time = os.path.getmtime(graph_image_path)

        if os.path.getmtime(graph_image_path) > last_graph_modified_time:
            last_graph_modified_time = os.path.getmtime(graph_image_path)
            return send_file(graph_image_path, mimetype='image/png')
        else:
            return send_file(graph_image_path, mimetype='image/png')
    except Exception as e:
        app.logger.error(f"Error in graph_image route: {str(e)}")
        return '', 500  # Return a 500 error response


@app.route('/update_checkbox_state', methods=['POST'])
def update_checkbox_state():
    isChecked = request.form.get('isChecked', 'false') == 'true'  # Convert to boolean
    config.view_all = isChecked

    return str(isChecked)  # required to return something


@app.route('/')
def index():
    return render_template('index.html', numOfChicken=config.chicken_num)


if __name__ == "__main__":
    log = logging.getLogger('werkzeug')
    log.disabled = True
    task = threading.Thread(target=start_process)
    task.start()
    app.run(host="192.168.1.107", port=5000)
