from PyQt5.QtWidgets import QMainWindow, QDesktopWidget, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import QUrl, Qt, QTimer
import subprocess
import sys
import os
import signal

class VideoPlayerWindow(QMainWindow):
    def __init__(self, bvid, title=""):
        super().__init__()
        self.bvid = bvid
        self.video_title = title
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

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)

        msg = QLabel("正在通过外部播放器播放视频...\n\n(使用的是 Edge WebView2 / HTML5)")
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("font-size: 16px; color: #333; margin-bottom: 20px;")
        layout.addWidget(msg)
        
        close_btn = QPushButton("关闭播放器")
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
            url = f"https://player.bilibili.com/player.html?bvid={self.bvid}&high_quality=1&autoplay=1"
            
            # Path to loader script
            # Handle frozen env (PyInstaller) if needed, but for now assuming source or standard structure
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            loader_path = os.path.join(base_path, 'core', 'player_loader.py')
            
            # Command
            cmd = [sys.executable, loader_path, "--url", url, "--title", f"{self.video_title} - {self.bvid}"]
            
            # Launch
            # CREATE_NO_WINDOW to hide console on Windows
            creationflags = 0
            if sys.platform == 'win32':
                creationflags = 0x08000000 # CREATE_NO_WINDOW
                
            self.player_process = subprocess.Popen(cmd, creationflags=creationflags)
            
        except Exception as e:
            print(f"Error starting player: {e}")
            from ui.message_box import BilibiliMessageBox
            BilibiliMessageBox.error(self, "播放错误", f"无法启动播放器: {e}")

    def check_process_status(self):
        if self.player_process:
            return_code = self.player_process.poll()
            if return_code is not None:
                # Process ended
                self.monitor_timer.stop()
                if return_code != 0:
                    from ui.message_box import BilibiliMessageBox
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
