import os
import logging
import json
import re
import subprocess
from core.config import ConfigManager

logger = logging.getLogger('bilibili_core.watermark')

class WatermarkRemover:
    def __init__(self, ffmpeg_path, runner=None):
        self.ffmpeg_path = ffmpeg_path
        self.runner = runner
        self.strategies = {
            'delogo': self.remove_watermark_delogo,
            'external': self.remove_watermark_external
        }

    def calculate_watermark_rect(self, width, height):
        """
        Heuristic to calculate watermark position based on resolution.
        Bilibili watermarks are usually at top-right.
        """
        if width >= 3840: # 4K
            wm_w, wm_h = 320, 100
            margin_x, margin_y = 55, 45
        elif width >= 2560: # 2K
            wm_w, wm_h = 250, 80
            margin_x, margin_y = 45, 35
        elif width >= 1920: # 1080p
            wm_w, wm_h = 200, 65
            margin_x, margin_y = 40, 30
        elif width >= 1280: # 720p
            wm_w, wm_h = 150, 50
            margin_x, margin_y = 25, 20
        else:
            wm_w = max(int(width * 0.12), 100)
            wm_h = max(int(height * 0.06), 40)
            margin_x = int(width * 0.03)
            margin_y = int(height * 0.03)
        
        # Adjust for vertical video
        if height > width:
            wm_w = int(width * 0.35)
            wm_h = int(wm_w * 0.35)
            margin_x = int(width * 0.05)
            margin_y = int(height * 0.02)
        
        wm_x = width - wm_w - margin_x
        wm_y = margin_y
        
        # Boundary checks
        wm_x = max(0, min(wm_x, width - wm_w))
        wm_y = max(0, min(wm_y, height - wm_h))
        
        return wm_x, wm_y, wm_w, wm_h

    def remove_watermark_delogo(self, input_path, output_path=None, rect=None, progress_callback=None):
        """
        Use FFmpeg delogo filter.
        rect: (x, y, w, h) tuple. If None, auto-calculated.
        """
        if not output_path:
            input_dir = os.path.dirname(input_path)
            input_name = os.path.splitext(os.path.basename(input_path))[0]
            ext = os.path.splitext(input_path)[1]
            output_path = os.path.join(input_dir, f"{input_name}_clean{ext}")

        if not rect:
            # Need resolution
            w, h = self._get_resolution(input_path)
            if w and h:
                rect = self.calculate_watermark_rect(w, h)
                logger.info(f"Auto-calculated watermark rect for {w}x{h}: {rect}")
            else:
                return False, "Could not determine video resolution"
        
        x, y, w, h = rect
        
        # band option might not be supported in all ffmpeg versions or builds
        # Simplified filter string
        filter_str = f"delogo=x={x}:y={y}:w={w}:h={h}:show=0"
        
        cmd = [
            self.ffmpeg_path,
            '-i', input_path,
            '-vf', filter_str,
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-c:a', 'copy',
            '-y', output_path
        ]
        
        logger.info(f"Executing delogo: {cmd}")
        
        if self.runner:
            success = self.runner(cmd, progress_callback)
            if success:
                return True, output_path
            else:
                return False, "去水印失败"
        return False, "Runner not configured"

    def remove_watermark_external(self, input_path, output_path=None, tool_cmd=None, progress_callback=None):
        """
        Use external tool (e.g. AI model CLI).
        tool_cmd: Command template list, e.g. ["python", "main.py", "--input", "{input}", "--output", "{output}"]
        """
        if not tool_cmd:
            return False, "No external tool configured"
            
        if not output_path:
            input_dir = os.path.dirname(input_path)
            input_name = os.path.splitext(os.path.basename(input_path))[0]
            ext = os.path.splitext(input_path)[1]
            output_path = os.path.join(input_dir, f"{input_name}_ai_clean{ext}")
            
        # Format command
        cmd = []
        for arg in tool_cmd:
            cmd.append(arg.format(input=input_path, output=output_path))
            
        logger.info(f"Executing external tool: {cmd}")
        
        # We can use self.runner if it supports arbitrary commands, 
        # but self.runner might expect ffmpeg output format for progress parsing.
        # So we might need a custom runner or just subprocess here.
        
        try:
            # Simple execution
            subprocess.run(cmd, check=True)
            if os.path.exists(output_path):
                return True, output_path
            return False, "Output file not found"
        except Exception as e:
            return False, f"External tool failed: {e}"

    def _get_resolution(self, video_path):
        # Helper to get resolution using ffprobe/ffmpeg
        # Re-implement simple version or rely on caller to pass it?
        # For independence, let's implement a simple probe using ffmpeg
        try:
            cmd = [self.ffmpeg_path, '-i', video_path]
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True, encoding='utf-8', errors='replace')
            _, stderr = p.communicate()
            match = re.search(r'Stream #\d+:\d+.*Video:.* (\d{3,5})x(\d{3,5})', stderr)
            if match:
                return int(match.group(1)), int(match.group(2))
        except Exception as e:
            logger.error(f"Get resolution failed: {e}")
        return None, None
