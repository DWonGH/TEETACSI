import argparse

from playback_analysis import PlayBack


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="A directory containing the UI and eye tracking data.")
    parser.add_argument("--playback", dest='playback', action='store_true', help="Playback and view the recording")
    parser.add_argument("--video", dest='video', action='store_true', help="Create a video file from the recording")
    parser.add_argument("--all", dest='all', action='store_true', help="Create a video for each recording in the mirror directory")
    args = parser.parse_args()

    input_dir = "D:\\teetacsi_local\\2020-01-19-TEETACSI_TEST\\TEETACSI\\data\\analysis_sessions\\20-01-2021_19-23\\v2.0.0\\edf\\eval\\abnormal\\01_tcp_ar\\007\\00000768\\s003_2012_04_06\\20-01-2021-19-32-34"

    print(f"Running TEETACSI data processing")
    playback = PlayBack(input_dir, True, False)
    playback.process()
    playback.finish()
    print(f"Done")