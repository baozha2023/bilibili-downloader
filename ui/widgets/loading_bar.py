from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtCore import Qt

class LoadingBar(QProgressBar):
    """
    B站风格的加载进度条
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setRange(0, 0)  # Indeterminate mode
        self.setFixedHeight(4)
        self.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #f0f0f0;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #fb7299;
                border-radius: 2px;
            }
        """)
        self.hide()
    
    def start(self):
        self.show()
        
    def stop(self):
        self.hide()
