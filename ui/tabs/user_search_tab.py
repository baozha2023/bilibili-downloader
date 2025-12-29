import logging
import binascii
import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QListWidget, QListWidgetItem, QGroupBox, QFrame,
                             QDialog, QScrollArea, QGridLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl, QSize
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from ui.widgets.card_widget import CardWidget
from ui.widgets.loading_bar import LoadingBar
from ui.message_box import BilibiliMessageBox
from ui.utils.image_loader import ImageLoader

logger = logging.getLogger('bilibili_desktop')

class UserSearchWorker(QThread):
    finished_signal = pyqtSignal(list, str) # results, error
    progress_signal = pyqtSignal(str) # status message

    def __init__(self, crawler, keyword):
        super().__init__()
        self.crawler = crawler
        self.keyword = keyword

    def run(self):
        try:
            results = []
            keyword = self.keyword.strip()
            
            logger.info(f"开始搜索用户，关键词: {keyword}")
            
            # 1. Check if keyword is UID (digits)
            if keyword.isdigit():
                logger.info(f"识别为UID: {keyword}")
                self.progress_signal.emit(f"正在查询UID: {keyword}...")
                info = self.crawler.api.get_user_info(keyword)
                if info and info.get('code') == 0:
                    data = info.get('data', {})
                    user_item = self._parse_user_data(data)
                    results.append(user_item)
                    logger.info(f"UID查询成功: {data.get('name')}")
                else:
                    logger.warning(f"UID查询失败: {keyword}")
            
            # 2. Check if keyword is CRC32 Hash (8 hex chars)
            # Danmaku usually provides the CRC32 hash of the UID
            elif len(keyword) == 8 and self._is_hex(keyword):
                logger.info(f"识别为CRC32哈希: {keyword}")
                self.progress_signal.emit(f"检测到CRC32哈希，正在尝试反查UID (可能需要几十秒)...")
                uid = self._crack_crc32(keyword)
                if uid:
                    logger.info(f"CRC32反查成功: {keyword} -> {uid}")
                    self.progress_signal.emit(f"反查成功! UID: {uid}, 正在获取用户信息...")
                    # 修复 Bug: 确保使用反查出的 UID 进行查询
                    # 增加重试机制，防止偶发失败
                    max_retries = 3
                    info = None
                    
                    # 获取重试配置
                    retry_interval = 1
                    try:
                        config = self.crawler.network.config
                        if config:
                            max_retries = config.get('max_retries', 3)
                            retry_interval = config.get('retry_interval', 2)
                    except:
                        pass
                        
                    for i in range(max_retries):
                        info = self.crawler.api.get_user_info(str(uid))
                        if info and info.get('code') == 0:
                            break
                        
                        logger.warning(f"第 {i+1} 次查询UID失败: {info}, 正在重试...")
                        time.sleep(retry_interval) # 稍作等待
                    
                    if info and info.get('code') == 0:
                        data = info.get('data', {})
                        user_item = self._parse_user_data(data)
                        results.append(user_item)
                        logger.info(f"用户查询成功: {data.get('name')}")
                    else:
                        logger.warning(f"用户查询最终失败 (UID: {uid}), 返回信息: {info}")
                else:
                    logger.warning(f"CRC32反查失败: {keyword}")
                    self.progress_signal.emit("反查失败，未找到对应的UID")

            # 3. Search by name (always try this as well unless it's a confirmed UID/Hash)
            # If we found something by UID/Hash, we might still want to search by name?
            # Usually if it's a specific ID, we just want that. But user might input a name that looks like a hash.
            # So let's search by name if results is empty OR if the user explicitly wants to search by name (ambiguous).
            # For now, if we found a direct match, we skip broad search to be precise.
            
            if not results:
                logger.info(f"尝试按昵称搜索: {keyword}")
                self.progress_signal.emit(f"正在按昵称搜索: {keyword}...")
                search_results = self.crawler.api.search_users(keyword)
                if search_results:
                    logger.info(f"昵称搜索找到 {len(search_results)} 个结果")
                    # Avoid duplicate if MID found
                    existing_mids = [str(r['mid']) for r in results]
                    for user in search_results:
                        if str(user.get('mid')) not in existing_mids:
                            results.append(user)
                else:
                    logger.info("昵称搜索未找到结果")
                        
            self.finished_signal.emit(results, "")
        except Exception as e:
            logger.error(f"搜索过程出错: {e}", exc_info=True)
            self.finished_signal.emit([], str(e))

    def _is_hex(self, s):
        try:
            int(s, 16)
            return True
        except ValueError:
            return False

    def _crack_crc32(self, crc32_hash):
        """
        Brute-force crack CRC32 hash to find UID.
        This is slow in Python but feasible for typical UID ranges.
        """
        try:
            target = int(crc32_hash, 16)
            # Search range: 1 to 1 billion (covers most Bilibili UIDs)
            # Optimization: 1 billion iterations in Python is slow (~40-50s).
            # We can't easily optimize this without C extension or rainbow table.
            # We'll just run it.
            
            # TODO: If this is too slow, we might need a smaller range or an external tool/API.
            # Current max UID is around 3.5 billion? No, around hundreds of millions.
            # Let's try up to 800,000,000 (800 million)
            
            limit = 1000000000
            for i in range(1, limit):
                if i % 1000000 == 0:
                    # Check if thread is interrupted
                    if self.isInterruptionRequested():
                        return None
                        
                # binascii.crc32 returns signed 32-bit, we need unsigned
                if (binascii.crc32(str(i).encode()) & 0xffffffff) == target:
                    return i
            return None
        except Exception:
            return None

    def _parse_user_data(self, data):
        """Standardize user data format"""
        return {
            'mid': data.get('mid'),
            'uname': data.get('name'),
            'usign': data.get('sign'),
            'upic': data.get('face'),
            'level': data.get('level'),
            'fans': data.get('fans', -1), # Info API might not have fans, need separate call?
            # 'get_user_info' returns 'data' which has 'level', 'name', 'face', 'sign'.
            # It usually DOES NOT have 'fans' directly in the basic info, depends on API version.
            # The search API returns 'fans'.
            # We might leave fans as -1 if not available.
            'videos': -1,
            'sex': data.get('sex', '保密'),
            'birthday': data.get('birthday', ''),
            'place': data.get('place', '')
        }

