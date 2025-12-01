import os
import re
import logging
from .network import NetworkManager
from .api import BilibiliAPI
from .downloader import Downloader
from .processor import MediaProcessor

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
        self.processor = MediaProcessor()
        
        # 兼容旧属性
        self.ffmpeg_available = self.processor.ffmpeg_available
        self.ffmpeg_path = self.processor.ffmpeg_path
        
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
        
    def get_video_comments(self, aid, page=1):
        return self.api.get_video_comments(aid, page)
        
    def get_video_danmaku(self, cid):
        # XML 解析逻辑保留在这里或移入API
        # 这里简单处理，直接返回解析后的列表（旧代码逻辑）
        # 为了简化，我们暂时复用旧代码的解析逻辑，或者如果不需要弹幕展示，只下载
        xml_bytes = self.api.get_video_danmaku(cid)
        if not xml_bytes: return []
        
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_bytes)
            danmaku_list = []
            for d in root.findall('./d'):
                p_attr = d.get('p', '')
                text = d.text or ''
                if p_attr and text:
                    p_parts = p_attr.split(',')
                    if len(p_parts) >= 8:
                        danmaku_list.append({
                            'time': float(p_parts[0]),
                            'mode': int(p_parts[1]),
                            'fontsize': int(p_parts[2]),
                            'color': int(p_parts[3]),
                            'timestamp': int(p_parts[4]),
                            'pool': int(p_parts[5]),
                            'user_id': p_parts[6],
                            'dmid': p_parts[7],
                            'text': text
                        })
            return danmaku_list
        except Exception as e:
            logger.error(f"解析弹幕失败: {e}")
            return []

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
                      remove_watermark=False, download_danmaku=False, download_comments=False,
                      video_quality='1080p', video_codec='H.264/AVC', audio_quality='高音质 (Hi-Res/Dolby)',
                      stop_event=None):
        """下载视频主流程"""
        
        # 1. 获取下载链接
        print(f"正在获取视频 {bvid} 的下载链接 (画质: {video_quality}, 编码: {video_codec})...")
        
        # 检查停止信号
        if stop_event and stop_event.is_set():
            return {"download_success": False, "message": "下载已取消"}
            
        download_info = self.api.get_video_download_url(bvid, video_quality, video_codec, audio_quality)
        if not download_info:
            return {"download_success": False, "message": "无法获取下载地址"}
            
        # 2. 准备目录
        title = download_info['title']
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
        video_dir = os.path.join(self.download_dir, safe_title)
        if not os.path.exists(video_dir): os.makedirs(video_dir)
        
        output_path = os.path.join(video_dir, f"{safe_title}.mp4")
        
        # 检查是否已存在
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1024 * 1024:
            logger.info(f"视频已存在: {output_path}")
            return {
                "download_success": True,
                "merge_success": True,
                "output_path": output_path,
                "download_dir": video_dir,
                "message": "视频已存在，跳过下载"
            }
        
        # 3. 下载视频流
        video_url = download_info['video_url']
        video_path = os.path.join(video_dir, f"{safe_title}_video.mp4")
        print("开始下载视频流...")
        
        # 检查停止信号
        if stop_event and stop_event.is_set():
            return {"download_success": False, "message": "下载已取消"}
            
        video_success = self.downloader.download_file(video_url, video_path, f"{safe_title} - 视频", video_progress_callback, stop_event=stop_event)
        
        # 如果被中断
        if not video_success and stop_event and stop_event.is_set():
            # 清理文件
            if os.path.exists(video_path):
                try: os.remove(video_path)
                except: pass
            return {"download_success": False, "message": "下载已取消"}

        # 4. 下载音频流
        audio_url = download_info.get('audio_url')
        audio_path = None
        audio_success = True
        if audio_url:
            audio_path = os.path.join(video_dir, f"{safe_title}_audio.m4a")
            print("开始下载音频流...")
            audio_success = self.downloader.download_file(audio_url, audio_path, f"{safe_title} - 音频", audio_progress_callback, stop_event=stop_event)
            
            # 如果被中断
            if not audio_success and stop_event and stop_event.is_set():
                # 清理文件
                if os.path.exists(video_path):
                    try: os.remove(video_path)
                    except: pass
                if os.path.exists(audio_path):
                    try: os.remove(audio_path)
                    except: pass
                return {"download_success": False, "message": "下载已取消"}

        if not video_success or not audio_success:
            return {"download_success": False, "message": "文件下载失败"}
            
        # 5. 保存元数据 (Info, Danmaku, Comments)
        cid = download_info['video_info'].get('cid')
        aid = download_info['video_info'].get('aid')
        
        if download_danmaku and cid:
            # 检查停止信号
            if stop_event and stop_event.is_set():
                 return {"download_success": False, "message": "下载已取消"}

            print("正在获取视频弹幕...")
            if danmaku_progress_callback: danmaku_progress_callback(0, 100)
            danmaku_list = self.get_video_danmaku(cid)
            if danmaku_list:
                danmaku_path = os.path.join(video_dir, f"{safe_title}_danmaku.json")
                self.save_to_json(danmaku_list, f"{safe_title}_danmaku") # save_to_json会加.json后缀并存在data_dir
                # 为了保持一致性，我们手动保存到video_dir
                try:
                    import json
                    with open(danmaku_path, 'w', encoding='utf-8') as f:
                        json.dump(danmaku_list, f, ensure_ascii=False, indent=2)
                    print(f"弹幕已保存到: {danmaku_path}")
                except Exception as e:
                    logger.error(f"保存弹幕失败: {e}")
            if danmaku_progress_callback: danmaku_progress_callback(100, 100)
            
        if download_comments and aid:
            # 检查停止信号
            if stop_event and stop_event.is_set():
                 return {"download_success": False, "message": "下载已取消"}

            print("正在获取视频评论...")
            if comments_progress_callback: comments_progress_callback(0, 100)
            # 获取前5页
            all_comments = []
            for page in range(1, 6):
                # 检查停止信号
                if stop_event and stop_event.is_set():
                    return {"download_success": False, "message": "下载已取消"}
                    
                comments = self.get_video_comments(aid, page)
                if comments: all_comments.extend(comments)
                else: break
                if comments_progress_callback: comments_progress_callback(page*20, 100)
                
            if all_comments:
                comments_path = os.path.join(video_dir, f"{safe_title}_comments.json")
                try:
                    import json
                    with open(comments_path, 'w', encoding='utf-8') as f:
                        json.dump(all_comments, f, ensure_ascii=False, indent=2)
                    print(f"评论已保存到: {comments_path}")
                except Exception as e:
                    logger.error(f"保存评论失败: {e}")
            if comments_progress_callback: comments_progress_callback(100, 100)
        
        # 6. 合并/处理
        merge_success = False
        
        if should_merge and audio_path:
            # 检查停止信号
            if stop_event and stop_event.is_set():
                 return {"download_success": False, "message": "下载已取消"}

            print("开始合并视频...")
            merge_success = self.processor.merge_video_audio(
                video_path, audio_path, output_path, 
                remove_watermark=remove_watermark,
                progress_callback=merge_progress_callback
            )
            
            if merge_success and delete_original:
                try:
                    logger.info(f"删除原始文件: {video_path}, {audio_path}")
                    os.remove(video_path)
                    os.remove(audio_path)
                except Exception as e: 
                    logger.error(f"删除原始文件失败: {e}")
        else:
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

    # 兼容旧方法名
    def download_file(self, *args, **kwargs):
        return self.downloader.download_file(*args, **kwargs)
        
    def save_to_json(self, data, filename):
        # 简易实现
        import json
        path = os.path.join(self.data_dir, f"{filename}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    def crawl_popular_videos(self, pages=3):
        # 复用API
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
