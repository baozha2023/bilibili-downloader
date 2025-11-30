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

    def download_file(self, url, filepath, filename=None, progress_callback=None, stop_event=None):
        """下载单个文件"""
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
        try:
            # 直接使用session发起流式请求，以便手动处理Header
            response = self.network.session.get(
                url, 
                headers=headers, 
                cookies=self.network.cookies,
                stream=True, 
                timeout=30
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"下载请求失败: {e}")
            return False
            
        # 获取总大小
        total_size = file_size
        if 'content-length' in response.headers:
            total_size += int(response.headers['content-length'])
            
        # 块大小策略
        chunk_size = 1024 * 1024 # 1MB
        if total_size > 100 * 1024 * 1024:
            chunk_size = 2 * 1024 * 1024
            
        if filename:
            logger.info(f"正在下载: {filename}")
            
        downloaded_size = file_size
        start_time = time.time()
        last_update_time = start_time
        bytes_since_last_update = 0
        
        try:
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
                            
            # 如果被中断，删除未完成的文件（如果是全新的下载）
            # 这里简化处理：只要stop_event被设置，就认为中断
            if stop_event and stop_event.is_set():
                 # 注意：文件句柄已关闭
                 return False

            # 下载完成校验
            if total_size > 0 and downloaded_size != total_size:
                # 允许极小误差
                if abs(downloaded_size - total_size) > 1024:
                    logger.warning(f"文件大小不匹配: 预期 {total_size}, 实际 {downloaded_size}")
                    return False
            
            if progress_callback:
                progress_callback(downloaded_size, downloaded_size) # 100%
                
            elapsed = time.time() - start_time
            logger.info(f"下载完成: {filename or filepath}, 用时: {elapsed:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"下载过程中断: {e}")
            return False

    @staticmethod
    def format_size(size_bytes):
        if size_bytes < 1024: return f"{size_bytes} B"
        elif size_bytes < 1024**2: return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024**3: return f"{size_bytes/1024**2:.1f} MB"
        return f"{size_bytes/1024**3:.2f} GB"
