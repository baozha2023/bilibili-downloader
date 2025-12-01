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
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
            #CardWidget:hover {
                border: 1px solid #d0d0d0;
            }
        """)
        
        # 添加阴影效果 (已移除)
        # shadow = QGraphicsDropShadowEffect(self)
        # shadow.setBlurRadius(15)
        # shadow.setColor(QColor(0, 0, 0, 20))
        # shadow.setOffset(0, 2)
        # self.setGraphicsEffect(shadow)
        
        # 主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(20)
        
        # 标题
        if title:
            self.title_label = QLabel(title)
            self.title_label.setStyleSheet("""
                font-size: 26px;
                font-weight: bold;
                color: #333;
                padding-bottom: 10px;
                border-bottom: 2px solid #f0f0f0;
                margin-bottom: 10px;
            """)
            self.layout.addWidget(self.title_label)
            
    def add_widget(self, widget):
        self.layout.addWidget(widget)
        
    def add_layout(self, layout):
        self.layout.addLayout(layout)
        
    def add_stretch(self):
        self.layout.addStretch()
