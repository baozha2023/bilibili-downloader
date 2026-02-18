import os
import json
import time
import logging
import base64

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QStackedWidget, QGroupBox, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QTabWidget, QMessageBox, QGraphicsOpacityEffect,
                             QMenu, QAction, QApplication)
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QDesktopServices, QCursor, QColor
from PyQt5.QtCore import Qt, QUrl, QPropertyAnimation, QEasingCurve, QEvent, QTimer
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from ui.workers import AccountInfoThread
from ui.login_dialog import BilibiliLoginWindow
from ui.favorites_window import FavoritesWindow
from ui.styles import UIStyles
from ui.utils.image_loader import ImageLoader
from core.utils import decrypt_data
from core.constants import VideoQuality

logger = logging.getLogger('bilibili_desktop')

class AccountTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.crawler = main_window.crawler
        
        # 初始化图片加载器
        self.image_loader = ImageLoader(self)
        
        self.init_ui()
        # 移除自动调用，由 MainWindow 控制调用时机
        # self.check_login_status()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建两个堆叠的小部件，一个用于显示未登录状态，一个用于显示已登录状态
        self.account_stack = QStackedWidget()
        
        # 未登录状态
        not_logged_widget = QWidget()
        not_logged_layout = QVBoxLayout(not_logged_widget)
        
        not_logged_label = QLabel("您尚未登录B站账号")
        not_logged_label.setAlignment(Qt.AlignCenter)
        not_logged_label.setStyleSheet("font-size: 22px; margin: 20px;")
        not_logged_layout.addWidget(not_logged_label)
        
        login_btn = QPushButton("登录账号")
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setStyleSheet("background-color: #00a1d6; color: white; font-weight: bold; padding: 8px 15px; font-size: 22px;")
        login_btn.clicked.connect(self.open_login_window)
        not_logged_layout.addWidget(login_btn, alignment=Qt.AlignCenter)
        
        login_benefits = QLabel(
            "登录账号可以享受以下功能：\n"
            "• 下载高清视频（最高支持4K）\n"
            "• 下载会员专属视频\n"
            "• 同步您的收藏夹和历史记录"
        )
        login_benefits.setStyleSheet("color: #666; margin: 20px;")
        login_benefits.setWordWrap(True)
        login_benefits.setAlignment(Qt.AlignCenter)
        not_logged_layout.addWidget(login_benefits)
        
        self.account_stack.addWidget(not_logged_widget)
        
        # 已登录状态
        logged_widget = QWidget()
        logged_layout = QVBoxLayout(logged_widget)
        
        # 用户基本信息
        user_info_layout = QHBoxLayout()
        
        # 用户头像
        self.account_avatar = QLabel()
        self.account_avatar.setFixedSize(80, 80)
        self.account_avatar.setAlignment(Qt.AlignCenter)
        self.account_avatar.setStyleSheet("background-color: #f5f5f5; border-radius: 40px;")
        self.account_avatar.setText("头像")
        self.account_avatar.setCursor(Qt.PointingHandCursor)
        self.account_avatar.mousePressEvent = self.open_user_homepage
        user_info_layout.addWidget(self.account_avatar)
        
        # 用户详细信息
        user_details_layout = QVBoxLayout()
        user_details_layout.setSpacing(10)
        
        # 第一行：用户名
        self.account_name = QLabel("用户名")
        self.account_name.setStyleSheet("font-size: 32px; font-weight: bold; margin-bottom: 5px;")
        user_details_layout.addWidget(self.account_name)
        

        info_col1 = QVBoxLayout()
        info_col1.setSpacing(5)
        # 第二行：UID
        self.account_uid = QLabel("UID: --")
        self.account_uid.setStyleSheet("font-size: 24px; color: #666;")
        info_col1.addWidget(self.account_uid)
         # 第三行：等级
        self.account_level = QLabel("等级: --")
        self.account_level.setStyleSheet("font-size: 24px; color: #666;")
        info_col1.addWidget(self.account_level)
        
        user_details_layout.addLayout(info_col1)

        # 第四行：会员状态
        self.account_vip = QLabel("会员状态: 非会员")
        self.account_vip.setStyleSheet("font-size: 24px; color: #666;")
        user_details_layout.addWidget(self.account_vip)
        
        user_info_layout.addLayout(user_details_layout)
        user_info_layout.addStretch()
        
        # 操作按钮
        actions_layout = QVBoxLayout()
        
        refresh_btn = QPushButton("刷新信息")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh_account_info)
        actions_layout.addWidget(refresh_btn)
        
        logout_btn = QPushButton("退出登录")
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.clicked.connect(self.logout_account)
        actions_layout.addWidget(logout_btn)
        
        user_info_layout.addLayout(actions_layout)
        
        logged_layout.addLayout(user_info_layout)

        self.content_tabs = QTabWidget()
        self.content_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f6f7f8;
                color: #61666d;
                padding: 10px 20px;
                border: none;
                font-size: 18px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #fb7299;
                font-weight: bold;
                border-bottom: 2px solid #fb7299;
            }
        """)
        
        # 收藏夹列表
        self.favorites_list = QTableWidget(0, 4)
        self.favorites_list.setHorizontalHeaderLabels(["标题", "状态", "视频数量", "ID"])
        self.favorites_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.favorites_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.favorites_list.setFrameShape(QTableWidget.NoFrame)
        self.favorites_list.cellDoubleClicked.connect(self.on_favorite_double_clicked)
        self.favorites_list.setStyleSheet("""
            QTableWidget { 
                font-size: 18px; 
                border: none;
            }
            QHeaderView::section { 
                font-size: 18px; 
                padding: 8px; 
                background-color: #f9f9f9;
                border: none;
            }
            QTableWidget::item { padding: 5px; }
        """)
        self.content_tabs.addTab(self.favorites_list, "收藏夹")
        
        # 历史记录列表
        self.history_list = QTableWidget(0, 4)
        self.history_list.setHorizontalHeaderLabels(["标题", "UP主", "观看时间", "BV号"])
        self.history_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.history_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_list.setFrameShape(QTableWidget.NoFrame)
        self.history_list.cellDoubleClicked.connect(self.on_history_video_clicked)
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.show_history_context_menu)
        # 启用鼠标跟踪，用于显示悬停封面
        self.history_list.setMouseTracking(True)
        self.history_list.cellEntered.connect(self.on_cell_entered)
        self.history_list.installEventFilter(self)
        self.history_list.setStyleSheet("""
            QTableWidget { 
                font-size: 18px; 
                border: none;
            }
            QHeaderView::section { 
                font-size: 18px; 
                padding: 8px; 
                background-color: #f9f9f9;
                border: none;
            }
            QTableWidget::item { padding: 5px; }
        """)
        self.content_tabs.addTab(self.history_list, "历史记录")
        
        # 封面预览Label
        self.cover_label = QLabel(self)
        self.cover_label.setWindowFlags(Qt.ToolTip)
        self.cover_label.setStyleSheet("border: 2px solid white; border-radius: 4px;")
        self.cover_label.setScaledContents(True)
        self.cover_label.resize(320, 200)
        self.cover_label.hide()
        
        self.privacy_stack = QStackedWidget()
        
        # 1. Lock Screen
        self.lock_widget = QWidget()
        lock_layout = QVBoxLayout(self.lock_widget)
        lock_layout.setAlignment(Qt.AlignCenter)
        
        lock_icon = QLabel("🔒")
        lock_icon.setStyleSheet("font-size: 64px; margin-bottom: 20px;")
        lock_icon.setAlignment(Qt.AlignCenter)
        lock_layout.addWidget(lock_icon)
        
        lock_msg = QLabel("为了保护您的隐私，内容已隐藏")
        lock_msg.setStyleSheet("font-size: 24px; color: #666; margin-bottom: 30px;")
        lock_msg.setAlignment(Qt.AlignCenter)
        lock_layout.addWidget(lock_msg)
        
        unlock_btn = QPushButton("点击解锁")
        unlock_btn.setCursor(Qt.PointingHandCursor)
        unlock_btn.setStyleSheet(UIStyles.UNLOCK_BTN)
        unlock_btn.clicked.connect(self.unlock_content)
        lock_layout.addWidget(unlock_btn)
        
        self.privacy_stack.addWidget(self.lock_widget)
        
        # 2. Content
        self.privacy_stack.addWidget(self.content_tabs)
        
        # Initial state: Locked
        self.is_unlocked_once = False
        self.privacy_stack.setCurrentIndex(0)
        
        logged_layout.addWidget(self.privacy_stack)
        
        self.account_stack.addWidget(logged_widget)
        
        # 默认显示未登录状态
        self.account_stack.setCurrentIndex(0)
        layout.addWidget(self.account_stack)

    def open_login_window(self):
        """打开登录窗口"""
        self.login_window = BilibiliLoginWindow()
        self.login_window.show()
        self.login_window.finished_signal = lambda: self.check_login_status()

    def open_user_homepage(self, event):
        """打开用户主页"""
        if hasattr(self, 'current_mid') and self.current_mid:
            url = f"https://space.bilibili.com/{self.current_mid}"
            QDesktopServices.openUrl(QUrl(url))
            
    def switch_to_logged_view(self):
        """切换到已登录视图"""
        if self.account_stack.currentIndex() == 1:
            return
            
        # 设置淡入动画
        effect = QGraphicsOpacityEffect(self.account_stack.widget(1))
        self.account_stack.widget(1).setGraphicsEffect(effect)
        
        self.anim = QPropertyAnimation(effect, b"opacity")
        self.anim.setDuration(500)
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        
        self.account_stack.setCurrentIndex(1)
        self.anim.start()

    def check_login_status(self):
        """检查登录状态"""
        # 如果已经通过 StartupWorker 检查了，直接使用
        if hasattr(self.main_window, 'context') and self.main_window.context.get('login_info'):
            login_info = self.main_window.context.get('login_info')
            if login_info.get('is_login') and login_info.get('data'):
                # 清除 context 以免重复使用
                self.main_window.context['login_info'] = None
                
                # 直接处理数据
                cookies = login_info.get('cookies')
                if cookies:
                    self.crawler.cookies = cookies
                    
                self.on_account_info_finished({"status": "success", "data": login_info.get('data')})
                self.switch_to_logged_view()
                return

        self.main_window.log_to_console("正在检查登录状态...", "info")
        config_file = os.path.join(self.crawler.data_dir, "config", "login_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                
                config = None
                # Check if encrypted
                if isinstance(saved_data, dict) and "data" in saved_data and "version" in saved_data:
                    # Decrypt
                    decrypted_str = decrypt_data(saved_data["data"])
                    if decrypted_str:
                        config = json.loads(decrypted_str)

                if config:
                    cookies = config.get("cookies", {})
                    if cookies and "SESSDATA" in cookies:
                        self.crawler.cookies = cookies
                        self.get_account_info(cookies)
                        self.switch_to_logged_view()
                        return
            except Exception as e:
                logger.error(f"读取登录配置失败: {e}")
                self.main_window.log_to_console(f"读取登录配置失败: {e}", "error")
        
        self.account_stack.setCurrentIndex(0)
        self.main_window.log_to_console("未检测到登录状态", "info")

    def get_account_info(self, cookies):
        """获取账号信息"""
        self.account_thread = AccountInfoThread(self.crawler, cookies)
        self.account_thread.finished_signal.connect(self.on_account_info_finished)
        self.account_thread.start()

    def on_account_info_finished(self, result):
        if result["status"] == "success":
            user_info = result.get("data", {})
            self.current_mid = user_info.get('mid')
            username = user_info.get("uname", "未知用户")
            self.account_name.setText(username)
            self.account_uid.setText(f"UID: {self.current_mid if self.current_mid else '--'}")
            self.account_level.setText(f"等级: Lv{user_info.get('level_info', {}).get('current_level', 0)}")
            
            # 记录登录成功日志
            self.main_window.log_to_console(f"账号登录成功: {username}", "success")
            
            vip_type = user_info.get("vip", {}).get("type", 0)
            vip_status = user_info.get("vip", {}).get("status", 0)
            
            # status 1 为有效，0 为过期/无效
            if vip_type == 0 or vip_status != 1:
                self.account_vip.setText("会员状态: 非会员")
                self.account_vip.setStyleSheet("font-size: 24px; color: #666;")
            elif vip_type == 1:
                self.account_vip.setText("会员状态: 大会员")
                self.account_vip.setStyleSheet("font-size: 24px; color: #FB7299;")
            elif vip_type == 2:
                self.account_vip.setText("会员状态: 年度大会员")
                self.account_vip.setStyleSheet("font-size: 24px; color: #FB7299; font-weight: bold;")
            
            face_url = user_info.get("face", "")
            if face_url:
                self.load_account_avatar(face_url)
                
            # 更新收藏夹列表
            favorites = user_info.get("favorites", [])
            self.update_favorites_list(favorites)
            
            # 更新历史记录列表
            history = user_info.get("history", [])
            self.update_history_list(history)
            
            # 更新画质选择选项
            self.update_quality_options(vip_type, vip_status)
            
        else:
            # 登录失败或无效，重置画质选项
            self.update_quality_options(0, 0)

    def update_quality_options(self, vip_type, vip_status):
        """根据会员状态更新画质选项"""
        settings_tab = self.main_window.settings_tab
        current_quality = settings_tab.quality_combo.currentText()
        settings_tab.quality_combo.clear()
        
        # 基础选项
        qualities = [VideoQuality.Q_720P, VideoQuality.Q_480P, VideoQuality.Q_360P]
        
        # 登录用户 (非会员)
        is_logged_in = False
        if hasattr(self.crawler, 'cookies') and self.crawler.cookies:
            if "SESSDATA" in self.crawler.cookies:
                is_logged_in = True
        
        if self.account_stack.currentIndex() == 1:
            is_logged_in = True

        # 大会员判断: type > 0 通常表示是会员 (1:月度, 2:年度)
        # vip_status 1 表示有效
        is_vip = (vip_type > 0 and vip_status == 1)
        
        if is_vip:
            # 大会员: 4K, 1080P60, 1080P+
            qualities.insert(0, VideoQuality.Q_4K)
            qualities.insert(1, VideoQuality.Q_1080P_60)
            qualities.insert(2, VideoQuality.Q_1080P_PLUS)
            qualities.insert(3, VideoQuality.Q_1080P)
            
            # 自动设置为4K
            self.main_window.log_to_console("检测到大会员，自动调整画质为 4K", "info")
            # 查找4K的索引，通常是0
            target_quality = VideoQuality.Q_4K
        elif is_logged_in:
            # 普通登录用户: 1080P, 720P60
            qualities.insert(0, VideoQuality.Q_1080P)
            qualities.insert(1, VideoQuality.Q_720P_60)
            
            # 自动设置为1080P
            self.main_window.log_to_console("检测到已登录，自动调整画质为 1080P", "info")
            target_quality = VideoQuality.Q_1080P
        else:
            target_quality = None
            
        settings_tab.quality_combo.addItems(qualities)
        
        # 尝试选中目标画质
        if target_quality:
            index = settings_tab.quality_combo.findText(target_quality)
            if index >= 0:
                settings_tab.quality_combo.setCurrentIndex(index)
                # 更新配置
                if hasattr(self.main_window, 'config_manager'):
                    self.main_window.config_manager.set('video_quality', target_quality)
                    self.main_window.config_manager.save()
        else:
            # 如果没有目标画质（未登录），尝试恢复之前的选择或默认
            index = settings_tab.quality_combo.findText(current_quality)
            if index >= 0:
                settings_tab.quality_combo.setCurrentIndex(index)
            else:
                settings_tab.quality_combo.setCurrentIndex(0)

    def on_cell_entered(self, row, column):
        """鼠标移入单元格显示封面"""
        if row < 0:
            self.cover_label.hide()
            return
            
        # 获取BV号item，从中获取封面URL
        bvid_item = self.history_list.item(row, 3)
        if bvid_item:
            cover_url = bvid_item.data(Qt.UserRole)
            if cover_url:
                self.show_cover_preview(cover_url)
                
    def show_cover_preview(self, url):
        # 检查缓存
        if not hasattr(self, 'cover_cache'):
            self.cover_cache = {}
            
        if url in self.cover_cache:
            self.display_cover(self.cover_cache[url])
        else:
            # Use avatar_network_manager or create a new one?
            # Reuse avatar_network_manager for simplicity, but need to handle callback
            # Create a separate manager for covers to avoid conflict
            if not hasattr(self, 'cover_network_manager'):
                self.cover_network_manager = QNetworkAccessManager(self)
                self.cover_network_manager.finished.connect(self.on_cover_downloaded)
            
            self.cover_network_manager.get(QNetworkRequest(QUrl(url)))
            
    def on_cover_downloaded(self, reply):
        url = reply.url().toString()
        if reply.error():
            reply.deleteLater()
            return
        data = reply.readAll()
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self.cover_cache[url] = pixmap
        self.display_cover(pixmap)
        reply.deleteLater()
        
    def display_cover(self, pixmap):
        # 自适应缩放逻辑
        max_width = 320
        max_height = 240
        
        orig_width = pixmap.width()
        orig_height = pixmap.height()
        
        if orig_width == 0 or orig_height == 0:
            return

        aspect_ratio = orig_width / orig_height
        
        if aspect_ratio > 1: # 横屏
            new_width = min(orig_width, max_width)
            new_height = int(new_width / aspect_ratio)
        else: # 竖屏
            new_height = min(orig_height, max_height)
            new_width = int(new_height * aspect_ratio)
            
        scaled_pixmap = pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.cover_label.resize(new_width, new_height)
        self.cover_label.setPixmap(scaled_pixmap)
        
        cursor_pos = QCursor.pos()
        self.cover_label.move(cursor_pos.x() + 20, cursor_pos.y() + 20)
        self.cover_label.show()
        
    def eventFilter(self, source, event):
        if source == self.history_list and event.type() == QEvent.Leave:
            self.cover_label.hide()
        return super().eventFilter(source, event)

    def update_favorites_list(self, favorites):
        """更新收藏夹列表显示"""
        self.favorites_list.setRowCount(len(favorites))
        for i, fav in enumerate(favorites):
            title = fav.get("title", "")
            media_count = fav.get("media_count", 0)
            
            # 尝试获取隐私状态
            # attr lowest bit: 0 public, 1 private
            attr = fav.get("attr", 0)
            if attr & 1:
                status_text = "私密"
            else:
                status_text = "公开"
            
            fid = fav.get("id", 0)
            
            # 如果没有 attr 信息，尝试显示 ID
            if "attr" not in fav:
                 status_text = f"ID: {fid}"
            
            self.favorites_list.setItem(i, 0, QTableWidgetItem(title))
            self.favorites_list.setItem(i, 1, QTableWidgetItem(status_text))
            self.favorites_list.setItem(i, 2, QTableWidgetItem(str(media_count)))
            self.favorites_list.setItem(i, 3, QTableWidgetItem(str(fid)))

    def update_history_list(self, history):
        """更新历史记录列表显示"""
        self.history_list.setRowCount(len(history))
        for i, item in enumerate(history):
            title = item.get("title", "")
            author_name = item.get("author_name", "")
            if not author_name:
                author_name = item.get("owner", {}).get("name", "")
            
            view_at = item.get("view_at", 0)
            if view_at:
                view_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(view_at))
            else:
                view_time = "--"
                
            bvid = item.get("history", {}).get("bvid", "")
            if not bvid:
                bvid = item.get("bvid", "")
                
            cover = item.get("cover", "") or item.get("pic", "")
                
            self.history_list.setItem(i, 0, QTableWidgetItem(title))
            self.history_list.setItem(i, 1, QTableWidgetItem(author_name))
            self.history_list.setItem(i, 2, QTableWidgetItem(view_time))
            
            bvid_item = QTableWidgetItem(bvid)
            if cover:
                bvid_item.setData(Qt.UserRole, cover)
            self.history_list.setItem(i, 3, bvid_item)

    def load_account_avatar(self, url):
        # 先设置默认头像
        self.set_default_avatar()
        
        # 延迟1秒加载，避免初始化时的资源竞争
        QTimer.singleShot(1000, lambda: self._start_load_avatar(url))
        
    def _start_load_avatar(self, url):
        self.image_loader.load_image(url, self.on_avatar_loaded)
        
    def set_default_avatar(self):
        """设置默认头像"""
        try:
            default_pixmap = QPixmap(80, 80)
            default_pixmap.fill(Qt.transparent)
            
            painter = QPainter(default_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 绘制背景
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#E0E0E0"))) # 浅灰色
            painter.drawEllipse(0, 0, 80, 80)
            
            # 绘制文字
            painter.setPen(QColor("#FFFFFF"))
            font = painter.font()
            font.setPixelSize(40)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(0, 0, 80, 80, Qt.AlignCenter, "B")
            
            painter.end()
            self.account_avatar.setPixmap(default_pixmap)
        except Exception as e:
            logger.error(f"设置默认头像失败: {e}")
            self.account_avatar.setText("头像")

    def on_avatar_loaded(self, pixmap):
        try:
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                rounded_pixmap = QPixmap(80, 80)
                rounded_pixmap.fill(Qt.transparent)
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(scaled_pixmap))
                painter.drawEllipse(0, 0, 80, 80)
                painter.end()
                self.account_avatar.setPixmap(rounded_pixmap)
            else:
                logger.warning("头像加载失败: pixmap为空")
                # 保持默认头像
        except Exception as e:
            logger.error(f"处理头像图片失败: {e}")
            # 保持默认头像

    # def on_account_avatar_downloaded(self, reply): ... (Removed)

    def refresh_account_info(self):
        try:
            if hasattr(self.crawler, 'cookies') and self.crawler.cookies:
                self.get_account_info(self.crawler.cookies)
            else:
                self.check_login_status()
        except Exception as e:
            logger.error(f"刷新账号信息失败: {e}")
            self.main_window.log_to_console(f"刷新账号信息失败: {e}", "error")
    
    def logout_account(self):
        reply = QMessageBox.question(self, "确认退出", "确定要退出当前账号吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            username = self.account_name.text()
            self.crawler.cookies = None
            config_file = os.path.join(self.crawler.data_dir, "config", "login_config.json")
            if os.path.exists(config_file):
                try:
                    os.remove(config_file)
                except:
                    pass
            self.account_stack.setCurrentIndex(0)
            
            self.main_window.log_to_console(f"账号已退出登录: {username}", "warning")

            # Reset quality options
            self.update_quality_options(0, 0)

    def on_history_video_clicked(self, row, column):
        """历史记录视频双击处理"""
        item_bvid = self.history_list.item(row, 3)
        item_title = self.history_list.item(row, 0)
        if item_bvid:
            bvid = item_bvid.text()
            title = item_title.text() if item_title else ""
            
            self.main_window.tabs.setCurrentIndex(0)
            download_tab = self.main_window.download_tab
            download_tab.bvid_input.setText(bvid)
            if title:
                download_tab.bvid_input.setToolTip(title)
            download_tab.download_video(title)

    def on_favorite_double_clicked(self, row, column):
        """收藏夹双击处理"""
        item_id = self.favorites_list.item(row, 3)
        item_title = self.favorites_list.item(row, 0)
        if item_id:
            media_id = item_id.text()
            title = item_title.text() if item_title else ""
            
            # 打开收藏夹窗口
            self.fav_window = FavoritesWindow(self.main_window, media_id, title)
            self.fav_window.show()

    def show_history_context_menu(self, pos):
        item = self.history_list.itemAt(pos)
        if not item:
            return
            
        row = item.row()
        bvid_item = self.history_list.item(row, 3)
        title_item = self.history_list.item(row, 0)
        
        if not bvid_item:
            return
            
        bvid = bvid_item.text()
        title = title_item.text() if title_item else ""
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #eee;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 16px;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
                color: #fb7299;
            }
        """)
        
        download_action = QAction("📥 下载视频", self)
        download_action.triggered.connect(lambda: self.on_history_video_clicked(row, 0))
        menu.addAction(download_action)
        
        watch_action = QAction("📺 实时观看", self)
        watch_action.triggered.connect(lambda: self.watch_live(bvid, title))
        menu.addAction(watch_action)

        copy_bv_action = QAction("📋 复制BV号", self)
        copy_bv_action.triggered.connect(lambda: QApplication.clipboard().setText(bvid))
        menu.addAction(copy_bv_action)
        
        analyze_action = QAction("📊 视频分析", self)
        analyze_action.triggered.connect(lambda: self.analyze_video(bvid))
        menu.addAction(analyze_action)
        
        menu.exec_(self.history_list.viewport().mapToGlobal(pos))
        
    def analyze_video(self, bvid):
        self.main_window.tabs.setCurrentIndex(3)
        analysis_tab = self.main_window.analysis_tab
        analysis_tab.bvid_input.setText(bvid)
        analysis_tab.start_analysis()
        
    def watch_live(self, bvid, title):
        # 获取cookies
        cookies = {}
        if hasattr(self.crawler, 'cookies'):
            cookies = self.crawler.cookies
            
        self.player_window = VideoPlayerWindow(bvid, title, cookies)
        self.player_window.show()

    def unlock_content(self):
        self.privacy_stack.setCurrentIndex(1)
        self.is_unlocked_once = True

    def showEvent(self, event):
        # Check settings
        if hasattr(self.main_window, 'settings_tab'):
            settings = self.main_window.settings_tab
            always_lock = settings.always_lock_check.isChecked()
            
            if always_lock:
                # Always lock when showing tab
                self.privacy_stack.setCurrentIndex(0)
            else:
                # If not always lock, check if already unlocked once
                if self.is_unlocked_once:
                    self.privacy_stack.setCurrentIndex(1)
                else:
                    self.privacy_stack.setCurrentIndex(0)
        
        super().showEvent(event)

