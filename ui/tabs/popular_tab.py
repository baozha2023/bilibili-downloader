from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from ui.workers import WorkerThread

class PopularTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.crawler = main_window.crawler
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
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

    def get_popular_videos(self):
        """获取热门视频"""
        self.popular_btn.setEnabled(False)
        self.popular_status.setText("正在获取热门视频...")
        
        pages = self.popular_pages.value()
        
        # 收集配置
        # 需要访问 SettingsTab
        settings_tab = self.main_window.settings_tab
        config = {
            'cookies': self.crawler.cookies,
            'use_proxy': False,
            'proxies': {},
            'data_dir': settings_tab.data_dir_input.text().strip(),
            'max_retries': settings_tab.retry_count.value()
        }

        self.current_thread = WorkerThread("popular_videos", {"pages": pages}, config=config)
        self.current_thread.update_signal.connect(self.update_popular_status)
        self.current_thread.finished_signal.connect(self.on_popular_finished)
        self.current_thread.start()
    
    def update_popular_status(self, data):
        self.popular_status.setText(data.get("message", ""))
        self.main_window.statusBar().showMessage(data.get("message", ""))
    
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
            # Switch to download tab and set BV
            self.main_window.tabs.setCurrentIndex(0)
            download_tab = self.main_window.download_tab
            download_tab.bvid_input.setText(bvid)
            if title:
                download_tab.bvid_input.setToolTip(title)
            download_tab.download_video(title)
