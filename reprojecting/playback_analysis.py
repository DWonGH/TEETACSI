import os
import json
import sys
import time
from copy import deepcopy
import argparse
import cv2

from uistate import UIState
from eyestate import EyeState


class PlayBack:

    def __init__(self):
        self.ui_log_path = None
        self.eye_log_path = None
        self.ui_log = None
        self.eye_log = None
        self.ui_state = UIState()
        self.eye_state = EyeState()
        self.image_directory = None
        self.image_clean = None
        self.image_drawn = None
        self.frames = []
        self.eye_hz = None
        self.image_width = None
        self.image_height = None
        self.current_ui_line = None
        self.current_ui_dict = None
        self.previous_ui_line = None
        self.previous_ui_dict = None

    def process(self, playback, video):
        assert playback or video, "Need to specify an option to visualise"
        print(f"Visualising recording at {os.path.dirname(self.ui_log_path)}")
        print(f"playback {playback}, video {video}")

        # Read the first line from ui log and initialise the state
        self.current_ui_line = self.ui_log.readline()
        self.current_ui_dict = json.loads(self.current_ui_line)
        self.ui_state.update_state(self.current_ui_dict)

        # setup the first image and dimensions
        image_name = f"{int(self.ui_state.log_id)+1}.png"  # +1 because screenshot lag
        image_path = os.path.join(self.image_directory, image_name)
        assert os.path.exists(image_path), "Couldnt find the image"
        self.image_clean = cv2.imread(image_path)
        assert self.image_clean is not None
        self.image_height, self.image_width, _ = self.image_clean.shape
        self.eye_state.image_width = self.image_width
        self.eye_state.image_height = self.image_height
        if video:
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            writer = cv2.VideoWriter(os.path.join(os.path.dirname(self.ui_log_path), f"visualise.avi"), fourcc, 60, (self.image_width, self.image_height))


        # Want to throw away the UI tracking before the the eye tracker was started as it is not needed. To identify
        # the current UI log entry, we read up until the timestamp is newer than the eye tracking timestamp, and then
        # step back one entry.
        print("Skipping to start...")
        eye_line = self.eye_log.readline()
        eye_line.strip()
        eye_log = json.loads(eye_line)
        self.eye_state.update_state(eye_log)
        while True:
            if self.eye_state.time_stamp < self.ui_state.current_timestamp:
                self.ui_state.update_state(self.previous_ui_dict)
                break
            else:
                self.previous_ui_line = self.current_ui_line
                self.previous_ui_dict = self.current_ui_dict
                self.current_ui_line = self.ui_log.readline()
                self.current_ui_dict = json.loads(self.current_ui_line)
                self.ui_state.update_state(self.current_ui_dict)

        # setup the first image and dimensions
        image_name = f"{int(self.ui_state.log_id)+1}.png"  # +1 because screenshot lag
        image_path = os.path.join(self.image_directory, image_name)
        assert os.path.exists(image_path), "Couldnt find the image"
        self.image_clean = cv2.imread(image_path)
        assert self.image_clean is not None
        self.image_height, self.image_width, _ = self.image_clean.shape
        self.eye_state.image_width = self.image_width
        self.eye_state.image_height = self.image_height
        self.draw()
        if self.image_drawn is not None:
            if playback:
                cv2.imshow("Analysis Playback", self.image_drawn)
                cv2.waitKey(1)

        # Now process the rest of the data.
        print("Begin visualisation.")
        eye_log_id = 1
        self.ui_state.update_state(self.current_ui_dict)
        try:
            while True:

                # Read eye log
                eye_log = self.eye_log.readline()
                if eye_log is None:
                    break
                eye_log.strip()
                eye_log = json.loads(eye_log)
                self.eye_state.update_state(eye_log)
                self.eye_state.log_id = eye_log_id
                eye_log_id += 1

                # Load UI changes as time progresses according to eye data
                if self.eye_state.time_stamp > self.ui_state.current_timestamp:
                    self.previous_ui_line = self.current_ui_line
                    self.previous_ui_dict = self.current_ui_dict
                    self.current_ui_line = self.ui_log.readline()
                    self.current_ui_dict = json.loads(self.current_ui_line)

                # Visualising
                self.ui_state.update_state(self.previous_ui_dict)
                image_name = f"{int(self.ui_state.log_id)+1}.png"  # +1 because screenshot lag
                image_path = os.path.join(self.image_directory, image_name)
                self.image_clean = cv2.imread(image_path)
                self.draw()
                if self.image_drawn is not None:
                    if playback:
                        cv2.imshow("Analysis Playback", self.image_drawn)
                        cv2.waitKey(1)
                    if video:
                        writer.write(self.image_drawn)
                self.ui_state.update_state(self.current_ui_dict)
                sys.stdout.write(f"({eye_log_id}/{self.eye_state.num_logs})")
                sys.stdout.flush()
                sys.stdout.write('\r')
                sys.stdout.flush()
        finally:
            if video:
                writer.release()

    def draw(self):
        if self.image_clean is not None:
            self.image_drawn = deepcopy(self.image_clean)
            self.image_drawn = self.ui_state.draw(self.image_drawn)
            self.eye_state.draw(self.image_drawn)

    def setup(self, directory):
        assert(os.path.exists(directory)), f"The specified input directory is invalid {directory}"
        
        self.ui_log_path = os.path.join(directory, 'uilog', 'ui_log.txt')
        assert(os.path.exists(self.ui_log_path)), f"The specified ui log is invalid {self.ui_log_path}"
        self.ui_log = open(self.ui_log_path, 'r')
        assert(self.ui_log.closed is False)

        self.ui_state.montages_directory = os.path.join(directory, 'uilog', 'montages')
        assert(os.path.exists(self.ui_state.montages_directory))

        self.image_directory = os.path.join(directory, 'uilog', 'screenshots')
        assert(os.path.exists(self.image_directory))

        self.eye_log_path = os.path.join(directory, 'gaze_data.txt')
        assert(os.path.exists(self.eye_log_path)), f"The specified eye log is invalid {self.eye_log_path}"
        self.eye_state.num_logs = sum(1 for line in open(self.eye_log_path))
        assert self.eye_state.num_logs > 0, "There were no logs in the eye log"
        self.eye_log = open(self.eye_log_path, 'r')
        assert(self.eye_log.closed is False)

        self.display_window = cv2.namedWindow("Analysis Playback",cv2.WINDOW_NORMAL)

    def finish(self):
        self.ui_log.close()
        self.eye_log.close()
