import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QComboBox, QGroupBox, QListWidget)
from PyQt5.QtCore import Qt
from ui.widgets.netdisk_login_dialog import NetdiskLoginDialog
from core.netdisk.baidu import BaiduNetdisk
from core.netdisk.quark import QuarkNetdisk
from ui.message_box import BilibiliMessageBox

logger = logging.getLogger('bilibili_desktop')

class NetdiskTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.netdisks = {
            "百度网盘": BaiduNetdisk(),
            "夸克网盘": QuarkNetdisk()
        }
        self.current_netdisk = self.netdisks["百度网盘"]
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Controls
        ctrl_layout = QHBoxLayout()
        
        self.disk_combo = QComboBox()
        self.disk_combo.addItems(self.netdisks.keys())
        self.disk_combo.currentTextChanged.connect(self.on_disk_changed)
        self.disk_combo.setStyleSheet("padding: 5px; font-size: 14px;")
        
        ctrl_layout.addWidget(QLabel("选择网盘:"))
        ctrl_layout.addWidget(self.disk_combo)
        
        self.login_btn = QPushButton("扫码登录")
        self.login_btn.clicked.connect(self.show_login_dialog)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #fb7299;
                color: white;
                border-radius: 4px;
                padding: 6px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
        """)
        ctrl_layout.addWidget(self.login_btn)
        
        self.user_label = QLabel("未登录")
        self.user_label.setStyleSheet("color: #666; margin-left: 10px;")
        ctrl_layout.addWidget(self.user_label)
        
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)
        
        # Content (FileList)
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("border: 1px solid #ddd; border-radius: 5px; background-color: white;")
        layout.addWidget(self.file_list, 1)
        
        self.status_label = QLabel("提示：登录后可查看文件列表。目前仅支持查看根目录。")
        self.status_label.setStyleSheet("color: #999;")
        layout.addWidget(self.status_label)
        
    def on_disk_changed(self, name):
        self.current_netdisk = self.netdisks[name]
        self.user_label.setText("未登录")
        self.file_list.clear()
        
    def show_login_dialog(self):
        name = self.disk_combo.currentText()
        if name == "百度网盘":
            url = "https://pan.baidu.com/"
            pattern = "pan.baidu.com/disk"
        else:
            url = "https://pan.quark.cn/"
            pattern = "pan.quark.cn"
        
        dialog = NetdiskLoginDialog(name, url, pattern, self)
        dialog.login_success.connect(self.on_login_success)
        dialog.exec_()
        
    def on_login_success(self, cookies):
        self.current_netdisk.set_cookies(cookies)
        info = self.current_netdisk.get_user_info()
        if info:
            self.user_label.setText(f"已登录: {info.get('name', '未知用户')}")
        else:
            self.user_label.setText("已登录 (获取用户信息失败)")
            
        self.refresh_files()
        
    def refresh_files(self):
        self.file_list.clear()
        files = self.current_netdisk.list_files("/")
        if not files:
            self.file_list.addItem("暂无文件或获取失败")
            return
            
        for f in files:
            # Baidu uses 'server_filename', Quark uses 'file_name'
            name = f.get('server_filename') or f.get('filename') or f.get('file_name')
            if name:
                self.file_list.addItem(name)
