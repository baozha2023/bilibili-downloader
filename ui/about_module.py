import sys
import os
import re
import html
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QTextBrowser, QGroupBox)
from PyQt5.QtCore import Qt

class AboutDialog(QDialog):
    """
    作者声明对话框
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("作者声明 / Credits")
        self.setMinimumSize(800, 600)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # 1. Author Declaration (Credits)
        credits_group = QGroupBox("作者声明 / Credits")
        credits_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                color: #fb7299;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 2px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        credits_layout = QVBoxLayout(credits_group)
        credits_layout.setContentsMargins(15, 25, 15, 15)
        
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setStyleSheet("font-size: 16px; padding: 10px; font-family: Consolas, 'Microsoft YaHei'; border: none; background-color: #f9f9f9; border-radius: 4px;")
        self.load_credits()
        credits_layout.addWidget(self.text_browser)
        
        layout.addWidget(credits_group)
        
        # Close Button
        close_btn = QPushButton("关闭")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #fb7299;
                color: white;
                padding: 10px 10px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
            QPushButton:pressed {
                background-color: #e45c84;
            }
        """)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def load_credits(self):
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.dirname(__file__))
                
            credits_path = os.path.join(base_path, 'credits.txt')
            
            if os.path.exists(credits_path):
                with open(credits_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    content = html.escape(content)
                    html_content = content.replace('\n', '<br>')
                    url_pattern = re.compile(r'(https?://[^\s<]+)')
                    def replace_url(match):
                        url = match.group(1)
                        clean_url = url.rstrip(').,;]') 
                        return f'<a href="{clean_url}" style="color: #fb7299; text-decoration: none;">{clean_url}</a>'
                    html_content = url_pattern.sub(replace_url, html_content)
                    self.text_browser.setHtml(html_content)
            else:
                self.text_browser.setText(f"credits.txt 文件未找到。\n路径: {credits_path}")
        except Exception as e:
            self.text_browser.setText(f"读取 credits.txt 失败: {str(e)}")
