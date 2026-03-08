import os
import cv2
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
                             QSizePolicy, QSlider, QSpinBox, QFileDialog, 
                             QPushButton, QFrame, QSplitter, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from ui.widgets.edit_widgets import DragDropListWidget
from ui.widgets.zoomable_image_view import ZoomableImageWidget
from .base_page import BaseEditPage

class FramePage(BaseEditPage):
    def __init__(self, main_window, processor):
        super().__init__(main_window, processor)
        self.cap = None
        self.current_frame_img = None
        self.total_frames = 0
        self.fps = 30 # Default
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # Header
        self.setup_header(layout, "逐帧获取", "精确查看视频每一帧并保存高清截图")
        
        # Main Content - Splitter for resizing
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(1)
        
        # Top: File List (Collapsible-ish)
        file_widget = QWidget()
        file_layout = QVBoxLayout(file_widget)
        file_layout.setContentsMargins(0, 0, 0, 0)
        
        self.frame_file_list = DragDropListWidget()
        self.frame_file_list.file_dropped.connect(lambda p: self.load_video_for_frame(p))
        self.frame_file_list.clicked.connect(lambda: self.select_single_file(self.frame_file_list, None, callback=self.load_video_for_frame))
        self.frame_file_list.setMaximumHeight(80)
        self.frame_file_list.setToolTip("拖拽视频文件到此处")
        file_layout.addWidget(self.frame_file_list)
        
        splitter.addWidget(file_widget)
        
        # Middle: Preview (Large)
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 10, 0, 10)
        
        self.preview_widget = ZoomableImageWidget()
        self.preview_widget.set_selection_enabled(False) # No selection needed for frame view
        self.preview_widget.setMinimumHeight(300)
        preview_layout.addWidget(self.preview_widget)
        
        # Tips
        # tips = QLabel("提示: 滚轮缩放 | 右键拖拽移动")
        # tips.setAlignment(Qt.AlignCenter)
        # tips.setStyleSheet("color: #888; font-size: 12px;")
        # preview_layout.addWidget(tips)
        
        splitter.addWidget(preview_container)
        
        # Set stretch factors (Top: 0, Bottom: 1)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
        # Bottom: Controls
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(15, 15, 15, 15)
        
        # 1. Slider & Info
        slider_layout = QHBoxLayout()
        
        self.time_label = QLabel("00:00:00")
        self.time_label.setFixedWidth(80)
        self.time_label.setStyleSheet("font-family: monospace; font-weight: bold; color: #555; border: none;")
        slider_layout.addWidget(self.time_label)
        
        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setEnabled(False)
        self.frame_slider.valueChanged.connect(self.seek_frame)
        self.frame_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #ddd;
                height: 6px;
                background: #e0e0e0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #fb7299;
                border: 1px solid #fb7299;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #fb7299;
                border-radius: 3px;
            }
        """)
        slider_layout.addWidget(self.frame_slider)
        
        self.frame_info_label = QLabel("0 / 0")
        self.frame_info_label.setFixedWidth(100)
        self.frame_info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.frame_info_label.setStyleSheet("color: #555; border: none;")
        slider_layout.addWidget(self.frame_info_label)
        
        controls_layout.addLayout(slider_layout)
        
        # 2. Buttons
        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(10)
        
        # Jump Buttons
        self.btn_prev_s = QPushButton("⏪ -1秒")
        self.btn_prev_f = QPushButton("◀ 上一帧")
        self.btn_next_f = QPushButton("下一帧 ▶")
        self.btn_next_s = QPushButton("+1秒 ⏩")
        
        for btn in [self.btn_prev_s, self.btn_prev_f, self.btn_next_f, self.btn_next_s]:
            btn.setCursor(Qt.PointingHandCursor)
            btn.setEnabled(False)
            btn.setFixedWidth(90)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    border: 1px solid #dcdfe6;
                    color: #606266;
                    border-radius: 4px;
                    padding: 6px 0;
                }
                QPushButton:hover {
                    color: #fb7299;
                    border-color: #fb7299;
                    background-color: #ecf5ff;
                }
                QPushButton:pressed {
                    background-color: #fb7299;
                    color: white;
                }
                QPushButton:disabled {
                    background-color: #f5f7fa;
                    border-color: #e4e7ed;
                    color: #c0c4cc;
                }
            """)
            
        self.btn_prev_s.clicked.connect(lambda: self.jump_seconds(-1))
        self.btn_prev_f.clicked.connect(lambda: self.jump_frame(-1))
        self.btn_next_f.clicked.connect(lambda: self.jump_frame(1))
        self.btn_next_s.clicked.connect(lambda: self.jump_seconds(1))
        
        btns_layout.addWidget(self.btn_prev_s)
        btns_layout.addWidget(self.btn_prev_f)
        btns_layout.addWidget(self.btn_next_f)
        btns_layout.addWidget(self.btn_next_s)
        
        btns_layout.addStretch()
        
        # Frame Spin
        btns_layout.addWidget(QLabel("跳转帧:"))
        self.frame_spin = QSpinBox()
        self.frame_spin.setRange(0, 0)
        self.frame_spin.setEnabled(False)
        self.frame_spin.setFixedWidth(100)
        self.frame_spin.valueChanged.connect(self.on_frame_spin_changed)
        self.style_spinbox(self.frame_spin)
        btns_layout.addWidget(self.frame_spin)
        
        btns_layout.addSpacing(20)
        
        # Save Button
        self.save_frame_btn = QPushButton("📸 保存当前帧")
        self.save_frame_btn.setCursor(Qt.PointingHandCursor)
        self.save_frame_btn.setEnabled(False)
        self.save_frame_btn.setStyleSheet("""
            QPushButton {
                background-color: #fb7299;
                color: white;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
            QPushButton:pressed {
                background-color: #e45c84;
            }
            QPushButton:disabled {
                background-color: #f5f7fa;
                color: #c0c4cc;
                border: 1px solid #e4e7ed;
            }
        """)
        self.save_frame_btn.clicked.connect(self.save_current_frame)
        btns_layout.addWidget(self.save_frame_btn)
        
        controls_layout.addLayout(btns_layout)
        layout.addWidget(controls_frame)
        
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
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            if self.fps <= 0: self.fps = 30
            
            self.frame_slider.setRange(0, self.total_frames - 1)
            self.frame_slider.setValue(0)
            self.frame_slider.setEnabled(True)
            
            self.frame_spin.setRange(0, self.total_frames - 1)
            self.frame_spin.setValue(0)
            self.frame_spin.setEnabled(True)
            
            self.save_frame_btn.setEnabled(True)
            for btn in [self.btn_prev_s, self.btn_prev_f, self.btn_next_f, self.btn_next_s]:
                btn.setEnabled(True)
            
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

    def jump_frame(self, delta):
        current = self.frame_slider.value()
        new_val = max(0, min(self.total_frames - 1, current + delta))
        self.frame_slider.setValue(new_val)

    def jump_seconds(self, seconds):
        delta_frames = int(seconds * self.fps)
        self.jump_frame(delta_frames)
            
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
                
                # Use ZoomableImageWidget to set image
                self.preview_widget.set_image(qt_img)
                
                # Update Info
                self.frame_info_label.setText(f"{frame_idx} / {self.total_frames}")
                
                # Update Time
                seconds = frame_idx / self.fps
                m, s = divmod(seconds, 60)
                h, m = divmod(m, 60)
                self.time_label.setText(f"{int(h):02d}:{int(m):02d}:{int(s):02d}")
                
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
