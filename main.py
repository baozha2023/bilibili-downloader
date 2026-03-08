import os
import ctypes
import sys

# 防止 OpenMP / MKL 冲突（PyQt5 常见杀手）
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
# =============================================================================
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bilibili_downloader')


def global_exception_handler(exctype, value, tb):
    logger.error("Uncaught exception", exc_info=(exctype, value, tb))
    import traceback
    traceback.print_exception(exctype, value, tb)


sys.excepthook = global_exception_handler


def start_gui():
    """启动图形用户界面"""
    # Imports for GUI
    import ctypes
    from PyQt5.QtWidgets import QApplication
    from ui.splash_screen import SplashScreen

    app_version = None
    try:
        from core.config import APP_VERSION as app_version
        myappid = f'bilibili.downloader.gui.{app_version}'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        logger.warning(f"Failed to set AppUserModelID: {e}")

    app = QApplication(sys.argv)

    # 启动画面 / Splash Screen
    splash_img_path = "resource/logo.jpg"

    # PyInstaller path handling
    if hasattr(sys, '_MEIPASS'):
        splash_img_path = os.path.join(sys._MEIPASS, "resource", "logo.jpg")
    elif not os.path.exists(splash_img_path):
        # 如果 logo.jpg 不存在，尝试 png
        splash_img_path = "resource/logo.png"
        if hasattr(sys, '_MEIPASS'):
            splash_img_path = os.path.join(sys._MEIPASS, "resource", "logo.png")

    splash = SplashScreen(splash_img_path)
    splash.show()
    app.processEvents()

    if not app_version:
        app_version = "Unknown"
    splash.set_version(app_version)

    # 启动后台任务
    from ui.startup_worker import StartupWorker
    worker = StartupWorker()

    def on_startup_finished(context):
        try:
            # Main window module is likely already imported in worker
            from ui.main_window import BilibiliDesktop
            window = BilibiliDesktop(context=context)
            window.show()
            splash.close()
        except Exception as e:
            logger.error(f"Failed to start main window: {e}")
            sys.exit(1)

    worker.progress_signal.connect(splash.set_progress)
    worker.finished_signal.connect(on_startup_finished)
    worker.start()

    sys.exit(app.exec_())


def start_cli(args):
    """启动命令行界面"""
    from core.cli import CliHandler
    cli = CliHandler()
    cli.handle_args(args)


def main():
    """主函数"""
    import argparse
    try:
        from core.config import APP_VERSION
    except ImportError:
        APP_VERSION = "Unknown"

    parser = argparse.ArgumentParser(description=f'bilibiliDownloader {APP_VERSION}')
    parser.add_argument('-g', '--gui', action='store_true',
                        help='启动图形用户界面')
    parser.add_argument('-p', '--popular', action='store_true',
                        help='爬取热门视频')
    parser.add_argument('-v', '--video', type=str,
                        help='爬取指定BV号视频的详细信息')
    parser.add_argument('-d', '--download', type=str,
                        help='下载指定BV号的视频')
    parser.add_argument('--pages', type=int,
                        help='指定爬取的页数，用于热门视频')
    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {APP_VERSION}')

    parser.add_argument('--player-mode', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--player-url', help=argparse.SUPPRESS)
    parser.add_argument('--player-title', help=argparse.SUPPRESS)
    parser.add_argument('--player-cookies', help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args.player_mode:
        try:
            from core.player_loader import run_player
            run_player(args.player_url, args.player_title, args.player_cookies)
        except Exception as e:
            logger.error(f"Failed to start player: {e}")
        return

    if args.gui or len(sys.argv) == 1:
        start_gui()
    else:
        start_cli(args)


if __name__ == "__main__":
    main()
