from scipy import signal
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
        for f in self.fid_filters:
            if f.model == 0:
                btype = 'lowpass'
            elif f.model == 1:
                btype = 'highpass'
            elif f.model == 2:
                btype = 'bandpass'
            if f.ftype == 0:
                b, a = signal.butter(f.order, [f.low, f.high], btype=btype, analog=False, output='ba', fs=None)
                output = signal.filtfilt(b, a, self.data)

    def butter_lowpass_filter(self, data, cutoff_freq, nyq_freq, order=4):
        # Source: https://github.com/guillaume-chevalier/filtering-stft-and-laplace-transform
        b, a = self.butter_lowpass(cutoff_freq, nyq_freq, order=order)
        y = signal.filtfilt(b, a, data)
        return y

    @staticmethod
    def butter_lowpass(cutoff, nyq_freq, order=4):
        normal_cutoff = float(cutoff) / nyq_freq
        b, a = signal.butter(order, [normal_cutoff], btype='lowpass')
        return b, a

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
