import os
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from ui.widgets.edit_widgets import DragDropListWidget
from .base_page import BaseEditPage
from ..workers import GenericWorker

class ReversePage(BaseEditPage):
    def __init__(self, main_window, processor):
        super().__init__(main_window, processor)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        self.setup_header(layout, "视频反转", "将视频画面和音频进行倒放处理")
        
        self.reverse_file_list = DragDropListWidget()
        self.reverse_file_list.file_dropped.connect(lambda p: self.set_single_file(p, self.reverse_file_list, self.reverse_btn))
        self.reverse_file_list.clicked.connect(lambda: self.select_single_file(self.reverse_file_list, self.reverse_btn))
        self.reverse_file_list.setMaximumHeight(150)
        layout.addWidget(self.reverse_file_list)
        
        # Controls
        controls_frame = self.create_control_frame()
        controls_layout = QHBoxLayout(controls_frame)
        
        controls_layout.addStretch()
        
        self.reverse_btn = self.create_primary_button("开始反转", self.start_reverse)
        self.reverse_btn.setEnabled(False)
        controls_layout.addWidget(self.reverse_btn)
        
        layout.addWidget(controls_frame)
        
        self.reverse_progress = self.create_progress_bar()
        layout.addWidget(self.reverse_progress)
        
        self.reverse_status = QLabel("")
        self.reverse_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.reverse_status)
        
        layout.addStretch()
        self.reset_list(self.reverse_file_list, "👇 拖拽视频文件到此处")

    def start_reverse(self):
        if self.reverse_file_list.count() == 0 or not self.reverse_file_list.item(0).flags() & Qt.ItemIsEnabled:
            return
            
        file_path = self.reverse_file_list.item(0).data(Qt.UserRole)
        if not file_path:
             file_path = self.reverse_file_list.item(0).text()
             
        self.reverse_btn.setEnabled(False)
        self.reverse_progress.setVisible(True)
        self.reverse_progress.setValue(0)
        self.reverse_status.setText("正在反转中 (这可能需要一些时间)...")
        
        self.main_window.log_to_console(f"开始反转视频: {os.path.basename(file_path)}", "info")
        
        self.worker = GenericWorker(self.processor.reverse_video, file_path)
        self.worker.progress_signal.connect(self.reverse_progress.setValue)
        self.worker.finished_signal.connect(self.on_reverse_finished)
        self.worker.start()
        
    def on_reverse_finished(self, success, msg):
        self.reverse_btn.setEnabled(True)
        if success:
            self.reverse_status.setText(f"✅ 反转成功: {os.path.basename(msg)}")
            self.reverse_progress.setValue(100)
            self.main_window.log_to_console(f"反转成功: {msg}", "success")
        else:
            self.reverse_status.setText(f"❌ 失败: {msg}")
            self.main_window.log_to_console(f"反转失败: {msg}", "error")
