from PyQt5.QtWidgets import QSplashScreen, QProgressBar, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QColor, QFont
import os

class SplashScreen(QSplashScreen):
    def __init__(self, pixmap_path, version):
        # 如果图片存在则使用图片，否则使用白色背景
        if os.path.exists(pixmap_path):
            pixmap = QPixmap(pixmap_path)
        else:
            pixmap = QPixmap(500, 300)
            pixmap.fill(Qt.white)
            
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setEnabled(False)
        
        # 布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.addStretch()
        
        # 版本号
        self.version_label = QLabel(f"Version: {version}")
        self.version_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; background-color: rgba(0,0,0,0.5); padding: 4px; border-radius: 4px;")
        self.version_label.setAlignment(Qt.AlignRight)
        self.layout.addWidget(self.version_label)
        
        # 进度条
        self.progress = QProgressBar(self)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #e0e0e0;
                border-radius: 4px;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #fb7299;
                border-radius: 4px;
            }
        """)
        self.progress.setTextVisible(False)
        self.layout.addWidget(self.progress)
        
        # 加载文本
        self.status_label = QLabel("正在初始化...")
        self.status_label.setStyleSheet("color: white; font-size: 12px; background-color: rgba(0,0,0,0.5); padding: 2px; border-radius: 2px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_label)

    def set_progress(self, value, text=None):
        self.progress.setValue(value)
        if text:
            self.status_label.setText(text)
        QTimer.singleShot(0, lambda: self.repaint())
