import os
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
                             QStackedWidget, QDoubleSpinBox, QSpinBox, QMessageBox, QWidget)
from PyQt5.QtCore import Qt
from ui.widgets.custom_combobox import NoScrollComboBox
from ui.widgets.edit_widgets import DragDropListWidget
from .base_page import BaseEditPage
from ..workers import GenericWorker

class CutPage(BaseEditPage):
    def __init__(self, main_window, processor):
        super().__init__(main_window, processor)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        self.setup_header(layout, "视频剪辑", "精确裁剪视频片段，支持帧级剪辑")
        
        self.cut_file_list = DragDropListWidget()
        self.cut_file_list.setToolTip("支持拖拽视频文件到此处")
        self.cut_file_list.file_dropped.connect(lambda p: self.on_cut_file_dropped(p))
        self.cut_file_list.clicked.connect(lambda: self.select_single_file(self.cut_file_list, None, callback=self.on_cut_file_dropped))
        # Reduce size of file list area
        self.cut_file_list.setMaximumHeight(150)
        layout.addWidget(self.cut_file_list)
        
        # Controls Group
        settings_group = QGroupBox("剪辑设置")
        settings_group.setStyleSheet("QGroupBox { font-size: 16px; color: #333; border: 1px solid #ddd; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(15)
        
        # Unit & Range Row
        range_layout = QHBoxLayout()
        
        range_layout.addWidget(QLabel("单位:"))
        self.unit_combo = NoScrollComboBox()
        self.unit_combo.addItems(["秒 (Time)", "帧 (Frame)"])
        self.unit_combo.setFixedWidth(120)
        self.style_combo(self.unit_combo)
        self.unit_combo.currentIndexChanged.connect(self.update_cut_inputs)
        range_layout.addWidget(self.unit_combo)
        
        range_layout.addSpacing(20)
        
        # Time Inputs
        self.time_widget = QWidget()
        time_layout = QHBoxLayout(self.time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.addWidget(QLabel("开始(秒):"))
        self.start_time_spin = QDoubleSpinBox()
        self.start_time_spin.setRange(0, 99999)
        self.start_time_spin.setDecimals(1)
        self.style_spinbox(self.start_time_spin)
        time_layout.addWidget(self.start_time_spin)
        
        time_layout.addWidget(QLabel("结束(秒):"))
        self.end_time_spin = QDoubleSpinBox()
        self.end_time_spin.setRange(0, 99999)
        self.end_time_spin.setDecimals(1)
        self.style_spinbox(self.end_time_spin)
        time_layout.addWidget(self.end_time_spin)
        
        # Frame Inputs (Hidden by default)
        self.frame_widget = QWidget()
        frame_layout = QHBoxLayout(self.frame_widget)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.addWidget(QLabel("开始(帧):"))
        self.start_frame_spin = QSpinBox()
        self.start_frame_spin.setRange(0, 999999)
        self.style_spinbox(self.start_frame_spin)
        frame_layout.addWidget(self.start_frame_spin)
        
        frame_layout.addWidget(QLabel("结束(帧):"))
        self.end_frame_spin = QSpinBox()
        self.end_frame_spin.setRange(0, 999999)
        self.style_spinbox(self.end_frame_spin)
        frame_layout.addWidget(self.end_frame_spin)
        
        # Use QStackedWidget to prevent UI shifting
        self.input_stack = QStackedWidget()
        self.input_stack.addWidget(self.time_widget)
        self.input_stack.addWidget(self.frame_widget)
        range_layout.addWidget(self.input_stack)
        
        range_layout.addStretch()
        
        self.duration_label = QLabel("总时长: --")
        self.duration_label.setStyleSheet("color: #666; font-size: 14px;")
        range_layout.addWidget(self.duration_label)
        
        settings_layout.addLayout(range_layout)
        
        # Make settings group larger by giving it stretch in main layout
        layout.addWidget(settings_group, 1) # Add stretch factor 1 to settings
        
        # Controls
        controls_frame = self.create_control_frame()
        controls_layout = QHBoxLayout(controls_frame)
        
        controls_layout.addStretch()
        
        self.cut_btn = self.create_primary_button("开始剪辑", self.start_cut)
        self.cut_btn.setEnabled(False)
        controls_layout.addWidget(self.cut_btn)
        
        layout.addWidget(controls_frame)
        
        self.cut_progress = self.create_progress_bar()
        layout.addWidget(self.cut_progress)
        
        self.cut_status = QLabel("")
        self.cut_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.cut_status)
        
        layout.addStretch()
        self.reset_list(self.cut_file_list, "👇 拖拽视频文件到此处")

    def update_cut_inputs(self):
        is_frame = self.unit_combo.currentIndex() == 1
        self.input_stack.setCurrentIndex(1 if is_frame else 0)
        
        # Update limits if file loaded
        if self.cut_file_list.count() > 0:
            file_path = self.cut_file_list.item(0).data(Qt.UserRole)
            if not file_path: # Fallback if data is missing
                 file_path = self.cut_file_list.item(0).text()
                 
            if is_frame:
                # Update frame limits
                fps = self.processor.get_video_fps(file_path)
                duration = self.processor.get_video_duration(file_path)
                total_frames = int(duration * fps) if fps > 0 else 0
                self.start_frame_spin.setMaximum(total_frames)
                self.end_frame_spin.setMaximum(total_frames)
                if self.end_frame_spin.value() == 0:
                    self.end_frame_spin.setValue(total_frames)
                self.duration_label.setText(f"总时长: {duration}秒 (约 {total_frames} 帧)")
            else:
                duration = self.processor.get_video_duration(file_path)
                self.start_time_spin.setMaximum(duration)
                self.end_time_spin.setMaximum(duration)
                if self.end_time_spin.value() == 0:
                    self.end_time_spin.setValue(duration)
                self.duration_label.setText(f"总时长: {duration}秒")

    def on_cut_file_dropped(self, file_path):
        self.set_single_file(file_path, self.cut_file_list, self.cut_btn)
        # Get duration
        duration = self.processor.get_video_duration(file_path)
        self.duration_label.setText(f"总时长: {duration}秒")
        self.start_time_spin.setMaximum(duration)
        self.end_time_spin.setMaximum(duration)
        self.end_time_spin.setValue(duration)
        
        # Try to set fps-dependent frame limits
        try:
            fps = self.processor.get_video_fps(file_path)
            total_frames = int(duration * fps)
            self.start_frame_spin.setMaximum(total_frames)
            self.end_frame_spin.setMaximum(total_frames)
            self.end_frame_spin.setValue(total_frames)
        except:
            pass
        
    def start_cut(self):
        file_path = self.cut_file_list.item(0).data(Qt.UserRole)
        if not file_path:
             file_path = self.cut_file_list.item(0).text()
             
        start = self.start_time_spin.value()
        end = self.end_time_spin.value()
        unit = 'frame' if self.unit_combo.currentIndex() == 1 else 'time'
        
        if unit == 'frame':
            start = self.start_frame_spin.value()
            end = self.end_frame_spin.value()
        
        if start >= end:
            QMessageBox.warning(self, "错误", "开始时间必须小于结束时间")
            return
            
        self.cut_btn.setEnabled(False)
        self.cut_progress.setVisible(True)
        self.cut_progress.setValue(0)
        self.cut_status.setText("正在剪辑中...")
        
        self.main_window.log_to_console(f"开始剪辑视频: {os.path.basename(file_path)} ({start} - {end})", "info")
        
        # Removed fade_in and fade_out
        self.worker = GenericWorker(self.processor.cut_video, file_path, start, end, unit)
        self.worker.progress_signal.connect(self.cut_progress.setValue)
        self.worker.finished_signal.connect(self.on_cut_finished)
        self.worker.start()
        
    def on_cut_finished(self, success, msg):
        self.cut_btn.setEnabled(True)
        if success:
            self.cut_status.setText(f"✅ 剪辑成功: {os.path.basename(msg)}")
            self.cut_progress.setValue(100)
            self.main_window.log_to_console(f"剪辑成功: {msg}", "success")
        else:
            self.cut_status.setText(f"❌ 失败: {msg}")
            self.main_window.log_to_console(f"剪辑失败: {msg}", "error")
