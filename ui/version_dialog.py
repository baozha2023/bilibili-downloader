import sys
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QWidget,
                             QAbstractItemView)
from PyQt5.QtCore import Qt, QTimer
from ui.message_box import BilibiliMessageBox
from core.version_manager import VersionManager

class VersionDialog(QDialog):
    """
    版本管理对话框
    """
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.version_manager = VersionManager(main_window)
        self.setWindowTitle("版本管理")
        self.setMinimumSize(800, 500)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Version Management Group
        version_group = QGroupBox("版本列表")
        version_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                color: #fb7299;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        version_layout = QVBoxLayout(version_group)
        version_layout.setContentsMargins(20, 30, 20, 20)
        version_layout.setSpacing(10)
        
        # Current Version Info
        curr_layout = QHBoxLayout()
        v_label = QLabel("当前版本:")
        v_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        curr_layout.addWidget(v_label)
        
        # Get version from window title as requested
        title_ver = self.main_window.windowTitle().split(' ')[-1] if ' ' in self.main_window.windowTitle() else "未知"
        self.current_ver_display = QLabel(f"{title_ver} (Git: 检测中...)")
        self.current_ver_display.setStyleSheet("font-size: 16px; color: #fb7299; font-weight: bold;")
        curr_layout.addWidget(self.current_ver_display)
        curr_layout.addStretch()
        version_layout.addLayout(curr_layout)
        
        # Version Table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["版本号", "更新内容"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #f0f5ff;
                selection-color: #333;
            }
            QHeaderView::section {
                background-color: #f6f7f8;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ddd;
                font-weight: bold;
                color: #666;
            }
        """)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        version_layout.addWidget(self.table)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        
        self.switch_btn = QPushButton("切换至选中版本")
        self.switch_btn.setCursor(Qt.PointingHandCursor)
        self.switch_btn.setStyleSheet("""
            QPushButton {
                background-color: #00a1d6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #00b5e5;
            }
            QPushButton:pressed {
                background-color: #0090cc;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.switch_btn.clicked.connect(self.switch_version)
        self.switch_btn.setEnabled(False)
        btn_layout.addWidget(self.switch_btn)
        
        btn_layout.addStretch()
        
        # Close Button
        close_btn = QPushButton("关闭")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #666;
                padding: 10px 30px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 16px;
                border: 1px solid #ddd;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                color: #333;
            }
        """)
        btn_layout.addWidget(close_btn)
        
        version_layout.addLayout(btn_layout)
        layout.addWidget(version_group)
        
        # Load version info asynchronously
        QTimer.singleShot(100, self.load_version_info)

    def load_version_info(self):
        current_git = self.version_manager.get_current_version()
        title_ver = self.main_window.windowTitle().split(' ')[-1] if ' ' in self.main_window.windowTitle() else "未知"
        self.current_ver_display.setText(f"{title_ver} (Git: {current_git})")
        
        self.table.setRowCount(0)
        self.switch_btn.setEnabled(False)
        self.switch_btn.setText("加载中...")
        
        QTimer.singleShot(100, self._fetch_versions)
        
    def _fetch_versions(self):
        versions = self.version_manager.get_versions()
        self.table.setRowCount(len(versions))
        
        for i, ver in enumerate(versions):
            tag = ver.get('tag', '')
            # date = ver.get('date', '') # Not shown in 2-column layout
            msg = ver.get('message', '')
            
            # Clean up message (remove newlines for display)
            short_msg = msg.replace('\n', ' ').strip()
            if len(short_msg) > 100:
                short_msg = short_msg[:97] + "..."
            
            item_tag = QTableWidgetItem(tag)
            item_tag.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, item_tag)
            
            # item_date = QTableWidgetItem(date)
            # item_date.setTextAlignment(Qt.AlignCenter)
            # self.table.setItem(i, 1, item_date)
            
            item_msg = QTableWidgetItem(short_msg)
            item_msg.setToolTip(msg) # Full message in tooltip
            self.table.setItem(i, 1, item_msg)
            
        self.switch_btn.setText("切换至选中版本")
        self.on_selection_changed() # Update button state
            
    def on_selection_changed(self):
        selected = self.table.selectedItems()
        self.switch_btn.setEnabled(len(selected) > 0)
            
    def switch_version(self):
        row = self.table.currentRow()
        if row < 0:
            return
            
        tag = self.table.item(row, 0).text()
            
        reply = BilibiliMessageBox.question(
            self, "确认切换", 
            f"确定要切换到版本 {tag} 吗？\n\n1. 这将强制覆盖本地代码\n2. 将清空配置文件\n3. 程序将需要重启"
        )
        
        if reply == QDialog.Accepted:
            self.switch_btn.setEnabled(False)
            self.switch_btn.setText("切换中...")
            QTimer.singleShot(100, lambda: self._do_switch(tag))
            
    def _do_switch(self, tag):
        success, msg = self.version_manager.switch_version(tag)
        self.switch_btn.setEnabled(True)
        self.switch_btn.setText("切换至选中版本")
        
        if success:
            BilibiliMessageBox.information(self, "更新准备就绪", f"{msg}\n\n点击确定后程序将自动退出并开始更新。")
            # 退出程序以便批处理脚本可以替换文件
            sys.exit(0)
        else:
            BilibiliMessageBox.error(self, "切换失败", msg)
