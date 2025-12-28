import sys
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QWidget,
                             QAbstractItemView, QComboBox)
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
        self.current_versions = [] # Store raw version data
        self.setWindowTitle("版本管理")
        self.setMinimumSize(900, 600)
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
        version_layout.setSpacing(15)
        
        # Top Bar: Current Version & Source Selection
        top_bar = QHBoxLayout()
        
        # Current Version
        title_ver = self.main_window.windowTitle().split(' ')[-1] if ' ' in self.main_window.windowTitle() else "未知"
        curr_ver_label = QLabel(f"当前版本: {title_ver}")
        curr_ver_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        top_bar.addWidget(curr_ver_label)
        
        top_bar.addStretch()
        
        # Source Selection
        source_label = QLabel("代码源:")
        source_label.setStyleSheet("font-size: 14px; color: #555;")
        top_bar.addWidget(source_label)
        
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Gitee (需本地Python编译)", "GitHub (推荐, 免Python)"])
        self.source_combo.setStyleSheet("""
            QComboBox {
                padding: 5px 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                min-width: 200px;
            }
        """)
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        top_bar.addWidget(self.source_combo)
        
        version_layout.addLayout(top_bar)
        
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
        
        # Initial Load
        QTimer.singleShot(100, self.load_version_info)

    def load_version_info(self):
        self._fetch_versions()
        
    def on_source_changed(self):
        self._fetch_versions()
        
    def _fetch_versions(self):
        self.table.setRowCount(0)
        self.switch_btn.setEnabled(False)
        self.switch_btn.setText("正在获取版本列表...")
        
        # Determine source
        source_idx = self.source_combo.currentIndex()
        source = VersionManager.SOURCE_GITEE if source_idx == 0 else VersionManager.SOURCE_GITHUB
        
        QTimer.singleShot(100, lambda: self._do_fetch(source))
        
    def _do_fetch(self, source):
        self.current_versions = self.version_manager.get_versions(source)
        self.table.setRowCount(len(self.current_versions))
        
        for i, ver in enumerate(self.current_versions):
            tag = ver.get('tag', '')
            date = ver.get('date', '').replace('T', ' ').replace('Z', '')
            msg = ver.get('message', '')
            
            # Clean up message
            short_msg = msg.replace('\n', ' ').strip()
            if len(short_msg) > 100:
                short_msg = short_msg[:97] + "..."
            
            item_tag = QTableWidgetItem(tag)
            item_tag.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, item_tag)
            
            item_msg = QTableWidgetItem(short_msg)
            item_msg.setToolTip(msg)
            self.table.setItem(i, 1, item_msg)
            
        self.switch_btn.setText("切换至选中版本")
        self.on_selection_changed()
            
    def on_selection_changed(self):
        selected = self.table.selectedItems()
        self.switch_btn.setEnabled(len(selected) > 0)
            
    def switch_version(self):
        row = self.table.currentRow()
        if row < 0:
            return
            
        tag = self.table.item(row, 0).text()
        source_idx = self.source_combo.currentIndex()
        source_name = "Gitee" if source_idx == 0 else "GitHub"
        
        # Check Python for Gitee
        if source_idx == 0 and not self.version_manager.check_python_available():
            BilibiliMessageBox.error(self, "环境检查失败", 
                "使用 Gitee 源需要本地安装 Python 环境进行编译。\n"
                "检测到您的电脑未安装 Python，请切换至 GitHub 源下载编译好的版本。")
            return
            
        reply = BilibiliMessageBox.question(
            self, "确认切换", 
            f"确定要从 {source_name} 下载并切换到版本 {tag} 吗？\n\n"
            "1. 程序将自动下载并覆盖当前版本\n"
            "2. 配置文件可能被重置\n"
            "3. 程序将自动重启"
        )
        
        if reply == QDialog.Accepted:
            self.switch_btn.setEnabled(False)
            self.switch_btn.setText("正在准备更新...")
            
            source = VersionManager.SOURCE_GITEE if source_idx == 0 else VersionManager.SOURCE_GITHUB
            # Find version object for assets (needed for GitHub)
            assets = None
            if source == VersionManager.SOURCE_GITHUB:
                 for v in self.current_versions:
                     if v['tag'] == tag:
                         assets = v.get('assets')
                         break
            
            QTimer.singleShot(100, lambda: self._do_switch(tag, source, assets))
            
    def _do_switch(self, tag, source, assets):
        success, msg = self.version_manager.switch_version(tag, source, assets)
        
        if success:
            sys.exit(0)
        else:
            self.switch_btn.setEnabled(True)
            self.switch_btn.setText("切换至选中版本")
            BilibiliMessageBox.error(self, "更新失败", msg)
