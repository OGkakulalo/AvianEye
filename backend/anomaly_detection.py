import os
from email.mime.image import MIMEImage

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from hmmlearn.hmm import GaussianHMM
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config


class anomalyDetector:
    def __init__(self, dbController):
        self.dbController = dbController

        # Define the minimum consecutive anomaly duration
        self.MIN_CONSECUTIVE_ANOMALIES = 6  # 1 data point every 5 minutes

        # chicken threshold for possibility of being sick
        self.LOW_POSSIBILITY = 3600  # second
        self.HIGH_POSSIBILITY = 7200  # second

        # threshold for how long anomaly data to not be detected before resetting
        self.RESET_ANOMALIES_DURATION_THRESHOLD = 1800  # second
        self.MAHALANOBIS_DIST_DIFF_THRESHOLD = 0.2

        self.consecutive_record = []
        self.anomalies = []
        self.consecutive_count = -1
        self.still_continuing = False
        self.start_end_time_list = []
        self.add_counter = 0
        self.total_anomalies_duration = 0
        self.prev_end_time = None

    def detect_anomaly(self, id):
        try:
            # Fetch data for the current chicken ID
            result = self.dbController.get_analysis_data(id)

            if not result:
                return None

            # Create a DataFrame from the fetched data
            data = pd.DataFrame(result, columns=["time", "inactivity", "eating", "drinking"])
            data.set_index("time", inplace=True)

            # Prepare the multivariate data for HMM
            multivariate_data = data[["inactivity", "eating", "drinking"]].values

            # Standardize the data (important for HMM)
            scaler = StandardScaler()
            multivariate_data = scaler.fit_transform(multivariate_data)

            # Define the number of hidden states (you can adjust this based on your data)
            n_components = 3

            # Set a default random seed for reproducibility
            np.random.seed(42)

            # Create a Gaussian HMM
            model = GaussianHMM(n_components=n_components, covariance_type="full")

            # Fit the model to the data
            model.fit(multivariate_data)

            # Predict the most likely sequence of hidden states for the data
            hidden_states = model.predict(multivariate_data)

            # Detect anomalies based on Mahalanobis distance from the means
            mahalanobis_dist = np.array(
                [np.linalg.norm(obs - model.means_[state]) for obs, state in zip(multivariate_data, hidden_states)])

            # Detect anomalies based current point and previous point
            self.anomalies = []

            for i in range(len(mahalanobis_dist)):
                if abs(mahalanobis_dist[i - 1] - mahalanobis_dist[i]) < self.MAHALANOBIS_DIST_DIFF_THRESHOLD:
                    self.anomalies.append(True)
                else:
                    self.anomalies.append(False)

            # Apply a minimum consecutive anomaly duration threshold
            self.consecutive_count = -1
            self.consecutive_record = []
            self.still_continuing = False
            self.start_end_time_list = []
            self.add_counter = 0
            self.total_anomalies_duration = 0
            self.prev_end_time = None

            for i in range(len(self.anomalies)):
                if self.anomalies[i]:
                    self.consecutive_count += 1
                    self.consecutive_record.append(i)

                    # Check if the consecutive threshold is reached
                    if self.consecutive_count >= self.MIN_CONSECUTIVE_ANOMALIES:
                        if not self.still_continuing:
                            self.still_continuing = True
                            time_started = data.index[i - self.consecutive_count]  # Time when it started

                        # check if it is the last data and update if it is
                        if self.still_continuing and i == len(self.anomalies) - 1:
                            self.fill_prev(data, i, time_started)
                    else:
                        self.anomalies[i] = False

                else:
                    if not self.still_continuing:
                        self.consecutive_count = 0
                        self.consecutive_record.clear()

                    if self.still_continuing:
                        self.fill_prev(data, i, time_started)

            # Define a list of colors for different anomaly durations
            anomaly_colors = []
            for start_time, end_time in self.start_end_time_list:
                duration = (end_time - start_time).total_seconds()

                if self.LOW_POSSIBILITY < duration < self.HIGH_POSSIBILITY:
                    anomaly_colors.append("yellow")
                    config.bbox_color[id] = config.yellow_color
                    print(f"anomaly detected medium possibility for {id}")
                elif duration > self.HIGH_POSSIBILITY:
                    anomaly_colors.append("red")
                    config.bbox_color[id] = config.red_color
                    print(f"anomaly detected high for {id}")
                else:
                    anomaly_colors.append("green")
                    config.bbox_color[id] = config.green_color
                    print(f"anomaly detected low possibility for {id}")

            return data, result, anomaly_colors, self.start_end_time_list, mahalanobis_dist
        except Exception as e:
            print(f"Error while detecting anomalies: {e}")
            return None

    def fill_prev(self, data, i, time_started):
        for j in self.consecutive_record:
            self.anomalies[j - 1] = True

        self.consecutive_count = 0
        self.consecutive_record.clear()
        self.still_continuing = False

        time_ended = data.index[i]  # Time when it ended

        # get the start time and end time of the anomaly and calculate the total
        if self.prev_end_time is not None:
            elapse_time = (time_started - self.prev_end_time).total_seconds()

        # add the total duration to a list if it passed the threshold and start a new total duration
        if self.prev_end_time is not None and elapse_time < self.RESET_ANOMALIES_DURATION_THRESHOLD:
            self.total_anomalies_duration += (time_ended - time_started).total_seconds()
            self.start_end_time_list[self.add_counter - 1][1] = time_ended
        else:
            self.total_anomalies_duration = (time_ended - time_started).total_seconds()
            self.start_end_time_list.append([time_started, time_ended])
            self.add_counter += 1
        self.prev_end_time = time_ended

    def send_alert(self, id, graph_path):
        # Email configuration
        sender_email = "chengteo123@gmail.com"
        receiver_email = "chenglickliang@gmail.com"  # Replace with the recipient's email address
        password = "krbf ssik hkxi mnzu"  # Replace with your Gmail password

        # Create a message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = f"Chicken with id {id} is sick"

        # Attach the image as an attachment
        img_data = open(graph_path, 'rb').read()
        image = MIMEImage(img_data, name=os.path.basename(graph_path))
        message.attach(image)

        # Connect to Gmail's SMTP server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()

        # Login to your Gmail account
        server.login(sender_email, password)

        # Send the email
        server.sendmail(sender_email, receiver_email, message.as_string())

        print("successfully sent")
        # Close the SMTP server
        server.quit()
