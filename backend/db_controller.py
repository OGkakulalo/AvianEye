import datetime
import random
import config
import mysql.connector


class DbController:
    def __init__(self):
        self.host = "localhost"
        self.user = "root"
        self.password = ""
        self.port = "3306"
        self.database = "fyp"
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                database=self.database
            )
            print("Connected to the database.")
        except mysql.connector.Error as error:
            print(f"Failed to connect to the database: {error}")

    def close(self):
        if self.connection:
            self.connection.close()

    def execute_query(self, query, values=None, have_result=False):
        cursor = self.connection.cursor(buffered=True)
        try:
            if values:
                cursor.execute(query, values)
            else:
                cursor.execute(query)
            self.connection.commit()

            if have_result:
                return cursor.fetchall()  # Return the fetched result directly
        except mysql.connector.Error as error:
            print("test")
            print(f"Error executing query: {error}")
            if have_result:
                return []
        finally:
            cursor.close()

    def insert_pos(self, track_id, x1, y1, x2, y2, table):
        query = f"INSERT INTO {table} (id, x1, y1, x2, y2) VALUES (%s, %s, %s, %s, %s)"
        values = (
            track_id,
            x1, y1, x2, y2
        )
        self.execute_query(query, values)

    def insert_action(self, track_id):
        query = f"INSERT INTO {config.actionTable} (id, moving, resting, eating, drinking, etc) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (
            track_id,
            0, 0, 0, 0, 0
        )
        self.execute_query(query, values)

    def insert_analysis(self, track_id):
        query = f"INSERT INTO {config.analysisTable} (id, time, moving, resting, eating, drinking, etc) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        values = (
            track_id,
            datetime.datetime.now(),
            0, 0, 0, 0, 0
        )
        self.execute_query(query, values)

    def update_current_pos(self, track_id, x1, y1, x2, y2):
        query = f"UPDATE {config.currentPosTable} SET x1 = %s, y1 = %s, x2 = %s, y2 = %s WHERE id = %s"
        values = (x1, y1, x2, y2, track_id)
        self.execute_query(query, values)
        print("current position update successfully")

    def update_prev_pos(self, track_id, x1, y1, x2, y2):
        query = f"UPDATE {config.prevPosTable} SET x1 = %s, y1 = %s, x2 = %s, y2 = %s WHERE id = %s"
        values = (x1, y1, x2, y2, track_id)
        self.execute_query(query, values)

    def update_action(self, action, track_id):
        updates = action + " = " + action + " + 1"
        condition = "id = " + str(track_id)
        query = f"UPDATE {config.actionTable} SET {updates} WHERE {condition}"
        self.execute_query(query)

    def get_data(self, track_id, table):
        query = f"SELECT * FROM {table} WHERE id = {track_id}"
        result = self.execute_query(query, have_result=True)
        return result

    def check_chicken_id(self, track_id):
        query = f"SELECT id FROM chicken_list WHERE track_id = {track_id}"
        result = self.execute_query(query, have_result=True)
        if result:
            return result[0][0]
        else:
            return None

    def get_x1(self, track_id, table):
        data = self.get_data(track_id, table)
        if data:
            position_x = data[0][1]  # Assuming position_x is stored in the second column
            return position_x
        else:
            return None

    def get_y1(self, track_id, table):
        data = self.get_data(track_id, table)
        if data:
            position_y = data[0][2]  # Assuming position_y is stored in the third column
            return position_y
        else:
            return None

    def get_x2(self, track_id, table):
        data = self.get_data(track_id, table)
        if data:
            position_x = data[0][3]  # Assuming position_x is stored in the second column
            return position_x
        else:
            return None

    def get_y2(self, track_id, table):
        data = self.get_data(track_id, table)
        if data:
            position_y = data[0][4]  # Assuming position_y is stored in the third column
            return position_y
        else:
            return None

    def insert_log(self, track_id, action):
        query = f"INSERT INTO {config.chickenActionLog} (id, action, timestamp) VALUES (%s, %s, %s)"
        values = (
            track_id,
            action,
            datetime.datetime.now()
        )
        self.execute_query(query, values)

    def get_log(self, track_id):
        query = f"SELECT action FROM {config.chickenActionLog} WHERE id = {track_id} ORDER BY timestamp DESC LIMIT 1"
        data = self.execute_query(query, have_result=True)
        if data:
            return data[0][0]
        else:
            return None

    def decrement_action(self, track_id, action):
        updates = action + " = " + action + " - 1"
        condition = "id = " + str(track_id)
        query = f"UPDATE {config.actionTable} SET {updates} WHERE {condition}"
        self.execute_query(query)

        query = f"DELETE FROM {config.chickenActionLog} WHERE id = {track_id} ORDER BY timestamp DESC LIMIT 1"
        self.execute_query(query)

    def clear_log(self):
        query = f"DELETE FROM {config.chickenActionLog}"
        self.execute_query(query)
        self.connection.commit()

    def update_analysis(self, toUpdate, toInsert):
        query = f"SELECT * FROM {config.actionTable}"
        result = self.execute_query(query, have_result=True)

        if toUpdate:
            print("Analysis is Updated")
            for row in result:
                track_id = row[0]  # Access the 'id' column using integer index
                # Find the largest action count and corresponding action
                max_action_count = max(row[
                                       2:])  # Skip the first column (id) and second column (time) and find the largest value in the remaining columns
                action_names = ['moving', 'resting', 'eating', 'drinking', 'etc']
                max_action = action_names[
                    row.index(max_action_count) - 1]  # Map the index to the corresponding action name

                updates = f"{max_action} = {max_action} + 1"
                condition = f"id = {track_id} AND time = (SELECT MAX(time) FROM {config.analysisTable} WHERE id = {track_id})"
                query = f"UPDATE {config.analysisTable} SET {updates} WHERE {condition}"
                self.execute_query(query)
        if toInsert:
            print("Analysis is Added")
            for row in result:
                track_id = row[0]  # Access the 'id' column using integer index
                self.insert_analysis(track_id)

        # Clear the chickenAction table action counts back to 0
        query = f"UPDATE {config.actionTable} SET moving = 0, resting = 0, eating = 0, drinking = 0, etc = 0"
        self.execute_query(query)

    """
    def get_chicken_id(self):
        query = f"SELECT id FROM {config.actionTable}"
        result = self.execute_query(query, have_result=True)
        return result
    """

    def get_analysis_data(self, track_id, table):
        query = f"SELECT time, moving, resting, eating, drinking, etc FROM {table} WHERE id = {track_id}"
        result = self.execute_query(query, have_result=True)
        return result

    # Insert mock data into the MySQL database
    def insert_mock_data(self):
        for track_id in range(1, 11):  # Generate data for 10 chicken IDs
            moving = random.randint(0, 10)
            resting = random.randint(0, 10)
            eating = random.randint(0, 10)
            drinking = random.randint(0, 10)
            etc = random.randint(0, 10)

            query = f"INSERT INTO {config.actionTable} (id, moving, resting, eating, drinking, etc) VALUES (%s, %s, %s, %s, %s, %s)"
            values = (track_id, moving, resting, eating, drinking, etc)
            self.execute_query(query, values)

        for i in range(1, 11):
            for track_id in range(1, 11):  # Generate data for 10 chicken IDs
                time = datetime.datetime.now() - datetime.timedelta(hours=random.randint(0, 1),
                                                                    minutes=random.randint(0, 59),
                                                                    seconds=random.randint(0, 59))
                moving = random.randint(0, 10)
                resting = random.randint(0, 10)
                eating = random.randint(0, 10)
                drinking = random.randint(0, 10)
                etc = random.randint(0, 10)

                query = f"INSERT INTO {config.analysisTable} (id, time, moving, resting, eating, drinking, etc) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                values = (track_id, time, moving, resting, eating, drinking, etc)
                self.execute_query(query, values)

    def insert_log(self, track_id, action):
        query = f"INSERT INTO {config.chickenActionLog} (id, action, timestamp) VALUES (%s, %s, %s)"
        values = (
            track_id,
            action,
            datetime.datetime.now()
        )
        self.execute_query(query, values)

    def delete_record(self, table, condition):
        query = f"DELETE FROM {table} WHERE {condition}"
        return self.execute_query(query)

    def insert_chicken_id(self):
        for i in range(1, 11):
            query = f"INSERT INTO chicken_list (id) VALUES (%s)"
            values = (i,)
            self.execute_query(query, values)

    def update_chicken_data(self, track_id, active, last_update, x, y, w, h, class_name, confidence):
        query = "UPDATE chicken_list SET active=%s, last_update=%s, x=%s, y=%s, w=%s, h=%s, class_name=%s, confidence=%s WHERE track_id=%s"
        values = (
            active,
            last_update,
            int(x), int(y), int(w), int(h),
            class_name,
            float(confidence),
            track_id
        )
        print("chicken with track id ", track_id, " update successfully")
        self.execute_query(query, values)

    def update_track_id(self, track_id, id):
        query = "UPDATE chicken_list SET track_id=%s WHERE id=%s"
        values = (
            track_id,
            id
        )
        print("chicken with track id ", track_id, " been assigned to ", id)
        self.execute_query(query, values)

    def update_id_status(self, track_id, active):
        query = "UPDATE chicken_list SET active=%s WHERE track_id=%s"
        values = (
            active,
            track_id
        )
        self.execute_query(query, values)

    def get_chicken_track_id(self):
        query = "SELECT track_id FROM chicken_list"
        result = self.execute_query(query, have_result=True)
        return [row[0] for row in result]

    def get_chicken_id(self, track_id):
        query = f"SELECT id FROM chicken_list WHERE track_id={track_id}"
        result = self.execute_query(query, have_result=True)
        return [row[0] for row in result]

    def get_all_from_chicken_list(self):
        query = f"SELECT * FROM chicken_list"
        result = self.execute_query(query, have_result=True)
        return result

    def get_active_chicken_ids(self):
        query = "SELECT track_id FROM chicken_list WHERE active = 1"
        result = self.execute_query(query, have_result=True)
        return [row[0] for row in result]

    def get_chicken_status(self, id):
        query = f"SELECT active FROM chicken_list WHERE id = {id}"
        result = self.execute_query(query, have_result=True)
        if result:
            print(result)
            # Check if the result list is not empty
            return result[0][0]
        else:
            # Handle the case where no rows were returned from the query
            return None  # or any other suitable value or error handling logic

    def get_inactive_chicken_ids(self):
        query = "SELECT id FROM chicken_list WHERE active = 0"
        result = self.execute_query(query, have_result=True)
        return [row[0] for row in result]

    def get_last_appear_position(self, track_id):
        query = f"SELECT x, y FROM chicken_list WHERE id = {track_id}"
        result = self.execute_query(query, have_result=True)
        if result:
            return result[0]
        else:
            return None

    def get_last_disappear_position(self, track_id):
        query = f"SELECT x, y FROM chicken_list WHERE id = {track_id} AND active = 0"
        result = self.execute_query(query, have_result=True)
        if result:
            return result[0]
        else:
            return None

    def get_available_id(self):
        query = f"SELECT id FROM chicken_list WHERE track_id = 0 LIMIT 1"
        result = self.execute_query(query, have_result=True)
        if result:
            return result[0][0]
        else:
            return None

    def remove_track_id_from_log(self, track_id):
        query = f"DELETE FROM track_log WHERE track_id = {track_id}"
        self.execute_query(query)

    def insert_track_id_to_log(self, track_id, id, assigned_time):
        # Check if the combination of track_id and id exists in the log table
        query = "SELECT * FROM track_log WHERE track_id=%s AND id=%s"
        values = (track_id, id)
        result = self.execute_query(query, values, True)
        if not result:
            print("inserting id to log")
            # If it doesn't exist, insert it into the log table
            query = "INSERT INTO track_log (track_id, id, assigned_time) VALUES (%s, %s, %s)"
            values = (track_id, id, assigned_time)
            print(f"the assigned time is {assigned_time}")
            self.execute_query(query, values)

    def update_track_id_log_time(self, track_id, db_id, updated_time):
        print("updating id to log")
        print(f"track id {track_id}, id {db_id}, updated time {updated_time}")
        # If it doesn't exist, insert it into the log table
        query = "UPDATE track_log SET assigned_time=%s WHERE track_id = %s AND id = %s"
        values = (updated_time, track_id, db_id)
        self.execute_query(query, values)

    def get_previous_id(self, track_id):
        query = f"SELECT id FROM track_log WHERE track_id = %s ORDER BY assigned_time ASC LIMIT 1"
        values = (track_id, )
        result = self.execute_query(query, values, have_result=True)
        if result:
            return result[0][0]
        else:
            print("No Result")
            return None

    def get_updated_time(self, id):
        query = f"SELECT last_update FROM chicken_list WHERE id = {id}"
        result = self.execute_query(query, have_result=True)
        if result:
            return result[0][0]
        else:
            return None

    def get_assigned_time(self, track_id):
        query = f"SELECT assigned_time FROM track_log WHERE track_id = {track_id}"
        result = self.execute_query(query, have_result=True)
        if result:
            return result[0][0]
        else:
            return None

    def get_all_track_ids_from_log(self):
        query = f"SELECT track_id FROM track_log"
        result = self.execute_query(query, have_result=True)
        if result:
            # Extract the first element from each tuple and create a normal list
            value = [item[0] for item in result]
            return value
        else:
            return None

    def clear_table(self):
        query = f"DELETE FROM {config.currentPosTable}"
        self.execute_query(query)
        self.connection.commit()
        query = f"DELETE FROM {config.actionTable}"
        self.execute_query(query)
        self.connection.commit()
        query = f"DELETE FROM {config.prevPosTable}"
        self.execute_query(query)
        self.connection.commit()
        query = f"DELETE FROM {config.chickenActionLog}"
        self.execute_query(query)
        self.connection.commit()
        query = f"DELETE FROM {config.analysisTable}"
        self.execute_query(query)
        self.connection.commit()
        query = f"DELETE FROM chicken_list"
        self.execute_query(query)
        self.connection.commit()
        query = f"DELETE FROM track_log"
        self.execute_query(query)
        self.connection.commit()
