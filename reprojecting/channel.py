from lxml import etree
import os
from io import StringIO, BytesIO
from filter_class import FidFilter


class Channel:

    def __init__(self, channel_id, label, factor, voltspercm, screen_offset, polarity, data=None):
        self.id = channel_id
        self.label = label
        self.factor = factor
        self.voltspercm = voltspercm
        self.screen_offset = screen_offset
        self.polarity = polarity
        self.fid_filters = []
        self.data = data
        self.baseline = None

    def update_baseline(self, graph_height, num_channels, graph_top):
        step = graph_height / (num_channels + 1)
        self.baseline = step
        self.baseline += (self.id * int(step)) + (int(graph_top) + int(float(self.screen_offset)))
        self.baseline = int(self.baseline)

    def apply_filters(self):
        pass

    def apply_amplitude(self):
        pass

    def print_channel(self):
        print(f"id: {self.id}")
        print(f"label: {self.label}")
        print(f"factor: {self.factor}")
        print(f"voltspercm: {self.voltspercm}")
        print(f"screen_offset: {self.screen_offset}")
        print(f"polarity: {self.polarity}")
        print(f"filter_cnt: {self.filter_cnt}")
