import os
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel
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
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        self.setup_header(layout, "格式转换", "支持 mp4, mp3, mkv, avi, gif 等多种格式互转")
        
        # File List
        self.convert_file_list = DragDropListWidget()
        self.convert_file_list.file_dropped.connect(lambda p: self.set_single_file(p, self.convert_file_list, self.convert_btn))
        self.convert_file_list.clicked.connect(lambda: self.select_single_file(self.convert_file_list, self.convert_btn))
        layout.addWidget(self.convert_file_list)
        
        # Controls
        controls_frame = self.create_control_frame()
        controls_layout = QHBoxLayout(controls_frame)
        
        controls_layout.addStretch()
        
        controls_layout.addWidget(QLabel("目标格式:"))
        self.format_combo = NoScrollComboBox()
        self.format_combo.addItems(["mp4", "mp3", "mkv", "avi", "mov", "gif"])
        self.format_combo.setFixedWidth(100)
        self.style_combo(self.format_combo)
        controls_layout.addWidget(self.format_combo)
        
        controls_layout.addSpacing(20)
        
        self.convert_btn = self.create_primary_button("开始转换", self.start_conversion)
        self.convert_btn.setEnabled(False)
        controls_layout.addWidget(self.convert_btn)
        
        layout.addWidget(controls_frame)
        
        # Progress
        self.convert_progress = self.create_progress_bar()
        layout.addWidget(self.convert_progress)
        
        self.convert_status = QLabel("")
        self.convert_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.convert_status)
        
        layout.addStretch()
        
        self.reset_list(self.convert_file_list, "👇 拖拽视频文件到此处")

    def start_conversion(self):
        if self.convert_file_list.count() == 0 or not self.convert_file_list.item(0).flags() & Qt.ItemIsEnabled:
            return
        
        file_path = self.convert_file_list.item(0).data(Qt.UserRole)
        if not file_path:
             file_path = self.convert_file_list.item(0).text()
             
        fmt = self.format_combo.currentText()
        
        self.convert_btn.setEnabled(False)
        self.convert_progress.setVisible(True)
        self.convert_progress.setValue(0)
        self.convert_status.setText("正在转换中...")
        
        self.main_window.log_to_console(f"开始转换视频: {os.path.basename(file_path)} -> {fmt}", "info")
        
        self.worker = GenericWorker(self.processor.convert_video, file_path, fmt)
        self.worker.progress_signal.connect(self.convert_progress.setValue)
        self.worker.finished_signal.connect(self.on_convert_finished)
        self.worker.start()
        
    def on_convert_finished(self, success, msg):
        self.convert_btn.setEnabled(True)
        if success:
            self.convert_status.setText(f"✅ 转换成功: {os.path.basename(msg)}")
            self.convert_progress.setValue(100)
            self.main_window.log_to_console(f"转换成功: {msg}", "success")
        else:
            self.convert_status.setText(f"❌ 失败: {msg}")
            self.main_window.log_to_console(f"转换失败: {msg}", "error")
