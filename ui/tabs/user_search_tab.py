import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QListWidget, QListWidgetItem, QGroupBox, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QPixmap
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from ui.widgets.card_widget import CardWidget
from ui.widgets.loading_bar import LoadingBar
from ui.message_box import BilibiliMessageBox

logger = logging.getLogger('bilibili_desktop')

class UserSearchWorker(QThread):
    finished_signal = pyqtSignal(list, str) # results, error

    def __init__(self, crawler, keyword):
        super().__init__()
        self.crawler = crawler
        self.keyword = keyword

    def run(self):
        try:
            # Check if keyword is digit -> maybe MID?
            results = []
            if self.keyword.isdigit():
                # Try fetch as MID first
                info = self.crawler.api.get_user_info(self.keyword)
                if info and info.get('code') == 0:
                    data = info.get('data', {})
                    # Adapt to search result format
                    user_item = {
                        'mid': data.get('mid'),
                        'uname': data.get('name'),
                        'usign': data.get('sign'),
                        'upic': data.get('face'),
                        'level': data.get('level'),
                        'fans': -1, # Info API might not return fans count directly here without extra calls
                        'videos': -1
                    }
                    results.append(user_item)
            
            # Search by name
            search_results = self.crawler.api.search_users(self.keyword)
            if search_results:
                # Avoid duplicate if MID found
                existing_mids = [str(r['mid']) for r in results]
                for user in search_results:
                    if str(user.get('mid')) not in existing_mids:
                        results.append(user)
                        
            self.finished_signal.emit(results, "")
        except Exception as e:
            self.finished_signal.emit([], str(e))

class UserSearchTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.crawler = main_window.crawler
        self.avatar_cache = {}
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Input
        input_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入用户ID或昵称")
        self.search_input.setStyleSheet("padding: 10px; font-size: 16px; border-radius: 5px; border: 1px solid #ddd;")
        self.search_input.returnPressed.connect(self.start_search)
        input_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("搜索")
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setStyleSheet("""
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
        self.search_btn.clicked.connect(self.start_search)
        input_layout.addWidget(self.search_btn)
        
        layout.addLayout(input_layout)
        
        self.loading_bar = LoadingBar(self)
        layout.addWidget(self.loading_bar)
        
        # Results
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
            }
            QListWidget::item {
                background-color: white;
                border-radius: 8px;
                margin-bottom: 10px;
                border: 1px solid #eee;
            }
            QListWidget::item:hover {
                border-color: #fb7299;
            }
        """)
        layout.addWidget(self.results_list)
        
    def start_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            BilibiliMessageBox.warning(self, "提示", "请输入搜索关键词")
            return
            
        self.search_btn.setEnabled(False)
        self.loading_bar.start()
        self.results_list.clear()
        
        self.worker = UserSearchWorker(self.crawler, keyword)
        self.worker.finished_signal.connect(self.on_search_finished)
        self.worker.start()
        
    def on_search_finished(self, results, error):
        self.search_btn.setEnabled(True)
        self.loading_bar.stop()
        
        if error:
            BilibiliMessageBox.error(self, "错误", f"搜索失败: {error}")
            return
            
        if not results:
            BilibiliMessageBox.information(self, "提示", "未找到相关用户")
            return
            
        for user in results:
            self.add_user_item(user)
            
    def add_user_item(self, user):
        item = QListWidgetItem(self.results_list)
        item.setSizeHint(user_widget_size_hint()) # We need a size hint
        
        widget = UserCardWidget(user, self)
        item.setSizeHint(widget.sizeHint())
        self.results_list.addItem(item)
        self.results_list.setItemWidget(item, widget)

def user_widget_size_hint():
    from PyQt5.QtCore import QSize
    return QSize(0, 100)

class UserCardWidget(QFrame):
    def __init__(self, user, parent_tab):
        super().__init__()
        self.user = user
        self.parent_tab = parent_tab
        self.init_ui()
        self.load_avatar()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Avatar
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(60, 60)
        self.avatar_label.setStyleSheet("background-color: #eee; border-radius: 30px;")
        layout.addWidget(self.avatar_label)
        
        # Info
        info_layout = QVBoxLayout()
        
        name_layout = QHBoxLayout()
        name = QLabel(self.user.get('uname', '未知用户'))
        name.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        name_layout.addWidget(name)
        
        level = self.user.get('level', 0)
        level_label = QLabel(f"Lv{level}")
        level_label.setStyleSheet("""
            background-color: #f0f0f0; 
            color: #fb7299; 
            padding: 2px 5px; 
            border-radius: 3px; 
            font-size: 12px; 
            font-weight: bold;
        """)
        name_layout.addWidget(level_label)
        name_layout.addStretch()
        
        info_layout.addLayout(name_layout)
        
        sign = self.user.get('usign', '')
        sign_label = QLabel(sign if sign else "这个人很懒，什么都没有写")
        sign_label.setStyleSheet("color: #999; font-size: 14px;")
        sign_label.setWordWrap(True)
        info_layout.addWidget(sign_label)
        
        # Stats
        stats_text = []
        fans = self.user.get('fans')
        if fans and fans != -1:
            stats_text.append(f"粉丝: {fans}")
        videos = self.user.get('videos')
        if videos and videos != -1:
            stats_text.append(f"视频: {videos}")
        
        if stats_text:
            stats_label = QLabel("  ".join(stats_text))
            stats_label.setStyleSheet("color: #666; font-size: 13px; margin-top: 5px;")
            info_layout.addWidget(stats_label)
            
        layout.addLayout(info_layout)
        
        # Action
        mid = self.user.get('mid')
        mid_label = QLabel(f"UID: {mid}")
        mid_label.setStyleSheet("color: #ccc; font-size: 12px;")
        layout.addWidget(mid_label)
        
    def load_avatar(self):
        url = self.user.get('upic')
        if not url: return
        
        if url in self.parent_tab.avatar_cache:
            self.set_avatar(self.parent_tab.avatar_cache[url])
            return
            
        if not hasattr(self, 'network_manager'):
            self.network_manager = QNetworkAccessManager(self)
            self.network_manager.finished.connect(self.on_avatar_downloaded)
            
        self.network_manager.get(QNetworkRequest(QUrl(url)))
        
    def on_avatar_downloaded(self, reply):
        url = reply.url().toString()
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            self.parent_tab.avatar_cache[url] = pixmap
            self.set_avatar(pixmap)
        reply.deleteLater()
        
    def set_avatar(self, pixmap):
        from PyQt5.QtGui import QPainter, QBrush
        
        scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        rounded_pixmap = QPixmap(60, 60)
        rounded_pixmap.fill(Qt.transparent)
        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(scaled_pixmap))
        painter.drawEllipse(0, 0, 60, 60)
        painter.end()
        self.avatar_label.setPixmap(rounded_pixmap)
