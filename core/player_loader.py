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
            # Wait a bit for window to be ready
            time.sleep(1)
            # Inject cookies
            # Note: We are on player.bilibili.com, so we can set cookies for .bilibili.com
            for k, v in cookies.items():
                # Basic sanitation
                k = k.replace('"', '\\"')
                v = v.replace('"', '\\"')
                js = f'document.cookie = "{k}={v}; domain=.bilibili.com; path=/; expires=Fri, 31 Dec 9999 23:59:59 GMT";'
                try:
                    window.evaluate_js(js)
                except:
                    pass
            
            # Reload to apply cookies to the request
            # We add a timestamp to force reload if needed, but load_url should be enough
            window.load_url(args.url)

    # Create a window
    # width=1280, height=720
    window = webview.create_window(args.title, args.url, width=1280, height=720)
    webview.start(init_window, window)

if __name__ == "__main__":
    main()
