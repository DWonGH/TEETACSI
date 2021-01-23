import os
import sys
import time
import traceback
from datetime import datetime
import multiprocessing

import cv2
import numpy
from PyQt5.QtWidgets import QApplication
from channel import Channel
from edfreader import EDFreader
from filter_class import FidFilter
from lxml import etree


class UIState:

    def __del__(self):
        if self.multi is True:
            self.pool.close()
            self.pool.join()

    def __init__(self, montages_directory=None, multi=False):
        """
        Reconstructs the state and tracks the changes in a UI log file
        :param montages_directory: Need to specify the location of the corresponding montages that were saved with the log.
                                    These are used to reconstruct filters, baselines, active channels etc.
        """
        self.log_id = None
        self.last_event = None
        self.current_timestamp = None
        self.graph_width = None
        self.graph_height = None
        self.graph_top_left = None
        self.graph_top_right = None
        self.graph_bottom_left = None
        self.graph_bottom_right = None
        self.time_position = None
        self.time_scale = None
        self.num_channels = None
        self.channels = []
        self.opened = False

        self.montages_directory = montages_directory
        self.montage_file_name = None
        self.montage_file_path = None

        self.line_color = (0, 255, 0)
        self.line_width = 3
        self.font_color = (0, 0, 255)
        self.font_scale = 2
        self.font_thick = 2
        self.font_type = cv2.FONT_HERSHEY_PLAIN

        self.multi = multi
        if self.multi:
            self.num_cores = multiprocessing.cpu_count()
            lock = multiprocessing.Lock()
            self.pool = multiprocessing.Pool(initializer=self.init, processes=self.num_cores, initargs=(lock,))

    def update(self, entry):
        """
        Read an entry from the UI log file and reconstruct the state using the information
        :param entry: A line from the UI log loaded into a dictionary
        :return: False if the entry was "FILE_CLOSED"
        """
        event = entry['event']
        if "data" in entry:
            data = entry['data']
        self.log_id = entry['id']
        timestamp = entry['timestamp']
        self.current_timestamp = datetime.strptime(timestamp, "%d.%m.%Y %H:%M:%S:%f")
        
        # Update the state according the recorded events
        if event == 'FILE_OPENED':
            self.edf_file_path = data['edf_path']
            self.time_position = data['time']
            self.time_scale = data['time_scale']
            self.montage_file_name = data['montage_file']
            self.load_channels_from_montage()
            self.graph_width = data['graph_dimensions'][0]
            self.graph_height = data['graph_dimensions'][1]
            graph_box = data['graph_box']
            self.graph_top_left = (graph_box['top_left'][0], graph_box['top_left'][1])
            self.graph_top_right = (graph_box['top_right'][0], graph_box['top_right'][1])
            self.graph_bottom_left = (graph_box['bottom_left'][0], graph_box['bottom_left'][1])
            self.graph_bottom_right = (graph_box['bottom_right'][0], graph_box['bottom_right'][1])
            self.last_event = 'FILE_OPENED'
            print("Reading edf file")
            if os.path.exists(self.edf_file_path):
                self.edf = EDFreader(self.edf_file_path)
            else:
                user_input = input(f"The path to the edf file ({self.edf_file_path}) is invalid. Please specify the path"
                                    f"to the edf file. ")
                assert os.path.exists(user_input), f"The path {user_input} does not lead to a valid edf file."
                self.edf = EDFreader(self.edf_file_path)
            assert self.edf is not None
            self.update_channel_data()
            self.opened = True
        elif event == 'FILE_CLOSED':
            return False
        elif event == 'MONTAGE_CHANGED':
            self.montage_file_name = data['montage_file']
            self.load_channels_from_montage()
            if self.opened: self.update_channel_data()
            self.last_event = 'MONTAGE_CHANGED'
        elif event == 'CHANNELS_CHANGED':
            self.montage_file_name = data['montage_file']
            self.load_channels_from_montage()
            if self.opened: self.update_channel_data()
            self.last_event = 'CHANNELS_CHANGED'
        elif event == 'FILTER_CHANGED':
            self.montage_file_name = data['montage_file']
            self.load_channels_from_montage()
            if self.opened: self.update_channel_data()
            self.last_event = 'FILTER_CHANGED'
        elif event == 'AMPLITUDE_CHANGED':
            self.montage_file_name = data['montage_file']
            self.load_channels_from_montage()
            if self.opened: self.update_channel_data()
            self.last_event = 'AMPLITUDE CHANGED'
        elif event == 'TIMESCALE_CHANGED':
            self.time_scale = data['time_scale']
            if self.opened: self.update_channel_data()
            self.last_event = 'TIMESCALE_CHANGED'
        elif event == 'TIME_POSITION_CHANGED':
            self.time_position = data['time']
            if self.opened: self.update_channel_data()
            self.last_event = 'TIME_POSITION_CHANGED'
        elif event == 'VERTICAL_CHANGED':
            self.montage_file_name = data['montage_file']
            self.load_channels_from_montage()
            if self.opened: self.update_channel_data()
            self.last_event = 'VERTICAL_CHANGED'
        elif event == 'ZOOM_CHANGED':
            self.montage_file_name = data['montage_file']
            self.load_channels_from_montage()
            if self.opened: self.update_channel_data()
            self.time_scale = data['time_scale']
            self.time_position = data['time']
            self.last_event = 'ZOOM_CHANGED'
        elif entry['event'] == 'WINDOW_MOVED':
            graph_box = data['graph_box']
            self.graph_top_left = (graph_box['top_left'][0], graph_box['top_left'][1])
            self.graph_top_right = (graph_box['top_right'][0], graph_box['top_right'][1])
            self.graph_bottom_left = (graph_box['bottom_left'][0], graph_box['bottom_left'][1])
            self.graph_bottom_right = (graph_box['bottom_right'][0], graph_box['bottom_right'][1])
            if self.opened: self.update_channel_data()
            self.last_event = 'WINDOW_MOVED'
        elif entry['event'] == 'GRAPH_RESIZED':
            self.graph_width = data['graph_dimensions'][0]
            self.graph_height = data['graph_dimensions'][1]
            graph_box = data['graph_box']
            self.graph_top_left = (graph_box['top_left'][0], graph_box['top_left'][1])
            self.graph_top_right = (graph_box['top_right'][0], graph_box['top_right'][1])
            self.graph_bottom_left = (graph_box['bottom_left'][0], graph_box['bottom_left'][1])
            self.graph_bottom_right = (graph_box['bottom_right'][0], graph_box['bottom_right'][1])
            if self.opened: self.update_channel_data()
            self.last_event = 'GRAPH_RESIZED'
        elif event == 'MODAL_OPENED':
            self.last_event = 'MODAL_OPENED'
        elif event == 'MODAL_CLOSED':
            self.last_event = 'MODAL_CLOSED'
        elif event == 'MENU_OPENED':
            self.last_event = 'MENU_OPENED'
        elif event == 'MENU_SEARCH':
            self.last_event = 'MENU_SEARCH'
        elif event == 'MENU_CLOSED':
            self.last_event = 'MENU_CLOSED'
        elif event == 'WINDOW_MINIMISED':
            self.last_event = 'WINDOW_MINIMISED'
        elif event == 'WINDOW_MAXIMISED':
            self.last_event = 'WINDOW_MAXIMISED'
        elif event == 'WINDOW_OPENED':
            self.last_event = 'WINDOW_OPENED'
        elif event == 'WINDOW_FULLSCREEN':
            self.last_event = 'WINDOW_FULLSCREEN'
        else:
            print("Invalid event!")

    def load_channels_from_montage(self):
        """
        Each time a filter or amplitude or other channel parameters are changed a montage file will be saved using the
        log id as a filename e.g. 1.mtg. Use the corresponding montage to reconstruct the current state of the signals.
        :return:
        """

        # Update the current montage file path
        if self.montage_file_name is not None:
            if '.mtg' not in self.montage_file_name:
                self.montage_file_name = f"{self.montage_file_name}.mtg"
            self.montage_file_path = os.path.join(self.montages_directory, self.montage_file_name)
            assert os.path.exists(self.montage_file_path)

            # Read in the channels from the mtg file
            doc = etree.parse(self.montage_file_path)
            signals = doc.xpath('signalcomposition')
            self.channels.clear()
            for i, signal in enumerate(signals):
                # Channel info
                idx = i
                label = signal.xpath('signal/label')
                factor = signal.xpath('signal/factor')
                voltpercm = signal.xpath('voltpercm')
                screen_offset = signal.xpath('screen_offset')
                polarity = signal.xpath('polarity')
                filter_cnt = signal.xpath('filter_cnt')
                self.channels.append(Channel(idx, label[0].text, factor[0].text, voltpercm[0].text, screen_offset[0].text, polarity[0].text, filter_cnt[0].text))

                # Channel filters
                filters = signal.xpath('fidfilter')
                if len(filters) > 0:
                    for f in filters:
                        ftype = f.xpath('type')
                        freq_1 = f.xpath('frequency')
                        freq_2 = f.xpath('frequency2')
                        ripple = f.xpath('ripple')
                        order = f.xpath('order')
                        model = f.xpath('model')
                        self.channels[i].fid_filters.append(FidFilter(ftype[0].text, freq_1[0].text, freq_2[0].text, ripple[0].text, order[0].text, model[0].text))

                # Update the channel baseline
                self.channels[i].update_baseline(self.graph_height, len(self.channels), self.graph_top_left[1])

    def update_channel_data(self):
        """
        Reconstruct the signals for the current state.
        This is not complete, and the signals appear to be skewed left or right~?
        :return:
        """
        time_position = self.time_position_to_seconds()
        time_scale = self.timescale_to_seconds()
        for i, channel in enumerate(self.channels):
            start = int(self.edf.getSampleFrequency(i) * time_position)
            num_samples_to_read = int(self.edf.getSampleFrequency(i) * time_scale)
            print(num_samples_to_read)
            if num_samples_to_read > 0:
                self.edf.rewind(i)
                start = self.edf.fseek(i, start, 0)
                channel.data = numpy.empty(num_samples_to_read, dtype=numpy.float_)
                assert num_samples_to_read == self.edf.readSamples(i, channel.data, num_samples_to_read)
        # TODO: Apply filters to data
        # TODO: Apply amplitude to data

    def time_position_to_seconds(self):
        """
        Convert the recorded time string in the log
        :return:
        """
        try:
            x = self.time_position.split('(')[1].strip(')')
            x = datetime.strptime(x, '%H:%M:%S')
            return x.second + x.minute * 60 + x.hour * 3600
        except ValueError:
            x = self.time_position.split('(')[1].strip(')')
            x = datetime.strptime(x, '%H:%M:%S.%f')
            return x.second + x.minute * 60 + x.hour * 3600

    def time_position_to_samples(self, channel):
        x = self.time_position.split('(')[1].strip(')')
        x = time.strptime(x, '%H:%M:%S')
        total_seconds = x.tm_sec + x.tm_min * 60 + x.tm_hour * 3600
        return self.edf.getSampleFrequency(channel) * total_seconds

    def timescale_to_seconds(self):
        """
        The timescale is recorded from EDFBrowser as a string e.g. 10 sec.
        Change to seconds to perform calculations
        :return: an int describing a number of seconds
        """
        if "uS" in self.time_scale:
            split = self.time_scale.strip("uS")
            return float(split) / 1000000
        elif "mS" in self.time_scale:
            split = self.time_scale.strip("mS")
            return float(split) / 1000
        elif "sec" in self.time_scale:
            split = self.time_scale.strip(" sec")
            return float(split)
        else:
            try:
                pt = datetime.strptime(self.time_scale, '%H:%M:%S')
                return pt.second + pt.minute * 60 + pt.hour * 3600
            except ValueError:
                try:
                    pt = datetime.strptime(self.time_scale, '%M:%S')
                    return pt.second + pt.minute * 60 + pt.hour * 3600
                except ValueError:
                    print("Try a different format")

    def draw(self, image):
        if not (self.last_event == "MENU_OPENED" or self.last_event == "MENU_SEARCH" or self.last_event == "MENU_CLOSED" or self.last_event == "MODAL_OPENED" or self.last_event == "MODAL_CLOSED" or self.last_event == "WINDOW_MINIMISED"):
            image = self.draw_graph_bbox(image)
            image = self.draw_channel_baselines(image)
            image = self.draw_channel_signals(image)
        image = self.draw_log_info(image)
        return image

    def draw_graph_bbox(self, image):
        """
        Draws a box around the signals graph to validate tracking
        :param image: The corresponding screenshot to this current log
        :return: An image with a new box on it
        """
        image = cv2.line(image, self.graph_top_left, self.graph_top_right, self.line_color, self.line_width)
        image = cv2.line(image, self.graph_bottom_left, self.graph_bottom_right, self.line_color, self.line_width)
        image = cv2.line(image, self.graph_top_left, self.graph_bottom_left, self.line_color, self.line_width)
        image = cv2.line(image, self.graph_top_right, self.graph_bottom_right, self.line_color, self.line_width)
        return image

    def draw_log_info(self, image):
        """
        Draws the UI state to validate UI tracking
        :param image: The corresponding screenshot to this current log
        :return: An image with new writing on
        """
        pos = 100
        step = 25
        image = cv2.putText(image, f"id: {self.log_id}", (20, pos), self.font_type, self.font_scale, self.font_color, self.font_thick, cv2.LINE_AA)
        pos += step
        image = cv2.putText(image, f"time: {self.time_position}", (20, pos), self.font_type, self.font_scale, self.font_color, self.font_thick, cv2.LINE_AA)
        pos += step
        image = cv2.putText(image, f"timescale: {self.time_scale}", (20, pos), self.font_type, self.font_scale, self.font_color, self.font_thick, cv2.LINE_AA)
        pos += step
        image = cv2.putText(image, f"width: {self.graph_width}", (20, pos), self.font_type, self.font_scale, self.font_color, self.font_thick, cv2.LINE_AA)
        pos += step
        image = cv2.putText(image, f"height: {self.graph_height}", (20, pos), self.font_type, self.font_scale, self.font_color, self.font_thick, cv2.LINE_AA)
        pos += step
        image = cv2.putText(image, f"num channels: {len(self.channels)}", (20, pos), self.font_type, self.font_scale, self.font_color, self.font_thick, cv2.LINE_AA)
        pos += step
        image = cv2.putText(image, f"last event: {self.last_event}", (20, pos), self.font_type, self.font_scale, self.font_color, self.font_thick, cv2.LINE_AA)
        pos += step
        image = cv2.putText(image, f"montage: {self.montage_file_name}", (20, pos), self.font_type, self.font_scale, self.font_color, self.font_thick, cv2.LINE_AA)

        for channel in self.channels:
            image = cv2.putText(image, f"{channel.label}", (self.graph_top_right[0], channel.baseline), self.font_type, self.font_scale/2, self.font_color, self.font_thick, cv2.LINE_AA)

        return image
    
    def draw_channel_baselines(self, image):
        """
        Draws the baseline for each channel
        :param image: The corresponding screenshot to this current log
        :return: An image with new horizontal lines describing the position of the signal baselines
        """
        graph_left = self.graph_top_left[0]
        graph_right = self.graph_top_right[0]
        graph_top = self.graph_top_left[1]
        for i, channel in enumerate(self.channels):
            channel.update_baseline(self.graph_height, len(self.channels), graph_top)
            image = cv2.line(image, (graph_left, channel.baseline), (graph_right, channel.baseline), self.line_color, self.line_width)
        return image

    def draw_channel_signals(self, image):
        """
        Given the offset o and scale s, we should be able to read the original EDF file and then convert the
        raw data Yr to a vertical screen coordinate Yc using Yc = s * Yr + o
        :param image: The corresponding screenshot to this current log
        :return: An image with the EEG data traced over the top
        """

        # Scale is recorded in EDFBrowser as Volts per CM. So we need to find out our scale from pixels per inch to
        # pixels per cm
        dpi = 72
        ppc = dpi * 2.54

        tasks = []
        for channel in self.channels:
            tasks.append((self.graph_width, self.graph_top_left[0], ppc, channel))

        results = self.pool.starmap(self.draw_signal, tasks)

        for i in range(len(results)):
            for j in range(len(results[i])-2):
                image = cv2.line(image, (results[i][j][0], results[i][j][1]), (results[i][j+1][0], results[i][j+1][1]), (255, 0, 0), 1)

        return image

    @staticmethod
    def init(l):
        global lock
        lock = l

    @staticmethod
    def draw_signal(graph_width, graph_left, ppc, channel):
        if isinstance(channel.data, numpy.ndarray):
            num_samples = channel.data.size
            arr = numpy.empty((num_samples, 2), dtype=numpy.int)
            spacing = graph_width / num_samples
            for point in range(channel.data.size - 1):
                # Yc = s * Yr + o
                x = int(int(point * spacing) + graph_left)
                y = int((((float(channel.voltspercm) / ppc) * channel.data[point]) * -1) + channel.baseline)
                arr[point][0] = x
                arr[point][1] = y
            return arr


