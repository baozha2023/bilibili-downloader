import os
import sys
import time
import logging
from .network import NetworkManager

logger = logging.getLogger('bilibili_core.downloader')

class Downloader:
    """
    负责文件下载逻辑
    """
    def __init__(self, network_manager: NetworkManager):
        self.network = network_manager

    def download_file(self, url: str, filepath: str, filename: str = None, progress_callback=None, stop_event=None) -> bool:
        """下载单个文件，支持重试"""
        max_retries = self.network.config.get('max_retries', 3)
        retry_interval = self.network.config.get('retry_interval', 2)
        timeout = self.network.config.get('timeout', 30)
        
        for attempt in range(max_retries + 1):
            if stop_event and stop_event.is_set():
                return False
                
            if attempt > 0:
                logger.info(f"正在进行第 {attempt} 次重试...")
            
            try:
                # 断点续传检查
                file_size = 0
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    if file_size > 0:
                        logger.info(f"文件已存在，断点续传从 {file_size} 字节开始")
                
                # 设置Header Range
                headers = self.network.headers.copy()
                headers['User-Agent'] = self.network._get_random_ua()
                if file_size > 0:
                    headers['Range'] = f'bytes={file_size}-'
                    
                # 发起请求
                response = self.network.session.get(
                    url, 
                    headers=headers, 
                    cookies=self.network.cookies,
                    stream=True, 
                    timeout=(5, timeout)
                )
                response.raise_for_status()
                
                # 获取总大小
                total_size = file_size
                if 'content-length' in response.headers:
                    total_size += int(response.headers['content-length'])
                    
                # 块大小策略
                chunk_size = 1024 * 1024 # 1MB
                if total_size > 100 * 1024 * 1024:
                    chunk_size = 2 * 1024 * 1024
                    
                if filename and attempt == 0:
                    logger.info(f"正在下载: {filename}")
                    
                downloaded_size = file_size
                start_time = time.time()
                last_update_time = start_time
                bytes_since_last_update = 0
                
                mode = 'ab' if file_size > 0 else 'wb'
                with open(filepath, mode) as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        # 检查是否需要停止
                        if stop_event and stop_event.is_set():
                            logger.info("检测到停止信号，中断下载")
                            return False

                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            bytes_since_last_update += len(chunk)
                            
                            current_time = time.time()
                            if current_time - last_update_time >= 0.5:
                                if progress_callback:
                                    progress_callback(downloaded_size, total_size if total_size > 0 else -1)
                                last_update_time = current_time
                                bytes_since_last_update = 0
                                
                # 如果被中断，删除未完成的文件
                if stop_event and stop_event.is_set():
                     return False

                # 下载完成校验
                if total_size > 0 and downloaded_size != total_size:
                    # 允许极小误差
                    if abs(downloaded_size - total_size) > 1024:
                        raise Exception(f"文件大小不匹配: 预期 {total_size}, 实际 {downloaded_size}")
                
                if progress_callback:
                    progress_callback(downloaded_size, downloaded_size) # 100%
                    
                elapsed = time.time() - start_time
                logger.info(f"下载完成: {filename or filepath}, 用时: {elapsed:.2f}s")
                return True
                
            except Exception as e:
                logger.error(f"下载失败 (尝试 {attempt+1}/{max_retries+1}): {e}")
                
                # Check if we should retry
                if attempt < max_retries:
                    # check stop event before sleeping
                    if stop_event and stop_event.is_set():
                        return False
                    logger.info(f"等待 {retry_interval} 秒后重试...")
                    time.sleep(retry_interval)
                else:
                    logger.error(f"达到最大重试次数 {max_retries}，放弃下载")
                    return False
        
        return False
