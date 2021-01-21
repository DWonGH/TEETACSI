import os
import json
import sys
from copy import deepcopy
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
        self.next_ui_state = UIState()
        self.eye_state = EyeState()
        self.image_directory = None
        self.image_clean = None
        self.image_drawn = None
        self.frames = []
        self.eye_hz = None
        self.image_width = None
        self.image_height = None
        self.ui_line = None
        self.next_ui_line = None

    def process(self, playback, video):
        assert playback or video, "Need to specify an option to visualise"
        print(f"Visualising recording at {os.path.dirname(self.ui_log_path)}")
        print(f"playback {playback}, video {video}")

        # Read the first line from ui log and initialise the state
        self.next_ui_line = self.ui_log.readline()
        ui_entry = json.loads(self.next_ui_line)
        self.next_ui_state.update_state(ui_entry)

        # setup the first image and dimensions
        image_name = f"{int(self.next_ui_state.log_id)+1}.png"  # +1 because screenshot lag
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

        # Want to throw away the UI tracking before the the EYE tracking was started as it is not needed. To identify
        # the current UI log entry, we read up until the timestamp is newer than the eye tracking timestamp, and then
        # step back one entry.
        print("Skipping to start...")
        eye_line = self.eye_log.readline()
        eye_line.strip()
        eye_log = json.loads(eye_line)
        self.eye_state.update_state(eye_log)

        while self.eye_state.time_stamp > self.next_ui_state.current_timestamp:
            self.next_ui_log()

        # Now process the rest of the data.
        print("Begin visualisation.")
        eye_log_id = 1
        try:
            while True:

                # Read eye log
                eye_log = self.eye_log.readline()
                if eye_log is "":
                    break
                eye_log.strip()
                eye_log = json.loads(eye_log)
                self.eye_state.update_state(eye_log)
                self.eye_state.log_id = eye_log_id
                eye_log_id += 1

                # Load UI changes as time progresses according to eye data
                if self.eye_state.time_stamp > self.next_ui_state.current_timestamp:
                    self.next_ui_log()

                # Visualising
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

                sys.stdout.write(f"({eye_log_id}/{self.eye_state.num_logs})")
                sys.stdout.flush()
                sys.stdout.write('\r')
                sys.stdout.flush()
        finally:
            if video:
                writer.release()

    def next_ui_log(self):
        self.ui_line = self.next_ui_line
        self.next_ui_line = self.ui_log.readline()
        entry = json.loads(self.ui_line)
        next_entry = json.loads(self.next_ui_line)
        self.ui_state.update_state(entry)
        self.next_ui_state.update_state(next_entry)

    def draw(self):
        if self.image_clean is not None:
            self.image_drawn = deepcopy(self.image_clean)
            self.image_drawn = self.ui_state.draw(self.image_drawn)
            self.eye_state.draw(self.image_drawn)

    def analyse_fixation(self):
        # calculate a bounding box or circle around the current centre gaze point
        # top_left = centre_gaze_x - 10, centre_gaze_y + 10
        # top_right = centre_gaze_x + 10, centre_gaze_y + 10
        # bottom_left = centre_gaze_x - 10, centre_gaze_y - 10
        # bottom_right = centre_gaze_x + 10, centre_gaze_y - 10

        # Iterate the channels in the ui state
        # If the signal baseline is within the range of the bounding box then it is currently fixated
        # OR:
        # Get the highest y point of the signal in screen coordinates
        # Get the lowest y point of the signal in screen coordinates
        # if any of the signals range intersects with the y range of the gaze box; then it is in view
        # OR:
        # Convert the data points to ys
        # Build a list of ys for the bbox
        # use python intersection to see if the ranges cross

        # divide the graph width by the timescale to find out how many seconds per pixel
        # count pixels from graph left to gaze box, then multiply by the seconds per pixel to find how many seconds across.
        # Add the seconds to the current time
        # gaze_time = current_time + ((fixation_point - graph_left) * (graph_width / timescale))
        pass

    def setup(self, directory):
        assert(os.path.exists(directory)), f"The specified input directory is invalid {directory}"
        
        self.ui_log_path = os.path.join(directory, 'uilog', 'ui_log.txt')
        assert(os.path.exists(self.ui_log_path)), f"The specified ui log is invalid {self.ui_log_path}"
        self.ui_log = open(self.ui_log_path, 'r')
        assert(self.ui_log.closed is False)

        self.ui_state.montages_directory = os.path.join(directory, 'uilog', 'montages')
        assert (os.path.exists(self.ui_state.montages_directory))

        self.next_ui_state.montages_directory = os.path.join(directory, 'uilog', 'montages')
        assert(os.path.exists(self.next_ui_state.montages_directory))

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
