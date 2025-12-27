from PyQt5.QtWidgets import QMainWindow, QDesktopWidget, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import QUrl, Qt, QTimer
from PyQt5.QtGui import QIcon
from ui.message_box import BilibiliMessageBox

import subprocess
import sys
import os
import signal
import json

class VideoPlayerWindow(QMainWindow):
    def __init__(self, bvid, title="", cookies=None):
        super().__init__()
        self.bvid = bvid
        self.video_title = title
        self.cookies = cookies or {}
        self.player_process = None
        self.init_ui()
        self.start_player()
        
        # Monitor process
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.check_process_status)
        self.monitor_timer.start(1000) # Check every 1s

    def init_ui(self):
        self.setWindowTitle(f"播放控制器: {self.video_title}")
        self.resize(400, 200)
        self.center()
        
        # 设置图标
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "resource/icon.ico")
        if os.path.exists(icon_path):

            self.setWindowIcon(QIcon(icon_path))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)

        msg = QLabel("正在通过外部播放器播放视频...\n\n(使用的是 Edge WebView2 / HTML5)")
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("font-size: 16px; color: #333; margin-bottom: 20px;")
        layout.addWidget(msg)
        
        close_btn = QPushButton("关闭播放器")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #fb7299;
                color: white;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def start_player(self):
        try:
            # Construct URL
            # Use full video page for better compatibility and quality selection
            url = f"https://www.bilibili.com/video/{self.bvid}"
            
            # Determine command based on environment
            if getattr(sys, 'frozen', False):
                # Packaged environment (PyInstaller)
                # Call the executable itself with player mode arguments
                cmd = [
                    sys.executable, 
                    "--player-mode",
                    "--player-url", url,
                    "--player-title", f"{self.video_title} - {self.bvid}"
                ]
                if self.cookies:
                    cmd.extend(["--player-cookies", json.dumps(self.cookies)])
            else:
                # Development environment
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                loader_path = os.path.join(base_path, 'core', 'player_loader.py')
                
                cmd = [
                    sys.executable, 
                    loader_path, 
                    "--url", url, 
                    "--title", f"{self.video_title} - {self.bvid}"
                ]
                if self.cookies:
                    cmd.extend(["--cookies", json.dumps(self.cookies)])
            
            # Launch
            # CREATE_NO_WINDOW to hide console on Windows
            creationflags = 0
            if sys.platform == 'win32':
                creationflags = 0x08000000 # CREATE_NO_WINDOW
                
            self.player_process = subprocess.Popen(cmd, creationflags=creationflags)
            
        except Exception as e:
            print(f"Error starting player: {e}")

            BilibiliMessageBox.error(self, "播放错误", f"无法启动播放器: {e}")

    def check_process_status(self):
        if self.player_process:
            return_code = self.player_process.poll()
            if return_code is not None:
                # Process ended
                self.monitor_timer.stop()
                if return_code != 0:
                    BilibiliMessageBox.error(self, "播放器错误", f"播放器意外退出 (代码: {return_code})。\n可能原因：未安装 WebView2 运行时或缺少依赖。")
                self.player_process = None
                self.close()

    def closeEvent(self, event):
        self.monitor_timer.stop()
        if self.player_process:
            try:
                self.player_process.terminate()
                self.player_process = None
            except:
                pass
        super().closeEvent(event)
