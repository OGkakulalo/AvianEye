import datetime
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
        self.cursor = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                database=self.database
            )

            self.cursor = self.connection.cursor(buffered=True)
        except mysql.connector.Error as error:
            print(f"Failed to connect to the database: {error}")

    def close(self):
        if self.connection:
            self.connection.close()
            self.cursor.close()

    def execute_query(self, query, values=None):
        result = []
        try:
            # Check if the query starts with "SELECT"
            if query.strip().upper().startswith("SELECT"):
                have_result = True
            else:
                have_result = False
            
            if values:
                self.cursor.execute(query, values)
            else:
                self.cursor.execute(query)
            self.connection.commit()

            if have_result:
                result = self.cursor.fetchall()
        except mysql.connector.Error as error:
            print(f"Error executing query: {error}")
        return result

    def update_prev_pos(self, id, x, y, w, h):
        query = f"UPDATE {config.prevPosTable} SET x = %s, y = %s, w = %s, h = %s WHERE id = %s"
        values = (x, y, w, h, id)
        self.execute_query(query, values)

    def update_action(self, action, id):
        updates = action + " = " + action + " + 1"
        query = f"UPDATE {config.actionTable} SET {updates} WHERE id = {id}"
        self.execute_query(query)

    def get_x(self, id, table):
        query = f"SELECT x FROM {table} WHERE id = {id}"
        result = self.execute_query(query)
        if result:
            return result[0][0]
        else:
            return None

    def get_y(self, id, table):
        query = f"SELECT y FROM {table} WHERE id = {id}"
        result = self.execute_query(query)
        if result:
            return result[0][0]
        else:
            return None

    def insert_log(self, id, action):
        query = f"INSERT INTO {config.chickenActionLog} (id, action, timestamp) VALUES (%s, %s, %s)"
        values = (
            id,
            action,
            datetime.datetime.now()
        )
        self.execute_query(query, values)

    def get_log(self, id):
        query = f"SELECT action FROM {config.chickenActionLog} WHERE id = {id} ORDER BY timestamp DESC LIMIT 1"
        data = self.execute_query(query)
        if data:
            return data[0][0]
        else:
            return None

    def decrement_action(self, id, action):
        updates = action + " = " + action + " - 1"
        condition = "id = " + str(id)
        query = f"UPDATE {config.actionTable} SET {updates} WHERE {condition}"
        self.execute_query(query)

        # delete the action decremented from the log
        query = f"DELETE FROM {config.chickenActionLog} WHERE id = {id} ORDER BY timestamp DESC LIMIT 1"
        self.execute_query(query)

    def update_analysis(self, MIN_ACTION_COUNT):
        query = f"SELECT * FROM {config.actionTable}"
        result = self.execute_query(query)

        for row in result:
            id = row[0]
            # Find the largest action count and corresponding action
            # Skip the first column (id) and second column (time) and find the largest value in the remaining columns
            max_action_count = max(row[1:])

            # make sure that the action happen frequently enough for it to be added to analysis
            if max_action_count > MIN_ACTION_COUNT:
                action_names = ['inactivity', 'eating', 'drinking']
                max_action = action_names[row.index(max_action_count) - 1]  # Map the index to the corresponding action name

                updates = f"{max_action} = {max_action} + 1"
                condition = f"id = {id} AND time = (SELECT MAX(time) FROM {config.analysisTable} WHERE id = {id})"
                query = f"UPDATE {config.analysisTable} SET {updates} WHERE {condition}"
                self.execute_query(query)

        # Clear the chickenAction table action counts back to 0
        query = f"UPDATE {config.actionTable} SET inactivity = 0, eating = 0, drinking = 0"
        self.execute_query(query)

    def insert_analysis(self):
        for i in range(1, 11):
            query = f"INSERT INTO {config.analysisTable} (id, time) VALUES (%s, %s)"
            values = (i, datetime.datetime.now())
            self.execute_query(query, values)

    def get_analysis_data(self, id):
        query = f"SELECT time, inactivity, eating, drinking FROM {config.analysisTable} WHERE id = {id} ORDER BY time ASC"
        result = self.execute_query(query)
        return result

    def get_distinct_id(self):
        query = f"SELECT DISTINCT id FROM {config.analysisTable}"
        result = self.execute_query(query)
        return [row[0] for row in result]

    def insert_chicken_id(self):
        for i in range(1, 11):
            query = f"INSERT INTO {config.chickenList} (id) VALUES (%s)"
            values = (i,)
            self.execute_query(query, values)
            query = f"INSERT INTO {config.prevPosTable} (id) VALUES (%s)"
            values = (i,)
            self.execute_query(query, values)
            query = f"INSERT INTO {config.actionTable} (id) VALUES (%s)"
            values = (i,)
            self.execute_query(query, values)

    def update_chicken_data(self, track_id, active, last_update, x, y, w, h, class_name, confidence):
        query = f"UPDATE {config.chickenList} SET active=%s, last_update=%s, x=%s, y=%s, w=%s, h=%s, class_name=%s, confidence=%s WHERE track_id=%s"
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
        query = f"UPDATE {config.chickenList} SET track_id=%s WHERE id=%s"
        values = (
            track_id,
            id
        )
        self.execute_query(query, values)

    def update_id_status(self, track_id, active):
        query = f"UPDATE {config.chickenList} SET active=%s WHERE track_id=%s"
        values = (
            active,
            track_id
        )
        self.execute_query(query, values)

    def get_chicken_track_id(self):
        query = f"SELECT track_id FROM {config.chickenList}"
        result = self.execute_query(query)
        return [row[0] for row in result]

    def get_chicken_id(self, track_id):
        query = f"SELECT id FROM {config.chickenList} WHERE track_id={track_id}"
        result = self.execute_query(query)
        return [row[0] for row in result]

    def get_all_from_chicken_list(self):
        query = f"SELECT * FROM {config.chickenList}"
        result = self.execute_query(query)
        return result

    def get_active_chicken_ids(self):
        query = f"SELECT track_id FROM {config.chickenList} WHERE active = 1"
        result = self.execute_query(query)
        return [row[0] for row in result]

    def get_chicken_status(self, id):
        query = f"SELECT active FROM {config.chickenList} WHERE id = {id}"
        result = self.execute_query(query)
        if result:
            print(result)
            # Check if the result list is not empty
            return result[0][0]
        else:
            # Handle the case where no rows were returned from the query
            return None  # or any other suitable value or error handling logic

    def get_inactive_chicken_ids(self):
        query = f"SELECT id FROM {config.chickenList} WHERE active = 0"
        result = self.execute_query(query)
        return [row[0] for row in result]

    def get_last_appear_position(self, track_id):
        query = f"SELECT x, y FROM {config.chickenList} WHERE id = {track_id}"
        result = self.execute_query(query)
        if result:
            return result[0]
        else:
            return None

    def get_last_disappear_position(self, track_id):
        query = f"SELECT x, y FROM {config.chickenList} WHERE id = {track_id} AND active = 0"
        result = self.execute_query(query)
        if result:
            return result[0]
        else:
            return None

    def get_available_id(self):
        query = f"SELECT id FROM {config.chickenList} WHERE track_id = 0 LIMIT 1"
        result = self.execute_query(query)
        if result:
            return result[0][0]
        else:
            return None

    def remove_track_id_from_log(self, track_id):
        query = f"DELETE FROM {config.trackLog} WHERE track_id = {track_id}"
        self.execute_query(query)

    def insert_track_id_to_log(self, track_id, id, assigned_time):
        # Check if the combination of track_id and id exists in the log table
        query = f"SELECT * FROM {config.trackLog} WHERE track_id=%s AND id=%s"
        values = (track_id, id)
        result = self.execute_query(query, values)
        if not result:
            # If it doesn't exist, insert it into the log table
            query = f"INSERT INTO {config.trackLog} (track_id, id, assigned_time) VALUES (%s, %s, %s)"
            values = (track_id, id, assigned_time)
            self.execute_query(query, values)

    def update_track_id_log_time(self, track_id, db_id, updated_time):
        # If it doesn't exist, insert it into the log table
        query = f"UPDATE {config.trackLog} SET assigned_time=%s WHERE track_id = %s AND id = %s"
        values = (updated_time, track_id, db_id)
        self.execute_query(query, values)

    def get_previous_id(self, track_id):
        query = f"SELECT id FROM {config.trackLog} WHERE track_id = %s ORDER BY assigned_time ASC LIMIT 1"
        values = (track_id, )
        result = self.execute_query(query, values)
        if result:
            return result[0][0]
        else:
            print("No Result")
            return None

    def get_updated_time(self, id):
        query = f"SELECT last_update FROM {config.chickenList} WHERE id = {id}"
        result = self.execute_query(query)
        if result:
            return result[0][0]
        else:
            return None

    def get_assigned_time(self, track_id):
        query = f"SELECT assigned_time FROM {config.trackLog} WHERE track_id = {track_id}"
        result = self.execute_query(query)
        if result:
            return result[0][0]
        else:
            return None

    def get_all_track_ids_from_log(self):
        query = f"SELECT track_id FROM track_log"
        result = self.execute_query(query)
        if result:
            # Extract the first element from each tuple and create a normal list
            value = [item[0] for item in result]
            return value
        else:
            return None

    def get_action_log(self, id, start_time, end_time, action):
        # Assuming you have a database connection and a cursor set up
        # Execute a query to fetch non-inactive actions within the specified time range
        query = f"SELECT action FROM {config.chickenActionLog} WHERE id = %s AND timestamp BETWEEN %s AND %s AND action != %s"
        values = (id, start_time, end_time, action)
        results = self.execute_query(query, values)
        print("Result are ", results)
        if results:
            # Extract the actions from the query results
            recorded_action = [result[0] for result in results]
            return recorded_action
        else:
            return None

    def clear_action_log(self):
        # Calculate the number of records to delete
        query = f"""
            SELECT COUNT(*) FROM {config.chickenActionLog}
        """
        result = self.execute_query(query)

        if result:
            total_records = result[0][0]

            records_to_delete = int(total_records * 0.8)

            # Delete the top 80% of records by timestamp ASC
            query = f"""
                DELETE t1 FROM {config.chickenActionLog} t1
                JOIN (
                    SELECT timestamp
                    FROM {config.chickenActionLog}
                    ORDER BY timestamp ASC
                    LIMIT {records_to_delete}
                ) t2 ON t1.timestamp = t2.timestamp
            """
            self.execute_query(query)
        else:
            print("No records found.")

    def update_action_by_value(self, id, action_num, action):
        # Update the inactive actions count for the specified chicken ID in the database
        query = f"UPDATE {config.actionTable} SET {action} = {action} + %s WHERE id = %s"
        values = (action_num, id)

        self.execute_query(query, values)

    def decrement_action_by_value(self, id, action_num, action):
        # Update the inactive actions count for the specified chicken ID in the database
        query = f"UPDATE {config.actionTable} SET {action} = {action} - %s WHERE id = %s"
        values = (action_num, id)
        self.execute_query(query, values)

    def clear_table(self):
        query = f"DELETE FROM {config.actionTable}"
        self.execute_query(query)
        query = f"DELETE FROM {config.prevPosTable}"
        self.execute_query(query)
        query = f"DELETE FROM {config.chickenActionLog}"
        self.execute_query(query)
        query = f"DELETE FROM {config.analysisTable}"
        self.execute_query(query)
        query = f"DELETE FROM {config.chickenList}"
        self.execute_query(query)
        query = f"DELETE FROM {config.trackLog}"
        self.execute_query(query)
