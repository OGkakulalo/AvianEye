import cv2
import numpy as np


class BBox:
    def __init__(self):
        self.frame = None

        # Set the font parameters
        self.font_scale = 0.4  # Font scale
        self.font_color = (0, 0, 0)  # Font color in BGR format
        self.font = cv2.FONT_HERSHEY_SIMPLEX  # Font type
        self.font_thickness = 1  # Adjust the font thickness as needed

        # Set the background color for both label and bounding box
        self.bg_color = (0, 0, 255) # red
        self.border_color = (0, 0, 255) # red

        # Set the point size and color
        self.point_color = (0, 0, 255)  # Point color in BGR format
        self.point_size = 4  # Point size

        # Set the line parameters
        self.line_thickness = 2
        self.line_color = (255, 0, 0) # blue

        # Set the feeder bbox parameters
        self.feeder_bbox = [900, 250, 100, 90]
        self.feeder_border_color = (0, 255, 255)
        self.feeder_bg_color = (0, 255, 255)  # yellow

        # Set the drinker bbox parameters
        self.drinker1_bbox = [650, 190, 55, 38]
        self.drinker2_bbox = [920, 100, 60, 40]
        self.drinker_border_color = (255, 255, 0)
        self.drinker_bg_color = (255, 255, 0)  # light blue

    def set_frame(self, frame):
        self.frame = frame

    def draw_bbox(self, x, y, w, h, border_color):
        # Draw your custom bounding box
        cv2.rectangle(self.frame, (int(x - w / 2), int(y - h / 2)), (int(x + w / 2), int(y + h / 2)), border_color, self.line_thickness)

    def draw_label(self, track_id, class_name, confidence, x, y, w, h, bg_color):
        # Add your custom label with background
        label = f"#{track_id} Conf: {confidence:.2f}"
        (label_width, label_height), _ = cv2.getTextSize(label, self.font, self.font_scale, self.line_thickness)
        bg_rect = (int(x - w / 2), int(y - h / 2) - label_height - 10,
                   int(x - w / 2) + label_width + 10, int(y - h / 2))
        # Draw the background
        cv2.rectangle(self.frame, (bg_rect[0], bg_rect[1]), (bg_rect[2], bg_rect[3]), bg_color,
                      -1)  # Filled rectangle
        # Draw the label
        cv2.putText(self.frame, label, (int(x - w / 2) + 5, int(y - h / 2) - 5),
                    self.font, self.font_scale, self.font_color, self.font_thickness)

    def draw_polyline(self, track):
        # Check if 'track' is not empty before proceeding
        if len(track) > 0:
            points = np.hstack(track).astype(np.int32).reshape((-1, 1, 2))
            cv2.polylines(self.frame, [points], isClosed=False, color=self.line_color,
                          thickness=self.line_thickness)  # Polyline

    def draw_circle(self, x, y):
        # Draw a point at the center of the tracked object
        cv2.circle(self.frame, (int(x), int(y)), self.point_size, self.point_color, -1)  # Red dot

    def draw_chicken_bbox(self, track_id, class_name, confidence, x, y, w, h):
        self.draw_bbox(x, y, w, h, self.border_color)
        self.draw_label(track_id, class_name, confidence, x, y, w, h, self.bg_color)

    def draw_bbox_feeder(self):
        self.draw_bbox(self.feeder_bbox[0], self.feeder_bbox[1], self.feeder_bbox[2], self.feeder_bbox[3], self.feeder_border_color)
        self.draw_label(0, "feeder", 100, self.feeder_bbox[0], self.feeder_bbox[1], self.feeder_bbox[2], self.feeder_bbox[3], self.feeder_bg_color)

    def draw_bbox_drinker1(self):
        self.draw_bbox(self.drinker1_bbox[0], self.drinker1_bbox[1], self.drinker1_bbox[2], self.drinker1_bbox[3],
                       self.drinker_border_color)
        self.draw_label(0, "drinker", 100, self.drinker1_bbox[0], self.drinker1_bbox[1], self.drinker1_bbox[2],
                        self.drinker1_bbox[3], self.drinker_bg_color)

    def draw_bbox_drinker2(self):
        self.draw_bbox(self.drinker2_bbox[0], self.drinker2_bbox[1], self.drinker2_bbox[2], self.drinker2_bbox[3],
                       self.drinker_border_color)
        self.draw_label(0, "drinker", 100, self.drinker2_bbox[0], self.drinker2_bbox[1], self.drinker2_bbox[2],
                        self.drinker2_bbox[3], self.drinker_bg_color)
