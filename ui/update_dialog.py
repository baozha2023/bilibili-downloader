from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

class UpdateDialog(QDialog):
    def __init__(self, version, updates, parent=None):
        super().__init__(parent)
        self.setWindowTitle("更新公告")
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)  # 无边框
        
        self.countdown = 5
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        
        self.init_ui(version, updates)
        self.timer.start(1000)
        
    def init_ui(self, version, updates):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部栏（倒计时和标题）
        top_layout = QHBoxLayout()
        
        title = QLabel(f"版本更新 {version}")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #fb7299;")
        top_layout.addWidget(title)
        
        top_layout.addStretch()
        
        self.timer_label = QLabel(f"{self.countdown}s 后自动关闭")
        self.timer_label.setStyleSheet("color: #999; font-size: 12px;")
        top_layout.addWidget(self.timer_label)
        
        layout.addLayout(top_layout)
        
        # 分隔线
        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #eee;")
        layout.addWidget(line)
        
        # 更新内容
        content = QLabel(updates)
        content.setWordWrap(True)
        content.setStyleSheet("font-size: 16px; line-height: 1.6; margin-top: 15px; color: #333;")
        content.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(content)
        
        layout.addStretch()
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = QPushButton("我知道了")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #fb7299;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        # 设置整体样式
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
        """)
        
    def update_timer(self):
        self.countdown -= 1
        self.timer_label.setText(f"{self.countdown}s 后自动关闭")
        if self.countdown <= 0:
            self.timer.stop()
            self.accept()
