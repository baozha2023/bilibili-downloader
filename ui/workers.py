import time
import logging
import os
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
        
        # 设置重试次数
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = 2  # 秒
        
        # 设置超时时间
        self.timeout = 30  # 秒
        
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
            import traceback
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            
            # 发送错误信号
            self.error_signal.emit(error_msg, error_traceback)
            
            # 设置结果
            result = {
                "status": "error", 
                "message": f"执行任务时出错: {error_msg}",
                "error_traceback": error_traceback
            }
            
            # 记录日志
            logger.error(f"任务 {self.task_type} 执行出错: {error_msg}")
            logger.debug(error_traceback)
        
        # 计算执行时间
        execution_time = time.time() - start_time
        result["execution_time"] = execution_time
        
        # 发送完成信号
        self.finished_signal.emit(result)
    
    def _check_timeout(self):
        """检查任务是否超时"""
        if hasattr(self, 'start_time') and time.time() - self.start_time > self.timeout:
            # 对于下载任务，不进行超时检查，或者超时时间应该很长
            if self.task_type == "download_video":
                return
                
            self.is_running = False
            self.update_signal.emit({
                "status": "error", 
                "message": f"任务执行超时 (>{self.timeout}秒)"
            })
    
    def _get_popular_videos(self):
        """获取热门视频"""
        pages = self.params.get("pages", 3)
        videos = []
        
        for page in range(1, pages + 1):
            if not self.is_running:
                break
            
            self.update_signal.emit({"status": "running", "message": f"正在爬取第{page}页热门视频..."})
            
            # 添加重试逻辑
            for retry in range(self.max_retries):
                try:
                    page_videos = self.crawler.get_popular_videos(page)
                    if page_videos:
                        videos.extend(page_videos)
                        self.update_signal.emit({"status": "running", "message": f"成功获取{len(page_videos)}个视频"})
                        self.progress_signal.emit("video", len(videos), len(videos))
                        break
                    else:
                        if retry < self.max_retries - 1:
                            self.update_signal.emit({"status": "warning", "message": f"获取第{page}页失败，正在重试 ({retry+1}/{self.max_retries})..."})
                            time.sleep(self.retry_delay)
                        else:
                            self.update_signal.emit({"status": "warning", "message": f"获取第{page}页失败，跳过"})
                except Exception as e:
                    if retry < self.max_retries - 1:
                        self.update_signal.emit({"status": "warning", "message": f"获取第{page}页出错: {str(e)}，正在重试 ({retry+1}/{self.max_retries})..."})
                        time.sleep(self.retry_delay)
                    else:
                        self.update_signal.emit({"status": "error", "message": f"获取第{page}页出错: {str(e)}"})
                        break
        
        if videos:
            # 保存数据
            self.crawler.save_to_json(videos, "popular_videos")
            return {"status": "success", "data": videos, "message": f"成功获取{len(videos)}个热门视频"}
        else:
            return {"status": "error", "message": "未获取到任何视频"}
    
    def _get_video_info(self):
        """获取视频信息"""
        bvid = self.params.get("bvid", "")
        if not bvid:
            return {"status": "error", "message": "未提供BV号"}
            
        try:
            info = self.crawler.get_video_info(bvid)
            if info:
                return {"status": "success", "data": info, "message": "获取视频信息成功"}
            else:
                return {"status": "error", "message": "获取视频信息失败"}
        except Exception as e:
            return {"status": "error", "message": f"获取视频信息出错: {str(e)}"}

    def _download_video(self):
        """下载视频"""
        # 重试机制
        for retry in range(self.max_retries):
            try:
                bvid = self.params.get("bvid", "")
                if not bvid:
                    return {"status": "error", "message": "未提供BV号"}
                
                # 检查是否提供了标题
                title = self.params.get("title")
                
                # 如果没有提供标题，尝试获取视频信息
                if not title:
                    try:
                        info = self.crawler.get_video_info(bvid)
                    except Exception as e:
                        self.update_signal.emit({"status": "error", "message": f"获取视频信息失败: {str(e)}"})
                        logger.error(f"获取视频信息失败: {str(e)}")
                        
                        if retry < self.max_retries - 1:
                            self.update_signal.emit({"status": "warning", "message": f"正在重试获取视频信息 ({retry+1}/{self.max_retries})..."})
                            time.sleep(self.retry_delay)
                            continue
                        else:
                            return {"status": "error", "message": f"获取视频信息失败: {str(e)}"}
                    
                    if not info:
                        if retry < self.max_retries - 1:
                            self.update_signal.emit({"status": "warning", "message": f"获取视频信息失败，正在重试 ({retry+1}/{self.max_retries})..."})
                            time.sleep(self.retry_delay)
                            continue
                        else:
                            return {"status": "error", "message": "获取视频信息失败"}
                    
                    title = info.get("data", {}).get("title", "未知视频")
                
                # 只记录关键步骤，避免冗余
                # self.update_signal.emit({"status": "info", "message": f"准备下载: {title}"})
                
                # 定义视频下载进度回调函数
                def video_progress_callback(current, total):
                    self.progress_signal.emit("video", current, total)
                
                # 定义音频下载进度回调函数
                def audio_progress_callback(current, total):
                    self.progress_signal.emit("audio", current, total)
                
                # 定义合并进度回调函数
                def merge_progress_callback(current, total):
                    # 合并进度通常是0-100的整数
                    # 只有在需要合并时才发送进度信号
                    if self.params.get("should_merge", True):
                        self.progress_signal.emit("merge", current, 100)
                
                # 定义弹幕下载进度回调函数
                def danmaku_progress_callback(current, total):
                    self.progress_signal.emit("danmaku", current, total)
                
                # 定义评论下载进度回调函数
                def comments_progress_callback(current, total):
                    self.progress_signal.emit("comments", current, total)
                
                # 获取是否合并的选项
                should_merge = self.params.get("should_merge", True)
                if not should_merge:
                    self.update_signal.emit({"status": "info", "message": "用户设置不合并，将保留原始音视频文件"})
                
                # 获取是否删除原始文件的选项
                delete_original = self.params.get("delete_original", True)
                
                # 获取是否去除水印选项
                remove_watermark = self.params.get("remove_watermark", False)
                download_danmaku = self.params.get("download_danmaku", False)
                download_comments = self.params.get("download_comments", False)

                video_quality = self.params.get("video_quality", "1080p")
                video_codec = self.params.get("video_codec", "H.264/AVC")
                audio_quality = self.params.get("audio_quality", "高音质 (Hi-Res/Dolby)")

                # 下载视频
                start_time = time.time()
                self.update_signal.emit({"status": "download", "message": f"开始下载: {title}"})
                
                # Construct kwargs for download_video
                download_kwargs = {
                    'bvid': bvid,
                    'video_progress_callback': video_progress_callback,
                    'audio_progress_callback': audio_progress_callback,
                    'merge_progress_callback': merge_progress_callback,
                    'danmaku_progress_callback': danmaku_progress_callback,
                    'comments_progress_callback': comments_progress_callback,
                    'should_merge': should_merge,
                    'delete_original': delete_original,
                    'remove_watermark': remove_watermark,
                    'download_danmaku': download_danmaku,
                    'download_comments': download_comments,
                    'video_quality': video_quality,
                    'video_codec': video_codec,
                    'audio_quality': audio_quality,
                    'stop_event': self.stop_event
                }

                download_result = self.crawler.download_video(**download_kwargs)
                
                if download_result["download_success"]:
                    download_dir = os.path.abspath(self.crawler.download_dir)
                    
                    # 检查是否需要合并
                    should_merge = self.params.get("should_merge", True)
                    
                    # 额外检查：如果合并文件存在且大小合理，则认为合并成功，即使merge_success为False
                    if should_merge and not download_result["merge_success"] and download_result["output_path"]:
                        output_path = download_result["output_path"]
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 1024 * 1024:  # 大于1MB
                            download_result["merge_success"] = True
                            logger.info(f"检测到合并文件存在且大小正常: {output_path}，修正merge_success为True")
                    
                    # 检查合并是否成功或是否不需要合并
                    if download_result["merge_success"] or (not should_merge):
                        # 如果合并成功或用户选择不合并
                        result_data = {
                            "title": title, 
                            "download_dir": download_result.get("download_dir", download_dir)
                        }
                        
                        # 如果合并成功，添加合并文件路径
                        if download_result["merge_success"]:
                            result_data["merged_file"] = download_result["output_path"]
                            message = f"视频下载并合并完成: {title}"
                        else:
                            # 用户选择不合并，添加原始文件路径
                            result_data["video_file"] = download_result["video_path"]
                            result_data["audio_file"] = download_result["audio_path"]
                            message = f"视频下载完成(未合并): {title}"
                        
                        # 特殊处理：如果是"已存在"的情况
                        if "视频已存在" in download_result.get("message", ""):
                             message = f"视频已存在，跳过下载: {title}"

                        return {
                            "status": "success", 
                            "data": result_data, 
                            "message": message,
                            "execution_time": time.time() - start_time,
                            "should_merge": should_merge
                        }
                    else:
                        # 视频下载成功但合并失败
                        if not download_result["ffmpeg_available"]:
                            # ffmpeg不可用
                            return {
                                "status": "warning", 
                                "data": {
                                    "title": title, 
                                    "download_dir": download_dir,
                                    "video_file": download_result["video_path"],
                                    "audio_file": download_result["audio_path"]
                                }, 
                                "message": f"下载完成但无法合并(未检测到ffmpeg): {title}",
                                "execution_time": time.time() - start_time,
                                "should_merge": should_merge
                            }
                        else:
                            # ffmpeg可用但合并失败
                            # 再次检查合并文件是否存在
                            output_path = download_result["output_path"]
                            if output_path and os.path.exists(output_path) and os.path.getsize(output_path) > 1024 * 1024:  # 大于1MB
                                download_result["merge_success"] = True
                                logger.info(f"在返回结果前再次检查：合并文件存在且大小正常: {output_path}，修正merge_success为True")
                                
                                # 如果合并文件存在，则返回成功
                                return {
                                    "status": "success", 
                                    "data": {
                                        "title": title, 
                                        "download_dir": download_dir,
                                        "merged_file": output_path
                                    }, 
                                    "message": f"视频下载并合并完成: {title}",
                                    "execution_time": time.time() - start_time,
                                    "should_merge": should_merge
                                }
                            
                            # 检查合并过程是否真的失败，还是只是返回码不为0
                            # 如果ffmpeg可用且没有明确的错误信息，将不报告合并失败
                            if download_result["ffmpeg_available"]:
                                logger.info("ffmpeg可用，虽然合并结果不明确，但不报告为失败")
                                # 返回成功状态但带警告信息
                                return {
                                    "status": "success", 
                                    "data": {
                                        "title": title, 
                                        "download_dir": download_dir,
                                        "video_file": download_result["video_path"],
                                        "audio_file": download_result["audio_path"],
                                        "merged_file": download_result["output_path"]
                                    }, 
                                    "message": f"下载完成，请检查合并文件: {title}",
                                    "execution_time": time.time() - start_time,
                                    "should_merge": should_merge
                                }
                            
                            # 仅在确实无法合并时返回警告
                            return {
                                "status": "warning", 
                                "data": {
                                    "title": title, 
                                    "download_dir": download_dir,
                                    "video_file": download_result["video_path"],
                                    "audio_file": download_result["audio_path"],
                                    "merged_file": download_result["output_path"]
                                }, 
                                "message": f"下载完成但合并失败: {title}",
                                "execution_time": time.time() - start_time,
                                "should_merge": should_merge
                            }
                
                # 检查是否是取消下载
                elif download_result.get("message") == "下载已取消":
                    return {
                        "status": "cancelled", 
                        "message": "下载已取消",
                        "execution_time": time.time() - start_time
                    }
            except Exception as e:
                if retry < self.max_retries - 1:
                    self.update_signal.emit({"status": "warning", "message": f"下载出错: {str(e)}，重试中 ({retry+1}/{self.max_retries})..."})
                    time.sleep(self.retry_delay)
                else:
                    import traceback
                    error_traceback = traceback.format_exc()
                    logger.error(f"下载失败: {str(e)}\n{error_traceback}")
                    return {
                        "status": "error", 
                        "message": f"下载失败: {str(e)}",
                        "error_traceback": error_traceback
                    }
        
        return {"status": "error", "message": "下载失败，请稍后重试"}
    
    def stop(self):
        """停止线程"""
        self.is_running = False
        self.stop_event.set()
        self.update_signal.emit({"status": "warning", "message": "正在取消任务..."})
        
        # 尝试清理临时文件
        if self.task_type == "download_video" and hasattr(self, 'crawler'):
            try:
                # 这里需要crawler支持中断下载并清理
                # 目前只能通过is_running标志通知crawler停止
                pass
            except Exception as e:
                logger.error(f"清理资源失败: {e}")
        
        # 如果线程仍在运行，等待最多3秒
        if self.isRunning():
            self.wait(3000)
            
            # 如果仍在运行，强制终止
            if self.isRunning():
                self.terminate()
                self.wait()

