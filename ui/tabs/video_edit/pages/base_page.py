import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QProgressBar, QListWidgetItem, QFrame, QFileDialog, QGroupBox, 
                             QComboBox, QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QSize
from ui.widgets.custom_combobox import NoScrollComboBox
from ui.widgets.edit_widgets import VideoFileWidget

class BaseEditPage(QWidget):
    def __init__(self, main_window, processor):
        super().__init__()
        self.main_window = main_window
        self.processor = processor
        self.worker = None

    def setup_header(self, layout, title, subtitle):
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #333;")
        layout.addWidget(title_label)
        
        sub_label = QLabel(subtitle)
        sub_label.setStyleSheet("font-size: 20px; color: #999;")
        layout.addWidget(sub_label)

    def create_control_frame(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #f6f7f8;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        return frame

    def create_button(self, text, callback):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                font-size: 20px;
                padding: 8px 20px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 6px;
                color: #333;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #ccc;
                color: #fb7299;
                color: #fb7299;
            }
        """)
        btn.clicked.connect(callback)
        return btn

    def create_primary_button(self, text, callback):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                font-size: 22px;
                font-weight: bold;
                padding: 10px 30px;
                background-color: #fb7299;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
            QPushButton:disabled {
                background-color: #e0e0e0;
                color: #999;
            }
            QPushButton:pressed {
                background-color: #e45c84;
            }
        """)
        btn.clicked.connect(callback)
        return btn

    def create_progress_bar(self):
        bar = QProgressBar()
        bar.setVisible(False)
        bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 8px;
                background-color: #e0e0e0;
                text-align: center;
                height: 25px;
                font-size: 18px;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #fb7299;
                border-radius: 8px;
            }
        """)
        return bar

    def style_combo(self, combo):
        combo.setStyleSheet("""
            QComboBox {
                font-size: 20px;
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #fb7299;
            }
        """)

    def style_spinbox(self, spin):
        spin.setStyleSheet("""
            QSpinBox, QDoubleSpinBox {
                font-size: 20px;
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
            }
            QSpinBox:hover, QDoubleSpinBox:hover {
                border-color: #fb7299;
            }
        """)

    def reset_list(self, list_widget, text):
        list_widget.clear()
        item = QListWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        item.setFlags(Qt.NoItemFlags)
        list_widget.addItem(item)
        
    def set_single_file(self, file_path, list_widget, btn):
        list_widget.clear()
        
        # Get video info
        duration = 0
        size = 0
        try:
            duration = self.processor.get_video_duration(file_path)
            size = os.path.getsize(file_path) / (1024 * 1024)
        except Exception as e:
            self.main_window.log_to_console(f"获取视频信息失败: {str(e)}", "warning")
        
        item = QListWidgetItem(list_widget)
        item.setSizeHint(QSize(0, 80)) 
        
        # Create custom widget
        widget = VideoFileWidget(file_path, duration, size)
        list_widget.setItemWidget(item, widget)
        
        # Store path in item data for easy access
        item.setData(Qt.UserRole, file_path)
        
        if btn:
            btn.setEnabled(True)
            
        return file_path
        
    def select_single_file(self, list_widget, btn, callback=None):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", self.main_window.crawler.data_dir, 
            "Video Files (*.mp4 *.mkv *.avi *.mov *.flv);;All Files (*.*)"
        )
        if file_path:
            self.set_single_file(file_path, list_widget, btn)
            if callback:
                callback(file_path)
