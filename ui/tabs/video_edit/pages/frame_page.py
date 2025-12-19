import os
import cv2
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
                             QSizePolicy, QSlider, QSpinBox, QFileDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from ui.widgets.edit_widgets import DragDropListWidget
from .base_page import BaseEditPage

class FramePage(BaseEditPage):
    def __init__(self, main_window, processor):
        super().__init__(main_window, processor)
        self.cap = None
        self.current_frame_img = None
        self.total_frames = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        self.setup_header(layout, "逐帧获取", "查看视频任意帧并保存")
        
        # File Selection
        self.frame_file_list = DragDropListWidget()
        self.frame_file_list.file_dropped.connect(lambda p: self.load_video_for_frame(p))
        self.frame_file_list.clicked.connect(lambda: self.select_single_file(self.frame_file_list, None, callback=self.load_video_for_frame))
        self.frame_file_list.setMaximumHeight(100)
        layout.addWidget(self.frame_file_list)
        
        # Preview Area
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #000; border-radius: 8px;")
        self.preview_label.setMinimumHeight(300)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.preview_label)
        
        # Controls
        controls_group = QGroupBox("帧控制")
        controls_group.setStyleSheet("QGroupBox { font-size: 16px; color: #333; border: 1px solid #ddd; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        controls_layout = QVBoxLayout(controls_group)
        
        # Slider
        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setEnabled(False)
        self.frame_slider.valueChanged.connect(self.seek_frame)
        controls_layout.addWidget(self.frame_slider)
        
        # Info & SpinBox
        info_layout = QHBoxLayout()
        self.frame_info_label = QLabel("0 / 0 帧")
        info_layout.addWidget(self.frame_info_label)
        
        info_layout.addStretch()
        
        info_layout.addWidget(QLabel("跳转到:"))
        self.frame_spin = QSpinBox()
        self.frame_spin.setRange(0, 0)
        self.frame_spin.setEnabled(False)
        self.frame_spin.valueChanged.connect(self.on_frame_spin_changed)
        self.style_spinbox(self.frame_spin)
        info_layout.addWidget(self.frame_spin)
        
        controls_layout.addLayout(info_layout)
        layout.addWidget(controls_group)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.save_frame_btn = self.create_primary_button("保存当前帧", self.save_current_frame)
        self.save_frame_btn.setEnabled(False)
        btn_layout.addWidget(self.save_frame_btn)
        
        layout.addLayout(btn_layout)
        
        self.reset_list(self.frame_file_list, "👇 拖拽视频文件到此处")

    def load_video_for_frame(self, file_path):
        self.set_single_file(file_path, self.frame_file_list, None)
        
        if self.cap is not None:
            self.cap.release()
            
        try:
            self.cap = cv2.VideoCapture(file_path)
            if not self.cap.isOpened():
                self.main_window.log_to_console("无法打开视频文件", "error")
                return
                
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            # fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            self.frame_slider.setRange(0, self.total_frames - 1)
            self.frame_slider.setValue(0)
            self.frame_slider.setEnabled(True)
            
            self.frame_spin.setRange(0, self.total_frames - 1)
            self.frame_spin.setValue(0)
            self.frame_spin.setEnabled(True)
            
            self.save_frame_btn.setEnabled(True)
            
            self.update_frame_preview(0)
        except Exception as e:
            self.main_window.log_to_console(f"加载视频失败: {e}", "error")
        
    def seek_frame(self, frame_idx):
        if self.frame_spin.value() != frame_idx:
            self.frame_spin.blockSignals(True)
            self.frame_spin.setValue(frame_idx)
            self.frame_spin.blockSignals(False)
        self.update_frame_preview(frame_idx)
        
    def on_frame_spin_changed(self, val):
        if self.frame_slider.value() != val:
            self.frame_slider.setValue(val)
            
    def update_frame_preview(self, frame_idx):
        if not self.cap or not self.cap.isOpened():
            return
            
        try:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.cap.read()
            if ret:
                # Convert BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.current_frame_img = frame
                
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qt_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # Scale to fit label
                pixmap = QPixmap.fromImage(qt_img)
                scaled_pixmap = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(scaled_pixmap)
                
                self.frame_info_label.setText(f"{frame_idx} / {self.total_frames} 帧")
        except Exception as e:
            pass # Ignore preview errors during seek
            
    def save_current_frame(self):
        if self.current_frame_img is None:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存帧", 
            os.path.join(self.main_window.crawler.data_dir, f"frame_{self.frame_slider.value()}.jpg"), 
            "Image Files (*.jpg *.png *.bmp)"
        )
        
        if file_path:
            try:
                # Save using cv2 (need BGR)
                bgr_frame = cv2.cvtColor(self.current_frame_img, cv2.COLOR_RGB2BGR)
                cv2.imwrite(file_path, bgr_frame)
                self.main_window.log_to_console(f"已保存帧到: {file_path}", "success")
            except Exception as e:
                 self.main_window.log_to_console(f"保存失败: {e}", "error")
