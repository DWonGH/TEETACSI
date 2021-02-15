import argparse

from playback_analysis import PlayBack


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="A directory containing the UI and eye tracking data.")
    parser.add_argument("--playback", dest='playback', action='store_true', help="Playback and view the recording")
    parser.add_argument("--video", dest='video', action='store_true', help="Create a video file from the recording")
    parser.add_argument("--ui", dest="ui", action="store_true", help="Process UI tracking data only")

    # The signals option has more work to do to before it is stable. Issues will likely occur when loading timescales
    # larger than the size of the recording, and will not track signals when zoomed in past 1msec per page
    parser.add_argument("--signals", dest="signals", action="store_true", help="Reproject and track the eeg signals instead of baselines")
    #parser.add_argument("--all", dest='all', action='store_true', help="Create a video for each recording in the mirror directory")
    args = parser.parse_args()

    # Debugging

    # args.input = input_dir
    # args.playback = True
    # args.signals = True
    # args.video = True


    print(f"Running TEETACSI data processing")
    playback = PlayBack(args.input, args.playback, args.video, args.signals, args.ui)
    playback.finish()
    print(f"Done")