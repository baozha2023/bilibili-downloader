import sys
import os
import json
import time
import logging
import csv
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QTabWidget, QCheckBox, 
                             QGroupBox, QMessageBox, QStackedWidget, QFileDialog, QGridLayout,
                             QProgressBar, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
                             QSpinBox, QComboBox, QMenu, QDialog)
from PyQt5.QtGui import QIcon, QPixmap, QImage, QPainter, QBrush, QDesktopServices
from PyQt5.QtCore import Qt, QUrl, QSize, QTimer
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from core.crawler import BilibiliCrawler
from ui.workers import WorkerThread, AccountInfoThread
from ui.login_dialog import BilibiliLoginWindow
from ui.update_dialog import UpdateDialog

# 配置日志
logger = logging.getLogger('bilibili_desktop')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class BilibiliDesktop(QMainWindow):
    """哔哩哔哩桌面端主窗口"""
    
    def __init__(self):
        super().__init__()
        self.crawler = BilibiliCrawler()
        self.download_history = self.load_download_history()
        # 初始化网络管理器，避免重复创建导致错误
        self.avatar_network_manager = QNetworkAccessManager(self)
        self.avatar_network_manager.finished.connect(self.on_account_avatar_downloaded)
        
        self.init_ui()
        self.set_style()
        
        # 显示更新公告
        QTimer.singleShot(500, self.show_update_dialog)

    def closeEvent(self, event):
        """关闭窗口事件"""
        # 清除登录信息
        try:
            # 获取配置文件路径
            config_dir = os.path.join(self.crawler.data_dir, 'config')
            login_config_path = os.path.join(config_dir, "login_config.json")
            
            if os.path.exists(login_config_path):
                os.remove(login_config_path)
                print("已清除登录信息")
        except Exception as e:
            print(f"清除登录信息失败: {e}")
            
        event.accept()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("哔哩哔哩视频下载器 v1.10")
        self.setMinimumSize(1000, 700)
        
        # 设置应用图标
        if os.path.exists("resource/icon.ico"):
            self.setWindowIcon(QIcon("resource/icon.ico"))
        elif os.path.exists("resource/logo.png"):
            self.setWindowIcon(QIcon("resource/logo.png"))
        
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部标题栏
        # title_layout = QHBoxLayout()
        # title_label = QLabel("哔哩哔哩视频下载器")
        # title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #fb7299;")
        # title_layout.addWidget(title_label)
        # title_layout.addStretch()
        # main_layout.addLayout(title_layout)
        
        # 标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 创建各个标签页
        self.create_download_tab()
        self.create_popular_tab()
        self.create_account_tab()
        self.create_settings_tab()
        
        # 底部状态栏
        self.statusBar().showMessage("就绪")
        
        # 控制台日志
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout(log_group)
        self.console_log = QTextEdit()
        self.console_log.setReadOnly(True)
        self.console_log.setMaximumHeight(150)
        self.console_log.setStyleSheet("background-color: #1e1e1e; color: #f0f0f0; font-family: Consolas, Monospace;")
        log_layout.addWidget(self.console_log)
        
        # 日志控制按钮
        log_ctrl_layout = QHBoxLayout()
        
        self.auto_scroll_check = QCheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        log_ctrl_layout.addWidget(self.auto_scroll_check)
        
        log_ctrl_layout.addStretch()
        
        clear_log_btn = QPushButton("清除日志")
        clear_log_btn.setStyleSheet("background-color: #666; padding: 3px 8px;")
        clear_log_btn.clicked.connect(self.clear_console_log)
        log_ctrl_layout.addWidget(clear_log_btn)
        
        save_log_btn = QPushButton("保存日志")
        save_log_btn.setStyleSheet("background-color: #666; padding: 3px 8px;")
        save_log_btn.clicked.connect(self.save_console_log)
        log_ctrl_layout.addWidget(save_log_btn)
        
        log_layout.addLayout(log_ctrl_layout)
        main_layout.addWidget(log_group)
        
        # 加载配置
        self.load_config_from_file()
        
        # 欢迎信息
        self.log_to_console("欢迎使用哔哩哔哩视频下载器！", "info")
        self.log_to_console(f"数据存储目录: {self.crawler.data_dir}", "system")
        
        # 检查ffmpeg
        if self.crawler.ffmpeg_available:
            self.log_to_console(f"ffmpeg检测成功: {self.crawler.ffmpeg_path}", "system")
        else:
            self.log_to_console("未检测到ffmpeg，视频合并功能将不可用", "warning")

    def create_download_tab(self):
        # 下载标签页
        download_tab = QWidget()
        self.tabs.addTab(download_tab, "视频下载")
        
        layout = QVBoxLayout(download_tab)
        
        # 输入区域
        input_group = QGroupBox("下载选项")
        input_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        input_layout = QHBoxLayout(input_group)
        
        input_layout.addWidget(QLabel("视频BV号:"))
        self.bvid_input = QLineEdit()
        self.bvid_input.setPlaceholderText("请输入视频BV号，例如: BV1xx411c7mD")
        input_layout.addWidget(self.bvid_input)
        
        self.download_btn = QPushButton("开始下载")
        self.download_btn.clicked.connect(lambda: self.download_video())
        self.download_btn.setStyleSheet("background-color: #fb7299; color: white; font-weight: bold; padding: 5px 15px;")
        input_layout.addWidget(self.download_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("background-color: #999; color: white; padding: 5px 15px;")
        input_layout.addWidget(self.cancel_btn)
        
        layout.addWidget(input_group)
        
        # 进度显示区域
        progress_group = QGroupBox("下载进度")
        progress_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        progress_layout = QVBoxLayout(progress_group)
        
        # 视频进度
        video_layout = QHBoxLayout()
        video_layout.addWidget(QLabel("视频:"))
        self.video_progress = QProgressBar()
        video_layout.addWidget(self.video_progress)
        progress_layout.addLayout(video_layout)
        
        # 音频进度
        audio_layout = QHBoxLayout()
        audio_layout.addWidget(QLabel("音频:"))
        self.audio_progress = QProgressBar()
        audio_layout.addWidget(self.audio_progress)
        progress_layout.addLayout(audio_layout)
        
        # 合并进度
        merge_layout = QHBoxLayout()
        merge_layout.addWidget(QLabel("合并:"))
        self.merge_progress = QProgressBar()
        merge_layout.addWidget(self.merge_progress)
        progress_layout.addLayout(merge_layout)
        
        # 详细信息
        info_layout = QHBoxLayout()
        self.download_status = QLabel("就绪")
        info_layout.addWidget(self.download_status)
        
        info_layout.addStretch()
        
        self.download_speed_label = QLabel("速度: 0 B/s")
        info_layout.addWidget(self.download_speed_label)
        
        info_layout.addSpacing(20)
        
        self.download_size_label = QLabel("大小: 0 B / 0 B")
        info_layout.addWidget(self.download_size_label)
        
        info_layout.addSpacing(20)
        
        self.download_eta_label = QLabel("剩余时间: --:--")
        info_layout.addWidget(self.download_eta_label)
        
        progress_layout.addLayout(info_layout)
        layout.addWidget(progress_group)
        
        # 历史记录按钮
        history_layout = QHBoxLayout()
        history_layout.addStretch()
        
        history_btn = QPushButton("查看下载历史")
        history_btn.clicked.connect(self.show_download_history)
        history_layout.addWidget(history_btn)
        
        open_dir_btn = QPushButton("打开下载目录")
        open_dir_btn.clicked.connect(lambda: self.open_download_dir())
        history_layout.addWidget(open_dir_btn)
        
        layout.addLayout(history_layout)
        
        layout.addStretch()

    def create_popular_tab(self):
        # 热门视频标签页
        popular_tab = QWidget()
        self.tabs.addTab(popular_tab, "热门视频")
        
        layout = QVBoxLayout(popular_tab)
        
        # 控制区域
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("页数:"))
        self.popular_pages = QSpinBox()
        self.popular_pages.setMinimum(1)
        self.popular_pages.setMaximum(10)
        self.popular_pages.setValue(3)
        control_layout.addWidget(self.popular_pages)
        self.popular_btn = QPushButton("获取热门视频")
        self.popular_btn.clicked.connect(self.get_popular_videos)
        control_layout.addWidget(self.popular_btn)
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 视频列表
        self.popular_table = QTableWidget(0, 5)
        self.popular_table.setHorizontalHeaderLabels(["标题", "UP主", "播放量", "点赞", "BV号"])
        # 设置第一列自动拉伸
        header = self.popular_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.popular_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.popular_table.cellDoubleClicked.connect(self.on_popular_video_clicked)
        layout.addWidget(self.popular_table)
        
        # 状态区域
        self.popular_status = QLabel("就绪")
        layout.addWidget(self.popular_status)

    def create_account_tab(self):
        """创建账号标签页"""
        account_tab = QWidget()
        self.tabs.addTab(account_tab, "我的账号")
        
        layout = QVBoxLayout(account_tab)
        
        # 账号信息区域
        account_group = QGroupBox("账号信息")
        account_layout = QVBoxLayout(account_group)
        
        # 创建两个堆叠的小部件，一个用于显示未登录状态，一个用于显示已登录状态
        self.account_stack = QStackedWidget()
        
        # 未登录状态
        not_logged_widget = QWidget()
        not_logged_layout = QVBoxLayout(not_logged_widget)
        
        not_logged_label = QLabel("您尚未登录B站账号")
        not_logged_label.setAlignment(Qt.AlignCenter)
        not_logged_label.setStyleSheet("font-size: 14px; margin: 20px;")
        not_logged_layout.addWidget(not_logged_label)
        
        login_btn = QPushButton("登录账号")
        login_btn.setStyleSheet("background-color: #00a1d6; color: white; font-weight: bold; padding: 8px 15px;")
        login_btn.clicked.connect(self.open_login_window)
        not_logged_layout.addWidget(login_btn, alignment=Qt.AlignCenter)
        
        login_benefits = QLabel(
            "登录账号可以享受以下功能：\n"
            "• 下载高清视频（最高支持4K）\n"
            "• 批量下载视频\n"
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
        user_info_layout.addWidget(self.account_avatar)
        
        # 用户详细信息
        user_details_layout = QVBoxLayout()
        
        self.account_name = QLabel("用户名")
        self.account_name.setStyleSheet("font-size: 16px; font-weight: bold;")
        user_details_layout.addWidget(self.account_name)
        
        self.account_uid = QLabel("UID: --")
        user_details_layout.addWidget(self.account_uid)
        
        self.account_level = QLabel("等级: --")
        user_details_layout.addWidget(self.account_level)
        
        self.account_vip = QLabel("会员状态: 非会员")
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
        
        # 会员特权信息
        vip_group = QGroupBox("会员特权")
        vip_layout = QVBoxLayout(vip_group)
        
        self.vip_info = QLabel(
            "当前权益：\n"
            "• 支持下载 1080P 及以下清晰度视频\n"
            "• 支持批量下载视频\n"
            "• 支持导出视频弹幕和评论\n\n"
            "开通大会员可解锁 4K/1080P+ 画质及专属视频下载"
        )
        self.vip_info.setWordWrap(True)
        vip_layout.addWidget(self.vip_info)
        
        logged_layout.addWidget(vip_group)
        
        # 收藏夹和历史记录
        tabs_group = QGroupBox("我的内容")
        tabs_layout = QVBoxLayout(tabs_group)
        
        self.content_tabs = QTabWidget()
        
        # 收藏夹列表
        self.favorites_list = QTableWidget(0, 3)
        self.favorites_list.setHorizontalHeaderLabels(["标题", "创建时间", "视频数量"])
        self.favorites_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.favorites_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.content_tabs.addTab(self.favorites_list, "收藏夹")
        
        # 历史记录列表
        self.history_list = QTableWidget(0, 4)
        self.history_list.setHorizontalHeaderLabels(["标题", "UP主", "观看时间", "BV号"])
        self.history_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.history_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_list.cellDoubleClicked.connect(self.on_history_video_clicked)
        self.content_tabs.addTab(self.history_list, "历史记录")
        
        tabs_layout.addWidget(self.content_tabs)
        
        logged_layout.addWidget(tabs_group)
        
        self.account_stack.addWidget(logged_widget)
        
        # 默认显示未登录状态
        self.account_stack.setCurrentIndex(0)
        
        account_layout.addWidget(self.account_stack)
        layout.addWidget(account_group)
        
        # 状态区域
        status_layout = QHBoxLayout()
        self.account_status = QLabel("未登录")
        status_layout.addWidget(self.account_status)
        layout.addLayout(status_layout)
        
        # 检查是否已有登录信息
        self.check_login_status()

    def create_settings_tab(self):
        # 设置标签页
        settings_tab = QWidget()
        self.tabs.addTab(settings_tab, "设置")
        
        # 使用主垂直布局，增加边距和间距
        main_layout = QVBoxLayout(settings_tab)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # --- 1. 基本设置分组 ---
        basic_group = QGroupBox("基本设置")
        basic_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }")
        basic_layout = QGridLayout(basic_group)
        basic_layout.setVerticalSpacing(15)
        basic_layout.setHorizontalSpacing(15)
        basic_layout.setContentsMargins(20, 25, 20, 20)
        
        # 数据存储目录
        basic_layout.addWidget(QLabel("数据存储目录:"), 0, 0)
        self.data_dir_input = QLineEdit(os.path.abspath(self.crawler.data_dir))
        self.data_dir_input.setMinimumWidth(400)
        basic_layout.addWidget(self.data_dir_input, 0, 1)
        browse_btn = QPushButton("浏览...")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self.browse_data_dir)
        basic_layout.addWidget(browse_btn, 0, 2)

        # 最大重试次数
        basic_layout.addWidget(QLabel("最大重试次数:"), 1, 0)
        self.retry_count = QSpinBox()
        self.retry_count.setRange(1, 10)
        self.retry_count.setValue(3)
        self.retry_count.setFixedWidth(100)
        basic_layout.addWidget(self.retry_count, 1, 1)
        
        main_layout.addWidget(basic_group)
        
        # --- 2. 下载设置分组 ---
        download_group = QGroupBox("下载设置")
        download_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }")
        download_layout = QGridLayout(download_group)
        download_layout.setVerticalSpacing(15)
        download_layout.setHorizontalSpacing(15)
        download_layout.setContentsMargins(20, 25, 20, 20)
        
        # 画质选择
        download_layout.addWidget(QLabel("首选画质:"), 0, 0)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["720p", "480p", "360p"])
        self.quality_combo.setCurrentText("720p")
        self.quality_combo.setFixedWidth(200)
        download_layout.addWidget(self.quality_combo, 0, 1)
        tips_label = QLabel("（登录解锁1080P/4K）")
        tips_label.setStyleSheet("color: #888;")
        download_layout.addWidget(tips_label, 0, 2)

        # 复选框选项 - 使用网格布局排列
        # 第一行复选框
        self.merge_check = QCheckBox("合并视频和音频")
        self.merge_check.setChecked(True)
        self.merge_check.setToolTip("推荐勾选，否则视频和音频将分离开")
        download_layout.addWidget(self.merge_check, 1, 0, 1, 3)
        
        self.delete_original_check = QCheckBox("合并后删除原始文件")
        self.delete_original_check.setChecked(True)
        download_layout.addWidget(self.delete_original_check, 2, 0, 1, 3)

        # 第二行复选框
        self.remove_watermark_check = QCheckBox("尝试去除水印 (实验性)")
        self.remove_watermark_check.setChecked(False)
        download_layout.addWidget(self.remove_watermark_check, 3, 0, 1, 3)
        
        # 额外下载选项
        extra_container = QHBoxLayout()
        self.download_danmaku_check = QCheckBox("下载弹幕")
        extra_container.addWidget(self.download_danmaku_check)
        
        self.download_comments_check = QCheckBox("下载评论")
        extra_container.addWidget(self.download_comments_check)
        extra_container.addStretch()
        
        download_layout.addLayout(extra_container, 4, 0, 1, 3)
        
        # 下载完成后操作
        download_layout.addWidget(QLabel("下载完成后:"), 5, 0)
        self.complete_action = QComboBox()
        self.complete_action.addItems(["无操作", "打开文件夹", "播放视频", "关闭程序"])
        self.complete_action.setCurrentIndex(1)
        self.complete_action.setFixedWidth(200)
        download_layout.addWidget(self.complete_action, 5, 1)
        
        main_layout.addWidget(download_group)
        
        # 底部保存按钮
        main_layout.addStretch()
        save_btn = QPushButton("保存设置")
        save_btn.setMinimumHeight(45)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                font-weight: bold; 
                font-size: 16px; 
                background-color: #fb7299; 
                color: white; 
                border-radius: 6px;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
            QPushButton:pressed {
                background-color: #e45c84;
            }
        """)
        save_btn.clicked.connect(self.save_settings)
        
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(save_btn)
        btn_container.addStretch()
        
        main_layout.addLayout(btn_container)
        main_layout.addSpacing(20)

    def show_update_dialog(self):
        """显示更新公告"""
        version = "v1.10"
        updates = (
            "1. 优化登录弹窗二维码显示，修复变形问题\n"
            "2. 移除登录界面冗余选项，简化登录流程\n"
            "3. 全新设计的设置界面，布局更清晰美观\n"
            "4. 优化视频下载取消逻辑，自动清理残留文件\n"
            "5. 代码结构重构与优化，提升软件稳定性"
        )
        dialog = UpdateDialog(version, updates, self)
        dialog.exec_()

    def set_style(self):
        """设置应用样式"""
        # 全局样式表
        style = """
        QMainWindow {
            background-color: #f5f5f5;
        }
        QTabWidget {
            background-color: #ffffff;
        }
        QTabWidget::pane {
            border: 1px solid #cccccc;
            background-color: #ffffff;
            border-radius: 4px;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            color: #333333;
            padding: 8px 15px;
            border: 1px solid #cccccc;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #fb7299;
            color: white;
            font-weight: bold;
        }
        QLabel {
            color: #333333;
        }
        QPushButton {
            background-color: #fb7299;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #fc8bab;
        }
        QPushButton:pressed {
            background-color: #e45c84;
        }
        QPushButton:disabled {
            background-color: #cccccc;
        }
        QLineEdit {
            border: 1px solid #cccccc;
            padding: 5px;
            border-radius: 3px;
        }
        QProgressBar {
            border: 1px solid #cccccc;
            border-radius: 3px;
            background-color: #f0f0f0;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #fb7299;
        }
        QTableWidget {
            border: 1px solid #cccccc;
            border-radius: 3px;
            alternate-background-color: #f9f9f9;
        }
        QTableWidget::item:selected {
            background-color: #f1d1dc;
            color: #333333;
        }
        QHeaderView::section {
            background-color: #e0e0e0;
            color: #333333;
            padding: 5px;
            border: 1px solid #cccccc;
        }
        QTextEdit {
            border: 1px solid #cccccc;
            border-radius: 3px;
        }
        """
        self.setStyleSheet(style)

    def log_to_console(self, message, level="info"):
        """向控制台日志添加消息"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        
        # 根据日志级别设置颜色
        color_map = {
            "info": "#d1d1d1",     # 浅灰 (普通信息)
            "warning": "#e6a23c",   # 橙黄
            "error": "#f56c6c",     # 红色
            "success": "#67c23a",   # 绿色
            "download": "#409eff",  # 蓝色
            "system": "#909399",    # 深灰
            "debug": "#9b59b6",     # 紫色
            "network": "#00ced1"    # 青色
        }
        
        # 简化的前缀
        prefix_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
            "download": "⬇️",
            "system": "🖥️",
            "debug": "🐞",
            "network": "🌐"
        }
        
        color = color_map.get(level, "#d1d1d1")
        prefix = prefix_map.get(level, "ℹ️")
        
        # 格式化日志消息 (时间 + 图标 + 内容)
        formatted_message = f'<span style="color:#888">[{timestamp}]</span> <span style="color:{color}">{prefix} {message}</span>'
        
        # 添加到控制台
        self.console_log.append(formatted_message)
        
        # 如果启用了自动滚动，滚动到底部
        if self.auto_scroll_check.isChecked():
            self.console_log.verticalScrollBar().setValue(
                self.console_log.verticalScrollBar().maximum()
            )
        
        # 同时记录到系统日志
        logger.info(message)

    def clear_console_log(self):
        """清除控制台日志"""
        self.console_log.clear()
        self.log_to_console("日志已清除", "system")
    
    def save_console_log(self):
        """保存控制台日志到文件"""
        # 获取当前时间作为文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        default_filename = f"bilibili_download_log_{timestamp}.txt"
        
        # 打开文件保存对话框
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存日志", default_filename, "文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if filename:
            try:
                # 获取纯文本内容
                plain_text = self.console_log.toPlainText()
                
                # 写入文件
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(plain_text)
                
                self.log_to_console(f"日志已保存到: {filename}", "success")
            except Exception as e:
                self.log_to_console(f"保存日志失败: {str(e)}", "error")
                QMessageBox.warning(self, "保存失败", f"保存日志失败: {str(e)}")

    def download_video(self, title=None):
        """下载视频"""
        bvid = self.bvid_input.text().strip()
        if not bvid:
            QMessageBox.warning(self, "警告", "请输入视频BV号")
            return
        
        # 检查BV号格式
        if not bvid.startswith("BV") or len(bvid) < 10:
            reply = QMessageBox.question(
                self, "BV号格式可能不正确", 
                f"输入的BV号 '{bvid}' 格式可能不正确，是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # 禁用下载按钮，启用取消按钮
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        # 如果没有提供标题，尝试从输入框的工具提示中获取
        if not title and self.bvid_input.toolTip():
            title = self.bvid_input.toolTip()
        
        # 重置UI状态
        self.download_status.setText("正在获取视频信息...")
        self.reset_progress_bars()
        
        # 记录下载开始时间
        self.download_start_time = time.time()
        
        # 添加日志
        self.log_to_console(f"开始下载视频: {bvid}", "download")
        if title:
            self.log_to_console(f"视频标题: {title}", "info")
        self.log_to_console("正在获取视频信息...", "info")
        
        # 获取是否合并的选项（从设置界面获取）
        should_merge = self.merge_check.isChecked()
        if not should_merge:
            self.log_to_console("已设置不合并视频和音频，将保留原始文件", "info")
            # 如果不合并，直接将合并进度条设置为100%
            self.merge_progress.setValue(100)
            self.set_progress_bar_style(self.merge_progress, "success")
        
        # 创建并启动工作线程
        params = {
            "bvid": bvid, 
            "should_merge": should_merge,
            "delete_original": self.delete_original_check.isChecked(),
            "remove_watermark": self.remove_watermark_check.isChecked(),
            "download_danmaku": self.download_danmaku_check.isChecked(),
            "download_comments": self.download_comments_check.isChecked(),
            "video_quality": self.quality_combo.currentText()
        }
        if title:
            params["title"] = title
            
        # 收集配置
        config = {
            'cookies': self.crawler.cookies,
            'use_proxy': False,
            'proxies': {},
            'data_dir': self.data_dir_input.text().strip(),
            'max_retries': self.retry_count.value()
        }
        
        self.current_thread = WorkerThread("download_video", params, config=config)
        self.current_thread.update_signal.connect(self.update_download_status)
        self.current_thread.finished_signal.connect(self.on_download_finished)
        self.current_thread.progress_signal.connect(self.update_download_progress)
        self.current_thread.start()

    def update_download_status(self, data):
        """更新下载状态"""
        message = data.get("message", "")
        self.download_status.setText(message)
        self.statusBar().showMessage(message)
        
        status = data.get("status", "")
        if status == "error":
            self.log_to_console(message, "error")
        elif status == "warning":
            self.log_to_console(message, "warning")
        elif status == "success":
            self.log_to_console(message, "success")
        else:
            self.log_to_console(message, "info")

    def update_download_progress(self, progress_type, current, total):
        """更新下载进度"""
        # 如果是合并进度，但用户选择不合并，则忽略
        if progress_type == "merge" and not self.merge_check.isChecked():
            return
            
        # 计算已用时间
        elapsed_time = time.time() - self.download_start_time
        
        # 特殊情况：total=1表示下载完成但无法确定总大小
        if total == 1:
            if progress_type == "video":
                self.video_progress.setValue(100)
            elif progress_type == "audio":
                self.audio_progress.setValue(100)
            elif progress_type == "merge":
                self.merge_progress.setValue(100)
            return
        
        if total > 0:
            progress = int(current * 100 / total)
            
            if progress_type == "video":
                self.video_progress.setValue(progress)
            elif progress_type == "audio":
                self.audio_progress.setValue(progress)
            elif progress_type == "merge":
                self.merge_progress.setValue(progress)
            
            # 格式化大小显示
            formatted_current = self.format_size(current)
            formatted_total = self.format_size(total)
            self.download_size_label.setText(f"大小: {formatted_current} / {formatted_total}")
            
            # 计算下载速度
            if elapsed_time > 0 and progress_type != "merge":
                speed = current / elapsed_time
                formatted_speed = self.format_size(speed) + "/s"
                self.download_speed_label.setText(f"速度: {formatted_speed}")
                
                if speed > 0:
                    remaining_bytes = total - current
                    eta_seconds = int(remaining_bytes / speed)
                    eta = self.format_time(eta_seconds)
                    self.download_eta_label.setText(f"剩余时间: {eta}")

    def on_download_finished(self, result):
        """下载完成后的处理"""
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        execution_time = result.get("execution_time", 0)
        formatted_time = self.format_time(int(execution_time)) if execution_time else "未知"
        
        data = result.get("data", {})
        bvid = self.bvid_input.text().strip()
        title = data.get("title", "未知视频")
        
        # 确保所有进度条都显示100%
        self.video_progress.setValue(100)
        self.audio_progress.setValue(100)
        self.merge_progress.setValue(100)
        
        if result["status"] == "success" or result["status"] == "warning":
            success_message = f"下载完成！用时: {formatted_time}"
            self.download_status.setText(success_message)
            self.log_to_console(success_message, "success")
            self.add_download_history(bvid, title, "成功")
            
            # 完成后操作
            try:
                complete_action = self.complete_action.currentIndex()
                if complete_action == 1:  # 打开文件夹
                    video_dir = data.get("download_dir")
                    if video_dir:
                        self.open_download_dir(video_dir)
                    else:
                        self.open_download_dir()
                elif complete_action == 2:  # 播放视频
                    merged_file = data.get("merged_file")
                    if merged_file and os.path.exists(merged_file):
                        os.startfile(merged_file)
                elif complete_action == 3:  # 关闭程序
                    self.close()
            except Exception as e:
                self.log_to_console(f"执行完成后操作出错: {str(e)}", "error")
                
        else:
            error_message = f"下载失败: {result.get('message', '未知错误')}"
            self.download_status.setText(error_message)
            self.log_to_console(error_message, "error")
            self.add_download_history(bvid, title, "失败")
            QMessageBox.critical(self, "下载失败", error_message)

    def cancel_download(self):
        """取消当前下载任务"""
        if hasattr(self, 'current_thread') and self.current_thread is not None:
            self.log_to_console("正在取消下载...", "warning")
            self.current_thread.stop()
            self.download_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.download_status.setText("下载已取消")
            self.log_to_console("下载已取消", "warning")

    def get_popular_videos(self):
        """获取热门视频"""
        self.popular_btn.setEnabled(False)
        self.popular_status.setText("正在获取热门视频...")
        
        pages = self.popular_pages.value()
        
        # 收集配置
        config = {
            'cookies': self.crawler.cookies,
            'use_proxy': False,
            'proxies': {},
            'data_dir': self.data_dir_input.text().strip(),
            'max_retries': self.retry_count.value()
        }

        self.current_thread = WorkerThread("popular_videos", {"pages": pages}, config=config)
        self.current_thread.update_signal.connect(self.update_popular_status)
        self.current_thread.finished_signal.connect(self.on_popular_finished)
        self.current_thread.start()
    
    def update_popular_status(self, data):
        self.popular_status.setText(data.get("message", ""))
        self.statusBar().showMessage(data.get("message", ""))
    
    def on_popular_finished(self, result):
        self.popular_btn.setEnabled(True)
        if result["status"] == "success":
            videos = result.get("data", [])
            self.popular_status.setText(result["message"])
            self.popular_table.setRowCount(len(videos))
            for i, video in enumerate(videos):
                self.popular_table.setItem(i, 0, QTableWidgetItem(video.get("title", "")))
                self.popular_table.setItem(i, 1, QTableWidgetItem(video.get("owner", {}).get("name", "")))
                self.popular_table.setItem(i, 2, QTableWidgetItem(str(video.get("stat", {}).get("view", 0))))
                self.popular_table.setItem(i, 3, QTableWidgetItem(str(video.get("stat", {}).get("like", 0))))
                self.popular_table.setItem(i, 4, QTableWidgetItem(video.get("bvid", "")))
        else:
            self.popular_status.setText(result["message"])
            QMessageBox.warning(self, "获取失败", result["message"])
    
    def on_popular_video_clicked(self, row, column):
        item_bvid = self.popular_table.item(row, 4)
        item_title = self.popular_table.item(row, 0)
        if item_bvid:
            bvid = item_bvid.text()
            title = item_title.text() if item_title else ""
            self.tabs.setCurrentIndex(0)
            self.bvid_input.setText(bvid)
            if title:
                self.bvid_input.setToolTip(title)
            self.download_video(title)

    def on_history_video_clicked(self, row, column):
        """历史记录视频双击处理"""
        item_bvid = self.history_list.item(row, 3)
        item_title = self.history_list.item(row, 0)
        if item_bvid:
            bvid = item_bvid.text()
            title = item_title.text() if item_title else ""
            self.tabs.setCurrentIndex(0)
            self.bvid_input.setText(bvid)
            if title:
                self.bvid_input.setToolTip(title)
            self.download_video(title)

    def open_login_window(self):
        """打开登录窗口"""
        self.login_window = BilibiliLoginWindow()
        self.login_window.show()
        self.login_window.finished_signal = lambda: self.check_login_status()
        self.account_status.setText("正在登录...")

    def check_login_status(self):
        """检查登录状态"""
        config_file = os.path.join(self.crawler.data_dir, "config", "login_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                cookies = config.get("cookies", {})
                if cookies and "SESSDATA" in cookies:
                    self.crawler.cookies = cookies
                    self.get_account_info(cookies)
                    self.account_stack.setCurrentIndex(1)
                    self.account_status.setText("已登录")
                    return
            except Exception as e:
                logger.error(f"读取登录配置失败: {e}")
        
        self.account_stack.setCurrentIndex(0)
        self.account_status.setText("未登录")

    def get_account_info(self, cookies):
        """获取账号信息"""
        self.account_thread = AccountInfoThread(self.crawler, cookies)
        self.account_thread.update_signal.connect(self.update_account_status)
        self.account_thread.finished_signal.connect(self.on_account_info_finished)
        self.account_thread.start()
    
    def update_account_status(self, data):
        self.account_status.setText(data.get("message", ""))
    
    def on_account_info_finished(self, result):
        if result["status"] == "success":
            user_info = result.get("data", {})
            self.account_name.setText(user_info.get("uname", "未知用户"))
            self.account_uid.setText(f"UID: {user_info.get('mid', '--')}")
            self.account_level.setText(f"等级: Lv{user_info.get('level_info', {}).get('current_level', 0)}")
            
            vip_type = user_info.get("vip", {}).get("type", 0)
            vip_status = user_info.get("vip", {}).get("status", 0)
            
            # status 1 为有效，0 为过期/无效
            if vip_type == 0 or vip_status != 1:
                self.account_vip.setText("会员状态: 非会员")
                self.vip_info.setText(
                    "当前权益：\n"
                    "• 支持下载 1080P 及以下清晰度视频\n"
                    "• 支持批量下载视频\n"
                    "• 支持导出视频弹幕和评论\n\n"
                    "开通大会员可解锁 4K/1080P+ 画质及专属视频下载"
                )
            elif vip_type == 1:
                self.account_vip.setText("会员状态: 大会员")
                self.account_vip.setStyleSheet("color: #FB7299;")
                self.vip_info.setText(
                    "尊贵的大会员权益：\n"
                    "• 支持下载 4K/1080P+ 及所有清晰度视频\n"
                    "• 支持下载大会员专属视频\n"
                    "• 支持批量下载视频\n"
                    "• 支持导出视频弹幕和评论"
                )
            elif vip_type == 2:
                self.account_vip.setText("会员状态: 年度大会员")
                self.account_vip.setStyleSheet("color: #FB7299; font-weight: bold;")
                self.vip_info.setText(
                    "尊贵的年度大会员权益：\n"
                    "• 支持下载 4K/1080P+ 及所有清晰度视频\n"
                    "• 支持下载大会员专属视频\n"
                    "• 支持批量下载视频\n"
                    "• 支持导出视频弹幕和评论"
                )
            
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
            
            self.account_status.setText("账号信息获取成功")
        else:
            self.account_status.setText(result["message"])
            # 登录失败或无效，重置画质选项
            self.update_quality_options(0, 0)

    def update_quality_options(self, vip_type, vip_status):
        """根据会员状态更新画质选项"""
        current_quality = self.quality_combo.currentText()
        self.quality_combo.clear()
        
        # 基础选项
        qualities = ["720p", "480p", "360p"]
        
        # 登录用户 (非会员)
        # 只要有cookies就算登录，不必严格依赖account_status文本
        is_logged_in = False
        if hasattr(self, 'crawler') and hasattr(self.crawler, 'cookies') and self.crawler.cookies:
            if "SESSDATA" in self.crawler.cookies:
                is_logged_in = True
        
        # 也可以检查account_stack的index
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
            
        self.quality_combo.addItems(qualities)
        
        # 尝试恢复之前的选择，如果不存在则默认选择第一个（最高画质）
        index = self.quality_combo.findText(current_quality)
        if index >= 0:
            self.quality_combo.setCurrentIndex(index)
        else:
            self.quality_combo.setCurrentIndex(0)

    def update_favorites_list(self, favorites):
        """更新收藏夹列表显示"""
        self.favorites_list.setRowCount(len(favorites))
        for i, fav in enumerate(favorites):
            title = fav.get("title", "")
            media_count = fav.get("media_count", 0)
            # 时间戳转换，如果API返回的是ctime
            ctime = fav.get("ctime", 0)
            # 尝试其他可能的字段
            if not ctime:
                 ctime = fav.get("mtime", 0)
            
            if ctime:
                create_time = time.strftime("%Y-%m-%d", time.localtime(ctime))
            else:
                # 如果没有时间，显示ID
                fid = fav.get("id", 0)
                create_time = f"ID: {fid}"
            
            self.favorites_list.setItem(i, 0, QTableWidgetItem(title))
            self.favorites_list.setItem(i, 1, QTableWidgetItem(create_time))
            self.favorites_list.setItem(i, 2, QTableWidgetItem(str(media_count)))

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
                
            # bvid usually in history_business_network -> bvid ? 
            # structure varies. Check 'bvid' or 'history' -> 'bvid'
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
            self.log_to_console(f"刷新账号信息失败: {e}", "error")
    
    def logout_account(self):
        reply = QMessageBox.question(self, "确认退出", "确定要退出当前账号吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.crawler.cookies = None
            config_file = os.path.join(self.crawler.data_dir, "config", "login_config.json")
            if os.path.exists(config_file):
                try:
                    os.remove(config_file)
                except:
                    pass
            self.account_stack.setCurrentIndex(0)
            self.account_status.setText("已退出登录")

    def browse_data_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择数据存储目录", os.path.abspath(self.crawler.data_dir))
        if dir_path:
            self.data_dir_input.setText(dir_path)

    def save_settings(self):
        new_data_dir = self.data_dir_input.text().strip()
        if new_data_dir and os.path.exists(new_data_dir):
            self.crawler.data_dir = new_data_dir
            self.crawler.download_dir = os.path.join(new_data_dir, 'downloads')
            if not os.path.exists(self.crawler.download_dir):
                os.makedirs(self.crawler.download_dir)
        
        # 移除代理设置的保存逻辑
        self.crawler.use_proxy = False
        self.crawler.proxies = {}
        
        self.save_config_to_file()
        QMessageBox.information(self, "设置保存", "设置已保存")

    def save_config_to_file(self):
        config = {
            'data_dir': self.data_dir_input.text().strip(),
            'max_retries': self.retry_count.value(),
            'merge_video': self.merge_check.isChecked(),
            'delete_original': self.delete_original_check.isChecked(),
            'remove_watermark': self.remove_watermark_check.isChecked(),
            'download_danmaku': self.download_danmaku_check.isChecked(),
            'download_comments': self.download_comments_check.isChecked(),
            'complete_action': self.complete_action.currentIndex(),
            'video_quality': self.quality_combo.currentText()
        }
        try:
            config_dir = os.path.join(self.crawler.data_dir, 'config')
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            config_path = os.path.join(config_dir, 'settings.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"配置已保存到 {config_path}")
        except Exception as e:
            logger.error(f"保存配置文件时出错: {e}")

    def load_config_from_file(self):
        config_path = os.path.join(self.crawler.data_dir, 'config', 'settings.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                if 'data_dir' in config and os.path.exists(config['data_dir']):
                    self.data_dir_input.setText(config['data_dir'])
                    self.crawler.data_dir = config['data_dir']
                    self.crawler.download_dir = os.path.join(config['data_dir'], 'downloads')
                if 'max_retries' in config:
                    self.retry_count.setValue(config['max_retries'])
                if 'merge_video' in config:
                    self.merge_check.setChecked(config['merge_video'])
                if 'delete_original' in config:
                    self.delete_original_check.setChecked(config['delete_original'])
                if 'remove_watermark' in config:
                    self.remove_watermark_check.setChecked(config['remove_watermark'])
                if 'download_danmaku' in config:
                    self.download_danmaku_check.setChecked(config['download_danmaku'])
                if 'download_comments' in config:
                    self.download_comments_check.setChecked(config['download_comments'])
                if 'complete_action' in config:
                    self.complete_action.setCurrentIndex(config['complete_action'])
                if 'video_quality' in config:
                    self.quality_combo.setCurrentText(config['video_quality'])
            except Exception as e:
                logger.error(f"加载配置文件时出错: {e}")

    def open_download_dir(self, specific_dir=None):
        try:
            if specific_dir and os.path.exists(specific_dir):
                os.startfile(specific_dir)
            else:
                download_dir = os.path.abspath(self.crawler.download_dir)
                if os.path.exists(download_dir):
                    os.startfile(download_dir)
                else:
                    QMessageBox.warning(self, "错误", "下载目录不存在，无法打开")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开下载目录时出错: {str(e)}")

    def show_download_history(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("下载历史记录")
        dialog.setMinimumSize(600, 400)
        layout = QVBoxLayout(dialog)
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["标题", "BV号", "下载时间", "状态"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(table)
        for i, item in enumerate(self.download_history):
            table.insertRow(i)
            table.setItem(i, 0, QTableWidgetItem(item.get("title", "")))
            table.setItem(i, 1, QTableWidgetItem(item.get("bvid", "")))
            table.setItem(i, 2, QTableWidgetItem(item.get("time", "")))
            status_item = QTableWidgetItem(item.get("status", ""))
            if item.get("status") == "成功":
                status_item.setForeground(Qt.green)
            elif item.get("status") == "失败":
                status_item.setForeground(Qt.red)
            table.setItem(i, 3, status_item)
        
        buttons_layout = QHBoxLayout()
        redownload_btn = QPushButton("重新下载")
        redownload_btn.clicked.connect(lambda: self.redownload_from_history(table))
        buttons_layout.addWidget(redownload_btn)
        clear_btn = QPushButton("清空历史")
        clear_btn.clicked.connect(lambda: self.clear_download_history(table))
        buttons_layout.addWidget(clear_btn)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        buttons_layout.addWidget(close_btn)
        layout.addLayout(buttons_layout)
        dialog.exec_()

    def redownload_from_history(self, table):
        selected_rows = table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要重新下载的视频")
            return
        row = selected_rows[0].row()
        bvid_item = table.item(row, 1)
        if bvid_item and bvid_item.text():
            bvid = bvid_item.text()
            self.bvid_input.setText(bvid)
            self.tabs.setCurrentIndex(0)
            self.download_video()

    def clear_download_history(self, table):
        reply = QMessageBox.question(self, "确认清空", "确定要清空所有下载历史记录吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.download_history = []
            self.save_download_history()
            table.setRowCount(0)

    def load_download_history(self):
        history_file = os.path.join(self.crawler.data_dir, "download_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_download_history(self):
        history_file = os.path.join(self.crawler.data_dir, "download_history.json")
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.download_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存下载历史记录失败: {e}")

    def add_download_history(self, bvid, title, status):
        history_item = {
            "bvid": bvid,
            "title": title,
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "status": status
        }
        self.download_history.insert(0, history_item)
        if len(self.download_history) > 100:
            self.download_history = self.download_history[:100]
        self.save_download_history()

    def reset_progress_bars(self):
        self.video_progress.setMaximum(100)
        self.video_progress.setValue(0)
        self.set_progress_bar_style(self.video_progress, "normal")
        
        self.audio_progress.setMaximum(100)
        self.audio_progress.setValue(0)
        self.set_progress_bar_style(self.audio_progress, "normal")
        
        self.merge_progress.setMaximum(100)
        self.merge_progress.setValue(0)
        self.set_progress_bar_style(self.merge_progress, "normal")
        
        self.download_status.setText("就绪")
        self.download_speed_label.setText("速度: 0 B/s")
        self.download_eta_label.setText("剩余时间: --:--")
        self.download_size_label.setText("大小: 0 B / 0 B")

    def set_progress_bar_style(self, progress_bar, style="normal"):
        color = "#1890ff" if style == "normal" else "#52c41a" if style == "success" else "#ff4d4f"
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: #f0f0f0;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)
    
    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.1f} MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.2f} GB"

    def format_time(self, seconds):
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds//60}分{seconds%60}秒"
        else:
            return f"{seconds//3600}时{(seconds%3600)//60}分{seconds%60}秒"
