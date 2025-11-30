import logging
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QBrush

class BilibiliMessageBox(QDialog):
    """Custom Message Box for Bilibili Style"""
    
    Info = 0
    Warning = 1
    Error = 2
    Question = 3
    
    def __init__(self, parent=None, title="", message="", type=Info):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Main Frame
        self.frame = QFrame()
        self.frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e7e7e7;
            }
        """)
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(30, 30, 30, 30)
        self.frame_layout.setSpacing(25)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        title_color = "#333333"
        if type == self.Warning:
            title_color = "#fa8c16"
        elif type == self.Error:
            title_color = "#f5222d"
        
        self.title_label.setStyleSheet(f"""
            font-size: 26px; 
            font-weight: bold; 
            color: {title_color}; 
            margin-bottom: 10px;
        """)
        self.frame_layout.addWidget(self.title_label)
        
        # Message
        self.msg_label = QLabel(message)
        self.msg_label.setAlignment(Qt.AlignCenter)
        self.msg_label.setWordWrap(True)
        self.msg_label.setStyleSheet("font-size: 22px; color: #666666; line-height: 1.5;")
        self.frame_layout.addWidget(self.msg_label)
        
        # Buttons
        self.btn_layout = QVBoxLayout()
        self.btn_layout.setSpacing(15)
        
        if type == self.Question:
            self.ok_btn = QPushButton("确定")
            self.ok_btn.clicked.connect(self.accept)
            self.style_primary_button(self.ok_btn)
            self.btn_layout.addWidget(self.ok_btn)
            
            self.cancel_btn = QPushButton("取消")
            self.cancel_btn.clicked.connect(self.reject)
            self.style_secondary_button(self.cancel_btn)
            self.btn_layout.addWidget(self.cancel_btn)
        else:
            self.ok_btn = QPushButton("我知道了")
            self.ok_btn.clicked.connect(self.accept)
            self.style_primary_button(self.ok_btn)
            self.btn_layout.addWidget(self.ok_btn)
            
        self.frame_layout.addLayout(self.btn_layout)
        self.layout.addWidget(self.frame)
        
        # Shadow effect (optional, simple implementation)
        # self.setGraphicsEffect(...) 
        
        self.resize(400, 300)
        
    def style_primary_button(self, btn):
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(50)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #fb7299;
                color: white;
                border-radius: 25px;
                font-size: 22px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
            QPushButton:pressed {
                background-color: #e45c84;
            }
        """)

    def style_secondary_button(self, btn):
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(50)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #f6f7f8;
                color: #666666;
                border-radius: 25px;
                font-size: 22px;
                font-weight: bold;
                border: 1px solid #e7e7e7;
            }
            QPushButton:hover {
                background-color: #eeeeee;
            }
            QPushButton:pressed {
                background-color: #dddddd;
            }
        """)

    @staticmethod
    def warning(parent, title, message):
        dialog = BilibiliMessageBox(parent, title, message, BilibiliMessageBox.Warning)
        return dialog.exec_()

    @staticmethod
    def information(parent, title, message):
        dialog = BilibiliMessageBox(parent, title, message, BilibiliMessageBox.Info)
        return dialog.exec_()
        
    @staticmethod
    def question(parent, title, message):
        dialog = BilibiliMessageBox(parent, title, message, BilibiliMessageBox.Question)
        return dialog.exec_()
