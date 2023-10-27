from datetime import datetime

import config

class chickenAnalysis:
    def __init__(self, dbController):
        self.ANALYSIS_UPDATE_THRESHOLD = 30 * config.speed_ratio  # second
        self.ANALYSIS_THRESHOLD = 10  # how many times update before inserting new row
        self.analysis_updated = 0
        self.prev_timestamp = 0
        self.prev_start = True
        self.dbController = dbController

    def update_threshold(self):
        self.ANALYSIS_UPDATE_THRESHOLD = 30 * config.speed_ratio  # second

    def update_analysis(self):
        current_time = datetime.now()
        if self.prev_start:
            self.prev_timestamp = current_time
            self.prev_start = False

        print("time difference: ", current_time - self.prev_timestamp, "    ", self.ANALYSIS_UPDATE_THRESHOLD)
        elapse_time = current_time - self.prev_timestamp

        # update each id action based on the highest action value, update it every few minutes
        if elapse_time.total_seconds() > self.ANALYSIS_UPDATE_THRESHOLD:
            self.dbController.update_analysis()
            self.prev_start = True
            self.analysis_updated += 1

        # insert new row and update on the new row, while old row become record for anomaly detection
        if self.analysis_updated > self.ANALYSIS_THRESHOLD:
            self.dbController.insert_analysis()
            self.dbController.update_analysis()
            self.analysis_updated = 1

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