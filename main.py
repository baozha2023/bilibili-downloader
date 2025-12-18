#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bilibiliDownloader主程序入口
v4.9
"""

import ctypes
import sys
import os
import argparse
import logging
from PyQt5.QtWidgets import QApplication

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bilibili_downloader')

# 导入项目模块
from ui.main_window import BilibiliDesktop
from core.crawler import BilibiliCrawler

def start_gui():
    """启动图形用户界面"""
    try:
        # 设置AppUserModelID，确保任务栏图标正常显示
        myappid = 'mycompany.myproduct.subproduct.version' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass
        
    from PyQt5.QtWidgets import QApplication
    from ui.main_window import BilibiliDesktop
    app = QApplication(sys.argv)
    window = BilibiliDesktop()
    window.show()
    sys.exit(app.exec_())

def start_cli(args):
    """启动命令行界面"""
    from core.cli import CliHandler
    cli = CliHandler()
    cli.handle_args(args)

def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='bilibiliDownloader v4.9')
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
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 如果指定了gui参数或者没有指定任何参数，则启动图形界面
    if args.gui or len(sys.argv) == 1:
        start_gui()
    else:
        # 否则启动命令行模式
        start_cli(args)

if __name__ == "__main__":
    main()
