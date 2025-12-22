from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                             QFrame, QStackedWidget, QGraphicsOpacityEffect)
from PyQt5.QtCore import QEasingCurve, QPropertyAnimation

from .pages.convert_page import ConvertPage
from .pages.cut_page import CutPage
from .pages.merge_page import MergePage
from .pages.compress_page import CompressPage
from .pages.frame_page import FramePage
from .pages.reverse_page import ReversePage

class VideoEditTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.processor = main_window.crawler.processor
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left Sidebar
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("""
            QFrame {
                background-color: #f1f2f3;
                border-right: 1px solid #e7e7e7;
            }
            QPushButton {
                text-align: left;
                padding: 15px 20px;
                border: none;
                font-size: 20px;
                color: #61666d;
                background-color: transparent;
                border-radius: 6px;
                margin: 5px 10px;
            }
            QPushButton:hover {
                background-color: #e3e5e7;
                color: #18191c;
            }
            QPushButton:checked {
                background-color: #ffffff;
                color: #fb7299;
                font-weight: bold;
            }
        """)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 0)
        sidebar_layout.setSpacing(5)
        
        self.nav_btns = []
        nav_items = [
            ("格式转换", "convert"), 
            ("视频剪辑", "cut"), 
            ("视频合并", "merge"), 
            ("视频压缩", "compress"), 
            ("视频反转", "reverse"),
            ("逐帧获取", "frame")
        ]
        
        for text, tag in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=tag: self.switch_page(t))
            sidebar_layout.addWidget(btn)
            self.nav_btns.append((tag, btn))
            
        sidebar_layout.addStretch()
        main_layout.addWidget(self.sidebar)
        
        # Right Content
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: #ffffff;")
        main_layout.addWidget(self.content_stack)
        
        # Initialize pages
        self.pages = {}
        self.pages['convert'] = ConvertPage(self.main_window, self.processor)
        self.pages['cut'] = CutPage(self.main_window, self.processor)
        self.pages['merge'] = MergePage(self.main_window, self.processor)
        self.pages['compress'] = CompressPage(self.main_window, self.processor)
        self.pages['reverse'] = ReversePage(self.main_window, self.processor)
        self.pages['frame'] = FramePage(self.main_window, self.processor)
        
        for tag, page in self.pages.items():
            self.content_stack.addWidget(page)
            
        # Select first page
        self.nav_btns[0][1].click()

    def switch_page(self, tag):
        # Update buttons style
        for t, btn in self.nav_btns:
            btn.setChecked(t == tag)
            
        # Switch stack
        if tag in self.pages:
            new_widget = self.pages[tag]
            current_widget = self.content_stack.currentWidget()
            
            if current_widget == new_widget:
                return
                
            self.content_stack.setCurrentWidget(new_widget)
            
            # Animation
            self.fade_in(new_widget)

    def fade_in(self, widget):
        # Reset opacity
        opacity = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity)
        
        # Opacity Animation
        anim = QPropertyAnimation(opacity, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.OutQuad)
        
        # Cleanup effect after animation
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        
        # Position Animation (Slide up slightly)
        pos_anim = QPropertyAnimation(widget, b"pos")
        pos_anim.setDuration(300)
        start_pos = widget.pos()
        # Create a temporary offset
        widget.move(start_pos.x(), start_pos.y() + 20)
        pos_anim.setStartValue(widget.pos())
        pos_anim.setEndValue(start_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutQuad)
        
        anim.start()
        # Keep reference
        widget.anim = anim