class AccountInfoThread(QThread):
    """处理账号信息查询的线程"""
    update_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, crawler, cookies):
        super().__init__()
        self.crawler = crawler
        self.cookies = cookies
        self.is_running = True
        
        # 设置重试次数
        self.max_retries = 3
        self.retry_delay = 2  # 秒
    
    def run(self):
        """线程主函数"""
        result = {"status": "error", "data": None, "message": "未知错误"}
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 获取账号信息
            result = self.get_account_info()
        except Exception as e:
            # 记录异常信息
            import traceback
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            
            # 设置结果
            result = {
                "status": "error", 
                "message": f"执行任务时出错: {error_msg}",
                "error_traceback": error_traceback
            }
            
            # 记录日志
            logger.error(f"获取账号信息时出错: {error_msg}")
            logger.debug(error_traceback)
        
        # 计算执行时间
        execution_time = time.time() - start_time
        result["execution_time"] = execution_time
        
        # 发送完成信号
        self.finished_signal.emit(result)
    
    def get_account_info(self):
        """获取账号信息"""
        if not self.cookies or "SESSDATA" not in self.cookies:
            return {"status": "error", "message": "无效的登录信息"}
        
        self.update_signal.emit({"status": "info", "message": "正在获取账号信息..."})
        
        # 重试机制
        for retry in range(self.max_retries):
            try:
                # 设置cookies
                self.crawler.cookies = self.cookies
                
                # 获取用户信息
                url = "https://api.bilibili.com/x/web-interface/nav"
                response = self.crawler.make_request(url)
                
                if not response or response.get("code") != 0:
                    error_msg = response.get("message", "未知错误") if response else "请求失败"
                    if retry < self.max_retries - 1:
                        self.update_signal.emit({"status": "warning", "message": f"获取账号信息失败: {error_msg}，正在重试 ({retry+1}/{self.max_retries})..."})
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return {"status": "error", "message": f"获取账号信息失败: {error_msg}"}
                
                # 获取用户数据
                user_data = response.get("data", {})
                if not user_data or not user_data.get("isLogin", False):
                    if retry < self.max_retries - 1:
                        self.update_signal.emit({"status": "warning", "message": "登录状态无效，正在重试..."})
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return {"status": "error", "message": "登录状态无效，请重新登录"}
                
                # 获取收藏夹信息
                try:
                    mid = user_data.get("mid")
                    if mid:
                        self.update_signal.emit({"status": "info", "message": "正在获取收藏夹信息..."})
                        fav_url = f"https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid={mid}"
                        fav_response = self.crawler.make_request(fav_url)
                        if fav_response and fav_response.get("code") == 0:
                            fav_list = fav_response.get("data", {}).get("list", [])
                            user_data["favorites"] = fav_list
                            
                        # 获取历史记录
                        self.update_signal.emit({"status": "info", "message": "正在获取历史记录..."})
                        history_list = self.crawler.get_history(1)
                        user_data["history"] = history_list
                        
                except Exception as e:
                    logger.error(f"获取额外信息失败: {e}")
                    # 不影响主要信息展示
                
                # 返回成功结果
                return {
                    "status": "success",
                    "data": user_data,
                    "message": f"账号信息获取成功: {user_data.get('uname', '未知用户')}"
                }
                
            except Exception as e:
                if retry < self.max_retries - 1:
                    self.update_signal.emit({"status": "warning", "message": f"获取账号信息出错: {str(e)}，正在重试 ({retry+1}/{self.max_retries})..."})
                    time.sleep(self.retry_delay)
                else:
                    return {"status": "error", "message": f"获取账号信息出错: {str(e)}"}
        
        return {"status": "error", "message": "获取账号信息失败，请稍后重试"}
    
    def stop(self):
        """停止线程"""
        self.is_running = False
        
        # 如果线程仍在运行，等待最多3秒
        if self.isRunning():
            self.wait(3000)
            
            # 如果仍在运行，强制终止
            if self.isRunning():
                self.terminate()
                self.wait()
