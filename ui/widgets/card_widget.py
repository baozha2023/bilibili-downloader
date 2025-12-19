from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QPropertyAnimation, QPoint
from PyQt5.QtGui import QColor

class CardWidget(QFrame):
    """卡片式容器组件"""
    def __init__(self, title=None, parent=None):
        super().__init__(parent)
        self.setObjectName("CardWidget")
        self.setStyleSheet("""
            #CardWidget {
                background-color: transparent;
                border: none;
            }
        """)
        
        # 主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(20)
        
        # 标题
        if title:
            self.title_label = QLabel(title)
            self.title_label.setStyleSheet("""
                font-size: 24px;
                font-weight: bold;
                color: #333;
                padding-bottom: 10px;
                border-bottom: 1px solid #ddd;
                margin-bottom: 15px;
            """)
            self.layout.addWidget(self.title_label)
            
    def add_widget(self, widget):
        self.layout.addWidget(widget)
        
    def add_layout(self, layout):
        self.layout.addLayout(layout)
        
    def add_stretch(self):
        self.layout.addStretch()
