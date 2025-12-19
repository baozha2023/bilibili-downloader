import os
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QSpinBox
from PyQt5.QtCore import Qt
from ui.widgets.custom_combobox import NoScrollComboBox
from ui.widgets.edit_widgets import DragDropListWidget
from .base_page import BaseEditPage
from ..workers import GenericWorker

class CompressPage(BaseEditPage):
    def __init__(self, main_window, processor):
        super().__init__(main_window, processor)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        self.setup_header(layout, "视频压缩", "调整分辨率和画质以减小体积")
        
        self.compress_file_list = DragDropListWidget()
        self.compress_file_list.file_dropped.connect(lambda p: self.set_single_file(p, self.compress_file_list, self.compress_btn))
        self.compress_file_list.clicked.connect(lambda: self.select_single_file(self.compress_file_list, self.compress_btn))
        # Reduce size of file list area
        self.compress_file_list.setMaximumHeight(150)
        layout.addWidget(self.compress_file_list)
        
        # Settings
        settings_group = QGroupBox("压缩设置")
        settings_group.setStyleSheet("QGroupBox { font-size: 20px; color: #333; border: 1px solid #ddd; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(15)
        
        # Res & CRF
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("目标分辨率:"))
        self.res_combo = NoScrollComboBox()
        self.res_combo.addItems(["1920x1080", "1280x720", "854x480", "640x360"])
        self.style_combo(self.res_combo)
        params_layout.addWidget(self.res_combo)
        
        params_layout.addWidget(QLabel("画质 (CRF):"))
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(18, 51)
        self.crf_spin.setValue(23)
        self.crf_spin.setToolTip("数值越小画质越好，体积越大。推荐23。")
        self.style_spinbox(self.crf_spin)
        params_layout.addWidget(self.crf_spin)
        settings_layout.addLayout(params_layout)
        
        layout.addWidget(settings_group, 1) # Add stretch
        
        # Controls
        controls_frame = self.create_control_frame()
        controls_layout = QHBoxLayout(controls_frame)
        
        controls_layout.addStretch()
        
        self.compress_btn = self.create_primary_button("开始压缩", self.start_compress)
        self.compress_btn.setEnabled(False)
        controls_layout.addWidget(self.compress_btn)
        
        layout.addWidget(controls_frame)
        
        self.compress_progress = self.create_progress_bar()
        layout.addWidget(self.compress_progress)
        
        self.compress_status = QLabel("")
        self.compress_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.compress_status)
        
        layout.addStretch()
        self.reset_list(self.compress_file_list, "👇 拖拽视频文件到此处")

    def start_compress(self):
        if self.compress_file_list.count() == 0 or not self.compress_file_list.item(0).flags() & Qt.ItemIsEnabled:
            return
            
        file_path = self.compress_file_list.item(0).data(Qt.UserRole)
        if not file_path:
             file_path = self.compress_file_list.item(0).text()
             
        res = self.res_combo.currentText()
        crf = self.crf_spin.value()
        
        self.compress_btn.setEnabled(False)
        self.compress_progress.setVisible(True)
        self.compress_progress.setValue(0)
        self.compress_status.setText("正在压缩中...")
        
        self.main_window.log_to_console(f"开始压缩视频: {os.path.basename(file_path)} (Res={res}, CRF={crf})", "info")
        
        # Removed fade_in/fade_out arguments
        self.worker = GenericWorker(self.processor.compress_video, file_path, res, crf)
        self.worker.progress_signal.connect(self.compress_progress.setValue)
        self.worker.finished_signal.connect(self.on_compress_finished)
        self.worker.start()
        
    def on_compress_finished(self, success, msg):
        self.compress_btn.setEnabled(True)
        if success:
            self.compress_status.setText(f"✅ 压缩成功: {os.path.basename(msg)}")
            self.compress_progress.setValue(100)
            self.main_window.log_to_console(f"压缩成功: {msg}", "success")
        else:
            self.compress_status.setText(f"❌ 失败: {msg}")
            self.main_window.log_to_console(f"压缩失败: {msg}", "error")
