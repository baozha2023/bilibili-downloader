import os
import re
import time
import subprocess
import logging
import threading
import shutil
import tempfile

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

    def convert_video(self, input_path, output_format, progress_callback=None):
        """
        视频格式转换
        :param input_path: 输入文件路径
        :param output_format: 目标格式 (mp4, avi, mkv, mp3, etc.)
        :param progress_callback: 进度回调
        :return: 成功/失败, 输出路径/错误信息
        """
        if not self.ffmpeg_available:
            return False, "ffmpeg未安装"
            
        if not os.path.exists(input_path):
            return False, "输入文件不存在"
            
        # 生成输出路径
        input_dir = os.path.dirname(input_path)
        input_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(input_dir, f"{input_name}_converted.{output_format}")
        
        # 如果输出文件已存在，自动重命名
        counter = 1
        while os.path.exists(output_path):
            output_path = os.path.join(input_dir, f"{input_name}_converted_{counter}.{output_format}")
            counter += 1
            
        cmd = [self.ffmpeg_path, '-i', input_path]
        
        # 根据不同格式设置参数
        if output_format.lower() == 'mp3':
            # 提取音频
            cmd.extend(['-vn', '-acodec', 'libmp3lame', '-q:a', '2'])
        elif output_format.lower() == 'gif':
            # 转换为GIF (限制帧率和分辨率以减小体积)
            cmd.extend(['-vf', 'fps=10,scale=480:-1:flags=lanczos', '-c:v', 'gif'])
        else:
            # 视频转换
            cmd.extend(['-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-c:a', 'aac', '-b:a', '128k'])
            
        cmd.append(output_path)
        cmd.append('-y')
        
        cmd_str = ' '.join([f'"{c}"' if ' ' in str(c) else str(c) for c in cmd])
        logger.info(f"执行转换命令: {cmd_str}")
        
        success = self._run_ffmpeg_with_progress(cmd, progress_callback)
        
        if success:
            return True, output_path
        else:
            return False, "转换失败"

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
                
                # 智能计算水印位置 (针对B站水印优化)
                # 根据常见分辨率预设水印大小和位置
                if w >= 3840: # 4K
                    wm_w = 320
                    wm_h = 100
                    margin_x = 55
                    margin_y = 45
                elif w >= 2560: # 2K
                    wm_w = 250
                    wm_h = 80
                    margin_x = 45
                    margin_y = 35
                elif w >= 1920: # 1080p
                    wm_w = 200
                    wm_h = 65
                    margin_x = 40
                    margin_y = 30
                elif w >= 1280: # 720p
                    wm_w = 150
                    wm_h = 50
                    margin_x = 25
                    margin_y = 20
                else:
                    # 其他分辨率使用比例计算
                    wm_w = max(int(w * 0.12), 100)
                    wm_h = max(int(h * 0.06), 40)
                    margin_x = int(w * 0.03)
                    margin_y = int(h * 0.03)
                
                # 针对竖屏视频调整
                if h > w:
                    wm_w = int(w * 0.35) # 再次增加宽度
                    wm_h = int(wm_w * 0.35)
                    margin_x = int(w * 0.05)
                    margin_y = int(h * 0.02)
                
                wm_x = w - wm_w - margin_x
                wm_y = margin_y
                
                # 边界检查和微调
                if wm_x < 0: wm_x = 0
                if wm_y < 0: wm_y = 0
                if wm_x + wm_w > w: wm_w = max(1, w - wm_x)
                if wm_y + wm_h > h: wm_h = max(1, h - wm_y)
                
                # 确保尺寸有效
                if wm_w <= 0 or wm_h <= 0:
                    logger.warning("水印区域计算无效，跳过去水印")
                    cmd_video = ['-c:v', 'copy']
                else:
                    # 增加band参数使边缘过渡更自然 (32)
                    # 增加 show=0 参数确保不显示边界框 (delogo默认show=0，但显式指定更安全)
                    filter_str = f"delogo=x={wm_x}:y={wm_y}:w={wm_w}:h={wm_h}:band=32:show=0"
                    logger.info(f"应用去水印滤镜: {filter_str} (分辨率: {w}x{h})")
                    # 使用libx264重编码，crf 16提升画质 (原17)，preset medium平衡速度和质量
                    cmd_video = ['-vf', filter_str, '-c:v', 'libx264', '-preset', 'medium', '-crf', '16']
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

    def get_video_info(self, video_path):
        """获取视频信息：时长(秒), 分辨率(w,h), 帧率"""
        try:
            cmd = [self.ffmpeg_path, '-i', video_path]
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            else:
                startupinfo = None

            p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, 
                               universal_newlines=True, startupinfo=startupinfo, 
                               encoding='utf-8', errors='replace')
            _, stderr = p.communicate()
            
            info = {
                'duration': 0,
                'width': 0,
                'height': 0,
                'fps': 0
            }
            
            # Duration
            match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)', stderr)
            if match:
                h, m, s = match.groups()
                info['duration'] = int(h) * 3600 + int(m) * 60 + float(s)
            else:
                # Fallback for integer seconds
                match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})', stderr)
                if match:
                    h, m, s = map(int, match.groups())
                    info['duration'] = h * 3600 + m * 60 + s

            # Resolution & FPS
            # Stream #0:0(und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(tv, bt709), 1920x1080 [SAR 1:1 DAR 16:9], 1666 kb/s, 30 fps, 30 tbr, 16k tbn, 60 tbc
            match = re.search(r'Stream #\d+:\d+.*Video:.* (\d{3,5})x(\d{3,5}).*, (\d+(?:\.\d+)?) fps', stderr)
            if match:
                info['width'] = int(match.group(1))
                info['height'] = int(match.group(2))
                info['fps'] = float(match.group(3))
            
            return info
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
            return None

    def _get_video_resolution(self, video_path):
        """获取视频分辨率 (w, h)"""
        info = self.get_video_info(video_path)
        if info:
            return info['width'], info['height']
        return None

    def get_video_duration(self, video_path):
        """获取视频时长(秒)"""
        info = self.get_video_info(video_path)
        if info:
            return info['duration']
        return 0

    def cut_video(self, input_path, start_time, end_time, output_path=None, progress_callback=None):
        """
        剪辑视频
        :param start_time: 开始时间 (秒)
        :param end_time: 结束时间 (秒)
        """
        if not self.ffmpeg_available:
            return False, "ffmpeg未安装"
            
        if not output_path:
            input_dir = os.path.dirname(input_path)
            input_name = os.path.splitext(os.path.basename(input_path))[0]
            ext = os.path.splitext(input_path)[1]
            output_path = os.path.join(input_dir, f"{input_name}_cut{ext}")
            
        # 计算持续时间
        duration = end_time - start_time
        if duration <= 0:
            return False, "无效的时间范围"
            
        # 使用 -ss (before -i) 快速定位，重编码保证精确
        cmd = [
            self.ffmpeg_path, 
            '-ss', str(start_time),
            '-i', input_path,
            '-t', str(duration),
            '-c:v', 'libx264', '-c:a', 'aac',
            '-y', output_path
        ]
        
        logger.info(f"剪辑视频: {cmd}")
        if self._run_ffmpeg_with_progress(cmd, progress_callback):
            return True, output_path
        else:
            return False, "剪辑失败"

    def merge_video_files(self, file_list, output_path, progress_callback=None):
        """
        合并多个视频文件 (Concat)
        """
        if not self.ffmpeg_available:
            return False, "ffmpeg未安装"
        
        if len(file_list) < 2:
            return False, "至少需要两个文件"
            
        # 创建临时列表文件
        try:
            fd, list_path = tempfile.mkstemp(suffix=".txt", text=True)
            os.close(fd)
            
            with open(list_path, 'w', encoding='utf-8') as f:
                for file in file_list:
                    # 转义路径中的单引号
                    path = file.replace("'", "'\\''")
                    f.write(f"file '{path}'\n")
            
            cmd = [
                self.ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', list_path,
                '-c', 'copy', # 尝试复制流 (前提是格式一致)
                '-y', output_path
            ]
            
            logger.info(f"合并视频: {cmd}")
            success = self._run_ffmpeg_with_progress(cmd, progress_callback)
            
            # 清理临时文件
            if os.path.exists(list_path):
                os.remove(list_path)
                
            if success:
                return True, output_path
            else:
                # 如果copy失败，尝试重编码合并 (更稳健但更慢)
                logger.warning("流复制合并失败，尝试重编码合并...")
                cmd = [
                    self.ffmpeg_path,
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', list_path,
                    '-c:v', 'libx264', '-c:a', 'aac',
                    '-y', output_path
                ]
                
                # 再次创建列表文件 (因为可能已被删除)
                with open(list_path, 'w', encoding='utf-8') as f:
                    for file in file_list:
                        path = file.replace("'", "'\\''")
                        f.write(f"file '{path}'\n")
                        
                success = self._run_ffmpeg_with_progress(cmd, progress_callback)
                if os.path.exists(list_path):
                    os.remove(list_path)
                    
                if success:
                    return True, output_path
                else:
                    return False, "合并失败"
                    
        except Exception as e:
            logger.error(f"合并出错: {e}")
            return False, str(e)

    def remove_watermark_custom(self, input_path, x, y, w, h, output_path=None, progress_callback=None):
        """
        自定义区域去水印
        """
        if not self.ffmpeg_available:
            return False, "ffmpeg未安装"
            
        if not output_path:
            input_dir = os.path.dirname(input_path)
            input_name = os.path.splitext(os.path.basename(input_path))[0]
            ext = os.path.splitext(input_path)[1]
            output_path = os.path.join(input_dir, f"{input_name}_clean{ext}")
            
        # 使用更智能的delogo参数
        # show=0: 不显示绿框
        # band=4: 边缘过渡宽度 (默认4，适度增加可平滑)
        filter_str = f"delogo=x={x}:y={y}:w={w}:h={h}:band=10:show=0"
        
        cmd = [
            self.ffmpeg_path,
            '-i', input_path,
            '-vf', filter_str,
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-c:a', 'copy',
            '-y', output_path
        ]
        
        logger.info(f"自定义去水印: {cmd}")
        if self._run_ffmpeg_with_progress(cmd, progress_callback):
            return True, output_path
        else:
            return False, "去水印失败"

    def compress_video(self, input_path, target_resolution, crf=23, output_path=None, progress_callback=None):
        """
        压缩视频
        :param target_resolution: 目标分辨率 (e.g. "1280x720", "1920x1080")
        :param crf: 压缩质量 (18-28, 越小画质越好体积越大)
        """
        if not self.ffmpeg_available:
            return False, "ffmpeg未安装"
            
        if not output_path:
            input_dir = os.path.dirname(input_path)
            input_name = os.path.splitext(os.path.basename(input_path))[0]
            ext = os.path.splitext(input_path)[1]
            output_path = os.path.join(input_dir, f"{input_name}_compressed_{target_resolution}{ext}")
            
        cmd = [
            self.ffmpeg_path,
            '-i', input_path,
            '-vf', f'scale={target_resolution}:force_original_aspect_ratio=decrease',
            '-c:v', 'libx264', 
            '-crf', str(crf), 
            '-preset', 'medium',
            '-c:a', 'aac', '-b:a', '128k',
            '-y', output_path
        ]
        
        logger.info(f"压缩视频: {cmd}")
        if self._run_ffmpeg_with_progress(cmd, progress_callback):
            return True, output_path
        else:
            return False, "压缩失败"

    def _run_ffmpeg_with_progress(self, cmd, progress_callback):
        """运行ffmpeg并解析进度"""
        try:
            # 使用shell=False, cmd为列表
            # 创建无窗口标志 (仅Windows)
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.Popen(
                cmd, 
                shell=False, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace',
                startupinfo=startupinfo
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
