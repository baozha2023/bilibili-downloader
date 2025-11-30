import os
import re
import time
import subprocess
import logging
import threading
import shutil

logger = logging.getLogger('bilibili_core.processor')

class MediaProcessor:
    """
    负责媒体处理：合并、去水印、转码
    """
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffmpeg_available = self.ffmpeg_path is not None
        
    def _find_ffmpeg(self):
        """查找ffmpeg路径"""
        # 1. 项目内 ffmpeg/ffmpeg.exe
        cwd = os.getcwd()
        possible_paths = [
            os.path.join(cwd, 'ffmpeg', 'ffmpeg.exe'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ffmpeg', 'ffmpeg.exe'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"找到项目内ffmpeg: {path}")
                return path
                
        # 2. 系统PATH
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            logger.info(f"使用系统ffmpeg: {system_ffmpeg}")
            return system_ffmpeg
            
        logger.warning("未找到ffmpeg")
        return None

    def merge_video_audio(self, video_path, audio_path, output_path, remove_watermark=False, progress_callback=None):
        """
        合并视频和音频，可选去水印
        """
        if not self.ffmpeg_available:
            logger.error("ffmpeg不可用")
            return False
            
        if not os.path.exists(video_path) or not os.path.exists(audio_path):
            logger.error("输入文件不存在")
            return False
            
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        cmd_base = [self.ffmpeg_path, '-i', video_path, '-i', audio_path]
        
        # 视频编码参数
        if remove_watermark:
            resolution = self._get_video_resolution(video_path)
            if resolution:
                w, h = resolution
                # 估算水印位置 (右上角)
                # 宽: 12% (至少150px)
                # 高: 6% (至少50px)
                # 边距: 3%
                wm_w = max(int(w * 0.12), 150)
                wm_h = max(int(h * 0.06), 50)
                wm_x = int(w - wm_w - w * 0.03)
                wm_y = int(h * 0.03)
                
                # 边界检查
                if wm_x < 0: wm_x = 0
                if wm_y < 0: wm_y = 0
                if wm_x + wm_w > w: wm_w = max(1, w - wm_x)
                if wm_y + wm_h > h: wm_h = max(1, h - wm_y)
                
                # 确保尺寸有效
                if wm_w <= 0 or wm_h <= 0:
                    logger.warning("水印区域计算无效，跳过去水印")
                    cmd_video = ['-c:v', 'copy']
                else:
                    filter_str = f"delogo=x={wm_x}:y={wm_y}:w={wm_w}:h={wm_h}"
                    logger.info(f"应用去水印滤镜: {filter_str} (分辨率: {w}x{h})")
                    # 使用libx264重编码，crf 23保持较好画质
                    cmd_video = ['-vf', filter_str, '-c:v', 'libx264', '-preset', 'fast', '-crf', '23']
            else:
                logger.warning("无法获取分辨率，跳过去水印")
                cmd_video = ['-c:v', 'copy']
        else:
            cmd_video = ['-c:v', 'copy']
            
        cmd_audio = ['-c:a', 'copy']
        cmd_out = ['-map', '0:v:0', '-map', '1:a:0', output_path, '-y']
        
        full_cmd = cmd_base + cmd_video + cmd_audio + cmd_out
        
        # 打印命令供调试
        cmd_str = ' '.join([f'"{c}"' if ' ' in str(c) else str(c) for c in full_cmd])
        logger.info(f"执行合并命令: {cmd_str}")
        
        return self._run_ffmpeg_with_progress(full_cmd, progress_callback)

    def _get_video_resolution(self, video_path):
        """获取视频分辨率 (w, h)"""
        try:
            cmd = [self.ffmpeg_path, '-i', video_path]
            # 必须使用shell=False并传入列表
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
            _, stderr = p.communicate()
            
            # 查找 Stream #0:0... Video: ... 1920x1080
            # 注意：有时会有多个流，或者格式不同，这里匹配最常见的
            match = re.search(r'Stream #\d+:\d+.*Video:.* (\d{3,5})x(\d{3,5})', stderr)
            if match:
                return int(match.group(1)), int(match.group(2))
        except Exception as e:
            logger.error(f"获取分辨率失败: {e}")
        return None

    def _run_ffmpeg_with_progress(self, cmd, progress_callback):
        """运行ffmpeg并解析进度"""
        try:
            # 使用shell=False, cmd为列表
            process = subprocess.Popen(
                cmd, 
                shell=False, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )
            
            def read_stderr():
                duration_seconds = 0
                duration_pattern = re.compile(r'Duration: (\d{2}):(\d{2}):(\d{2})')
                time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2})')
                
                for line in process.stderr:
                    # logger.debug(line.strip()) # 调试用
                    if not duration_seconds:
                        match = duration_pattern.search(line)
                        if match:
                            h, m, s = map(int, match.groups())
                            duration_seconds = h * 3600 + m * 60 + s
                            
                    if duration_seconds and progress_callback:
                        match = time_pattern.search(line)
                        if match:
                            h, m, s = map(int, match.groups())
                            current = h * 3600 + m * 60 + s
                            progress = min(int(current * 100 / duration_seconds), 99)
                            progress_callback(progress, 100)

            t = threading.Thread(target=read_stderr)
            t.start()
            
            process.wait()
            t.join()
            
            if progress_callback:
                progress_callback(100, 100)
                
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"ffmpeg执行出错: {e}")
            return False
