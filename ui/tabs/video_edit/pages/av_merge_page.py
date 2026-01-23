import os
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QGroupBox, QLineEdit)
from PyQt5.QtCore import Qt
from .base_page import BaseEditPage
from ..workers import GenericWorker
from ui.message_box import BilibiliMessageBox

class AVMergePage(BaseEditPage):
    def __init__(self, main_window, processor):
        super().__init__(main_window, processor)
        self.video_path = ""
        self.audio_path = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        self.setup_header(layout, "音视频合并", "将独立的视频文件和音频文件合并为一个视频")
        
        # Video Selection
        video_group = QGroupBox("视频源文件 (Video)")
        video_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; color: #333; margin-top: 10px; }")
        video_layout = QHBoxLayout(video_group)
        
        self.video_input = QLineEdit()
        self.video_input.setPlaceholderText("请选择视频文件...")
        self.video_input.setReadOnly(True)
        self.video_input.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px; background: #f9f9f9;")
        video_layout.addWidget(self.video_input)
        
        video_btn = self.create_button("选择视频", self.select_video)
        video_layout.addWidget(video_btn)
        layout.addWidget(video_group)
        
        # Audio Selection
        audio_group = QGroupBox("音频源文件 (Audio)")
        audio_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; color: #333; margin-top: 10px; }")
        audio_layout = QHBoxLayout(audio_group)
        
        self.audio_input = QLineEdit()
        self.audio_input.setPlaceholderText("请选择音频文件...")
        self.audio_input.setReadOnly(True)
        self.audio_input.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px; background: #f9f9f9;")
        audio_layout.addWidget(self.audio_input)
        
        audio_btn = self.create_button("选择音频", self.select_audio)
        audio_layout.addWidget(audio_btn)
        layout.addWidget(audio_group)

        layout.addStretch()
        
        # Progress Bar
        self.progress_bar = self.create_progress_bar()
        layout.addWidget(self.progress_bar)
        
        # Action Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.start_btn = self.create_primary_button("开始合并", self.start_merge)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def select_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "Video Files (*.mp4 *.mkv *.avi *.flv *.mov);;All Files (*.*)")
        if path:
            self.video_path = path
            self.video_input.setText(path)

    def select_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择音频文件", "", "Audio Files (*.mp3 *.m4a *.wav *.aac *.flac);;All Files (*.*)")
        if path:
            self.audio_path = path
            self.audio_input.setText(path)

    def start_merge(self):
        if not self.video_path or not self.audio_path:
            BilibiliMessageBox.warning(self, "提示", "请先选择视频和音频文件！")
            return
            
        if not os.path.exists(self.video_path) or not os.path.exists(self.audio_path):
            BilibiliMessageBox.warning(self, "错误", "输入文件不存在！")
            return

        self.start_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.worker = GenericWorker(self.processor.av_merge, self.video_path, self.audio_path)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_merge_finished)
        self.worker.start()

    def update_progress(self, current, total):
        if total > 0:
            val = int((current / total) * 100)
            self.progress_bar.setValue(val)

    def on_merge_finished(self, success, result):
        self.start_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            BilibiliMessageBox.information(self, "成功", f"合并成功！\n文件已保存至: {result}")
        else:
            BilibiliMessageBox.error(self, "失败", f"合并失败: {result}")
