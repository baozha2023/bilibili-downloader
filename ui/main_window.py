import sys
import os
import json
import time
import logging
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTabWidget, QGroupBox, 
                             QTextEdit, QCheckBox, QFileDialog, QDialog, 
                             QTableWidget, QHeaderView, QTableWidgetItem, QMessageBox)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer, Qt

from core.crawler import BilibiliCrawler
from ui.update_dialog import UpdateDialog
from ui.tabs.download_tab import DownloadTab
from ui.tabs.popular_tab import PopularTab
from ui.tabs.account_tab import AccountTab
from ui.tabs.settings_tab import SettingsTab

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
        
        self.init_ui()
        self.set_style()
        
        # 显示更新公告
        QTimer.singleShot(500, self.show_update_dialog)

    def closeEvent(self, event):
        """关闭窗口事件"""
        event.accept()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("哔哩哔哩视频下载器 v2.2")
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
        
        # 标签页
        self.tabs = QTabWidget()
        # 添加过渡动画效果
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: #ffffff;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                color: #333333;
                padding: 10px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #fb7299;
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #ffb3cf;
            }
        """)
        main_layout.addWidget(self.tabs)
        
        # 创建各个标签页
        # 注意：DownloadTab和PopularTab可能需要访问SettingsTab获取配置
        # 所以先创建SettingsTab
        self.settings_tab = SettingsTab(self)
        self.download_tab = DownloadTab(self)
        self.popular_tab = PopularTab(self)
        self.account_tab = AccountTab(self)
        
        self.tabs.addTab(self.download_tab, "视频下载")
        self.tabs.addTab(self.popular_tab, "热门视频")
        self.tabs.addTab(self.account_tab, "我的账号")
        self.tabs.addTab(self.settings_tab, "设置")
        
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
        
        # 欢迎信息
        self.log_to_console("欢迎使用哔哩哔哩视频下载器 v2.0！", "info")
        self.log_to_console(f"数据存储目录: {self.crawler.data_dir}", "system")
        
        # 检查ffmpeg
        if self.crawler.ffmpeg_available:
            self.log_to_console(f"ffmpeg检测成功: {self.crawler.ffmpeg_path}", "system")
        else:
            self.log_to_console("未检测到ffmpeg，视频合并功能将不可用", "warning")

    def show_update_dialog(self):
        """显示更新公告"""
        version = "v2.2"
        updates = (
            "1. 新增评论和弹幕下载进度显示，下载过程更清晰\n"
            "2. 登录弹窗新增“保存账号信息”选项，支持自动登录\n"
            "3. 优化登录按钮交互体验，鼠标悬停样式更自然\n"
            "4. 升级去水印算法，更智能识别并去除水印\n"
            "5. UI界面全面美化，增加过渡动画，贴近B站风格\n"
            "6. 优化项目结构，提升运行稳定性"
        )
        dialog = UpdateDialog(version, updates, self)
        dialog.exec_()

    def set_style(self):
        """设置应用样式"""
        # 全局样式表
        style = """
        QMainWindow {
            background-color: #f6f7f8;
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
        }
        QTabWidget {
            background-color: #ffffff;
            border: none;
        }
        QTabWidget::pane {
            border: 1px solid #e7e7e7;
            background-color: #ffffff;
            border-radius: 6px;
            top: -1px; 
        }
        QTabBar::tab {
            background-color: #f6f7f8;
            color: #61666d;
            padding: 10px 25px;
            border: 1px solid #e7e7e7;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 4px;
            font-size: 14px;
            min-width: 80px;
        }
        QTabBar::tab:selected {
            background-color: #ffffff;
            color: #fb7299;
            font-weight: bold;
            border-bottom: 1px solid #ffffff;
        }
        QTabBar::tab:hover:!selected {
            background-color: #ffffff;
            color: #fb7299;
        }
        QLabel {
            color: #18191c;
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
        }
        QPushButton {
            background-color: #fb7299;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #fc8bab;
        }
        QPushButton:pressed {
            background-color: #e45c84;
        }
        QPushButton:disabled {
            background-color: #e7e7e7;
            color: #999999;
        }
        QLineEdit {
            border: 1px solid #e7e7e7;
            padding: 8px;
            border-radius: 4px;
            background-color: #ffffff;
            selection-background-color: #fb7299;
            font-size: 13px;
        }
        QLineEdit:focus {
            border: 1px solid #fb7299;
        }
        QProgressBar {
            border: none;
            border-radius: 4px;
            background-color: #e7e7e7;
            text-align: center;
            font-size: 12px;
            color: #333333;
        }
        QProgressBar::chunk {
            background-color: #fb7299;
            border-radius: 4px;
        }
        QTableWidget {
            border: 1px solid #e7e7e7;
            border-radius: 6px;
            background-color: #ffffff;
            selection-background-color: #fef0f5;
            selection-color: #fb7299;
            gridline-color: #f0f0f0;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QHeaderView::section {
            background-color: #f6f7f8;
            color: #61666d;
            padding: 8px;
            border: none;
            border-bottom: 1px solid #e7e7e7;
            border-right: 1px solid #e7e7e7;
            font-weight: bold;
        }
        QGroupBox {
            border: 1px solid #e7e7e7;
            border-radius: 6px;
            margin-top: 20px;
            font-weight: bold;
            padding-top: 15px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 10px;
            color: #333333;
        }
        QCheckBox {
            spacing: 5px;
            color: #61666d;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #cccccc;
            border-radius: 3px;
            background-color: white;
        }
        QCheckBox::indicator:unchecked:hover {
            border-color: #fb7299;
        }
        QCheckBox::indicator:checked {
            background-color: #fb7299;
            border-color: #fb7299;
            image: url(resource/checkbox_checked.png); /* 如果没有图片会显示纯色 */
        }
        QComboBox {
            border: 1px solid #e7e7e7;
            border-radius: 4px;
            padding: 5px 10px;
            min-width: 6em;
        }
        QComboBox:hover {
            border-color: #c0c0c0;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 0px;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
        }
        QTextEdit {
            border: 1px solid #e7e7e7;
            border-radius: 4px;
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
            self.tabs.setCurrentIndex(0)
            self.download_tab.bvid_input.setText(bvid)
            self.download_tab.download_video()

    def clear_download_history(self, table):
        reply = QMessageBox.question(self, "确认清空", "确定要清空所有下载历史记录吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.download_history = []
            self.save_download_history()
            table.setRowCount(0)

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