class UserDetailsDialog(QDialog):
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.setWindowTitle(f"用户详情 - {user_data.get('uname', '')}")
        self.resize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Scroll Area for details
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(15)
        
        # Avatar
        avatar_label = QLabel()
        avatar_label.setFixedSize(100, 100)
        avatar_label.setStyleSheet("border-radius: 50px; border: 2px solid #fb7299;")
        avatar_label.setScaledContents(True)
        
        def set_round_avatar(pixmap):
             if not pixmap or pixmap.isNull(): return
             scaled = pixmap.scaled(100, 100, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
             rounded = QPixmap(100, 100)
             rounded.fill(Qt.transparent)
             from PyQt5.QtGui import QPainter, QBrush, QPainterPath
             painter = QPainter(rounded)
             painter.setRenderHint(QPainter.Antialiasing)
             path = QPainterPath()
             path.addEllipse(0, 0, 100, 100)
             painter.setClipPath(path)
             painter.drawPixmap(0, 0, scaled)
             painter.end()
             avatar_label.setPixmap(rounded)

        if self.parent() and hasattr(self.parent(), 'image_loader'):
            url = self.user_data.get('upic')
            self.parent().image_loader.load_image(url, set_round_avatar)
        
        grid.addWidget(avatar_label, 0, 0, 2, 1)
        
        # Basic Info
        name_label = QLabel(self.user_data.get('uname', ''))
        name_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        grid.addWidget(name_label, 0, 1)
        
        mid_label = QLabel(f"UID: {self.user_data.get('mid', '')}")
        mid_label.setStyleSheet("color: #666; font-size: 14px;")
        grid.addWidget(mid_label, 1, 1)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        grid.addWidget(line, 2, 0, 1, 2)
        
        # Details
        row = 3
        details = [
            ("等级", f"Lv{self.user_data.get('level', 0)}"),
            ("性别", self.user_data.get('sex', '保密')),
            ("签名", self.user_data.get('usign', '')),
            # Add more if available
        ]
        
        for label, value in details:
            l = QLabel(f"{label}:")
            l.setStyleSheet("font-weight: bold; color: #555;")
            v = QLabel(str(value))
            v.setWordWrap(True)
            v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            
            grid.addWidget(l, row, 0)
            grid.addWidget(v, row, 1)
            row += 1
            
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Close btn
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("padding: 8px 20px;")
        layout.addWidget(close_btn, 0, Qt.AlignCenter)

class UserSearchTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.crawler = main_window.crawler
        self.avatar_cache = {}
        # 初始化图片加载器
        self.image_loader = ImageLoader(self)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Input
        input_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入用户ID、昵称或弹幕哈希(例如 2df9a7b3)")
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
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        self.status_label.hide()
        layout.addWidget(self.status_label)
        
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
        # Task 3: Remove context menu
        self.results_list.setContextMenuPolicy(Qt.NoContextMenu)
        # Task 4: Double click to show details
        self.results_list.itemDoubleClicked.connect(self.on_user_double_clicked)
        
        layout.addWidget(self.results_list)
        
    def start_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            BilibiliMessageBox.warning(self, "提示", "请输入搜索关键词")
            return
            
        self.search_btn.setEnabled(False)
        self.loading_bar.start()
        self.results_list.clear()
        self.status_label.setText("正在搜索...")
        self.status_label.show()
        
        self.worker = UserSearchWorker(self.crawler, keyword)
        self.worker.finished_signal.connect(self.on_search_finished)
        self.worker.progress_signal.connect(self.update_status)
        self.worker.start()
        
    def update_status(self, msg):
        self.status_label.setText(msg)
        
    def on_search_finished(self, results, error):
        self.search_btn.setEnabled(True)
        self.loading_bar.stop()
        self.status_label.hide()
        
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
        item.setData(Qt.UserRole, user) # Store user data
        
        widget = UserCardWidget(user, self)
        item.setSizeHint(widget.sizeHint())
        self.results_list.addItem(item)
        self.results_list.setItemWidget(item, widget)
        
    def on_user_double_clicked(self, item):
        user_data = item.data(Qt.UserRole)
        if user_data:
            dialog = UserDetailsDialog(user_data, self)
            dialog.exec_()

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
        # 只展示第一行签名
        display_sign = sign.split('\n')[0] if sign else "这个人很懒，什么都没有写"
        sign_label = QLabel(display_sign)
        sign_label.setStyleSheet("color: #999; font-size: 14px;")
        sign_label.setWordWrap(False) # 不换行
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
        
        # Use ImageLoader from parent tab
        if hasattr(self.parent_tab, 'image_loader'):
            self.parent_tab.image_loader.load_image(url, self.on_avatar_loaded)
        else:
            # Fallback if image_loader not available (should not happen)
            pass
            
    def on_avatar_loaded(self, pixmap):
        if not pixmap or pixmap.isNull():
            return
            
        # Update cache in parent tab (optional, image_loader has its own cache)
        # self.parent_tab.avatar_cache[self.user.get('upic')] = pixmap
        self.set_avatar(pixmap)
        
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
