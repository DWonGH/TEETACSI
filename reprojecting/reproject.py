import argparse

from playback_analysis import PlayBack


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="A directory containing the UI and eye tracking data.")
    parser.add_argument("--playback", dest='playback', action='store_true', help="Playback and view the recording")
    parser.add_argument("--video", dest='video', action='store_true', help="Create a video file from the recording")
    parser.add_argument("--all", dest='all', action='store_true', help="Create a video for each recording in the mirror directory")
    args = parser.parse_args()

    print(f"Running TEETACSI data processing")
    playback = PlayBack()
    playback.setup(args.input)
    # playback.playback(args.playback, args.video, args.all)
    playback.process(args.playback, args.video)
    playback.finish()
    print(f"Done")