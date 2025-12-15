import sys
import argparse
import webview
import json
import time

def main():
    parser = argparse.ArgumentParser(description="Bilibili Player Loader")
    parser.add_argument("--url", required=True, help="Video URL")
    parser.add_argument("--title", default="Bilibili Player", help="Window Title")
    parser.add_argument("--cookies", help="JSON cookies")
    args = parser.parse_args()

    cookies = {}
    if args.cookies:
        try:
            cookies = json.loads(args.cookies)
        except:
            pass

    def init_window(window):
        if cookies:
            # Load a page on the main domain first to set cookies effectively
            # window.load_url("https://www.bilibili.com/robots.txt")
            # time.sleep(1)
            
            # Inject cookies
            for k, v in cookies.items():
                k = k.replace('"', '\\"')
                v = v.replace('"', '\\"')
                # Set cookie for .bilibili.com
                js = f'document.cookie = "{k}={v}; domain=.bilibili.com; path=/; expires=Fri, 31 Dec 9999 23:59:59 GMT";'
                try:
                    window.evaluate_js(js)
                except:
                    pass
            
            # Force reload to apply cookies
            # time.sleep(0.5)
            
        # Load the actual video URL
        window.load_url(args.url)

    # Create a window
    # Start with a dummy page on bilibili.com to allow cookie setting
    # Then init_window will load the actual URL
    window = webview.create_window(args.title, "https://www.bilibili.com/robots.txt", width=1280, height=720)
    webview.start(init_window, window)

if __name__ == "__main__":
    main()
