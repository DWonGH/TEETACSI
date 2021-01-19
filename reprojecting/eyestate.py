from datetime import datetime

import cv2
import ast


class EyeState:
    
    def __init__(self):
        self.log_id = None
        self.num_logs = None
        self.time_stamp = None
        self.left_eye = None
        self.right_eye = None
        self.center_gaze = None
        self.gaze = None
        self.image_width = None
        self.image_height = None

    def update_state(self, data):
        timestamp = data["timestamp"]
        self.time_stamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
        if "nan" not in data["left_eye"]:
            self.left_eye = self.format_coords(data["left_eye"])
        else:
            self.left_eye = None
        if "nan" not in data["right_eye"]:
            self.right_eye = self.format_coords(data["right_eye"])
        else:
            self.right_eye = None
        if self.left_eye is not None and self.right_eye is not None:
            self.center_gaze = self.center_gaze_coords(self.left_eye, self.right_eye)
        else:
            self.center_gaze = None

    def draw(self, image):
        if self.left_eye is not None:
            image = cv2.circle(image, self.left_eye, 5, (0, 0, 200), thickness=2)
        if self.right_eye is not None:
            image = cv2.circle(image, self.right_eye, 5, (0, 0, 200), thickness=2)
        if self.center_gaze is not None:
            image = cv2.circle(image, self.center_gaze, 30, (255, 51, 221), thickness=3)
        return image

    def format_coords(self, coords):
        coords = ast.literal_eval(coords)
        coords = (int((coords[0] * self.image_width)), int((coords[1] * self.image_height)))
        return coords

    def center_gaze_coords(self, left_eye, right_eye):
        return (int(((left_eye[0] + right_eye[0]) / 2)), int(((left_eye[1] + right_eye[1]) / 2)))

    def print_state(self):
        print(f"timestamp: {self.time_stamp}")