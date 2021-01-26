import datetime
import os
import json
import sys
import time
import traceback
from copy import deepcopy
import cv2

from uistate import UIState
from eyestate import EyeState


class PlayBack:

    def __init__(self, directory=None, playback=False, video=False, signals=False):
        assert (os.path.exists(directory)), f"The specified input directory is invalid {directory}"

        # State trackers
        self.eye = EyeState()
        self.ui = UIState(multi=True, signals=signals)
        self.ui_next = UIState()
        self.gaze_targets = []
        self.gaze_time = None

        # Setup UI log
        self.ui_log_path = os.path.join(directory, 'uilog', 'ui_log.txt')
        assert (os.path.exists(self.ui_log_path)), f"The specified ui log is invalid {self.ui_log_path}"
        self.ui_log = open(self.ui_log_path, 'r')
        assert (self.ui_log.closed is False)

        # Setup EYE log
        self.eye_log_path = os.path.join(directory, 'gaze_data.txt')
        assert (os.path.exists(self.eye_log_path)), f"The specified eye log is invalid {self.eye_log_path}"
        self.eye.num_logs = sum(1 for line in open(self.eye_log_path))
        assert self.eye.num_logs > 0, "There were no logs in the eye log"
        self.eye_log = open(self.eye_log_path, 'r')
        assert (self.eye_log.closed is False)

        # Setup montages directory
        self.ui.montages_directory = os.path.join(directory, 'uilog', 'montages')
        assert (os.path.exists(self.ui.montages_directory))
        self.ui_next.montages_directory = os.path.join(directory, 'uilog', 'montages')
        assert (os.path.exists(self.ui_next.montages_directory))

        # Setup images, dimensions and visualisations
        self.image_directory = os.path.join(directory, 'uilog', 'screenshots')
        assert (os.path.exists(self.image_directory))
        image_name = f"0.png"
        image_path = os.path.join(self.image_directory, image_name)
        assert os.path.exists(image_path), "Couldn't find the image to setup dimensions"
        self.image_clean = cv2.imread(image_path)
        assert self.image_clean is not None
        self.image_height, self.image_width, _ = self.image_clean.shape
        self.eye.image_width = self.image_width
        self.eye.image_height = self.image_height
        self.image_with_ui = None
        self.image_drawn = None

        # Display options
        self.playback = playback
        if self.playback:
            self.display_window = cv2.namedWindow("Analysis Playback", cv2.WINDOW_NORMAL)
        self.video = video
        if self.video:
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            self.writer = cv2.VideoWriter(os.path.join(os.path.dirname(self.ui_log_path), f"visualise.avi"), fourcc, 60,
                                          (self.image_width, self.image_height))

        assert playback or video, "Need to specify an option to visualise"
        print(f"Visualising recording at {os.path.dirname(self.ui_log_path)}")
        print(f"playback {playback}, video {video}")

        self.signals = signals

        self.ui_line = None
        self.next_ui_line = None

        self.line_color = (0, 255, 0)
        self.line_width = 3
        self.font_color = (0, 0, 255)
        self.font_scale = 2
        self.font_thick = 2
        self.font_type = cv2.FONT_HERSHEY_PLAIN

    def process(self):
        """
        Iterates the data in the log files using the eye tracking data to keep time.
        :return:
        """

        # Read the first line from ui log and initialise the state
        self.next_ui_line = self.ui_log.readline()
        ui_entry = json.loads(self.next_ui_line)
        self.ui_next.update(ui_entry)

        # Read the first line from the eye log and initialise state
        self.next_eye_log()

        # Throw away the UI tracking before EYE tracking is started
        print("Skipping to start...")
        while self.eye.time_stamp > self.ui_next.current_timestamp:
            self.next_ui_log()

        print("Begin visualisation.")
        eye_log_id = 1
        try:
            while self.next_eye_log():

                # Read UI changes as time progresses according to the eye data
                if self.eye.time_stamp > self.ui_next.current_timestamp:
                    self.next_ui_log()
                    self.next_screenshot()

                if not self.signals:
                    self.analyse_fixation_baselines()
                else:
                    self.analyse_fixation_signals()

                # Display / write
                self.visualise()

                # sys.stdout.write(f"({eye_log_id}/{self.eye.num_logs})")
                # sys.stdout.flush()
                # sys.stdout.write('\r')
                # sys.stdout.flush()
                eye_log_id += 1
        except Exception as e:
            traceback.print_exc()
        finally:
            if self.video:
                self.writer.release()

    def analyse_fixation_baselines(self):
        """
        Identify which channels were being looked at and at what time
        :return: A list of channels under the gaze point, the time the user was looking at
        """

        self.gaze_targets.clear()
        if self.eye.center_gaze is not None and self.ui.last_event != "MENU_OPENED" and self.ui.last_event != "MENU_SEARCH" and self.ui.last_event != "MODAL_OPENED" and self.ui.last_event != "WINDOW_MINIMISED":
            # Iterate the channels in the ui state
            # If the signal baseline is within the range of the gaze point then it is currently fixated
            if self.ui.graph_top_left[0] < self.eye.center_gaze[0] < self.ui.graph_top_right[0]:
                for channel in self.ui.channels:
                        if self.eye.center_gaze[1] + 30 > channel.baseline > self.eye.center_gaze[1] - 30:
                            self.gaze_targets.append(channel.label.strip())
            else:
                self.gaze_targets.append("Off")

            # divide the graph width by the timescale to find out how many seconds per pixel
            # count pixels from graph left to gaze point, then multiply by the seconds per pixel to find how many seconds across.
            # Add the seconds to the current time position
            if self.ui.graph_top_left[0] < self.eye.center_gaze[0] < self.ui.graph_top_right[0]:
                seconds_per_pixel = self.ui.timescale_to_seconds() / self.ui.graph_width
                pixels_from_left = self.eye.center_gaze[0] - self.ui.graph_top_left[0]
                seconds_across = seconds_per_pixel * pixels_from_left
                gaze_time = self.ui.time_position_to_seconds() + seconds_across
                self.gaze_time = datetime.timedelta(seconds=gaze_time)
            else:
                self.gaze_time = "Off"
        else:
            self.gaze_targets.append("Off")
            self.gaze_time = "Off"

    def analyse_fixation_signals(self):
        raise NotImplementedError

    def visualise(self):
        """
        Reads the corresponding screenshot for the current UI log.
        :return:
        """
        self.draw_eye()
        if self.image_drawn is not None:
            if self.playback:
                cv2.imshow("Analysis Playback", self.image_drawn)
                cv2.waitKey(1)
            if self.video:
                self.writer.write(self.image_drawn)

    def draw_eye(self):
        """
        Add visualisations to the current screenshot e.g. bounding boxes, fixation point, channel names etc
        :return:
        """
        if self.image_with_ui is not None:
            self.image_drawn = deepcopy(self.image_with_ui)
            self.eye.draw(self.image_drawn)
            self.draw_gaze_target(self.image_drawn)

    def draw_ui(self):
        """
        Add visualisations to the current screenshot e.g. bounding boxes, fixation point, channel names etc
        :return:
        """
        if self.image_clean is not None:
            self.image_with_ui = deepcopy(self.image_clean)
            self.image_with_ui = self.ui.draw(self.image_with_ui)

    def draw_gaze_target(self, image):
        pos = 350
        step = 25
        string = ""
        for signal in self.gaze_targets:
            string += f"{signal}, "
        image = cv2.putText(image, f"signals: {string}", (20, pos), self.font_type, self.font_scale,
                            self.font_color, self.font_thick, cv2.LINE_AA)
        pos += step
        image = cv2.putText(image, f"gaze time: {self.gaze_time}", (20, pos), self.font_type, self.font_scale,
                            self.font_color, self.font_thick, cv2.LINE_AA)
        return image

    def next_screenshot(self):
        image_name = f"{int(self.ui.log_id) + 1}.png"  # +1 because screenshot lag
        image_path = os.path.join(self.image_directory, image_name)
        self.image_clean = cv2.imread(image_path)
        self.image_with_ui = None
        self.image_drawn = None
        self.draw_ui()

    def next_eye_log(self):
        """
        Reads the next line from the gaze/ fixation data file
        :return:
        """
        eye_log = self.eye_log.readline()
        if eye_log is "":
            return False
        eye_log.strip()
        eye_log = json.loads(eye_log)
        self.eye.update(eye_log)
        return True

    def next_ui_log(self):
        """
        Reads the next line from the UI tracking log. Keeps track of the current log, and the log in front. Use the timestamp
        from the next log to trigger changes in the playback.
        :return:
        """
        self.ui_line = self.next_ui_line
        self.next_ui_line = self.ui_log.readline()
        entry = json.loads(self.ui_line)
        next_entry = json.loads(self.next_ui_line)
        self.ui.update(entry)
        self.ui_next.update(next_entry)

    def finish(self):
        """
        Tidy up and close
        :return:
        """
        self.ui_log.close()
        self.eye_log.close()
