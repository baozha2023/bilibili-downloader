import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QComboBox, QFileDialog, QProgressBar, QMessageBox, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from ui.message_box import BilibiliMessageBox

class ConvertWorker(QThread):
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, processor, input_path, output_format):
        super().__init__()
        self.processor = processor
        self.input_path = input_path
        self.output_format = output_format
        
    def run(self):
        def callback(current, total):
            self.progress_signal.emit(current, total)
            
        success, msg = self.processor.convert_video(self.input_path, self.output_format, callback)
        self.finished_signal.emit(success, msg)

class DragDropListWidget(QListWidget):
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #ccc;
                border-radius: 10px;
                font-size: 16px;
                color: #666;
                background-color: #f9f9f9;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
        """)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            for url in event.mimeData().urls():
                file_path = str(url.toLocalFile())
                if os.path.isfile(file_path):
                    self.file_dropped.emit(file_path)
        else:
            event.ignore()

class ConverterTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.processor = main_window.crawler.processor
        self.current_file = None
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title_label = QLabel("视频格式转换")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        layout.addWidget(title_label)
        
        # 拖拽区域 / 文件列表
        self.file_list = DragDropListWidget()
        self.file_list.file_dropped.connect(self.on_file_dropped)
        self.file_list.setSelectionMode(QListWidget.SingleSelection)
        self.file_list.clicked.connect(self.on_file_selected)
        
        # 添加提示项 - 移动到最后初始化，因为依赖 convert_btn
        # self.add_placeholder_item()
        
        layout.addWidget(self.file_list)
        
        # 操作区域
        controls_layout = QHBoxLayout()
        
        # 选择文件按钮
        select_btn = QPushButton("选择文件")
        select_btn.setCursor(Qt.PointingHandCursor)
        select_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                padding: 8px 20px;
                background-color: #f6f7f8;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        select_btn.clicked.connect(self.select_file)
        controls_layout.addWidget(select_btn)
        
        controls_layout.addSpacing(20)
        
        # 格式选择
        controls_layout.addWidget(QLabel("目标格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mp3", "mkv", "avi", "mov", "gif"])
        self.format_combo.setCurrentText("mp4")
        self.format_combo.setFixedWidth(100)
        self.format_combo.setStyleSheet("font-size: 16px; padding: 5px;")
        controls_layout.addWidget(self.format_combo)
        
        controls_layout.addStretch()
        
        # 转换按钮
        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.setCursor(Qt.PointingHandCursor)
        self.convert_btn.setEnabled(False)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                padding: 10px 30px;
                background-color: #fb7299;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.convert_btn.clicked.connect(self.start_conversion)
        controls_layout.addWidget(self.convert_btn)
        
        layout.addLayout(controls_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #fb7299;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 14px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # 添加提示项
        self.add_placeholder_item()

    def add_placeholder_item(self):
        self.file_list.clear()
        item = QListWidgetItem("拖拽视频文件到此处，或点击“选择文件”按钮")
        item.setTextAlignment(Qt.AlignCenter)
        item.setFlags(Qt.NoItemFlags) # 不可选中
        self.file_list.addItem(item)
        self.current_file = None
        self.convert_btn.setEnabled(False)

    def on_file_dropped(self, file_path):
        self.set_current_file(file_path)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", self.main_window.crawler.data_dir, 
            "Video Files (*.mp4 *.mkv *.avi *.mov *.flv);;All Files (*.*)"
        )
        if file_path:
            self.set_current_file(file_path)

    def set_current_file(self, file_path):
        self.current_file = file_path
        self.file_list.clear()
        
        item = QListWidgetItem(f"已选择: {os.path.basename(file_path)}")
        item.setToolTip(file_path)
        item.setTextAlignment(Qt.AlignLeft)
        self.file_list.addItem(item)
        
        self.convert_btn.setEnabled(True)
        self.status_label.setText("准备就绪")
        self.progress_bar.setVisible(False)

    def on_file_selected(self):
        # 处理点击列表项，实际上我们只允许一个文件，所以不需要复杂逻辑
        pass

    def start_conversion(self):
        if not self.current_file:
            return
            
        output_format = self.format_combo.currentText()
        
        self.convert_btn.setEnabled(False)
        self.file_list.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText(f"正在转换为 {output_format} ...")
        
        self.worker = ConvertWorker(self.processor, self.current_file, output_format)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_conversion_finished)
        self.worker.start()

    def update_progress(self, current, total):
        self.progress_bar.setValue(current)

    def on_conversion_finished(self, success, msg):
        self.convert_btn.setEnabled(True)
        self.file_list.setEnabled(True)
        
        if success:
            self.status_label.setText(f"转换成功！输出文件: {os.path.basename(msg)}")
            self.progress_bar.setValue(100)
            BilibiliMessageBox.info(self, "转换成功", f"文件已保存至:\n{msg}")
            
            # 询问是否打开文件夹
            reply = QMessageBox.question(self, "打开文件夹", "是否打开输出文件夹？", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    os.startfile(os.path.dirname(msg))
                except:
                    pass
        else:
            self.status_label.setText(f"转换失败: {msg}")
            BilibiliMessageBox.warning(self, "转换失败", msg)
