import sys
import argparse
import json
import time
import ctypes
import webbrowser
import logging

# Configure logger
logger = logging.getLogger('bilibili_player')

def check_webview2():
    """Check if WebView2 Runtime is installed via Registry"""
    try:
        import winreg
        # Check machine-wide installation
        key_path = r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                return True
        except:
            pass
            
        # Check per-user installation
        key_path = r"Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                return True
        except:
            pass
            
        return False
    except Exception as e:
        logger.error(f"Error checking WebView2: {e}")
        return False # Assume false if registry check fails

def show_webview2_error():
    """Show error message and guide user to download"""
    MB_ICONERROR = 0x10
    MB_YESNO = 0x04
    IDYES = 6
    
    title = "组件缺失"
    message = "实时观看功能需要 Microsoft Edge WebView2 运行时。\n\n当前系统未检测到该组件，是否立即打开下载页面？"
    
    # Use ctypes to show native message box
    result = ctypes.windll.user32.MessageBoxW(0, message, title, MB_ICONERROR | MB_YESNO)
    if result == IDYES:
        webbrowser.open("https://go.microsoft.com/fwlink/p/?LinkId=2124703")

def run_player(url, title="Bilibili Player", cookies_json=None):
    # 1. Check WebView2 availability on Windows
    if sys.platform == 'win32' and not check_webview2():
        show_webview2_error()
        return

    # 2. Import webview here to avoid import errors if dependency is missing in main process
    try:
        import webview
    except ImportError:
        ctypes.windll.user32.MessageBoxW(0, "缺少 pywebview 依赖库，无法启动播放器。", "错误", 0x10)
        return

    cookies = {}
    if cookies_json:
        try:
            cookies = json.loads(cookies_json)
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
        window.load_url(url)
        
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
    window = webview.create_window(title, "https://www.bilibili.com/", width=1280, height=720)
    webview.start(init_window, window)

def main():
    parser = argparse.ArgumentParser(description="Bilibili Player Loader")
    parser.add_argument("--url", required=True, help="Video URL")
    parser.add_argument("--title", default="Bilibili Player", help="Window Title")
    parser.add_argument("--cookies", help="JSON cookies")
    args = parser.parse_args()
    
    run_player(args.url, args.title, args.cookies)

if __name__ == "__main__":
    main()
