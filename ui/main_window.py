import sys
import os
import json
import time
import logging
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTabWidget, QGroupBox, 
                             QTextEdit, QCheckBox, QFileDialog, QDialog, 
                             QTableWidget, QHeaderView, QTableWidgetItem, QMessageBox, QAction, QMenu)
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import QTimer, Qt, QEvent

from core.crawler import BilibiliCrawler
from core.config import ConfigManager, APP_VERSION
from ui.update_dialog import UpdateDialog
from ui.tabs.download_tab import DownloadTab
from ui.tabs.bangumi_tab import BangumiTab
from ui.tabs.popular_tab import PopularTab
from ui.tabs.account_tab import AccountTab
from ui.tabs.settings_tab import SettingsTab
from ui.tabs.video_edit import VideoEditTab
from ui.tabs.analysis import AnalysisTab
from ui.tabs.user_search_tab import UserSearchTab
from ui.widgets.floating_window import FloatingWindow
from ui.qt_logger import QtLogHandler

from ui.styles import UIStyles
from core.history_manager import HistoryManager

# 配置日志 / Configure logging
logger = logging.getLogger('bilibili_desktop')

class BilibiliDesktop(QMainWindow):
    """
    哔哩哔哩桌面端主窗口
    Bilibili Desktop Main Window
    """
    
    def __init__(self):
        super().__init__()
        self.crawler = BilibiliCrawler()
        self.config_manager = ConfigManager()
        self.history_manager = HistoryManager(self.crawler.data_dir)
        self.download_history = self.history_manager.get_history()
        
        self.floating_window = FloatingWindow()
        
        self.init_ui()
        self.set_style()
        
        # 显示更新公告 / Show update dialog
        QTimer.singleShot(500, self.show_update_dialog)

    def closeEvent(self, event):
        """
        关闭窗口事件
        Close window event
        """
        # 移除 QtLogHandler 以避免关闭时出错
        root_logger = logging.getLogger()
        if hasattr(self, 'qt_log_handler') and self.qt_log_handler in root_logger.handlers:
            root_logger.removeHandler(self.qt_log_handler)
        
        event.accept()
        
    def resource_path(self, relative_path):
        """
        获取资源文件的绝对路径
        Get absolute path of resource file
        """
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller打包后的路径
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def init_ui(self):
        """
        初始化UI
        Initialize UI
        """
        self.setWindowTitle(f"bilibiliDownloader {APP_VERSION}")
        self.setMinimumSize(1100, 900)
        
        # 设置应用图标 / Set application icon
        icon_path = self.resource_path("resource/icon.ico")
        logo_jpg = self.resource_path("resource/logo.jpg")
        logo_png = self.resource_path("resource/logo.png")
        
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        elif os.path.exists(logo_jpg):
            self.setWindowIcon(QIcon(logo_jpg))
        elif os.path.exists(logo_png):
            self.setWindowIcon(QIcon(logo_png))
        
        # 主布局 / Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10) # 默认边距
        
        # ---------------------------------------------------------------
        # 1. 初始化控制台日志 / Initialize console log
        # ---------------------------------------------------------------
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout(log_group)
        self.console_log = QTextEdit()
        self.console_log.setReadOnly(True)
        self.console_log.setMaximumHeight(150)
        self.console_log.setStyleSheet("background-color: #1e1e1e; color: #f0f0f0; font-family: Consolas, Monospace; font-size: 20px;")
        log_layout.addWidget(self.console_log)
        
        # 日志控制按钮 / Log control buttons
        log_ctrl_layout = QHBoxLayout()
        
        self.auto_scroll_check = QCheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        log_ctrl_layout.addWidget(self.auto_scroll_check)
        
        log_ctrl_layout.addStretch()
        
        clear_log_btn = QPushButton("清除日志")
        clear_log_btn.setCursor(Qt.PointingHandCursor)
        clear_log_btn.setStyleSheet("background-color: #666; padding: 3px 8px;")
        clear_log_btn.clicked.connect(self.clear_console_log)
        log_ctrl_layout.addWidget(clear_log_btn)
        
        save_log_btn = QPushButton("保存日志")
        save_log_btn.setCursor(Qt.PointingHandCursor)
        save_log_btn.setStyleSheet("background-color: #666; padding: 3px 8px;")
        save_log_btn.clicked.connect(self.save_console_log)
        log_ctrl_layout.addWidget(save_log_btn)
        
        log_layout.addLayout(log_ctrl_layout)
        
        # ---------------------------------------------------------------
        # 1.1 初始化日志系统 / Initialize logging system
        # ---------------------------------------------------------------
        # 配置根日志，使其包含控制台输出和UI输出
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # 清除现有的处理器
        root_logger.handlers = []
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Qt UI 处理器
        self.qt_log_handler = QtLogHandler()
        # 这里只保留消息内容，因为颜色和图标会在 log_to_console 中添加
        qt_formatter = logging.Formatter('%(message)s') 
        self.qt_log_handler.setFormatter(qt_formatter)
        self.qt_log_handler.log_signal.connect(self.log_to_console)
        root_logger.addHandler(self.qt_log_handler)
        
        # ---------------------------------------------------------------
        # 2. 标签页 / Tabs
        # ---------------------------------------------------------------
        self.tabs = QTabWidget()
        # 优化Tab样式
        self.tabs.setStyleSheet(UIStyles.TAB_WIDGET)
        
        # 允许拖拽和右键菜单
        self.tabs.setMovable(True)
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.show_tab_context_menu)
        self.tabs.tabBar().tabMoved.connect(self.on_tab_moved)
        
        main_layout.addWidget(self.tabs, 1) # Set stretch factor to 1
        
        # 创建各个标签页
        # 注意：DownloadTab和PopularTab可能需要访问SettingsTab获取配置
        # 所以先创建SettingsTab
        self.settings_tab = SettingsTab(self)
        self.download_tab = DownloadTab(self)
        self.bangumi_tab = BangumiTab(self)
        self.popular_tab = PopularTab(self)
        self.account_tab = AccountTab(self)
        self.video_edit_tab = VideoEditTab(self)
        self.analysis_tab = AnalysisTab(self)
        self.user_search_tab = UserSearchTab(self)
        
        # 定义所有可用标签页
        self.all_tabs = {
            "视频下载": self.download_tab,
            "番剧下载": self.bangumi_tab,
            "热门视频": self.popular_tab,
            "用户查询": self.user_search_tab,
            "视频分析": self.analysis_tab,
            "我的账号": self.account_tab,
            "视频编辑": self.video_edit_tab,
            "设置": self.settings_tab
        }
        
        # 从配置加载标签页顺序和可见性
        self.load_tabs()
        
        # 连接设置变更信号
        self.settings_tab.merge_check.stateChanged.connect(self.download_tab.update_progress_visibility)
        self.settings_tab.download_danmaku_check.stateChanged.connect(self.download_tab.update_progress_visibility)
        self.settings_tab.download_comments_check.stateChanged.connect(self.download_tab.update_progress_visibility)
        
        # 底部状态栏
        self.statusBar().showMessage("就绪")
        
        # 添加日志组件到主布局 (在标签页下方)
        main_layout.addWidget(log_group)
        
        # 欢迎信息 (通过logger输出)
        logger.info(f"欢迎使用bilibiliDownloader {APP_VERSION}！")
        logger.info(f"数据存储目录: {self.crawler.data_dir}")
        
        # 检查ffmpeg
        if self.crawler.ffmpeg_available:
            logger.info(f"ffmpeg检测成功: {self.crawler.ffmpeg_path}")
        else:
            logger.warning("未检测到ffmpeg，视频合并功能将不可用")

    def show_update_dialog(self):
        """显示更新公告 / Show update announcement"""
        version = APP_VERSION
        updates = (
            "1. 重构：重写版本管理逻辑，自动检测本地Python环境。\n"
            "2. 优化：无本地Python环境时不显示版本管理按钮，避免误操作。\n"
            "3. 优化：版本切换优先使用用户本地Python环境进行编译。\n"
            "4. 优化：自动检测并安装缺失的依赖库，确保编译成功率。\n"
            "5. 优化：代码结构优化，提升稳定性。\n"
        )
        dialog = UpdateDialog(version, updates, self)
        dialog.exec_()

    def set_style(self):
        """设置应用样式 / Set application style"""
        self.setStyleSheet(UIStyles.get_main_style())

    def log_to_console(self, message, level="info"):
        """向控制台日志添加消息 / Log message to console"""
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

    def clear_console_log(self):
        """清除控制台日志 / Clear console log"""
        self.console_log.clear()
        self.log_to_console("日志已清除", "system")
    
    def save_console_log(self):
        """保存控制台日志到文件 / Save console log to file"""
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

    def add_download_history(self, bvid, title, status):
        """添加下载历史 / Add download history"""
        self.history_manager.add_history(bvid, title, status)
        self.download_history = self.history_manager.get_history()

    def show_download_history(self):
        """显示下载历史对话框 / Show download history dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("下载历史记录")
        dialog.setMinimumSize(900, 600)
        layout = QVBoxLayout(dialog)
        
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["标题", "BV号", "下载时间", "状态"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 优化表格样式
        table.setStyleSheet("""
            QTableWidget {
                font-size: 16px;
            }
            QHeaderView::section {
                font-size: 16px;
                padding: 8px;
                font-weight: bold;
                background-color: #f0f0f0;
            }
        """)
        table.verticalHeader().setDefaultSectionSize(45)
        
        layout.addWidget(table)
        
        for i, item in enumerate(self.download_history):
            table.insertRow(i)
            
            title_item = QTableWidgetItem(item.get("title", ""))
            title_item.setToolTip(item.get("title", ""))
            table.setItem(i, 0, title_item)
            
            table.setItem(i, 1, QTableWidgetItem(item.get("bvid", "")))
            table.setItem(i, 2, QTableWidgetItem(item.get("time", "")))
            
            status_item = QTableWidgetItem(item.get("status", ""))
            if item.get("status") == "成功":
                status_item.setForeground(Qt.green)
            elif item.get("status") == "失败":
                status_item.setForeground(Qt.red)
            elif item.get("status") == "已取消":
                status_item.setForeground(QColor("#e6a23c")) # Orange
            status_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 3, status_item)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)
        
        redownload_btn = QPushButton("重新下载")
        redownload_btn.clicked.connect(lambda: self.redownload_from_history(table))
        redownload_btn.setCursor(Qt.PointingHandCursor)
        redownload_btn.setStyleSheet(UIStyles.POPULAR_BTN)
        buttons_layout.addWidget(redownload_btn)
        
        clear_btn = QPushButton("清空历史")
        clear_btn.clicked.connect(lambda: self.clear_download_history(table))
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(UIStyles.POPULAR_BTN)
        buttons_layout.addWidget(clear_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px; 
                padding: 10px 25px;
                background-color: #f6f7f8;
                color: #666;
                border-radius: 5px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        dialog.exec_()

    def redownload_from_history(self, table):
        """从历史重新下载 / Redownload from history"""
        selected_rows = table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要重新下载的视频")
            return
        row = selected_rows[0].row()
        bvid_item = table.item(row, 1)
        if bvid_item and bvid_item.text():
            bvid = bvid_item.text()
            self.tabs.setCurrentIndex(0)
            self.download_tab.bvid_input.setText(bvid)
            self.download_tab.download_video()

    def clear_download_history(self, table):
        """清空历史 / Clear history"""
        reply = QMessageBox.question(self, "确认清空", "确定要清空所有下载历史记录吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.history_manager.clear_history()
            self.download_history = []
            table.setRowCount(0)

    def open_download_dir(self, specific_dir=None):
        """打开下载目录 / Open download directory"""
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

    def load_tabs(self):
        """加载Tab顺序和可见性 / Load tabs order and visibility"""
        tab_order = self.config_manager.get('tab_order', [])
        tab_visibility = self.config_manager.get('tab_visibility', {})
        
        # 默认顺序
        default_order = ["视频下载", "番剧下载", "热门视频", "视频分析", "我的账号", "视频编辑", "设置"]
        
        # 如果没有保存的顺序，使用默认顺序
        if not tab_order:
            tab_order = default_order[:]
            
        # 确保所有Tab都在order中 (处理新版本增加Tab的情况)
        for name in default_order:
            if name not in tab_order:
                tab_order.append(name)
                
        # 添加Tab
        self.tabs.clear()
        for name in tab_order:
            if name in self.all_tabs:
                # 默认显示，除非明确设置为隐藏
                if tab_visibility.get(name, True):
                    self.tabs.addTab(self.all_tabs[name], name)
                    
    def save_tab_order(self):
        """保存Tab顺序 / Save tab order"""
        current_order = []
        for i in range(self.tabs.count()):
            current_order.append(self.tabs.tabText(i))
            
        # 添加隐藏的Tab到列表末尾，保持它们在列表中的存在
        all_names = self.all_tabs.keys()
        for name in all_names:
            if name not in current_order:
                current_order.append(name)
                
        self.config_manager.set('tab_order', current_order)
        self.config_manager.save()
        
    def on_tab_moved(self, from_index, to_index):
        """Tab移动事件 / Tab moved event"""
        self.save_tab_order()
        
    def show_tab_context_menu(self, pos):
        """显示Tab右键菜单 / Show tab context menu"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #eee;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 14px;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
                color: #fb7299;
            }
            QMenu::separator {
                height: 1px;
                background: #eee;
                margin: 5px 0;
            }
        """)
        
        # 获取当前点击的Tab索引
        tab_index = self.tabs.tabBar().tabAt(pos)
        
        # 如果点击了某个Tab，提供隐藏选项
        if tab_index != -1:
            tab_name = self.tabs.tabText(tab_index)
            # 防止隐藏最后一个Tab
            if self.tabs.count() > 1:
                hide_action = QAction(f"隐藏 \"{tab_name}\"", self)
                hide_action.triggered.connect(lambda: self.toggle_tab_visibility(tab_name, False))
                menu.addAction(hide_action)
                menu.addSeparator()
            
        # 显示"恢复显示"子菜单
        restore_menu = QMenu("恢复显示", self)
        tab_visibility = self.config_manager.get('tab_visibility', {})
        
        hidden_tabs = []
        for name in self.all_tabs.keys():
            if not tab_visibility.get(name, True):
                hidden_tabs.append(name)
                
        if hidden_tabs:
            for name in hidden_tabs:
                action = QAction(name, self)
                action.triggered.connect(lambda checked, n=name: self.toggle_tab_visibility(n, True))
                restore_menu.addAction(action)
        else:
            no_hidden_action = QAction("无隐藏标签页", self)
            no_hidden_action.setEnabled(False)
            restore_menu.addAction(no_hidden_action)
            
        menu.addMenu(restore_menu)
        
        menu.exec_(self.tabs.mapToGlobal(pos))
        
    def toggle_tab_visibility(self, tab_name, visible):
        """切换Tab可见性 / Toggle tab visibility"""
        tab_visibility = self.config_manager.get('tab_visibility', {})
        tab_visibility[tab_name] = visible
        self.config_manager.set('tab_visibility', tab_visibility)
        self.config_manager.save()
        
        # 重新加载Tabs以反映更改
        # 为了保持当前选中的Tab，记录下当前Tab的名称
        current_index = self.tabs.currentIndex()
        current_tab_name = ""
        if current_index != -1:
            current_tab_name = self.tabs.tabText(current_index)
            
        self.load_tabs()
        
        # 尝试恢复选中状态
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == current_tab_name:
                self.tabs.setCurrentIndex(i)
                break
