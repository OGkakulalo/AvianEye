# todo-insert and update image of the coop every time it is processed with time frame (max 5 row then remove old update new)
# todo-update the graph every 5 minutes to save memory
# todo-store the graph image for up to 1 month(30 days)
# todo-store the graph as per day when in a day every 5 minute it will update and use back the previous row

# todo - if chicken is in a group when they are near the feeder, detect all as eating

# todo - find better method to stream the viedo (now idea is to use json send whole thing, another idea is to use cv2.cap the whole window and stream that)
# todo - if farmer remove the chicken from the farm and put it back (after like 1 day), ask the farmer if it is new chicken, if didnt clarify in 10 minutes then it new chicken, if farmer select old chicken then select the id from a drop down list of the old chicken that is no longer in the frame previously, allow farmer to still reassign back the id if needed
# todo - compare the graph of all chicken to see the pattern if differ too much and persist then can label as warning, then the farmer can set whether the warning is necessary or not once they check as that might just be the chicken normal behaviour
# todo - check on web post and request to allow communication from the rpi to the webserver
# todo - always save the image into local storage or db every 1 hour with the label so taht in case of power outage, the farmer can reassig the chicken id back according to the pic

# todo - detect that all chicken action is successfully updated if its it waiting to check threshold before analysis open new row

from datetime import datetime, timedelta
from shapely.geometry import box
import config
from bbox import BBox


