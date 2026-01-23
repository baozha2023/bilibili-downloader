import time
import logging
import os
import traceback
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from threading import Event
from core.crawler import BilibiliCrawler

# 配置日志
logger = logging.getLogger('ui_workers')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class GenericWorker(QThread):
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(bool, object)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        def callback(current, total):
            self.progress_signal.emit(current, total)
            
        # Inject callback into kwargs
        self.kwargs['progress_callback'] = callback
        try:
            success, msg = self.func(*self.args, **self.kwargs)
            self.finished_signal.emit(success, msg)
        except Exception as e:
            self.finished_signal.emit(False, str(e))

class WorkerThread(QThread):
    """通用工作线程"""
    update_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(str, int, int)  # 进度类型(video/audio/merge)，当前进度，总进度
    error_signal = pyqtSignal(str, str)  # 错误消息，错误类型
    
    def __init__(self, task_type, params=None, config=None):
        super().__init__()
        self.task_type = task_type
        self.params = params or {}
        self.config = config or {}
        self.is_running = True
        self.stop_event = Event()
        
        # Initialize crawler with config
        use_proxy = self.config.get('use_proxy', False)
        cookies = self.config.get('cookies', None)
        self.crawler = BilibiliCrawler(use_proxy=use_proxy, cookies=cookies)
        
        # Apply other config
        if 'proxies' in self.config and self.config['proxies']:
            self.crawler.proxies = self.config['proxies']
            
        if 'data_dir' in self.config and self.config['data_dir']:
            self.crawler.data_dir = self.config['data_dir']
            self.crawler.download_dir = os.path.join(self.crawler.data_dir, 'downloads')
            if not os.path.exists(self.crawler.data_dir):
                os.makedirs(self.crawler.data_dir)
            if not os.path.exists(self.crawler.download_dir):
                os.makedirs(self.crawler.download_dir)
        
        # Allow overriding download_dir directly
        if 'download_dir' in self.config and self.config['download_dir']:
            self.crawler.download_dir = self.config['download_dir']
            if not os.path.exists(self.crawler.download_dir):
                os.makedirs(self.crawler.download_dir)
        
        # 设置重试次数
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_interval', 2)  # 秒
        
        # 设置超时时间
        self.timeout = self.config.get('timeout', 30)  # 秒
        
        # Update crawler config with thread-specific config
        if hasattr(self.crawler, 'network') and hasattr(self.crawler.network, 'config'):
            self.crawler.network.config.update({
                'max_retries': self.max_retries,
                'retry_interval': self.retry_delay,
                'timeout': self.timeout
            })
        
        # Task mapping
        self.task_map = {
            "popular_videos": self._get_popular_videos,
            "video_info": self._get_video_info,
            "download_video": self._download_video
        }
    
    def run(self):
        """线程主函数，根据任务类型执行不同操作"""
        result = {"status": "error", "data": None, "message": "未知错误"}
        
        # 记录开始时间
        start_time = time.time()
        self.start_time = start_time
        
        try:
            # 设置超时检查
            self.timeout_timer = QTimer()
            self.timeout_timer.timeout.connect(self._check_timeout)
            self.timeout_timer.start(1000)  # 每秒检查一次
            
            # 根据任务类型执行不同操作
            task_func = self.task_map.get(self.task_type)
            if task_func:
                result = task_func()
            else:
                result = {"status": "error", "message": f"未知任务类型: {self.task_type}"}
            
            # 停止超时计时器
            self.timeout_timer.stop()
            
        except Exception as e:
            # 记录异常信息
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            self.error_signal.emit(error_msg, error_traceback)
            
        finally:
             # Clean up
             if hasattr(self, 'timeout_timer'):
                 self.timeout_timer.stop()
                 
        self.finished_signal.emit(result)

    def stop(self):
        """停止线程"""
        self.is_running = False
        self.stop_event.set()

    def _check_timeout(self):
        if time.time() - self.start_time > self.timeout:
            self.is_running = False
            self.stop_event.set()
            
    def _get_popular_videos(self):
        page = self.params.get('page', 1)
        data = self.crawler.get_popular_videos(page)
        return {"status": "success", "data": data}

    def _get_video_info(self):
        bvid = self.params.get('bvid')
        data = self.crawler.get_video_info(bvid)
        return {"status": "success", "data": data}

    def _download_video(self):
        bvid = self.params.get('bvid')
        
        def video_cb(current, total):
            if total > 0:
                self.progress_signal.emit("video", current, total)
        
        def audio_cb(current, total):
            if total > 0:
                self.progress_signal.emit("audio", current, total)
        
        def merge_cb(current, total):
             self.progress_signal.emit("merge", current, total)
             
        should_merge = self.params.get('should_merge', True)
        delete_original = self.params.get('delete_original', True)
        download_danmaku = self.params.get('download_danmaku', False)
        download_comments = self.params.get('download_comments', False)
        
        result = self.crawler.download_video(
            bvid,
            video_progress_callback=video_cb,
            audio_progress_callback=audio_cb,
            merge_progress_callback=merge_cb,
            should_merge=should_merge,
            delete_original=delete_original,
            download_danmaku=download_danmaku,
            download_comments=download_comments,
            stop_event=self.stop_event,
            video_quality=self.params.get('video_quality', '1080p'),
            video_codec=self.params.get('video_codec', 'H.264/AVC'),
            audio_quality=self.params.get('audio_quality', '高音质 (Hi-Res/Dolby)')
        )
        
        status = "error"
        if result.get("download_success"):
            status = "success"
        elif self.stop_event.is_set():
            status = "cancelled"
            
        return {
            "status": status, 
            "data": result,
            "message": result.get("message", "")
        }

class AccountInfoThread(QThread):
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, crawler, cookies):
        super().__init__()
        self.crawler = crawler
        # Ensure we use the provided cookies for this check
        if cookies:
            self.crawler.cookies = cookies
            
    def run(self):
        try:
            # 1. Get Nav Info (User Info)
            nav_info = self.crawler.api.get_nav_info()
            if not nav_info or nav_info.get('code') != 0:
                self.finished_signal.emit({"status": "error", "message": "无法获取用户信息，Cookies可能已失效"})
                return

            user_data = nav_info.get('data', {})
            if not user_data.get('isLogin'):
                self.finished_signal.emit({"status": "error", "message": "未登录状态"})
                return

            mid = user_data.get('mid')
            
            # 2. Get Favorites
            favorites = []
            try:
                fav_resp = self.crawler.api.get_fav_folder_list(mid)
                if fav_resp and fav_resp.get('code') == 0:
                    favorites = fav_resp.get('data', {}).get('list', [])
            except Exception as e:
                logger.warning(f"获取收藏夹失败: {e}")
                
            # 3. Get History
            history = []
            try:
                hist_resp = self.crawler.api.get_history()
                if hist_resp: 
                    history = hist_resp
            except Exception as e:
                 logger.warning(f"获取历史记录失败: {e}")

            # Merge into user_data
            user_data['favorites'] = favorites
            user_data['history'] = history
            
            self.finished_signal.emit({"status": "success", "data": user_data})
            
        except Exception as e:
            logger.error(f"获取账号信息异常: {e}")
            self.finished_signal.emit({"status": "error", "message": str(e)})
