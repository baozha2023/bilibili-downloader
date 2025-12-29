import os
import re
import shutil
import logging
import xml.etree.ElementTree as ET
import json

from .network import NetworkManager
from .api import BilibiliAPI
from .downloader import Downloader
from .processor import MediaProcessor
from .utils import parse_danmaku_xml

# 配置日志
logger = logging.getLogger('bilibili_crawler') # 保持旧名称以便兼容日志配置

class BilibiliCrawler:
    """
    核心控制器：协调网络、API、下载和处理
    """
    def __init__(self, use_proxy=False, cookies=None):
        self.data_dir = 'bilibili_data'
        self.download_dir = os.path.join(self.data_dir, 'downloads')
        self._init_dirs()
        
        # 初始化组件
        self.network = NetworkManager(use_proxy, cookies)
        self.api = BilibiliAPI(self.network)
        self.downloader = Downloader(self.network)
        self._processor = None
        
    @property
    def processor(self):
        if self._processor is None:
            self._processor = MediaProcessor()
        return self._processor
        
    @property
    def ffmpeg_available(self):
        return self.processor.ffmpeg_available
        
    @property
    def ffmpeg_path(self):
        return self.processor.ffmpeg_path
        
    def _init_dirs(self):
        if not os.path.exists(self.data_dir): os.makedirs(self.data_dir)
        if not os.path.exists(self.download_dir): os.makedirs(self.download_dir)
        
    @property
    def cookies(self):
        return self.network.cookies
    
    @cookies.setter
    def cookies(self, value):
        self.network.cookies = value
        
    @property
    def use_proxy(self):
        return self.network.use_proxy
        
    @use_proxy.setter
    def use_proxy(self, value):
        self.network.use_proxy = value
        
    @property
    def proxies(self):
        return self.network.proxies
        
    @proxies.setter
    def proxies(self, value):
        self.network.proxies = value
        
    # --- 代理 API 方法 ---
    def get_popular_videos(self, page=1):
        return self.api.get_popular_videos(page)
        
    def get_video_info(self, bvid):
        return self.api.get_video_info(bvid)

    def get_video_tags(self, aid):
        return self.api.get_video_tags(aid)
        
    def get_video_comments(self, aid, page=1):
        return self.api.get_video_comments(aid, page)
        
    def get_video_danmaku(self, cid):
        xml_bytes = self.api.get_video_danmaku(cid)
        return parse_danmaku_xml(xml_bytes)

    def get_history(self, page=1):
        return self.api.get_history(page)
        
    def get_favorite_resources(self, media_id, page=1):
        return self.api.get_favorite_resources(media_id, page)
            
    def make_request(self, *args, **kwargs):
        return self.network.make_request(*args, **kwargs)

    # --- 核心业务逻辑 ---
    def download_video(self, bvid, video_progress_callback=None, audio_progress_callback=None,
                      merge_progress_callback=None, danmaku_progress_callback=None, 
                      comments_progress_callback=None, should_merge=True, delete_original=True,
                      download_danmaku=False, download_comments=False,
                      video_quality='1080p', video_codec='H.264/AVC', audio_quality='高音质 (Hi-Res/Dolby)',
                      stop_event=None):
        """下载视频主流程"""
        
        # 1. 获取下载链接
        print(f"正在获取视频 {bvid} 的下载链接 (画质: {video_quality}, 编码: {video_codec})...")
        if self._check_stop(stop_event): return self._get_cancel_result()
            
        download_info = self.api.get_video_download_url(bvid, video_quality, video_codec, audio_quality)
        if not download_info:
            return {"download_success": False, "message": "无法获取下载地址"}
            
        # 2. 准备目录和路径
        title = download_info['title']
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
        video_dir = os.path.join(self.download_dir, safe_title)
        if not os.path.exists(video_dir): os.makedirs(video_dir)
        
        output_path = os.path.join(video_dir, f"{safe_title}.mp4")
        
        # 3. 检查是否已存在
        if self._is_file_exists(output_path):
            logger.info(f"视频已存在: {output_path}")
            return {
                "download_success": True, "merge_success": True,
                "output_path": output_path, "download_dir": video_dir,
                "message": "视频已存在，跳过下载"
            }
        
        # 4. 下载流媒体 (视频和音频)
        video_url = download_info['video_url']
        video_path = os.path.join(video_dir, f"{safe_title}_video.mp4")
        audio_url = download_info.get('audio_url')
        audio_path = os.path.join(video_dir, f"{safe_title}_audio.m4a") if audio_url else None
        
        if not self._download_streams(video_url, video_path, audio_url, audio_path, safe_title, 
                                      video_progress_callback, audio_progress_callback, stop_event):
            if self._check_stop(stop_event):
                self._cleanup_dir(video_dir)
                return self._get_cancel_result(message="下载已取消")
            return self._get_cancel_result(message="流媒体下载失败")

        # 5. 下载弹幕和评论
        if not self._download_metadata(download_info, video_dir, safe_title, download_danmaku, 
                                       download_comments, danmaku_progress_callback, 
                                       comments_progress_callback, stop_event):
            if self._check_stop(stop_event):
                self._cleanup_dir(video_dir)
                return self._get_cancel_result(message="下载已取消")
            return self._get_cancel_result(message="弹幕和评论下载失败")
        
        # 6. 合并/处理
        merge_success = self._process_media(video_path, audio_path, output_path, should_merge, 
                                            delete_original, merge_progress_callback, stop_event)
        
        if self._check_stop(stop_event):
            self._cleanup_dir(video_dir)
            return self._get_cancel_result(message="下载已取消")
            
        if not should_merge:
            output_path = None
            
        return {
            "download_success": True,
            "merge_success": merge_success,
            "video_path": video_path,
            "audio_path": audio_path,
            "output_path": output_path,
            "download_dir": video_dir,
            "ffmpeg_available": self.processor.ffmpeg_available
        }

    def _cleanup_dir(self, dir_path):
        """清理目录"""
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                logger.info(f"已清理目录: {dir_path}")
            except Exception as e:
                logger.error(f"清理目录失败: {e}")

    def _check_stop(self, stop_event):
        return stop_event and stop_event.is_set()

    def _get_cancel_result(self, message="下载已取消"):
        return {"download_success": False, "message": message}

    def _is_file_exists(self, path):
        return os.path.exists(path) and os.path.getsize(path) > 1024 * 1024

    def _download_streams(self, video_url, video_path, audio_url, audio_path, safe_title, 
                          video_cb, audio_cb, stop_event):
        # 下载视频
        if not self._download_stream(video_url, video_path, f"{safe_title} - 视频", video_cb, stop_event):
            return False
        
        # 下载音频
        if audio_url:
            if not self._download_stream(audio_url, audio_path, f"{safe_title} - 音频", audio_cb, stop_event):
                # 清理视频文件
                if os.path.exists(video_path):
                    try: os.remove(video_path)
                    except: pass
                return False
        return True

    def _download_metadata(self, download_info, video_dir, safe_title, download_danmaku, 
                           download_comments, danmaku_cb, comments_cb, stop_event):
        cid = download_info['video_info'].get('cid')
        aid = download_info['video_info'].get('aid')
        
        if download_danmaku and cid:
            if not self._save_danmaku(cid, video_dir, safe_title, danmaku_cb, stop_event):
                return False
            
        if download_comments and aid:
            if not self._save_comments(aid, video_dir, safe_title, comments_cb, stop_event):
                return False
        return True

    def _process_media(self, video_path, audio_path, output_path, should_merge, 
                       delete_original, merge_cb, stop_event):
        if not (should_merge and audio_path):
            return False
            
        if self._check_stop(stop_event):
            return False

        print("开始合并视频...")
        merge_success = self.processor.merge_video_audio(
            video_path, audio_path, output_path, 
            progress_callback=merge_cb
        )
        
        if merge_success and delete_original:
            try:
                logger.info(f"删除原始文件: {video_path}, {audio_path}")
                os.remove(video_path)
                os.remove(audio_path)
            except Exception as e: 
                logger.error(f"删除原始文件失败: {e}")
        return merge_success

    def _download_stream(self, url, path, desc, progress_callback, stop_event):
        if stop_event and stop_event.is_set(): return False
        success = self.downloader.download_file(url, path, desc, progress_callback, stop_event=stop_event)
        if not success and stop_event and stop_event.is_set():
             if os.path.exists(path):
                try: os.remove(path)
                except: pass
        return success

    def _save_danmaku(self, cid, video_dir, safe_title, progress_callback, stop_event):
        """保存弹幕"""
        if stop_event and stop_event.is_set(): return False
        
        logger.info("正在获取视频弹幕...")
        if progress_callback: progress_callback(0, 100)
        danmaku_list = self.get_video_danmaku(cid)
        if danmaku_list:
            danmaku_path = os.path.join(video_dir, f"{safe_title}_danmaku.json")
            try:

                with open(danmaku_path, 'w', encoding='utf-8') as f:
                    json.dump(danmaku_list, f, ensure_ascii=False, indent=2)
                logger.info(f"弹幕已保存到: {danmaku_path}")
            except Exception as e:
                logger.error(f"保存弹幕失败: {e}")
        if progress_callback: progress_callback(100, 100)
        return True

    def _save_comments(self, aid, video_dir, safe_title, progress_callback, stop_event):
        """保存评论"""
        if stop_event and stop_event.is_set(): return False
        
        logger.info("正在获取视频评论...")
        if progress_callback: progress_callback(0, 100)
        
        all_comments = []
        for page in range(1, 6):
            if stop_event and stop_event.is_set(): return False
            comments = self.get_video_comments(aid, page)
            if comments: all_comments.extend(comments)
            else: break
            if progress_callback: progress_callback(page*20, 100)
            
        if all_comments:
            comments_path = os.path.join(video_dir, f"{safe_title}_comments.json")
            try:
                with open(comments_path, 'w', encoding='utf-8') as f:
                    json.dump(all_comments, f, ensure_ascii=False, indent=2)
                logger.info(f"评论已保存到: {comments_path}")
            except Exception as e:
                logger.error(f"保存评论失败: {e}")
        if progress_callback: progress_callback(100, 100)
        return True

    def save_to_json(self, data, filename):
        path = os.path.join(self.data_dir, f"{filename}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    def crawl_popular_videos(self, pages=3):
        videos = []
        for p in range(1, pages+1):
            v = self.get_popular_videos(p)
            if v: videos.extend(v)
        if videos:
            self.save_to_json(videos, "popular_videos")
        return videos
        
    def crawl_video_details(self, bvid):
        info = self.get_video_info(bvid)
        if info:
            self.save_to_json(info, f"video_{bvid}")
        return info
