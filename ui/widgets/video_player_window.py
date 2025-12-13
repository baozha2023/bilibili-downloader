from PyQt5.QtWidgets import QMainWindow, QDesktopWidget, QLabel
from PyQt5.QtCore import QUrl

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False

class VideoPlayerWindow(QMainWindow):
    def __init__(self, bvid, title=""):
        super().__init__()
        self.bvid = bvid
        self.video_title = title
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"正在播放: {self.video_title} - {self.bvid}")
        self.resize(1280, 720)
        self.center()

        if WEB_ENGINE_AVAILABLE:
            # Web Engine View
            self.browser = QWebEngineView()
            
            # 设置User-Agent以避免被识别为不支持HTML5的旧浏览器
            # 获取全局Profile
            from PyQt5.QtWebEngineWidgets import QWebEngineProfile
            
            # 使用常见的现代浏览器UA
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            
            # 如果可能，创建一个独立的Profile来设置UA (避免影响全局，虽然这里只有一个View)
            # 或者直接在默认Profile上设置
            QWebEngineProfile.defaultProfile().setHttpUserAgent(ua)
            
            # 使用嵌入式播放器
            url = f"https://player.bilibili.com/player.html?bvid={self.bvid}&high_quality=1&autoplay=1"
            self.browser.setUrl(QUrl(url))
            self.setCentralWidget(self.browser)
        else:
            # Fallback when module is missing
            msg = QLabel("无法加载播放器组件\n\n请安装 PyQtWebEngine:\npip install PyQtWebEngine")
            msg.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
            msg.setAlignment(QUrl("").host()) # Dummy usage to import Alignment flags? No.
            # Use int for alignment if Qt.AlignCenter is not imported here, 
            # or better, just style it.
            from PyQt5.QtCore import Qt
            msg.setAlignment(Qt.AlignCenter)
            self.setCentralWidget(msg)
        
        # Style
        self.setStyleSheet("background-color: black;")

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def closeEvent(self, event):
        if WEB_ENGINE_AVAILABLE and hasattr(self, 'browser'):
            self.browser.setUrl(QUrl("about:blank")) # Stop playback
        super().closeEvent(event)
