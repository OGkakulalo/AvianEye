# todo-check on the chicken id, if old id misisng, check the position of the new id, if it close to the old bbox, then reassign back the id
# todo-insert and update image of the coop every time it is processed with time frame (max 5 row then remove old update new)
# todo-update the graph every 5 minutes to save memory
# todo-store the graph image for up to 1 month(30 days)
# todo-store the graph as per day when in a day every 5 minute it will update and use back the previous row
import numpy as np
from ultralytics import YOLO

# todo - find better method to stream the viedo (now idea is to use json send whole thing, another idea is to use cv2.cap the whole window and stream that)
# todo - if farmer remove the chicken from the farm and put it back (after like 1 day), ask the farmer if it is new chicken, if didnt clarify in 10 minutes then it new chicken, if farmer select old chicken then select the id from a drop down list of the old chicken that is no longer in the frame previously, allow farmer to still reassign back the id if needed
# todo - compare the graph of all chicken to see the pattern if differ too much and persist then can label as warning, then the farmer can set whether the warning is necessary or not once they check as that might just be the chicken normal behaviour
# todo - check on web post and request to allow communication from the rpi to the webserver
# todo - always save the image into local storage or db every 1 hour with the label so taht in case of power outage, the farmer can reassig the chicken id back according to the pic


import config
import cv2
import math


