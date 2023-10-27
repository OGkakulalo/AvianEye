import os
import matplotlib.pyplot as plt
from backend.anomaly_detection import anomalyDetector
from backend.db_controller import DbController


class graphDrawer:
    def save_graph(self, id, result, data=None, anomaly_colors=None, with_anomaly=False, start_end_time_list=None, mahalanobis_dist=None):
        try:
            # Create a figure for visualization
            plt.figure(figsize=(12, 6))

            # Separate the data into lists for plotting
            time = [record[0] for record in result]
            inactivity = [record[1] for record in result]
            eating = [record[2] for record in result]
            drinking = [record[3] for record in result]

            plt.plot(time, inactivity, label='Inactivity')
            plt.plot(time, eating, label='Eating')
            plt.plot(time, drinking, label='Drinking')

            # for user
            # Create a dictionary to map unique anomaly colors to labels
            anomaly_color_labels = {}

            if with_anomaly:
                # Plot self.anomalies with different colors based on their durations
                for i, (start_time, end_time) in enumerate(start_end_time_list):
                    color = anomaly_colors[i]
                    if color not in anomaly_color_labels:
                        # Assign a new label for this unique color
                        if color == "green":
                            anomaly_color_labels[color] = "Not sick"
                        elif color == "yellow":
                            anomaly_color_labels[color] = "Might be sick"
                        else:
                            anomaly_color_labels[color] = "Is sick"

                        # Use the color and label corresponding to the unique color
                        plt.fill_between(data.index, 0, 1,
                                         where=(data.index >= start_time) & (data.index <= end_time),
                                         color=color, alpha=0.2, label=anomaly_color_labels[color])
                    else:
                        # Use the color and label corresponding to the unique color
                        plt.fill_between(data.index, 0, 1,
                                         where=(data.index >= start_time) & (data.index <= end_time),
                                         color=color, alpha=0.2)
            # for developer to see
            """plt.plot(data.index, mahalanobis_dist, label="Mahalanobis Distance", color="blue")
            # Plot red dots at every data point
            plt.scatter(data.index, mahalanobis_dist, c='red', s=10, label='Data Points', zorder=5)

            # Plot self.anomalies with different colors based on their durations
            for i, (start_time, end_time) in enumerate(start_end_time_list):
                # Use the color from the first part, but fill only within the anomaly range
                plt.fill_between(data.index, 0, 1,
                                 where=(data.index >= start_time) & (data.index <= end_time),
                                 color=anomaly_colors[i], alpha=0.2, label="Anomalies")

            plt.title(f"Anomaly Detection for Chicken ID {id}")
            plt.xlabel("Time")
            plt.ylabel("Mahalanobis Distance")
            plt.legend()
            plt.show()"""

            # Add the legend to the plot
            # Add the legend to the plot and specify the coordinates for its position
            plt.legend(loc="upper right")  # You can try different 'loc' values
            plt.legend(loc=(0.8, 0.85))  # You can adjust these coordinates to position the legend

            # Customize the plot
            plt.title(f'Chicken Activity Analysis (ID: {id})')
            plt.xlabel('Time')
            plt.ylabel('Activity Level')
            plt.legend()
            plt.grid(True)

            # Save the plot as an image
            plt.savefig(f'./static/assets/graph/chicken_{id}.png')
            print(f"Saved graph {id} successfully")
        except Exception as e:
            print(f"Error while saving image for Chicken ID {id}: {str(e)}")

    def delete_graph(self, id):
        file_path = f'./static/assets/graph/chicken_{id}.png'
        # Check if the file exists before attempting to delete it
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted graph {id} successfully")
        else:
            print(f"File {file_path} does not exist, so it cannot be deleted.")

# for developer
if __name__ == "__main__":
    dbController = DbController()
    dbController.connect()
    ad = anomalyDetector(dbController)
    ids = dbController.get_distinct_id()
    gd = graphDrawer()

    for id in ids:
        graph = ad.detect_anomaly(id)
        if graph is not None:
            data, result, anomaly_colors, start_end_time_list, mahalanobis_dist = graph
            gd.save_graph(id, result, data, anomaly_colors, True, start_end_time_list. mahalanobis_dist)

