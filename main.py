#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
哔哩哔哩视频下载器主程序入口
v3.1
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
    crawler = BilibiliCrawler()
    
    if args.popular:
        # 爬取热门视频
        pages = args.pages or 3
        logger.info(f"正在爬取热门视频，页数：{pages}")
        crawler.crawl_popular_videos(pages)
    
    elif args.video:
        # 获取视频信息
        bvid = args.video
        logger.info(f"正在获取视频信息：{bvid}")
        crawler.crawl_video_details(bvid)
    
    elif args.download:
        # 下载视频
        bvid = args.download
        logger.info(f"正在下载视频：{bvid}")
        crawler.download_video(bvid)
        print(f"\n下载目录: {os.path.abspath(crawler.download_dir)}")
    
    else:
        # 如果没有指定参数，则启动交互式命令行
        run_interactive_cli()

def run_interactive_cli():
    """运行交互式命令行界面"""
    crawler = BilibiliCrawler()
    
    while True:
        print("\n哔哩哔哩视频下载器 v3.1 - 命令行模式")
        print("1. 爬取热门视频")
        print("2. 爬取指定视频详情")
        print("3. 下载视频")
        print("0. 退出")
        
        choice = input("请选择功能 (0-3): ")
        
        if choice == '1':
            try:
                val = input("请输入要爬取的页数 (默认3页): ")
                pages = int(val) if val else 3
                crawler.crawl_popular_videos(pages)
            except ValueError:
                print("输入无效，使用默认值3")
                crawler.crawl_popular_videos(3)
        
        elif choice == '2':
            bvid = input("请输入视频BV号 (例如: BV1xx411c7mD): ")
            if bvid:
                crawler.crawl_video_details(bvid)
        
        elif choice == '3':
            bvid = input("请输入要下载的视频BV号 (例如: BV1xx411c7mD): ")
            if bvid:
                crawler.download_video(bvid)
                print(f"\n下载目录: {os.path.abspath(crawler.download_dir)}")
        
        elif choice == '0':
            print("感谢使用，再见！")
            break
        
        else:
            print("无效的选择，请重新输入")

def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='哔哩哔哩视频下载器 v3.1')
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
