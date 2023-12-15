from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional


class Tracker:
    def __init__(self, model, dbController):
        self.tracker = "bytetrack.yaml"
        self.results = None
        self.model = model
        self.dbController = dbController

        # Store the track history
        self.track_history = defaultdict(lambda: [])

        # Store the last seen timestamp for each track ID
        self.last_seen_timestamp: Dict[int, Optional[datetime]] = defaultdict(lambda: None)

        # Create a dictionary to store the positions of newly appeared track IDs
        self.new_track_positions = defaultdict(lambda: [])

        self.DISTANCE_THRESHOLD = 1000 # in pixel
        # Use a timedelta for MAX_DISAPPEAR_TIME
        self.MAX_DISAPPEAR_TIME = timedelta(seconds=10)

        # Get the class mapping from your YOLO model (assuming it provides a class_map attribute)
        self.class_mapping = self.model.names

    def get_results(self, frame):
        # Run YOLOv8 tracking on the frame, persisting tracks between frames
        self.results = self.model.track(frame, persist=True, tracker=self.tracker)
        return self.results

    def get_track_history(self, track_id):
        return self.track_history[track_id]

    def plot_track(self, x, y, track_id):
        track = self.track_history[track_id]
        track.append((float(x), float(y)))  # x, y center point
        if len(track) > 30:  # retain 30 points for 30 frames
            track.pop(0)

    def check_missing_track_ids(self):
        # Get a list of all existing track IDs from your database
        existing_track_ids = self.dbController.get_chicken_track_id()
        print("Existing track IDs:", existing_track_ids)

        # Check if self.results is None or empty
        if self.results is not None:
            # Get a list of current frame track id
            current_frame_track_ids = self.results[0].boxes.id.int().cpu().tolist()

            # Iterate through existing track IDs and check if they are present in the current frame
            for track_id in existing_track_ids:
                if track_id not in current_frame_track_ids:
                    self.dbController.update_id_status(track_id, False)
                else:
                    self.dbController.update_id_status(track_id, True)
        else:
            print("No results available in self.results.")

    def maintain_id(self, dbController, track_id, x, y, w, h, class_name, confidence):
        # Check if this is the first time encountering the track ID
        if self.last_seen_timestamp[track_id] is None:
            self.last_seen_timestamp[track_id] = datetime.now()

        # Check if there's an available ID (with a value of 0) in the database
        available_id = dbController.get_available_id()
        if available_id is not None:
            # check if the track id have been previously linked with an id or not
            previous_id = dbController.get_previous_id(track_id)
            if previous_id is None:
                # Insert the  track ID into the log
                dbController.insert_track_id_to_log(track_id, available_id, datetime.now())
                self.last_seen_timestamp[track_id] = datetime.now()

                # Linked the track id to the available id
                dbController.update_track_id(track_id, available_id)
                dbController.update_chicken_data(track_id, True, datetime.now(), x, y, w, h, class_name, confidence)
                print(f"Assigned track_id {track_id} to ID {available_id}.")
        else:
            # When all id have been linked to a track id
            # check if the track id have been missing for longer than the threshold
            if dbController.get_all_track_ids_from_log() is not None:
                for db_track_id in dbController.get_all_track_ids_from_log():
                    if dbController.get_assigned_time(db_track_id) is not None:
                        time_difference = datetime.now() - dbController.get_assigned_time(db_track_id)
                        if time_difference > self.MAX_DISAPPEAR_TIME:
                            # the time it missing is longer than the threshold
                            # remove the track id from the list and from the log
                            self.last_seen_timestamp[db_track_id] = None
                            dbController.remove_track_id_from_log(db_track_id)

            # it is within range
            # check if the track id have been previously linked with an id or not
            previous_id = dbController.get_previous_id(track_id)
            if previous_id is not None:
                print(f"the {previous_id} id active status is ", dbController.get_chicken_status(previous_id))
                # check if have just been recently update
                if datetime.now() - dbController.get_updated_time(previous_id) > timedelta(seconds=1):
                    print(f"there is a no new id for id {track_id} and it previous id is {previous_id}")
                    # if the track id reappear, reassign it back to it assigned id
                    # Linked the track id to the available id
                    dbController.update_track_id(track_id, previous_id)
                    dbController.update_chicken_data(track_id, True, datetime.now(), x, y, w, h, class_name, confidence)

                    # update the last seen timestamp and log
                    self.dbController.update_track_id_log_time(track_id, previous_id, datetime.now())
                    self.last_seen_timestamp[track_id] = datetime.now()
            else:
                print(f"there is a newly appeared id {track_id}")
                # a new id have appeared and it is not linked with any id
                # get for inactive ids
                inactive_ids = dbController.get_inactive_chicken_ids()
                print(inactive_ids)
                track_ids_in_log = dbController.get_all_track_ids_from_log()
                print(track_ids_in_log)
                counter = 0
                if track_ids_in_log is not None:
                    for new_track_id in self.results[0].boxes.id.int().cpu().tolist():
                        if new_track_id not in track_ids_in_log:
                            print(new_track_id, " is new")
                            counter += 1
                print(counter)
                # if there is only 1 new id appeared and only 1 inactive id
                if counter == 1 and len(inactive_ids) == 1:
                    print(f"only 1 newly appeared id and only 1 inactive id")
                    inactive_id = inactive_ids[0]
                    # make sure it is not too far from each other
                    if self.calculate_distance((x, y), dbController.get_last_appear_position(inactive_id)) < self.DISTANCE_THRESHOLD:
                        dbController.update_track_id(track_id, inactive_id)
                        dbController.update_chicken_data(track_id, True, datetime.now(), x, y, w, h, class_name, confidence)

                        # update the last seen timestamp and insert the id into the log
                        print(f"the only track id is {track_id} and the inactive track id is {inactive_id}")
                        dbController.insert_track_id_to_log(track_id, inactive_id, datetime.now())
                        self.last_seen_timestamp[track_id] = datetime.now()
                        print(f"Object with track_id {track_id} assigned to missing ID {inactive_id}.")
                # if have 1 newly appeared id and more than 1 inactive id
                elif counter == 1 and len(inactive_ids) > 1:
                    print(f"the newly found track id is {track_id}")
                    # Initialize variables to keep track of the closest inactive ID and its distance
                    closest_inactive_id = None
                    closest_distance = float('inf')  # Initialize with a large value

                    # Get the position of the newly appeared ID
                    new_track_position = (x, y)

                    for inactive_id in inactive_ids:
                        # Get the last known position of the inactive ID
                        inactive_position = dbController.get_last_appear_position(inactive_id)

                        if inactive_position is not None:
                            # Calculate the distance between the newly appeared ID and the inactive ID
                            distance = self.calculate_distance(new_track_position[:2], inactive_position[:2])

                            # Check if this distance is the closest so far
                            if distance < closest_distance:
                                closest_distance = distance
                                closest_inactive_id = inactive_id

                    if closest_inactive_id is not None:
                        print(f"closest distance is {closest_distance} and Threshold is {self.DISTANCE_THRESHOLD}")
                        # make sure it is not too far from each other
                        if closest_distance < self.DISTANCE_THRESHOLD:
                            # Assign the newly appeared ID to the closest inactive ID
                            dbController.update_track_id(track_id, closest_inactive_id)
                            dbController.update_chicken_data(track_id, True, datetime.now(), x, y, w, h, class_name,
                                                                  confidence)

                            # Update the last seen timestamp and insert the ID into the log
                            dbController.insert_track_id_to_log(track_id, closest_inactive_id, datetime.now())
                            self.last_seen_timestamp[track_id] = datetime.now()

                            print(f"New track ID {track_id} assigned to the closest inactive ID {closest_inactive_id}.")
                # if have more than 1 newly appeared id and more than or equal 1 inactive id
                elif counter > 1 and len(inactive_ids) >= 1:
                    print(f"more than 1 newly appeared id and more than 1 inactive id")
                    # the nearest track id will be assigned with the inactive id
                    # Get the boxes, track IDs, class names, and confidences
                    boxes = self.results[0].boxes.xywh.cpu()
                    track_ids = self.results[0].boxes.id.int().cpu().tolist()
                    class_ids = self.results[0].boxes.cls.int().cpu().tolist()
                    confidences = self.results[0].boxes.conf.cpu()

                    for db_box, db_track_id, db_class_id, db_confidence in zip(boxes, track_ids, class_ids, confidences):
                        # Get the class name from the class mapping
                        db_class_name = self.class_mapping[db_class_id]

                        print(f"track id in logs are {track_ids_in_log}")
                        if db_track_id not in track_ids_in_log:
                            print(f"{db_track_id} is not in log")
                            db_x, db_y, db_w, db_h = db_box

                            # Store the position of the new track ID in the dictionary
                            self.new_track_positions[db_track_id].append((db_x, db_y, db_w, db_h, db_confidence, db_class_name))

                    # Iterate through the inactive IDs
                    for inactive_id in inactive_ids:
                        inactive_position = dbController.get_last_appear_position(inactive_id)

                        if inactive_position is not None:
                            # Calculate the distance between the inactive ID and all new track IDs
                            distances = {new_track_id: min(self.calculate_distance(new_position[:2], inactive_position[:2]) for new_position in new_positions) for new_track_id, new_positions in self.new_track_positions.items()}

                            # Find the new track ID with the minimum distance
                            closest_new_track_id = min(distances, key=distances.get)

                            # Get the closest distance
                            closest_distance = distances[closest_new_track_id]

                            # make sure it is not too far from each other
                            if closest_distance < self.DISTANCE_THRESHOLD:
                                # Assign the inactive ID to the closest new track ID
                                dbController.update_track_id(closest_new_track_id, inactive_id)

                                # Iterate through the dictionary and find items for the specific track_id
                                x_values = None
                                y_values = None
                                w_values = None
                                h_values = None
                                confidence_values = None
                                class_name_values = None

                                if closest_new_track_id in self.new_track_positions:
                                    positions = self.new_track_positions[closest_new_track_id]

                                    # Iterate through the positions for the specific track_id
                                    for position in positions:
                                        x, y, w, h, confidence, class_name = position
                                        x_values = x
                                        y_values = y
                                        w_values = w
                                        h_values = h
                                        confidence_values = confidence
                                        class_name_values = class_name
                                        break

                                print(f"closest track id is {closest_new_track_id} and the inactive track id is {inactive_id}")
                                dbController.update_chicken_data(closest_new_track_id, True, datetime.now(), x_values, y_values, w_values, h_values, class_name_values, confidence_values)
                                # update the last seen timestamp and insert the id into the log
                                dbController.insert_track_id_to_log(closest_new_track_id, inactive_id, datetime.now())
                                self.last_seen_timestamp[closest_new_track_id] = datetime.now()
                                print(f"Inactive ID {inactive_id} assigned to new track ID {closest_new_track_id}")
                                break
                    self.new_track_positions.clear()

    def calculate_distance(self, point1, point2):
        # Check if both point1 and point2 are not None
        if point1 is not None and point2 is not None:
            # Calculate the Euclidean distance between two points
            x1, y1 = point1
            x2, y2 = point2
            return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
        else:
            # Handle the case where either point1 or point2 is None
            return float("inf")
