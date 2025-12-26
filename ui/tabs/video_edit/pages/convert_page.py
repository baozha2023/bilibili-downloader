import os
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
from PyQt5.QtCore import Qt
from ui.widgets.custom_combobox import NoScrollComboBox
from ui.widgets.edit_widgets import DragDropListWidget
from .base_page import BaseEditPage
from ..workers import GenericWorker

class ConvertPage(BaseEditPage):
    def __init__(self, main_window, processor):
        super().__init__(main_window, processor)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(15)
        
        self.setup_header(layout, "格式转换", "支持视频格式互转及音频提取")

        # --- Video Conversion Section ---
        video_group = QGroupBox("视频转换")
        video_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 16px; }")
        video_layout = QVBoxLayout(video_group)
        
        # Video File List
        self.convert_file_list = DragDropListWidget()
        self.convert_file_list.file_dropped.connect(lambda p: self.set_single_file(p, self.convert_file_list, self.convert_btn))
        self.convert_file_list.clicked.connect(lambda: self.select_single_file(self.convert_file_list, self.convert_btn))
        video_layout.addWidget(self.convert_file_list)
        
        # Video Controls
        video_controls = QHBoxLayout()
        video_controls.addStretch()
        video_controls.addWidget(QLabel("目标格式:"))
        self.format_combo = NoScrollComboBox()
        self.format_combo.addItems(["mp4", "mkv", "avi", "mov", "gif"])
        self.format_combo.setFixedWidth(100)
        self.style_combo(self.format_combo)
        video_controls.addWidget(self.format_combo)
        video_controls.addSpacing(20)
        
        self.convert_btn = self.create_primary_button("开始视频转换", self.start_conversion)
        self.convert_btn.setEnabled(False)
        video_controls.addWidget(self.convert_btn)
        video_layout.addLayout(video_controls)
        
        layout.addWidget(video_group)

        # --- Audio Conversion Section ---
        audio_group = QGroupBox("音频转换/提取")
        audio_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 16px; }")
        audio_layout = QVBoxLayout(audio_group)
        
        # Audio File List
        self.audio_file_list = DragDropListWidget()
        self.audio_file_list.file_dropped.connect(lambda p: self.set_single_file(p, self.audio_file_list, self.audio_convert_btn))
        self.audio_file_list.clicked.connect(lambda: self.select_single_file(self.audio_file_list, self.audio_convert_btn))
        audio_layout.addWidget(self.audio_file_list)
        
        # Audio Controls
        audio_controls = QHBoxLayout()
        audio_controls.addStretch()
        audio_controls.addWidget(QLabel("目标格式:"))
        self.audio_format_combo = NoScrollComboBox()
        self.audio_format_combo.addItems(["mp3", "m4a", "wav", "flac"])
        self.audio_format_combo.setFixedWidth(100)
        self.style_combo(self.audio_format_combo)
        audio_controls.addWidget(self.audio_format_combo)
        audio_controls.addSpacing(20)
        
        self.audio_convert_btn = self.create_primary_button("开始音频转换", self.start_audio_conversion)
        self.audio_convert_btn.setEnabled(False)
        audio_controls.addWidget(self.audio_convert_btn)
        audio_layout.addLayout(audio_controls)
        
        layout.addWidget(audio_group)
        
        # Progress (Shared)
        self.convert_progress = self.create_progress_bar()
        layout.addWidget(self.convert_progress)
        
        self.convert_status = QLabel("")
        self.convert_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.convert_status)
        
        self.reset_list(self.convert_file_list, "👇 拖拽视频文件到此处")
        self.reset_list(self.audio_file_list, "👇 拖拽视频/音频文件到此处")

    def start_conversion(self):
        self._start_generic_conversion(self.convert_file_list, self.format_combo, self.convert_btn, "视频")

    def start_audio_conversion(self):
        self._start_generic_conversion(self.audio_file_list, self.audio_format_combo, self.audio_convert_btn, "音频")

    def _start_generic_conversion(self, list_widget, combo, btn, type_name):
        if list_widget.count() == 0 or not list_widget.item(0).flags() & Qt.ItemIsEnabled:
            return
        
        file_path = list_widget.item(0).data(Qt.UserRole)
        if not file_path:
             file_path = list_widget.item(0).text()
             
        fmt = combo.currentText()
        
        # Disable buttons
        self.convert_btn.setEnabled(False)
        self.audio_convert_btn.setEnabled(False)
        
        self.convert_progress.setVisible(True)
        self.convert_progress.setValue(0)
        self.convert_status.setText(f"正在转换{type_name}...")
        
        self.main_window.log_to_console(f"开始转换{type_name}: {os.path.basename(file_path)} -> {fmt}", "info")
        
        self.worker = GenericWorker(self.processor.convert_video, file_path, fmt)
        self.worker.progress_signal.connect(self.convert_progress.setValue)
        self.worker.finished_signal.connect(lambda s, m: self.on_convert_finished(s, m, btn))
        self.worker.start()
        
    def on_convert_finished(self, success, msg, btn):
        # Re-enable buttons if file loaded
        if self.convert_file_list.count() > 0 and self.convert_file_list.item(0).flags() & Qt.ItemIsEnabled:
            self.convert_btn.setEnabled(True)
        if self.audio_file_list.count() > 0 and self.audio_file_list.item(0).flags() & Qt.ItemIsEnabled:
            self.audio_convert_btn.setEnabled(True)
            
        if success:
            self.convert_status.setText(f"✅ 转换成功: {os.path.basename(msg)}")
            self.convert_progress.setValue(100)
            self.main_window.log_to_console(f"转换成功: {msg}", "success")
        else:
            self.convert_status.setText(f"❌ 失败: {msg}")
            self.main_window.log_to_console(f"转换失败: {msg}", "error")
