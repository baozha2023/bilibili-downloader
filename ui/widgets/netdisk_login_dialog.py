from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox, QLabel
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtCore import QUrl, pyqtSignal, QTimer, Qt
from PyQt5.QtNetwork import QNetworkCookie

class NetdiskLoginDialog(QDialog):
    """
    通用网盘登录对话框 (Webview)
    """
    login_success = pyqtSignal(dict) # returns cookies dict

    def __init__(self, name, login_url, success_url_pattern, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"登录 {name} (请在页面中扫码或账号登录)")
        self.resize(1100, 750)
        self.name = name
        self.success_url_pattern = success_url_pattern
        self.extracted_cookies = {}
        self.is_finished = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Hint
        self.hint_label = QLabel("正在加载登录页面...")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("background-color: #fff3cd; color: #856404; padding: 10px;")
        layout.addWidget(self.hint_label)
        
        # Webview
        self.webview = QWebEngineView()
        self.profile = QWebEngineProfile("netdisk_profile", self.webview) # Use a specific profile
        # self.profile.cookieStore().deleteAllCookies() # Clear cookies to force login and capture
        self.profile.cookieStore().cookieAdded.connect(self.on_cookie_added)
        
        self.page = QWebEnginePage(self.profile, self.webview)
        self.webview.setPage(self.page)
        
        layout.addWidget(self.webview)
        
        self.webview.load(QUrl(login_url))
        self.webview.urlChanged.connect(self.on_url_changed)
        self.webview.loadFinished.connect(self.on_load_finished)

    def on_load_finished(self, ok):
        if ok:
            self.hint_label.setText(f"请登录 {self.name}，登录成功后窗口将自动关闭")
            self.hint_label.setStyleSheet("background-color: #d4edda; color: #155724; padding: 10px;")
        else:
            self.hint_label.setText("页面加载失败，请检查网络")
            self.hint_label.setStyleSheet("background-color: #f8d7da; color: #721c24; padding: 10px;")

    def on_cookie_added(self, cookie):
        name = cookie.name().data().decode('utf-8')
        value = cookie.value().data().decode('utf-8')
        self.extracted_cookies[name] = value

    def on_url_changed(self, url):
        url_str = url.toString()
        # print(f"URL: {url_str}")
        
        if self.success_url_pattern in url_str and not self.is_finished:
            self.hint_label.setText("检测到登录成功，正在获取凭证...")
            # Wait a bit for all cookies (e.g. STOKEN) to settle
            QTimer.singleShot(2000, self.finish_login)

    def finish_login(self):
        if self.is_finished: return
        self.is_finished = True
        
        if self.extracted_cookies:
            self.login_success.emit(self.extracted_cookies)
            self.accept()
        else:
            # Retry?
            self.is_finished = False
