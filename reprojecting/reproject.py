import argparse

from playback_analysis import PlayBack


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="A directory containing the UI and eye tracking data.")
    parser.add_argument("--playback", dest='playback', action='store_true', help="Playback and view the recording")
    parser.add_argument("--video", dest='video', action='store_true', help="Create a video file from the recording")
    parser.add_argument("--signals", dest="signals", action="store_true", help="Reproject and track the eeg signals instead of baselines")
    parser.add_argument("--ui", dest="ui", action="store_true", help="Process UI tracking data only")
    parser.add_argument("--all", dest='all', action='store_true', help="Create a video for each recording in the mirror directory")
    args = parser.parse_args()

    # Debugging
    # input_dir = r'D:\teetacsi_local\TEETACSI\data\analysis_sessions\27-01-2021_13-50\v2.0.0\edf\eval\abnormal\01_tcp_ar\007\00000768\s003_2012_04_06\27-01-2021-13-59-42'
    # args.input = input_dir
    # args.playback = True
    # args.video = False
    # args.signals = False
    # args.ui = True
    print(f"Running TEETACSI data processing")
    playback = PlayBack(args.input, args.playback, args.video, args.signals, args.ui)
    playback.finish()
    print(f"Done")