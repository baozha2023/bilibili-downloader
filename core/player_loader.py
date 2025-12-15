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
            
            # Small delay to ensure cookies are set
            time.sleep(0.5)
            
        # Load the actual video URL
        window.load_url(args.url)

    # Create a window
    # Start with bilibili homepage to allow cookie setting
    window = webview.create_window(args.title, "https://www.bilibili.com/", width=1280, height=720)
    webview.start(init_window, window)

if __name__ == "__main__":
    main()
