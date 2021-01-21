import os
import sys
import time
from datetime import datetime

import cv2
import numpy
from PyQt5.QtWidgets import QApplication
from channel import Channel
from edfreader import EDFreader
from filter_class import FidFilter
from lxml import etree


class UIState:

    def __init__(self, montages_directory=None):

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

    def update_state(self, entry):

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
            self.last_event = 'MONTAGE_CHANGED'
        elif event == 'CHANNELS_CHANGED':
            self.montage_file_name = data['montage_file']
            self.load_channels_from_montage()
            self.last_event = 'CHANNELS_CHANGED'
        elif event == 'FILTER_CHANGED':
            self.montage_file_name = data['montage_file']
            self.load_channels_from_montage()
            self.last_event = 'FILTER_CHANGED'
        elif event == 'AMPLITUDE_CHANGED':
            self.montage_file_name = data['montage_file']
            self.load_channels_from_montage()
            self.last_event = 'AMPLITUDE CHANGED'
        elif event == 'TIMESCALE_CHANGED':
            self.time_scale = data['time_scale']
            self.last_event = 'TIMESCALE_CHANGED'
        elif event == 'TIME_POSITION_CHANGED':
            self.time_position = data['time']
            self.last_event = 'TIME_POSITION_CHANGED'
        elif event == 'VERTICAL_CHANGED':
            self.montage_file_name = data['montage_file']
            self.load_channels_from_montage()
            self.last_event = 'VERTICAL_CHANGED'
        elif event == 'ZOOM_CHANGED':
            self.montage_file_name = data['montage_file']
            self.load_channels_from_montage()
            self.time_scale = data['time_scale']
            self.time_position = data['time']
            self.last_event = 'ZOOM_CHANGED'
        elif entry['event'] == 'WINDOW_MOVED':
            graph_box = data['graph_box']
            self.graph_top_left = (graph_box['top_left'][0], graph_box['top_left'][1])
            self.graph_top_right = (graph_box['top_right'][0], graph_box['top_right'][1])
            self.graph_bottom_left = (graph_box['bottom_left'][0], graph_box['bottom_left'][1])
            self.graph_bottom_right = (graph_box['bottom_right'][0], graph_box['bottom_right'][1])
            self.last_event = 'WINDOW_MOVED'
        elif entry['event'] == 'GRAPH_RESIZED':
            self.graph_width = data['graph_dimensions'][0]
            self.graph_height = data['graph_dimensions'][1]
            graph_box = data['graph_box']
            self.graph_top_left = (graph_box['top_left'][0], graph_box['top_left'][1])
            self.graph_top_right = (graph_box['top_right'][0], graph_box['top_right'][1])
            self.graph_bottom_left = (graph_box['bottom_left'][0], graph_box['bottom_left'][1])
            self.graph_bottom_right = (graph_box['bottom_right'][0], graph_box['bottom_right'][1])
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
        total_seconds = self.time_position_to_seconds()
        y = int(self.time_scale.split(' ')[0])
        for i, channel in enumerate(self.channels):
            start = self.edf.getSampleFrequency(i) * total_seconds
            # print(f"start {start}")
            num_samples_to_read = int(self.edf.getSampleFrequency(i) * y)
            self.edf.rewind(0)
            start = self.edf.fseek(i, start, 'EDFSEEK_SET')
            channel.data = numpy.empty(num_samples_to_read, dtype=numpy.float_)
            assert num_samples_to_read == self.edf.readSamples(i, channel.data, num_samples_to_read)
        # TODO: Apply filters to data
        # TODO: Apply amplitude to data

    def time_position_to_seconds(self):
        x = self.time_position.split('(')[1].strip(')')
        x = time.strptime(x, '%H:%M:%S')
        return x.tm_sec + x.tm_min * 60 + x.tm_hour * 3600

    def time_position_to_samples(self, channel):
        x = self.time_position.split('(')[1].strip(')')
        x = time.strptime(x, '%H:%M:%S')
        total_seconds = x.tm_sec + x.tm_min * 60 + x.tm_hour * 3600
        return self.edf.getSampleFrequency(channel) * total_seconds

    def draw(self, image):
        image = self.draw_graph_bbox(image)
        image = self.draw_channel_baselines(image)
        # image = self.draw_channel_signals(image)
        image = self.draw_log_info(image)
        return image


    def draw_graph_bbox(self, image):
        image = cv2.line(image, self.graph_top_left, self.graph_top_right, self.line_color, self.line_width)
        image = cv2.line(image, self.graph_bottom_left, self.graph_bottom_right, self.line_color, self.line_width)
        image = cv2.line(image, self.graph_top_left, self.graph_bottom_left, self.line_color, self.line_width)
        image = cv2.line(image, self.graph_top_right, self.graph_bottom_right, self.line_color, self.line_width)
        return image

    def draw_log_info(self, image):
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
        graph_left = self.graph_top_left[0]
        graph_right = self.graph_top_right[0]
        graph_top = self.graph_top_left[1]
        for i, channel in enumerate(self.channels):
            channel.update_baseline(self.graph_height, len(self.channels), graph_top)
            image = cv2.line(image, (graph_left, channel.baseline), (graph_right, channel.baseline), self.line_color, self.line_width)
        return image

    def draw_channel_signals(self, image):
        app = QApplication(sys.argv)
        screen = app.screens()[0]
        dpi = screen.physicalDotsPerInch()
        print(f"dpi {dpi}")
        app.quit()
        ppc = dpi * 2.54
        graph_left = self.graph_top_left[0]
        for channel in range(len(self.channels)):
            channel = self.channels[channel]
            if isinstance(channel.data, numpy.ndarray):
                num_samples = channel.data.size
                spacing = self.graph_width / num_samples
                for point in range(channel.data.size-1):
                    x_1 = int(int(point * spacing) + graph_left)
                    y_1 = int(((float(channel.voltspercm)/dpi) * channel.data[point]) + channel.baseline)
                    x_2 = int(int((point+1) * spacing) + graph_left)
                    y_2 = int(((float(channel.voltspercm)/dpi) * channel.data[point+1]) + channel.baseline)
                    image = cv2.line(image, (x_1, y_1), (x_2, y_2), (255, 0, 0), 1)
