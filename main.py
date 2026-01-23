#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bilibiliDownloader主程序入口
"""
import ctypes
import sys
import argparse
import logging
import time
import os
import traceback
from PyQt5.QtWidgets import QApplication
# 导入项目模块
from core.cli import CliHandler
from core.config import APP_VERSION
from ui.splash_screen import SplashScreen
from ui.startup_worker import StartupWorker

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bilibili_downloader')

# Global exception handler
def global_exception_handler(exctype, value, tb):
    logger.error("Uncaught exception", exc_info=(exctype, value, tb))
    # 也可以弹窗显示错误，但如果在启动阶段可能无法显示
    traceback.print_exception(exctype, value, tb)

sys.excepthook = global_exception_handler

def start_gui():
    """启动图形用户界面"""
    try:
        # 设置AppUserModelID，确保任务栏图标正常显示
        myappid = f'bilibili.downloader.gui.{APP_VERSION}'
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
            
    splash = SplashScreen(splash_img_path, APP_VERSION)
    splash.show()
    
    # 启动后台任务
    worker = StartupWorker()
    
    # 定义启动完成后的回调
    def on_startup_finished(context):
        try:
            # 延迟导入 ui 模块
            from ui.main_window import BilibiliDesktop
            
            # 传递预加载的 context
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

    cli = CliHandler()
    cli.handle_args(args)

def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='bilibiliDownloader {APP_VERSION}')
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
    
    # 播放器模式参数 (用于子进程调用)
    parser.add_argument('--player-mode', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--player-url', help=argparse.SUPPRESS)
    parser.add_argument('--player-title', help=argparse.SUPPRESS)
    parser.add_argument('--player-cookies', help=argparse.SUPPRESS)
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 如果是播放器模式
    if args.player_mode:
        try:
            from core.player_loader import run_player
            run_player(args.player_url, args.player_title, args.player_cookies)
        except Exception as e:
            logger.error(f"Failed to start player: {e}")
        return

    # 如果指定了gui参数或者没有指定任何参数，则启动图形界面
    if args.gui or len(sys.argv) == 1:
        start_gui()
    else:
        # 否则启动命令行模式
        start_cli(args)

if __name__ == "__main__":
    main()