class chickenBehaviour:
    def __init__(self, dbController):
        self.img = None
        self.bbox = BBox()
        self.dbController = dbController

        self.EATING_TO_INACTIVE_THRESHOLD = 20  # second
        self.DRINKING_TO_INACTIVE_THRESHOLD = 20  # second
        self.MOVING_THRESHOLD = 1  # pixel
        self.INACTIVITY_THRESHOLD = 20  # second
        self.PROXIMITY_THRESHOLD = 10  # pixel
        self.INSIDE_FEEDER_THRESHOLD = 50  # pixel
        self.ANALYSIS_UPDATE_THRESHOLD = 3  # second
        self.ANALYSIS_THRESHOLD = 2  # how many time
        self.MOVEMENT_THRESHOLD = 2  # Number of consecutive movements to detect eating or drinking
        self.MOVEMENT_TIME_WINDOW = 20  # second

        self.movement_counter = {i: 0 for i in range(1, config.chicken_num + 1)}
        self.movement_timer = {i: datetime.now() for i in range(1, config.chicken_num + 1)}
        self.inactive_state = {i: False for i in range(1, config.chicken_num+1)}
        self.inactive_timer = {i: datetime.now() for i in range(1, config.chicken_num+1)}
        self.eating_state = {i: False for i in range(1, config.chicken_num+1)}
        self.eating_timer = {i: datetime.now() for i in range(1, config.chicken_num+1)}
        self.drinking_state = {i: False for i in range(1, config.chicken_num + 1)}
        self.drinking_timer = {i: datetime.now() for i in range(1, config.chicken_num + 1)}
        self.prev_timestamp = 0
        self.prev_start = True
        self.analysis_updated = 0
        self.track_id = None

    def update_analysis(self):  # update the analysis table when the threshold is met
        current_time = datetime.now()
        if self.prev_start:
            self.prev_timestamp = current_time
            self.prev_start = False

        # to update the analysis table
        print("time difference: ", current_time - self.prev_timestamp)
        if current_time - self.prev_timestamp > self.ANALYSIS_UPDATE_THRESHOLD:
            self.dbController.update_analysis(True, False)
            self.prev_start = True
            self.analysis_updated += 1

        if self.analysis_updated > self.ANALYSIS_THRESHOLD:
            self.dbController.update_analysis(False, True)
            self.analysis_updated = 0
        """
        # perform anomaly detection
        if self.analysis_updated > self.ANOMALY_THRESHOLD:
            for row in self.dbController.get_chicken_id():
                track_id = row[0]  # Access the 'id' column using integer index
                result = self.dbController.get_analysis_data(track_id)
                self.anomalyDetector.detect_anomaly(result)
            self.anomalyDetector.show_graph()
            self.anomaly_last_tracked = 0

        """

    def detect_eating_or_drinking(self, dbController, id, x, y, w, h , is_moving):
        # Check if the chicken head is inside the feeder bounding box
        print("eating or drinking is being checked for chicken ", id)
        current_time = datetime.now()
        action = None
        inactivity_threshold = None
        current_state = {}
        current_timer = {}

        is_inside_bbox, bbox_detected = self.is_inside_feeder_or_drinker_bbox(id, x, y, w, h)

        if id == 10:
            print("bbox detected for id 10 is ", bbox_detected)

        # detect the chicken in feeder or drinker
        if bbox_detected == "feeder":
            action = "eating"
            current_state = self.eating_state
            current_timer = self.eating_timer
            inactivity_threshold = self.EATING_TO_INACTIVE_THRESHOLD
        elif bbox_detected == "drinker1" or "drinker2":
            action = "drinking"
            current_state = self.drinking_state
            current_timer = self.drinking_timer
            inactivity_threshold = self.EATING_TO_INACTIVE_THRESHOLD

        if is_inside_bbox:
            print("Chicken ", id, f" is in the {bbox_detected}")

            # check if chicken is resting inside the feeder bbox or actually eating or drinking
            if is_moving:
                # Increment the movement counter for the chicken
                # movement is to detect whether the chicken is starting to drink or eat or just passing by
                if id == 10:
                    print(f"chicken {id} moved")

                if not current_state[id]:
                    elapsed_time = current_time - self.movement_timer[id]
                    if elapsed_time.total_seconds() > self.MOVEMENT_TIME_WINDOW:
                        # Reset the counter if the time window has passed
                        self.movement_counter[id] = 0
                        self.movement_timer[id] = current_time
                    else:
                        self.movement_counter[id] += 1

                        # increment the sleep or drink and decrement the previously detected action in this time range
                        if self.movement_counter[id] >= self.MOVEMENT_THRESHOLD:
                            # calculate how many count should be added for the passed time
                            frame_num = 20  # per second
                            processing_speed = 0.05  # second for 1 frame
                            frame_skipped = 1
                            total_frame = frame_num * self.MOVEMENT_THRESHOLD
                            accumulated_action_count = total_frame * processing_speed / frame_skipped

                            # Update the action counts in the database
                            dbController.update_action_by_value(id, accumulated_action_count-1, action)

                            # Fetch all actions from the database within the time range except for inactivity
                            start_time = self.movement_timer[id]
                            end_time = current_time
                            recorded_action = dbController.get_action_log(id, start_time, end_time, action)
                            if recorded_action is not None:
                                inactive_count = recorded_action.count("inactivity")
                                drinking_count = recorded_action.count("drinking")
                                eating_count = recorded_action.count("eating")

                                dbController.decrement_action_by_value(id, inactive_count, "inactivity")
                                dbController.decrement_action_by_value(id, drinking_count, "drinking")
                                dbController.decrement_action_by_value(id, eating_count, "eating")

                # Check if the movement counter exceeds the threshold
                if self.movement_counter[id] >= self.MOVEMENT_THRESHOLD:
                    # If previously detected as inactive, reset and start eating or drinking detection again
                    if not current_state[id]:
                        current_state[id] = True

                    # Chicken is still eating or drinking
                    dbController.update_action(action, id)
                    current_timer[id] = current_time

                    # Set as not inactive
                    self.inactive_state[id] = False
                    # Reset the resting timer to the current time
                    self.inactive_timer[id] = current_time

                    return True
            else:
                if current_state[id]:
                    elapsed_time = current_time - current_timer[id]

                    # If previously detected as eating or drinking, but has stopped moving for an extended period of time
                    if elapsed_time.total_seconds() >= inactivity_threshold:
                        # Calculate the time range for which to fetch actions from the database
                        start_time = current_time - timedelta(seconds=inactivity_threshold)
                        end_time = current_time

                        # Fetch all actions from the database within the time range except for inactivity
                        recorded_action = dbController.get_action_log(id, start_time, end_time, "inactivity")
                        if recorded_action is not None:
                            inactive_count = recorded_action.count("inactivity")
                            drinking_count = recorded_action.count("drinking")

                            dbController.decrement_action_by_value(id, inactive_count, "inactivity")
                            dbController.decrement_action_by_value(id, drinking_count, "drinking")

                        # calculate how many count should be added for the passed time
                        frame_num = 20  # per second
                        processing_speed = 0.05  # second for 1 frame
                        frame_skipped = 1
                        total_frame = frame_num * inactivity_threshold
                        accumulated_action_count = total_frame * processing_speed / frame_skipped

                        # Update the action counts in the database
                        dbController.update_action_by_value(id, accumulated_action_count, action)

                        # Detected as inactive
                        current_state[id] = False
                        current_timer[id] = None

                        # detect the inactivity
                        self.inactive_state[id] = True
                        self.detect_inactivity(dbController, id, is_moving)
                        return False
                    else:
                        # Chicken is still eating
                        dbController.update_action(action, id)
                        current_timer[id] = current_time

                        # Set as not inactive
                        self.inactive_state[id] = False
                        # Reset the resting timer to the current time
                        self.inactive_timer[id] = current_time
                        return True
        return False

    def detect_inactivity(self, dbController, id, is_moving):
        current_time = datetime.now()

        if is_moving:
            self.inactive_state[id] = False
            # reset timer
            self.inactive_timer[id] = current_time

            return False

        if self.inactive_state[id]:  # Chicken is currently inactive
            print("Chicken ", id, " is inactive")
            # Increment the resting action count
            dbController.update_action("inactivity", id)
            # Reset the resting timer to the current time
            self.inactive_timer[id] = current_time

            return True
        else:
            resting_time = current_time - self.inactive_timer[id]

            # Check if chicken is beginning its inactivity
            if resting_time.total_seconds() >= self.INACTIVITY_THRESHOLD:
                # Calculate the time range for which to fetch actions from the database
                start_time = current_time - timedelta(seconds=self.INACTIVITY_THRESHOLD)
                end_time = current_time

                # Fetch all actions from the database within the time range except for inactivity
                recorded_action = dbController.get_action_log(id, start_time, end_time, "inactivity")
                if recorded_action is not None:
                    eating_count = recorded_action.count("eating")
                    drinking_count = recorded_action.count("drinking")
                    dbController.decrement_action_by_value(id, eating_count, "eating")
                    dbController.decrement_action_by_value(id, drinking_count, "drinking")

                # calculate how many count should be added for the passed time
                frame_num = 20  # per second
                processing_speed = 0.05  # second for 1 frame
                frame_skipped = 1
                total_frame = frame_num * self.INACTIVITY_THRESHOLD
                accumulated_action_count = total_frame * processing_speed / frame_skipped

                # Update the action counts in the database
                dbController.update_action_by_value(id, accumulated_action_count, "inactivity")

                self.inactive_state[id] = True
                # Update the resting timer
                self.inactive_timer[id] = current_time
                return True
            return False

    def is_inside_feeder_or_drinker_bbox(self, id, x, y, w, h):
        bbox_detected = None
        feeder_x, feeder_y, feeder_w, feeder_h = self.bbox.feeder_bbox
        drinker1_x, drinker1_y, drinker1_w, drinker1_h = self.bbox.drinker1_bbox
        drinker2_x, drinker2_y, drinker2_w, drinker2_h = self.bbox.drinker2_bbox

        # Calculate the half-width and half-height of the chicken bounding box
        chicken_half_width = w / 2
        chicken_half_height = h / 2

        # Calculate the coordinates of the chicken bounding box's corners
        chicken_x1 = x - chicken_half_width
        chicken_y1 = y - chicken_half_height
        chicken_x2 = x + chicken_half_width
        chicken_y2 = y + chicken_half_height

        # Create a shapely geometry for the chicken bounding box
        chicken_bbox = box(chicken_x1, chicken_y1, chicken_x2, chicken_y2)

        # Calculate the coordinates of the feeder bounding box's corners
        feeder_x1 = feeder_x - feeder_w / 2
        feeder_y1 = feeder_y - feeder_h / 2
        feeder_x2 = feeder_x + feeder_w / 2
        feeder_y2 = feeder_y + feeder_h / 2

        # Calculate the coordinates of the drinker 1 bounding box's corners
        drinker1_x1 = drinker1_x - drinker1_w / 2
        drinker1_y1 = drinker1_y - drinker1_h / 2
        drinker1_x2 = drinker1_x + drinker1_w / 2
        drinker1_y2 = drinker1_y + drinker1_h / 2

        # Calculate the coordinates of the drinker 2 bounding box's corners
        drinker2_x1 = drinker2_x - drinker2_w / 2
        drinker2_y1 = drinker2_y - drinker2_h / 2
        drinker2_x2 = drinker2_x + drinker2_w / 2
        drinker2_y2 = drinker2_y + drinker2_h / 2

        # Create a shapely geometry for the feeder and drinker bounding box
        feeder_bbox = box(feeder_x1, feeder_y1, feeder_x2, feeder_y2)
        drinker1_bbox = box(drinker1_x1, drinker1_y1, drinker1_x2, drinker1_y2)
        drinker2_bbox = box(drinker2_x1, drinker2_y1, drinker2_x2, drinker2_y2)

        # Calculate the intersection area
        intersection_area = chicken_bbox.intersection(feeder_bbox).area
        if intersection_area == 0:
            intersection_area = chicken_bbox.intersection(drinker1_bbox).area
            if intersection_area == 0:
                intersection_area = chicken_bbox.intersection(drinker2_bbox).area
                if intersection_area == 0:
                    pass
                else:
                    bbox_detected = "drinker2"
            else:
                bbox_detected = "drinker1"
        else:
            bbox_detected = "feeder"

        if bbox_detected is not None:
            # Check if the chicken and feeder or drinker bounding boxes intersect
            if intersection_area > self.INSIDE_FEEDER_THRESHOLD:
                print(feeder_x1, " ", feeder_y1, " ", feeder_x2, " ", feeder_y2)
                print(x - w / 2, " ", y - h / 2, " ", x + w / 2, " ", y + h / 2)
                return True, bbox_detected
        return False, bbox_detected

        # todo - a method to get the fps and convert the threshold to follow the fps like ratio
    def is_moving(self, dbController, id, x, y, w, h):
        print("the track id for moving\n", id, " ", config.prevPosTable)
        prev_x = dbController.get_x(id, config.prevPosTable)
        prev_y = dbController.get_y(id, config.prevPosTable)

        if prev_x or prev_y is None:
            dbController.update_prev_pos(id, x, y, w, h)

        move_a_bit = False
        move_a_lot = False

        if id == 10:
            print("chicken 10 moving difference ", abs(x - prev_x), " ", abs(y - prev_y))

        # check if chicken moved or not
        if abs(x - prev_x) > self.MOVING_THRESHOLD or abs(y - prev_y) > self.MOVING_THRESHOLD:
            dbController.update_prev_pos(id, x, y, w, h)
            move_a_bit = True

        # check if chicken move a lot
        if abs(x - prev_x) > self.MOVING_THRESHOLD + 9 or abs(y - prev_y) > self.MOVING_THRESHOLD + 9:
            move_a_lot = True

        return move_a_bit, move_a_lot

    def decrement_action(self, dbController, id):
        actionLogged = dbController.get_log(id)
        # loop until there is no action anymore in log
        if actionLogged is not None:
            print(f"Action from chicken id {id} is being decremented")
            dbController.decrement_action(id, actionLogged)
