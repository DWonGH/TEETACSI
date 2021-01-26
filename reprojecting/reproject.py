import argparse

from playback_analysis import PlayBack


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="A directory containing the UI and eye tracking data.")
    parser.add_argument("--playback", dest='playback', action='store_true', help="Playback and view the recording")
    parser.add_argument("--video", dest='video', action='store_true', help="Create a video file from the recording")
    parser.add_argument("--signals", dest="signals", action="store_true", help="Reproject and track the eeg signals instead of baselines")
    parser.add_argument("--all", dest='all', action='store_true', help="Create a video for each recording in the mirror directory")
    args = parser.parse_args()

    # Debugging
    # input_dir = r'E:\computer_science\living_lab\2020TEETACSI\Tests\test6\26-01-2021-05-09-32'
    # args.input = input_dir
    # args.playback = True
    # args.video = True
    # args.signals = False
    print(f"Running TEETACSI data processing")
    playback = PlayBack(args.input, args.playback, args.video, args.signals)
    playback.process()
    playback.finish()
    print(f"Done")