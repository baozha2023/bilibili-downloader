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
        
        # Auto Web Fullscreen Logic
        # Wait for page to load and player to initialize
        time.sleep(3)
        
        # JS to find and click web fullscreen button
        js_fullscreen = """
        (function() {
            var attempts = 0;
            var maxAttempts = 20; // Try for 20 seconds
            
            var checkTimer = setInterval(function() {
                attempts++;
                
                // Try standard class
                var btn = document.querySelector('.bpx-player-ctrl-web');
                
                // Try aria-label
                if (!btn) {
                    btn = document.querySelector('[aria-label="网页全屏"]');
                }
                
                if (btn) {
                    console.log("Found web fullscreen button, clicking...");
                    btn.click();
                    clearInterval(checkTimer);
                } else if (attempts >= maxAttempts) {
                    console.log("Could not find web fullscreen button");
                    clearInterval(checkTimer);
                }
            }, 1000);
        })();
        """
        try:
            window.evaluate_js(js_fullscreen)
        except Exception as e:
            print(f"Failed to inject fullscreen script: {e}")

    # Create a window
    # Start with bilibili homepage to allow cookie setting
    window = webview.create_window(args.title, "https://www.bilibili.com/", width=1280, height=720)
    webview.start(init_window, window)

if __name__ == "__main__":
    main()
