import cv2
import numpy as np
import config

class BBox:
    def __init__(self):
        self.frame = None

        # Set the font parameters
        self.font_scale = 0.5  # Font scale
        self.font_color = config.white_color
        self.font = cv2.FONT_HERSHEY_SIMPLEX  # Font type
        self.font_thickness = 2  # Adjust the font thickness as needed

        # Set the point size and color
        self.point_size = 4  # Point size

        # Set the line parameters
        self.line_thickness = 2
        self.line_color = config.blue_color # blue

        # Set the feeder bbox parameters
        self.feeder_bbox = [900, 250, 100, 90]
        self.feeder_border_color = config.yellow_color
        self.feeder_bg_color = config.yellow_color  # yellow

        # Set the drinker bbox parameters
        self.drinker1_bbox = [650, 190, 55, 38]
        self.drinker2_bbox = [920, 100, 60, 40]
        self.drinker_border_color = config.light_blue_color
        self.drinker_bg_color = config.light_blue_color

    def set_frame(self, frame):
        self.frame = frame

    def draw_bbox(self, x, y, w, h, border_color):
        # Draw your custom bounding box
        cv2.rectangle(self.frame, (int(x - w / 2), int(y - h / 2)), (int(x + w / 2), int(y + h / 2)), border_color, self.line_thickness)

    def draw_label(self, track_id, confidence, x, y):
        # Add custom label
        label = f"#{track_id} {confidence:.2f}"
        (label_width, label_height), _ = cv2.getTextSize(label, self.font, self.font_scale, self.line_thickness)

        # Draw the label centered just below the object's center
        cv2.putText(self.frame, label, (int(x - label_width / 2), int(y) + 20),
                    self.font, self.font_scale, config.black_color, self.font_thickness+2)
        cv2.putText(self.frame, label, (int(x - label_width / 2), int(y) + 20),
                    self.font, self.font_scale, self.font_color, self.font_thickness)

    def draw_polyline(self, track):
        # Check if 'track' is not empty before proceeding
        if len(track) > 0:
            points = np.hstack(track).astype(np.int32).reshape((-1, 1, 2))
            cv2.polylines(self.frame, [points], isClosed=False, color=self.line_color,
                          thickness=self.line_thickness)  # Polyline

    def draw_circle(self, id, x, y):
        # Draw a point at the center of the tracked object
        cv2.circle(self.frame, (int(x), int(y)), self.point_size, config.bbox_color[id], -1)  # Red dot

    def draw_chicken_bbox(self, id, confidence, x, y, w, h):
        self.draw_bbox(x, y, w, h, config.bbox_color[id])
        self.draw_label(id, confidence, x, y)

    def draw_bbox_feeder(self):
        self.draw_bbox(self.feeder_bbox[0], self.feeder_bbox[1], self.feeder_bbox[2], self.feeder_bbox[3], self.feeder_border_color)

    def draw_bbox_drinker1(self):
        self.draw_bbox(self.drinker1_bbox[0], self.drinker1_bbox[1], self.drinker1_bbox[2], self.drinker1_bbox[3],
                       self.drinker_border_color)

    def draw_bbox_drinker2(self):
        self.draw_bbox(self.drinker2_bbox[0], self.drinker2_bbox[1], self.drinker2_bbox[2], self.drinker2_bbox[3],
                       self.drinker_border_color)