class chickenBehaviour:
    def __init__(self, device):
        self.img = None


        self.x1, self.y1, self.x2, self.y2 = 0, 0, 0, 0
        self.conf = 0
        self.EATING_THRESHOLD = 0.5  # second
        self.MOVING_THRESHOLD = 50  # pixel
        self.MOVEMENT_THRESHOLD = 10  # pixel
        self.RESTING_THRESHOLD = 0.5  # second
        self.PROXIMITY_THRESHOLD = 70  # pixel #todo-change back to 10 when get better detection model
        self.IOU_THRESHOLD = 0.02
        self.ANALYSIS_UPDATE_THRESHOLD = 3  # second
        self.ANALYSIS_THRESHOLD = 2  # how many time
        self.detections = []
        self.resting_state = {}
        self.resting_timer = {}
        self.eating_state = {}
        self.eating_timer = {}
        self.current_timestamp = 0
        self.prev_timestamp = 0
        self.prev_start = True
        self.analysis_updated = 0
        self.track_id = None

    def set_frame(self, img):
        self.img = img

    def set_current_timestamp(self, timestamp):
        self.current_timestamp = timestamp
        if self.prev_start:
            self.prev_timestamp = self.current_timestamp
            self.prev_start = False

        # to update the analysis table
        print("time difference: ", self.current_timestamp - self.prev_timestamp)
        if self.current_timestamp - self.prev_timestamp > self.ANALYSIS_UPDATE_THRESHOLD:
            config.dbController.update_analysis(True, False)
            self.prev_start = True
            self.analysis_updated += 1

        if self.analysis_updated > self.ANALYSIS_THRESHOLD:
            config.dbController.update_analysis(False, True)
            self.analysis_updated = 0
        """
        # perform anomaly detection
        if self.analysis_updated > self.ANOMALY_THRESHOLD:
            for row in config.dbController.get_chicken_id():
                track_id = row[0]  # Access the 'id' column using integer index
                result = config.dbController.get_analysis_data(track_id)
                self.anomalyDetector.detect_anomaly(result)
            self.anomalyDetector.show_graph()
            self.anomaly_last_tracked = 0

        """

    def set_positions(self, box):
        # Bounding Box
        self.x1, self.y1, self.x2, self.y2 = box.xyxy[0]
        self.x1, self.y1, self.x2, self.y2 = int(self.x1), int(self.y1), int(self.x2), int(self.y2)



    def detect_chicken_with_id(self):
        # Using deepsort to assign id on each chicken
        for track in self.tracker.tracks:
            bbox = track.bbox
            track_id = track.track_id

            # Get the x1 and y1 coordinates from the bbox
            x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            color = (255, 0, 255)  # Magenta bounding box

            cv2.rectangle(self.img, (x1, y1), (x2, y2), color, 3)
            # Print the info onto the bounding box
            cvzone.putTextRect(self.img, f'chicken ID:{track_id}', (max(0, x1), max(35, y1)), scale=1, thickness=1)

            action_detected = False
            # check if chicken id is already in the list or not
            if config.dbController.check_chicken_id(track_id) != []:
                config.dbController.update_current_pos(track_id, x1, y1, x2, y2)
                if self.detect_eating(track_id):
                    config.dbController.clear_log()
                    action_detected = True
                if self.detect_moving(track_id) and not action_detected:
                    config.dbController.insert_log(track_id, "moving")
                    action_detected = True
                if self.detect_etc(track_id) and not action_detected:
                    config.dbController.insert_log(track_id, "etc")
                    action_detected = True
                if not action_detected:
                    config.dbController.clear_log()
                    self.detect_resting(track_id)
            else:
                print(config.dbController.check_chicken_id(track_id))
                print("a chicken is being added")
                config.dbController.insert_pos(track_id, x1, y1, x2, y2, config.currentPosTable)
                config.dbController.insert_pos(track_id, x1, y1, x2, y2, config.prevPosTable)
                config.dbController.insert_action(track_id)
                config.dbController.insert_analysis(track_id)
                # Start the resting timer for the chicken
                self.resting_timer[track_id] = self.current_timestamp

    def detect_etc(self, track_id):
        prev_x1 = config.dbController.get_x1(track_id, config.prevPosTable)
        prev_y1 = config.dbController.get_y1(track_id, config.prevPosTable)
        prev_x2 = config.dbController.get_x2(track_id, config.prevPosTable)
        prev_y2 = config.dbController.get_y2(track_id, config.prevPosTable)

        x1 = config.dbController.get_x1(track_id, config.currentPosTable)
        y1 = config.dbController.get_y1(track_id, config.currentPosTable)
        x2 = config.dbController.get_x2(track_id, config.currentPosTable)
        y2 = config.dbController.get_y2(track_id, config.currentPosTable)

        # check if chicken moved or not
        if abs(x1 - prev_x1) > self.MOVEMENT_THRESHOLD or abs(y1 - prev_y1) > self.MOVEMENT_THRESHOLD or abs(
                x2 - prev_x2) > self.MOVEMENT_THRESHOLD or abs(y2 - prev_y2) > self.MOVEMENT_THRESHOLD:
            print("chicken ", id, " moved a little bit")
            config.dbController.update_action("etc", track_id)
            config.dbController.update_prev_pos(track_id, x1, y1, x2, y2)

            self.resting_state[track_id] = False  # Chicken is not resting anymore
            self.resting_timer[track_id] = self.current_timestamp  # Reset the resting timer
            return True
        return False

    def detect_foraging(self, chicken_y2, track_id):
        # Check if the head is close to the bottom of the chicken
        print(self.y2, " ", chicken_y2)
        if abs(self.y2 - chicken_y2) < 400:  # head is detected at the bottom # todo - make sure the 400 is scale with the size
            print("chicken ", track_id, "is foraging")
            # Increment the foraging action count
            # todo self.chickenAction[idx][track_id]['actions'][2] += 1

    def detect_eating(self, track_id):
        # Check if the chicken head is inside the feeder bounding box
        print("eating is being checked for chicken ", track_id)
        # Check if the chicken has been eating
        current_time = self.current_timestamp

        if self.is_inside_feeder_bbox(track_id):
            x1 = config.dbController.get_x1(track_id, config.currentPosTable)
            y1 = config.dbController.get_y1(track_id, config.currentPosTable)
            x2 = config.dbController.get_x2(track_id, config.currentPosTable)
            y2 = config.dbController.get_y2(track_id, config.currentPosTable)

            print("Chicken ", track_id, " is in the feeder")

            if track_id in self.eating_timer:
                elapsed_time = current_time - self.eating_timer[track_id]
                print("current time = ", current_time)
                print("eating time = ", self.eating_timer[track_id])
                print(self.eating_state.get(track_id))
                if self.eating_state.get(track_id):  # Chicken is currently eating
                    config.dbController.update_action("eating", track_id)
                    self.eating_timer[track_id] = current_time
                    self.resting_timer[track_id] = current_time
                    self.resting_state[track_id] = False
                    config.dbController.update_prev_pos(track_id, x1, y1, x2, y2)
                    return True
                else:
                    if elapsed_time >= self.EATING_THRESHOLD:
                        # 25 is the video fps, 10 is how many frame is skipped to the next
                        prev_eating = round((25 * self.EATING_THRESHOLD) / 10)
                        for i in range(prev_eating + 1):
                            # Increment the eating action count
                            config.dbController.update_action("eating", track_id)
                            # Decrement the previous action detected
                            self.decrement_action(track_id)

                        self.eating_state[track_id] = True
                        self.resting_state[track_id] = False
                        self.resting_timer[track_id] = current_time
                        self.resting_timer[track_id] = current_time
                        config.dbController.update_prev_pos(track_id, x1, y1, x2, y2)
                        return True
                    return False
            else:
                self.eating_timer[track_id] = current_time
                return False
        return False

    def conf_is_valid(self, box):
        # Confidence
        self.conf = math.ceil((box.conf[0] * 100)) / 100
        if self.conf > 0.5:
            return True
        return False

    def append_detection(self, box):
        conf = math.ceil((box.conf[0] * 100)) / 100

        # Data for deepsort
        self.detections.append([self.x1, self.y1, self.x2, self.y2, conf])

    def detect_moving(self, track_id):
        print("the track id for moving\n", track_id, " ", config.prevPosTable)
        prev_x1 = config.dbController.get_x1(track_id, config.prevPosTable)
        prev_y1 = config.dbController.get_y1(track_id, config.prevPosTable)
        prev_x2 = config.dbController.get_x2(track_id, config.prevPosTable)
        prev_y2 = config.dbController.get_y2(track_id, config.prevPosTable)

        x1 = config.dbController.get_x1(track_id, config.currentPosTable)
        y1 = config.dbController.get_y1(track_id, config.currentPosTable)
        x2 = config.dbController.get_x2(track_id, config.currentPosTable)
        y2 = config.dbController.get_y2(track_id, config.currentPosTable)

        # check if chicken moved or not
        if abs(x1 - prev_x1) > self.MOVING_THRESHOLD or abs(y1 - prev_y1) > self.MOVING_THRESHOLD or abs(
                x2 - prev_x2) > self.MOVING_THRESHOLD or abs(y2 - prev_y2) > self.MOVING_THRESHOLD:
            print("chicken ", id, " moved")
            config.dbController.update_action("moving", track_id)
            config.dbController.update_prev_pos(track_id, x1, y1, x2, y2)

            self.eating_state[track_id] = False  # Chicken is not eating anymore
            self.resting_state[track_id] = False  # Chicken is not resting anymore
            self.eating_timer[track_id] = self.current_timestamp  # Reset the eating timer
            self.resting_timer[track_id] = self.current_timestamp  # Reset the resting timer
            return True
        return False

    def update_tracker(self):
        self.tracker.update(self.img, self.detections)
        self.detections = []

    def detect_resting(self, track_id):
        current_time = self.current_timestamp
        if track_id in self.resting_timer:
            if self.resting_state.get(track_id):  # Chicken is currently resting
                print("Chicken ", track_id, " is resting")
                # Increment the resting action count
                config.dbController.update_action("resting", track_id)

                # Reset the resting timer to the current time
                self.resting_timer[track_id] = current_time
                return True
            else:  # Chicken is not currently resting
                resting_time = current_time - self.resting_timer[track_id]
                if resting_time >= self.RESTING_THRESHOLD:
                    # 25 is the video fps, 10 is how many frame is skipped to the next
                    prev_resting = round((25 * self.RESTING_THRESHOLD) / 10)
                    for i in range(prev_resting + 1):
                        # Update the action count to indicate resting
                        config.dbController.update_action("resting", track_id)
                        # Remove the previous detected action in this timestamp
                        self.decrement_action(track_id)

                    self.resting_state[track_id] = True
                    # update the resting timer
                    self.resting_timer[track_id] = current_time
                    return True
                return False
        else:
            self.resting_timer[track_id] = current_time
            return False

    def is_inside_feeder_bbox(self, track_id):
        # Assuming feeder_bbox is a tuple representing the bounding box coordinates of the feeder
        feeder_x1, feeder_y1, feeder_x2, feeder_y2 = self.FEEDER_BBOX
        x1 = config.dbController.get_x1(track_id, config.currentPosTable)
        y1 = config.dbController.get_y1(track_id, config.currentPosTable)
        x2 = config.dbController.get_x2(track_id, config.currentPosTable)
        y2 = config.dbController.get_y2(track_id, config.currentPosTable)

        # check if chicken is overlapped with the feeder bbox
        # Calculate the intersection area between the head and body bboxes
        print(x1, ", ", y1, ", ", x2, ", ", y2)
        print(feeder_x1, ", ", feeder_y1, ", ", feeder_x2, ", ", feeder_y2)
        intersection_area = max(0, min(x2, feeder_x2) - max(x1, feeder_x1)) * max(0, min(y2, feeder_y2) - max(y1,
                                                                                                              feeder_y1))

        print("intersection area = ", intersection_area)
        if intersection_area > 0:
            return True
        return False

    def decrement_action(self, track_id):
        actionLogged = config.dbController.get_log(track_id)
        if actionLogged is not None:
            config.dbController.decrement_action(track_id, actionLogged)

    def reset(self):
        config.dbController.clear_table()
