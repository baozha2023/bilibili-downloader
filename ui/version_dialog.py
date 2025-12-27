import sys
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QComboBox, QGroupBox, QWidget)
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
        self.setMinimumSize(500, 300)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Version Management Group
        version_group = QGroupBox("版本切换与更新")
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
        version_layout.setSpacing(20)
        
        # Current Version Row
        curr_layout = QHBoxLayout()
        v_label = QLabel("当前版本:")
        v_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        curr_layout.addWidget(v_label)
        
        self.current_ver_display = QLabel("检测中...")
        self.current_ver_display.setStyleSheet("font-size: 16px; color: #fb7299; font-weight: bold;")
        curr_layout.addWidget(self.current_ver_display)
        curr_layout.addStretch()
        version_layout.addLayout(curr_layout)
        
        # Switch Version Row
        switch_layout = QHBoxLayout()
        s_label = QLabel("切换版本:")
        s_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        switch_layout.addWidget(s_label)
        
        self.version_combo = QComboBox()
        self.version_combo.setMinimumWidth(200)
        self.version_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        switch_layout.addWidget(self.version_combo)
        switch_layout.addStretch()
        version_layout.addLayout(switch_layout)
        
        # Action Button
        self.switch_btn = QPushButton("切换/更新")
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
        version_layout.addWidget(self.switch_btn)
        
        layout.addWidget(version_group)
        
        layout.addStretch()
        
        # Close Button
        close_btn = QPushButton("关闭")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #fb7299;
                color: white;
                padding: 10px 40px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
            QPushButton:pressed {
                background-color: #e45c84;
            }
        """)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        # Load version info asynchronously
        QTimer.singleShot(100, self.load_version_info)

    def load_version_info(self):
        current = self.version_manager.get_current_version()
        self.current_ver_display.setText(current)
        
        self.version_combo.clear()
        self.version_combo.addItem("加载中...")
        self.switch_btn.setEnabled(False)
        
        QTimer.singleShot(100, self._fetch_versions)
        
    def _fetch_versions(self):
        versions = self.version_manager.get_versions()
        self.version_combo.clear()
        if versions:
            self.version_combo.addItems(versions)
            self.switch_btn.setEnabled(True)
        else:
            self.version_combo.addItem("无可用版本")
            self.switch_btn.setEnabled(False)
            
    def switch_version(self):
        tag = self.version_combo.currentText()
        if not tag or tag == "无可用版本":
            return
            
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
        self.switch_btn.setText("切换/更新")
        
        if success:
            BilibiliMessageBox.information(self, "切换成功", f"{msg}\n\n请手动重启程序以应用更改。")
            self.load_version_info()
        else:
            BilibiliMessageBox.error(self, "切换失败", msg)
