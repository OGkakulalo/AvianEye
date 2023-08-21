import pandas as pd
import matplotlib.pyplot as plt
import plotly.io as pio
import plotly.graph_objects as go
from adtk.data import validate_series
from adtk.detector import MinClusterDetector
from sklearn.cluster import KMeans

import config
import json

class AnomalyDetection:
    def detect_anomaly(self):
        fig_html_list = []

        for row in config.dbController.get_chicken_id():
            track_id = row[0]
            result = config.dbController.get_analysis_data(track_id, config.analysisTable)

            data = pd.DataFrame(result, columns=["time", "moving", "resting", "eating", "drinking", "etc"])
            data.set_index("time", inplace=True)
            data = validate_series(data)

            min_cluster_detector = MinClusterDetector(KMeans(n_clusters=3))
            anomalies = min_cluster_detector.fit_detect(data)

            # Create traces for different behaviors
            traces = []
            behaviors = ["moving", "resting", "eating", "drinking", "etc"]
            for behavior in behaviors:
                trace = go.Scatter(x=data.index, y=data[behavior], mode='lines', name=behavior.capitalize())
                traces.append(trace)

            # Create a vertical line for each detected anomaly
            anomaly_shapes = []
            for anomaly_time, is_anomaly in anomalies.items():
                if is_anomaly:
                    shape = dict(type='line', x0=anomaly_time, x1=anomaly_time, y0=0, y1=1,
                                 xref='x', yref='paper', line=dict(color='red', dash='dash'))
                    anomaly_shapes.append(shape)



            # Create a layout for the figure
            layout = go.Layout(
                plot_bgcolor='#c47c4e',  # Change the background color of the entire graph
                paper_bgcolor='#291b19',  # Change the background color of the plot area
                font=dict(
                    color='#FFFFFF'  # Font color (white)
                ),
                title=f"Anomaly Detection for Chicken ID {track_id}",
                xaxis=dict(title='Time'),
                yaxis=dict(title='Behavior'),
                shapes=anomaly_shapes
            )

            # Create a figure using the traces and layout
            fig = go.Figure(data=traces, layout=layout)
            # Add invisible trace for "Anomaly" label to show in legend
            fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', name="Anomaly",
                                     line=dict(color='red', dash='dash')))

            # Serialize the Plotly figure to HTML
            fig_html = pio.to_html(fig, full_html=False)
            print("it is here\n", fig_html)
            fig_html_list.append(fig_html)

        return fig_html_list

    def show_graph(self):
        # plt.show()
        return None

    def save_plot_to_image(self, chicken_id):
        image_filename = f"plot_chicken_{chicken_id}.png"  # Unique filename with chicken ID
        plt.savefig(image_filename)
        plt.close()  # Close the plot to release resources
        return image_filename
