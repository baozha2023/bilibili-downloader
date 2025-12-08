import os
import json
import time
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QStackedWidget, QGroupBox, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QTabWidget, QMessageBox, QGraphicsOpacityEffect)
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QDesktopServices, QCursor
from PyQt5.QtCore import Qt, QUrl, QPropertyAnimation, QEasingCurve
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from ui.workers import AccountInfoThread
from ui.login_dialog import BilibiliLoginWindow
from ui.favorites_window import FavoritesWindow

logger = logging.getLogger('bilibili_desktop')

class AccountTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.crawler = main_window.crawler
        
        # 初始化网络管理器
        self.avatar_network_manager = QNetworkAccessManager(self)
        self.avatar_network_manager.finished.connect(self.on_account_avatar_downloaded)
        
        self.init_ui()
        self.check_login_status()
        
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
        user_details_layout.setSpacing(10) # 增加间距
        
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
        refresh_btn.clicked.connect(self.refresh_account_info)
        actions_layout.addWidget(refresh_btn)
        
        logout_btn = QPushButton("退出登录")
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
        self.favorites_list.setFrameShape(QTableWidget.NoFrame) # 去除边框
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
        self.history_list.setFrameShape(QTableWidget.NoFrame) # 去除边框
        self.history_list.cellDoubleClicked.connect(self.on_history_video_clicked)
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
        
        logged_layout.addWidget(self.content_tabs)
        
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
        """切换到已登录视图（带动画）"""
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
        self.main_window.log_to_console("正在检查登录状态...", "info")
        config_file = os.path.join(self.crawler.data_dir, "config", "login_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
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
        qualities = ["720p", "480p", "360p"]
        
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
        
        # 只要登录了就可以尝试1080p (qn=80)
        if is_logged_in:
             if "1080p" not in qualities:
                qualities.insert(0, "1080p")
             
        # 大会员
        if is_vip:
            if "1080p+" not in qualities:
                qualities.insert(0, "1080p+")
            if "4k" not in qualities:
                qualities.insert(0, "4k")
            
        settings_tab.quality_combo.addItems(qualities)
        
        # 尝试恢复之前的选择，如果不存在则默认选择第一个（最高画质）
        index = settings_tab.quality_combo.findText(current_quality)
        if index >= 0:
            settings_tab.quality_combo.setCurrentIndex(index)
        else:
            settings_tab.quality_combo.setCurrentIndex(0)

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
                
            self.history_list.setItem(i, 0, QTableWidgetItem(title))
            self.history_list.setItem(i, 1, QTableWidgetItem(author_name))
            self.history_list.setItem(i, 2, QTableWidgetItem(view_time))
            self.history_list.setItem(i, 3, QTableWidgetItem(bvid))

    def load_account_avatar(self, url):
        self.account_avatar.setText("加载中...")
        self.avatar_network_manager.get(QNetworkRequest(QUrl(url)))
    
    def on_account_avatar_downloaded(self, reply):
        try:
            if reply.error() == QNetworkReply.NoError:
                data = reply.readAll()
                pixmap = QPixmap()
                pixmap.loadFromData(data)
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
                self.account_avatar.setText("加载失败")
        except Exception as e:
            self.account_avatar.setText("加载错误")
        finally:
            reply.deleteLater()

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
