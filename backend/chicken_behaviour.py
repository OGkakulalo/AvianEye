from datetime import datetime, timedelta
from shapely.geometry import box
import config
from bbox import BBox


class chickenBehaviour:
    def __init__(self, dbController):
        self.img = None
        self.bbox = BBox()
        self.dbController = dbController

        self.EATING_TO_INACTIVE_THRESHOLD = 10 * config.speed_ratio  # second
        self.DRINKING_TO_INACTIVE_THRESHOLD = 10 * config.speed_ratio  # second
        self.MOVING_THRESHOLD = 1  # pixel
        self.INACTIVITY_THRESHOLD = 20 * config.speed_ratio * config.speed_ratio  # second
        self.INSIDE_FEEDER_THRESHOLD = 50  # pixel
        self.MOVEMENT_THRESHOLD = 2  # Number of consecutive movements to detect eating or drinking
        self.MOVEMENT_TIME_WINDOW = 20 * config.speed_ratio  # second

        self.movement_counter = {i: 0 for i in range(1, config.chicken_num + 1)}
        self.movement_timer = {i: datetime.now() for i in range(1, config.chicken_num + 1)}
        self.inactive_state = {i: False for i in range(1, config.chicken_num + 1)}
        self.inactive_timer = {i: datetime.now() for i in range(1, config.chicken_num + 1)}
        self.eating_state = {i: False for i in range(1, config.chicken_num + 1)}
        self.eating_timer = {i: datetime.now() for i in range(1, config.chicken_num + 1)}
        self.drinking_state = {i: False for i in range(1, config.chicken_num + 1)}
        self.drinking_timer = {i: datetime.now() for i in range(1, config.chicken_num + 1)}

    def update_threshold(self):
        self.EATING_TO_INACTIVE_THRESHOLD = 10 * config.speed_ratio  # second
        self.DRINKING_TO_INACTIVE_THRESHOLD = 10 * config.speed_ratio  # second
        self.INACTIVITY_THRESHOLD = 20 * config.speed_ratio * config.speed_ratio  # second
        self.MOVEMENT_TIME_WINDOW = 20 * config.speed_ratio  # second

    def detect_eating_or_drinking(self, dbController, id, x, y, w, h, is_moving):
        # Check if the chicken head is inside the feeder bounding box
        print("eating or drinking is being checked for chicken ", id)
        current_time = datetime.now()
        action = None
        inactivity_threshold = None
        current_state = {}
        current_timer = {}

        is_inside_bbox, bbox_detected = self.is_inside_feeder_or_drinker_bbox(id, x, y, w, h)

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
            inactivity_threshold = self.DRINKING_TO_INACTIVE_THRESHOLD

        if is_inside_bbox:
            print("Chicken", id, f"is in the {bbox_detected}")
            print("Movement counter: ", self.movement_counter[id])
            # check if chicken is resting inside the feeder bbox or actually eating or drinking
            if is_moving:
                # movement is to detect whether the chicken is starting to drink or eat or just passing by
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
                            # Update the action counts in the database
                            dbController.update_action_by_value(id, self.count_accumulated_action(self.MOVEMENT_THRESHOLD) - 1, action)

                            # Fetch all actions from the database within the time range
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

                    self.dbController.insert_log(id, action)
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
                            drinking_count = recorded_action.count("drinking")
                            eating_count = recorded_action.count("eating")

                            dbController.decrement_action_by_value(id, drinking_count, "drinking")
                            dbController.decrement_action_by_value(id, eating_count, "eating")

                        # Update the action counts in the database
                        dbController.update_action_by_value(id, self.count_accumulated_action(inactivity_threshold), "inactivity")

                        # Detected as inactive
                        current_state[id] = False
                        current_timer[id] = None

                        # detect the inactivity
                        self.inactive_state[id] = True
                        self.detect_inactivity(dbController, id, is_moving)
                        return False
                    else:
                        # Chicken is still eating or drinking
                        dbController.update_action(action, id)

                        # Set as not inactive
                        self.inactive_state[id] = False
                        # Reset the resting timer to the current time
                        self.inactive_timer[id] = current_time

                        self.dbController.insert_log(id, action)
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

                # Update the action counts in the database
                dbController.update_action_by_value(id, self.count_accumulated_action(self.INACTIVITY_THRESHOLD), "inactivity")

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
        print("chicken current and prev position")
        print(f"{x}  {y} \n{prev_x}  {prev_y}")
        if abs(x - prev_x) > self.MOVING_THRESHOLD or abs(y - prev_y) > self.MOVING_THRESHOLD:
            dbController.update_prev_pos(id, x, y, w, h)
            print("chicken moved a bot")
            move_a_bit = True

        # check if chicken move a lot
        if abs(x - prev_x) > self.MOVING_THRESHOLD + 9 or abs(y - prev_y) > self.MOVING_THRESHOLD + 9:
            move_a_lot = True

        return move_a_bit, move_a_lot

    def count_accumulated_action(self, inactivity_threshold):
        # calculate how many count should be added for the passed time
        total_frame = config.frame_num * inactivity_threshold
        processing_speed = config.speed_ratio * config.standard_speed
        accumulated_action_count = total_frame * processing_speed / config.frame_skipped

        return accumulated_action_count
