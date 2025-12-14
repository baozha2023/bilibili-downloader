import sys
import argparse
import webview

def main():
    parser = argparse.ArgumentParser(description="Bilibili Player Loader")
    parser.add_argument("--url", required=True, help="Video URL")
    parser.add_argument("--title", default="Bilibili Player", help="Window Title")
    args = parser.parse_args()

    # Create a window
    # width=1280, height=720
    webview.create_window(args.title, args.url, width=1280, height=720)
    webview.start()

if __name__ == "__main__":
    main()
