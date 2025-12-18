# -*- coding: utf-8 -*-
import os
import sys
from core.crawler import BilibiliCrawler
import logging

logger = logging.getLogger('bilibili_cli')

class CliHandler:
    """Handles Command Line Interface operations"""
    
    def __init__(self):
        self.crawler = BilibiliCrawler()
        
    def handle_args(self, args):
        """Handle command line arguments"""
        if args.popular:
            # Crawl popular videos
            pages = args.pages or 3
            logger.info(f"正在爬取热门视频，页数：{pages}")
            self.crawler.crawl_popular_videos(pages)
        
        elif args.video:
            # Get video details
            bvid = args.video
            logger.info(f"正在获取视频信息：{bvid}")
            self.crawler.crawl_video_details(bvid)
        
        elif args.download:
            # Download video
            bvid = args.download
            logger.info(f"正在下载视频：{bvid}")
            self.crawler.download_video(bvid)
            print(f"\n下载目录: {os.path.abspath(self.crawler.download_dir)}")
        
        else:
            # Interactive mode
            self.run_interactive()

    def run_interactive(self):
        """Run interactive CLI"""
        while True:
            print("\nbilibiliDownloader v4.9 - 命令行模式")
            print("1. 爬取热门视频")
            print("2. 爬取指定视频详情")
            print("3. 下载视频")
            print("0. 退出")
            
            choice = input("请选择功能 (0-3): ")
            
            if choice == '1':
                try:
                    val = input("请输入要爬取的页数 (默认3页): ")
                    pages = int(val) if val else 3
                    self.crawler.crawl_popular_videos(pages)
                except ValueError:
                    print("输入无效，使用默认值3")
                    self.crawler.crawl_popular_videos(3)
            
            elif choice == '2':
                bvid = input("请输入视频BV号 (例如: BV1xx411c7mD): ")
                if bvid:
                    self.crawler.crawl_video_details(bvid)
            
            elif choice == '3':
                bvid = input("请输入要下载的视频BV号 (例如: BV1xx411c7mD): ")
                if bvid:
                    self.crawler.download_video(bvid)
                    print(f"\n下载目录: {os.path.abspath(self.crawler.download_dir)}")
            
            elif choice == '0':
                print("感谢使用，再见！")
                break
            
            else:
                print("无效的选择，请重新输入")
