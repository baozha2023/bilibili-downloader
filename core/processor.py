import os
import re
import time
import subprocess
import logging
import threading
import shutil
import tempfile
import cv2

from core.watermark import WatermarkRemover

logger = logging.getLogger('bilibili_core.processor')

class MediaProcessor:
    """
    负责媒体处理：合并、去水印、格式转换、剪辑、反转、剪辑
    """
    def __init__(self, hardware_acceleration=False):
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffmpeg_available = self.ffmpeg_path is not None
        self.watermark_remover = WatermarkRemover(self.ffmpeg_path, self._run_ffmpeg_with_progress) if self.ffmpeg_available else None
        self.hardware_acceleration = hardware_acceleration

    def set_hardware_acceleration(self, enabled):
        self.hardware_acceleration = enabled
        logger.info(f"硬件加速已{'启用' if enabled else '禁用'}")

    def _get_encoding_params(self, crf=23, preset='medium'):
        """获取编码参数 (根据硬件加速设置)"""
        if self.hardware_acceleration:
            # NVIDIA NVENC 参数
            # -cq 对应 -crf, 但数值范围略有不同，这里近似处理
            # -preset p4 是中等预设 (p1-p7, p7最慢)
            return ['-c:v', 'h264_nvenc', '-cq', str(crf), '-preset', 'p4']
        else:
            # CPU libx264 参数
            return ['-c:v', 'libx264', '-crf', str(crf), '-preset', preset]

    def _get_input_flags(self):
        """获取输入参数 (硬件解码)"""
        if self.hardware_acceleration:
            return ['-hwaccel', 'cuda']
        return []

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
            
        cmd = [self.ffmpeg_path] + self._get_input_flags() + ['-i', input_path]
        
        # 根据不同格式设置参数
        if output_format.lower() == 'mp3':
            # 提取音频
            cmd.extend(['-vn', '-acodec', 'libmp3lame', '-q:a', '2'])
        elif output_format.lower() == 'gif':
            # 转换为GIF (限制帧率和分辨率以减小体积)
            cmd.extend(['-vf', 'fps=10,scale=480:-1:flags=lanczos', '-c:v', 'gif'])
        else:
            # 视频转换
            cmd.extend(self._get_encoding_params())
            cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
            
        cmd.append(output_path)
        cmd.append('-y')
        
        cmd_str = ' '.join([f'"{c}"' if ' ' in str(c) else str(c) for c in cmd])
        logger.info(f"执行转换命令: {cmd_str}")
        
        success = self._run_ffmpeg_with_progress(cmd, progress_callback)
        
        if success:
            return True, output_path
        else:
            return False, "转换失败"

    def reverse_video(self, input_path, progress_callback=None):
        """
        视频反转
        :param input_path: 输入文件路径
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
        output_path = os.path.join(input_dir, f"{input_name}_reverse.mp4")
        
        counter = 1
        while os.path.exists(output_path):
            output_path = os.path.join(input_dir, f"{input_name}_reverse_{counter}.mp4")
            counter += 1
            
        # 视频反转 + 音频反转
        # -vf reverse 视频反转
        # -af areverse 音频反转
        # 注意: 反转操作非常耗时且占用内存，大视频可能会失败
        cmd = [self.ffmpeg_path] + self._get_input_flags() + ['-i', input_path]
        
        cmd.extend(['-vf', 'reverse', '-af', 'areverse'])
        cmd.extend(self._get_encoding_params())
        cmd.extend(['-c:a', 'aac', '-b:a', '128k', output_path, '-y'])
        
        logger.info(f"执行视频反转: {' '.join(cmd)}")
        
        success = self._run_ffmpeg_with_progress(cmd, progress_callback)
        
        if success:
            return True, output_path
        else:
            return False, "视频反转失败"

    def merge_video_audio(self, video_path, audio_path, output_path, progress_callback=None):
        """
        合并视频和音频
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
        cmd_video = ['-c:v', 'copy']
            
        cmd_audio = ['-c:a', 'copy']
        cmd_out = ['-map', '0:v:0', '-map', '1:a:0', output_path, '-y']
        
        full_cmd = cmd_base + cmd_video + cmd_audio + cmd_out
        
        # 打印命令供调试
        cmd_str = ' '.join([f'"{c}"' if ' ' in str(c) else str(c) for c in full_cmd])
        logger.info(f"执行合并命令: {cmd_str}")
        
        return self._run_ffmpeg_with_progress(full_cmd, progress_callback)

    def get_video_duration(self, video_path):
        """获取视频时长(秒)"""
        try:
            cmd = [self.ffmpeg_path, '-i', video_path]
            # 必须使用shell=False并传入列表
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            else:
                startupinfo = None

            # Explicitly use utf-8 encoding to avoid gbk decode error on Windows
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, 
                               universal_newlines=True, startupinfo=startupinfo, 
                               encoding='utf-8', errors='replace')
            _, stderr = p.communicate()
            
            match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)', stderr)
            if match:
                h = int(match.group(1))
                m = int(match.group(2))
                s = float(match.group(3))
                return h * 3600 + m * 60 + s
        except Exception as e:
            logger.error(f"获取时长失败: {e}")
        return 0

    def get_total_frames(self, video_path):
        """获取视频总帧数 (优先使用 OpenCV 精确获取)"""
        try:
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
                return count
        except Exception as e:
            logger.warning(f"OpenCV获取帧数失败，尝试使用ffmpeg估算: {e}")
        
        # Fallback
        fps = self.get_video_fps(video_path)
        duration = self.get_video_duration(video_path)
        if fps > 0:
            return int(duration * fps)
        return 0

    def get_video_fps(self, video_path):
        """获取视频帧率"""
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
            
            # Match 30 fps, 29.97 fps, etc.
            match = re.search(r', (\d+(?:\.\d+)?) fps', stderr)
            if match:
                return float(match.group(1))
        except Exception as e:
            logger.error(f"获取帧率失败: {e}")
        return 0

    def has_audio_stream(self, video_path):
        """Check if video has audio stream"""
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
            
            # Look for Audio stream info
            # Stream #0:1(und): Audio: aac (LC) (mp4a / 0x6134706D), 44100 Hz, stereo, fltp, 83 kb/s (default)
            return "Audio:" in stderr
        except Exception as e:
            logger.error(f"Failed to check audio stream: {e}")
            return False

    def av_merge(self, video_path, audio_path, output_path=None, progress_callback=None):
        """
        音视频合并 (AV Merge)
        :param video_path: 视频文件路径
        :param audio_path: 音频文件路径
        :param output_path: 输出文件路径
        :param progress_callback: 进度回调
        """
        if not self.ffmpeg_available:
            return False, "ffmpeg未安装"

        if not os.path.exists(video_path):
            return False, "视频文件不存在"
        if not os.path.exists(audio_path):
            return False, "音频文件不存在"

        if not output_path:
            input_dir = os.path.dirname(video_path)
            input_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(input_dir, f"{input_name}_av_merge.mp4")
            
            # Avoid overwrite
            counter = 1
            while os.path.exists(output_path):
                output_path = os.path.join(input_dir, f"{input_name}_av_merge_{counter}.mp4")
                counter += 1

        # ffmpeg -i video -i audio -c:v copy -c:a aac -strict experimental -map 0:v:0 -map 1:a:0 output
        # Map explicit streams to avoid confusion
        cmd = [
            self.ffmpeg_path, '-i', video_path, '-i', audio_path,
            '-c:v', 'copy', '-c:a', 'aac', 
            '-map', '0:v:0', '-map', '1:a:0',
            '-y', output_path
        ]
        
        logger.info(f"AV合并: {cmd}")
        if self._run_ffmpeg_with_progress(cmd, progress_callback):
            return True, output_path
        else:
            return False, "合并失败"

    def cut_video(self, input_path, start, end, unit='time', output_path=None, progress_callback=None):
        """
        剪辑视频
        :param start: 开始时间/帧
        :param end: 结束时间/帧
        :param unit: 'time' (秒) 或 'frame' (帧)
        """
        if not self.ffmpeg_available:
            return False, "ffmpeg未安装"
            
        if not output_path:
            input_dir = os.path.dirname(input_path)
            input_name = os.path.splitext(os.path.basename(input_path))[0]
            ext = os.path.splitext(input_path)[1]
            output_path = os.path.join(input_dir, f"{input_name}_cut{ext}")

        start_time = start
        duration = end - start
        
        # 如果是帧数模式，转换为时间
        if unit == 'frame':
            fps = self.get_video_fps(input_path)
            if fps <= 0:
                return False, "无法获取视频帧率，无法使用帧数剪辑"
            start_time = start / fps
            duration = (end - start) / fps

        if duration <= 0:
            return False, "无效的时间范围"

        cmd = [self.ffmpeg_path] + self._get_input_flags()
        
        # 使用 -ss 在输入前快速定位
        cmd.extend(['-ss', str(start_time)])
        cmd.extend(['-i', input_path])
        cmd.extend(['-t', str(duration)])
        
        # 重新编码以保证精确性
        cmd.extend(self._get_encoding_params())
        cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
            
        cmd.extend(['-y', output_path])
        
        logger.info(f"剪辑视频: {cmd}")
        if self._run_ffmpeg_with_progress(cmd, progress_callback):
            return True, output_path
        else:
            return False, "剪辑失败"

    def merge_video_files_complex(self, file_list, output_path, progress_callback=None):
        """
        高级合并：支持每个片段的裁剪范围
        file_list: [{'path': str, 'start': float, 'end': float, 'unit': 'time'|'frame'}, ...]
        """
        if not self.ffmpeg_available:
            return False, "ffmpeg未安装"
        
        if len(file_list) < 2:
            return False, "至少需要两个文件"

        # 构造 filter_complex
        # 1. 准备输入
        # 2. 对每个输入进行 trim (如果需要)
        # 3. 使用 xfade 和 acrossfade 连接
        
        inputs = []
        filter_complex = []
        
        # 预处理：获取FPS (为了帧转时间)
        # 假设所有视频FPS一致，或者ffmpeg会自动处理。
        # 为了安全，先把所有时间转换为秒
        
        processed_clips = []
        for i, clip in enumerate(file_list):
            path = clip['path']
            inputs.extend(self._get_input_flags())
            inputs.extend(['-i', path])
            
            start = clip.get('start', 0)
            end = clip.get('end', None)
            unit = clip.get('unit', 'time')
            
            if unit == 'frame':
                fps = self.get_video_fps(path)
                if fps > 0:
                    start = start / fps
                    if end is not None:
                        end = end / fps
                else:
                    # Fallback to seconds if fps fails, assuming user meant seconds? No, better error.
                    logger.warning(f"无法获取FPS: {path}, 将按秒处理")
            
            # 如果 end 为 None，需要获取视频时长
            if end is None:
                duration = self.get_video_duration(path)
                end = duration
            
            duration = end - start

            processed_clips.append({'index': i, 'start': start, 'end': end, 'duration': duration})

        # 构建 Filter Graph
        # [0:v]trim=start=s:end=e,setpts=PTS-STARTPTS[v0];
        # [0:a]atrim=start=s:end=e,asetpts=PTS-STARTPTS[a0];
        
        video_streams = []
        audio_streams = []
        
        for i, clip in enumerate(processed_clips):
            # Trim Video
            v_tag = f"v{i}"
            filter_complex.append(f"[{i}:v]trim=start={clip['start']}:end={clip['end']},setpts=PTS-STARTPTS[{v_tag}]")
            video_streams.append(v_tag)
            
            # Trim Audio
            a_tag = f"a{i}"
            path = file_list[clip['index']]['path']
            if self.has_audio_stream(path):
                filter_complex.append(f"[{i}:a]atrim=start={clip['start']}:end={clip['end']},asetpts=PTS-STARTPTS[{a_tag}]")
            else:
                 filter_complex.append(f"anullsrc=channel_layout=stereo:sample_rate=44100,atrim=duration={clip['duration']}[{a_tag}]")
            audio_streams.append(a_tag)

        if not transition:
            # 直接 concat
            v_concat = "".join([f"[{v}]" for v in video_streams])
            a_concat = "".join([f"[{a}]" for a in audio_streams])
            filter_complex.append(f"{v_concat}concat=n={len(file_list)}:v=1:a=0[outv]")
            filter_complex.append(f"{a_concat}concat=n={len(file_list)}:v=0:a=1[outa]")
        else:
            # Transition logic removed as requested
            # Fallback to direct concat
            v_concat = "".join([f"[{v}]" for v in video_streams])
            a_concat = "".join([f"[{a}]" for a in audio_streams])
            filter_complex.append(f"{v_concat}concat=n={len(file_list)}:v=1:a=0[outv]")
            filter_complex.append(f"{a_concat}concat=n={len(file_list)}:v=0:a=1[outa]")

        cmd = [self.ffmpeg_path] + inputs + ['-filter_complex', ";".join(filter_complex)]
        cmd.extend(['-map', '[outv]', '-map', '[outa]'])
        cmd.extend(self._get_encoding_params())
        cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
        cmd.extend(['-y', output_path])
        
        logger.info(f"高级合并: {cmd}")
        if self._run_ffmpeg_with_progress(cmd, progress_callback):
            return True, output_path
        else:
            return False, "合并失败"

    def merge_videos_with_range(self, file_list, output_path, progress_callback=None):
        """
        合并多个视频文件，支持片段剪辑
        file_list: [{'path': str, 'start': float, 'end': float}, ...]
        """
        if not self.ffmpeg_available:
            return False, "ffmpeg未安装"
        
        if len(file_list) < 2:
            return False, "至少需要两个文件"

        inputs = []
        filter_complex = []
        
        video_streams = []
        audio_streams = []
        
        for i, clip in enumerate(file_list):
            path = clip['path']
            inputs.extend(self._get_input_flags())
            inputs.extend(['-i', path])
            
            start = clip.get('start', 0)
            end = clip.get('end', None)
            
            # 如果 end 为 None，需要获取视频时长
            if end is None:
                duration_total = self.get_video_duration(path)
                end = duration_total
            
            duration = end - start
            
            # Trim Video
            v_tag = f"v{i}"
            filter_complex.append(f"[{i}:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[{v_tag}]")
            video_streams.append(v_tag)
            
            # Trim Audio
            a_tag = f"a{i}"
            if self.has_audio_stream(path):
                filter_complex.append(f"[{i}:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[{a_tag}]")
            else:
                # 生成静音音频
                filter_complex.append(f"anullsrc=channel_layout=stereo:sample_rate=44100,atrim=duration={duration}[{a_tag}]")
            
            audio_streams.append(a_tag)

        # Concat
        v_concat = "".join([f"[{v}]" for v in video_streams])
        a_concat = "".join([f"[{a}]" for a in audio_streams])
        filter_complex.append(f"{v_concat}concat=n={len(file_list)}:v=1:a=0[outv]")
        filter_complex.append(f"{a_concat}concat=n={len(file_list)}:v=0:a=1[outa]")

        cmd = [self.ffmpeg_path] + inputs + ['-filter_complex', ";".join(filter_complex)]
        cmd.extend(['-map', '[outv]', '-map', '[outa]'])
        cmd.extend(self._get_encoding_params())
        cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
        cmd.extend(['-y', output_path])
        
        logger.info(f"合并视频 {cmd}")
        if self._run_ffmpeg_with_progress(cmd, progress_callback):
            return True, output_path
        else:
            return False, "合并失败"

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
            
        # Filters
        filters = [f'scale={target_resolution}:force_original_aspect_ratio=decrease']
        
        cmd = [self.ffmpeg_path] + self._get_input_flags() + ['-i', input_path]
        
        cmd.extend(['-vf', ','.join(filters)])
        cmd.extend(self._get_encoding_params(crf=crf))
        cmd.extend(['-c:a', 'aac', '-b:a', '128k', '-y', output_path])
        
        logger.info(f"压缩视频: {cmd}")
        if self._run_ffmpeg_with_progress(cmd, progress_callback):
            return True, output_path
        else:
            return False, "压缩失败"

    def _run_ffmpeg_with_progress(self, cmd, progress_callback):
        """运行ffmpeg并解析进度"""
        try:
            # 使用shell=False, cmd为列表
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
                
                self.last_error_log = [] # 保存最后10行日志
                
                for line in process.stderr:
                    line_str = line.strip()
                    self.last_error_log.append(line_str)
                    if len(self.last_error_log) > 20:
                        self.last_error_log.pop(0)
                        
                    # logger.debug(line_str) # 调试用
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
            
            if process.returncode != 0:
                logger.error(f"ffmpeg执行失败，返回码: {process.returncode}")
                if hasattr(self, 'last_error_log'):
                    logger.error("FFmpeg最后输出:\n" + "\n".join(self.last_error_log))
            
            if progress_callback:
                progress_callback(100, 100)
                
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"ffmpeg执行出错: {e}")
            return False
