import os
import cv2
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFileDialog, QSizePolicy, QScrollArea, QFrame, QGroupBox)
from PyQt5.QtCore import Qt, QRect, QSize, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from .base_page import BaseEditPage
from ui.widgets.zoomable_image_view import ZoomableImageWidget
from ui.widgets.edit_widgets import DragDropListWidget
from core.watermark import WatermarkRemover

class WatermarkWorker(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, processor, input_path, rect, method="delogo"):
        super().__init__()
        self.processor = processor
        self.input_path = input_path
        self.rect = rect
        self.method = method
        # Use the processor's watermark_remover which is correctly configured with a runner
        if hasattr(processor, 'watermark_remover') and processor.watermark_remover:
            self.remover = processor.watermark_remover
        else:
            # Fallback or create new one with correct runner
            # Note: accessing protected member _run_ffmpeg_with_progress
            self.remover = WatermarkRemover(processor.ffmpeg_path, processor._run_ffmpeg_with_progress)

    def update_progress(self, current, total):
        if total > 0:
            self.progress_signal.emit(int(current / total * 100))

    def run(self):
        try:
            if self.method == 'lama':
                success, result = self.remover.remove_watermark_lama(
                    self.input_path, 
                    rect=self.rect,
                    progress_callback=self.update_progress
                )
            else:
                success, result = self.remover.remove_watermark_delogo(
                    self.input_path, 
                    rect=self.rect,
                    progress_callback=self.update_progress
                )
            self.finished_signal.emit(success, result)
        except Exception as e:
            self.finished_signal.emit(False, str(e))

class RemoveWatermarkPage(BaseEditPage):
    def __init__(self, main_window, processor):
        super().__init__(main_window, processor)
        self.input_path = ""
        self.selection_rect = None # QRect in video coordinates
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Title and Subtitle
        title_layout = QVBoxLayout()
        title_label = QLabel("视频去水印")
        title_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #333;")
        title_layout.addWidget(title_label)
        
        sub_label = QLabel("选择区域去除视频中的水印/文字")
        sub_label.setStyleSheet("font-size: 20px; color: #999;")
        title_layout.addWidget(sub_label)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Start Button (Moved to Header)
        self.start_btn = self.create_primary_button("开始去水印", self.start_processing)
        self.start_btn.setEnabled(False)
        header_layout.addWidget(self.start_btn)
        
        layout.addLayout(header_layout)

        # 1. File Selection
        self.file_list = DragDropListWidget()
        self.file_list.setToolTip("支持拖拽视频文件到此处")
        self.file_list.file_dropped.connect(self.handle_file_drop)
        self.file_list.clicked.connect(lambda: self.select_single_file(self.file_list, None, self.on_file_selected))
        self.file_list.setMaximumHeight(100)
        layout.addWidget(self.file_list)
        
        # 2. Preview Area
        # Simplified container for maximum space
        preview_container = QFrame()
        preview_container.setStyleSheet("background-color: #f0f0f0; border-radius: 4px;")
        container_layout = QVBoxLayout(preview_container)
        container_layout.setContentsMargins(0, 0, 0, 0) # Remove margins
        container_layout.setAlignment(Qt.AlignCenter)
        
        self.preview_widget = ZoomableImageWidget()
        self.preview_widget.setMinimumHeight(300)
        self.preview_widget.rect_selected.connect(self.on_rect_selected)
        container_layout.addWidget(self.preview_widget)
        
        layout.addWidget(preview_container, 1) # Give stretch to preview
        
        # Tips for controls
        # controls_tip = QLabel("操作提示: 滚轮缩放 | 右键拖拽移动 | 左键框选区域")
        # controls_tip.setAlignment(Qt.AlignCenter)
        # controls_tip.setStyleSheet("color: #888; font-size: 12px; margin-top: 5px;")
        # layout.addWidget(controls_tip)
        
        # Progress
        self.progress_bar = self.create_progress_bar()
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 14px;")
        layout.addWidget(self.status_label)
        
        self.reset_list(self.file_list, "👇 拖拽视频文件到此处")

    def handle_file_drop(self, file_path):
        self.set_single_file(file_path, self.file_list, None)
        self.on_file_selected(file_path)

    def on_file_selected(self, file_path):
        if not os.path.exists(file_path):
            return
            
        self.input_path = file_path
        self.load_preview(file_path)
        self.status_label.setText("请在预览图上框选水印区域")
        self.start_btn.setEnabled(False)
        self.selection_rect = None

    def load_preview(self, file_path):
        try:
            cap = cv2.VideoCapture(file_path)
            # Read a frame from the middle to ensure watermark is visible (sometimes intro doesn't have it)
            # But better: read first few seconds. Let's try 5th second or 10%
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Try to read at 5 seconds, or 10% if video is short
            target_frame = min(int(fps * 5), int(frame_count * 0.1))
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            ret, frame = cap.read()
            if not ret:
                # Fallback to start
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                
            if ret:
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                # Create QImage and ensure it's a copy with rgbSwapped
                convert_to_Qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
                
                # Pass the full resolution image to the widget
                self.preview_widget.set_image(convert_to_Qt_format)
                
            cap.release()
        except Exception as e:
            self.main_window.log_to_console(f"加载预览失败: {e}", "error")

    def on_rect_selected(self, rect):
        if not self.input_path:
            return
            
        # rect is already in image coordinates from ZoomableImageWidget
        self.selection_rect = rect
        self.final_rect = (rect.x(), rect.y(), rect.width(), rect.height())
        
        vid_x, vid_y, vid_w, vid_h = self.final_rect
        self.status_label.setText(f"选区坐标: ({vid_x}, {vid_y}), 大小: {vid_w}x{vid_h}")
        self.start_btn.setEnabled(True)

    def start_processing(self):
        if not self.input_path or not self.selection_rect:
            return
            
        self.start_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        method = "delogo"
        if hasattr(self.main_window, 'config_manager'):
             if self.main_window.config_manager.config.get('watermark_method') == 'Simple Lama (AI)':
                 method = 'lama'
        
        self.worker = WatermarkWorker(self.processor, self.input_path, self.final_rect, method)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()
        
    def on_finished(self, success, result):
        self.start_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.main_window.log_to_console(f"去水印成功: {result}", "success")
            self.status_label.setText(f"处理完成！输出文件: {os.path.basename(result)}")
        else:
            self.main_window.log_to_console(f"去水印失败: {result}", "error")
            self.status_label.setText(f"处理失败: {result}")

