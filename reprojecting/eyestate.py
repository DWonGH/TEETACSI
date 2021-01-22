from datetime import datetime

import cv2
import ast


class EyeState:
    
    def __init__(self):
        """
        Reconstructs the state and tracks the changes in a EYE tracking log file
        """
        self.log_id = None
        self.num_logs = None
        self.time_stamp = None
        self.left_eye = None
        self.right_eye = None
        self.center_gaze = None
        self.gaze = None
        self.image_width = None
        self.image_height = None

    def update(self, data):
        """
        Read an entry from the EYE log file and reconstruct the gaze using the information
        :param data: A line from the EYE log loaded into a dictionary
        """
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
        """
        Draw some circles describing the location of the eye tracking and current gaze
        :param image: The corresponding screenshot for the point in time of the current state
        :return: An image with some new circles
        """
        if self.left_eye is not None:
            image = cv2.circle(image, self.left_eye, 5, (0, 0, 200), thickness=2)
        if self.right_eye is not None:
            image = cv2.circle(image, self.right_eye, 5, (0, 0, 200), thickness=2)
        if self.center_gaze is not None:
            image = cv2.circle(image, self.center_gaze, 30, (255, 51, 221), thickness=3)
        return image

    def format_coords(self, coords):
        """
        Tobii SDK records gaze data as normalised coordinates so we need to find the actual pixel value in relation to the image
        :param coords: Normalised coordinates as a tuple e.g. (0.3, 0.12344)
        :return: Pixel coordinates as a tuple e.g. (234, 765)
        """
        coords = ast.literal_eval(coords)
        coords = (int((coords[0] * self.image_width)), int((coords[1] * self.image_height)))
        return coords

    def center_gaze_coords(self, left_eye, right_eye):
        """
        Calculate the current gaze spot by taking an average of the left and right eye points
        :param left_eye: A pixel coordinate tuple e.g. (234, 765)
        :param right_eye: A pixel coordinate tuple e.g. (234, 765)
        :return: A pixel coordinate tuple e.g. (234, 765) - describing the current gaze spot
        """
        return (int(((left_eye[0] + right_eye[0]) / 2)), int(((left_eye[1] + right_eye[1]) / 2)))
