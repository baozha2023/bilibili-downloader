from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QMenu, QAction)
from PyQt5.QtCore import Qt
from ui.workers import WorkerThread
from ui.widgets.video_player_window import VideoPlayerWindow

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
        
        page_label = QLabel("页数:")
        page_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        control_layout.addWidget(page_label)
        
        self.popular_pages = QSpinBox()
        self.popular_pages.setMinimum(1)
        self.popular_pages.setMaximum(10)
        self.popular_pages.setValue(3)
        self.popular_pages.setFixedWidth(80)
        self.popular_pages.setStyleSheet("font-size: 20px; padding: 5px;")
        control_layout.addWidget(self.popular_pages)
        
        self.popular_btn = QPushButton("获取热门视频")
        self.popular_btn.clicked.connect(self.get_popular_videos)
        self.popular_btn.setCursor(Qt.PointingHandCursor)
        self.popular_btn.setStyleSheet("""
            QPushButton {
                background-color: #fb7299;
                color: white;
                border-radius: 5px;
                font-size: 20px;
                font-weight: bold;
                padding: 8px 20px;
                border: none;
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
        """)
        control_layout.addWidget(self.popular_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 视频列表
        self.popular_table = QTableWidget(0, 5)
        self.popular_table.setHorizontalHeaderLabels(["标题", "UP主", "播放量", "点赞", "BV号"])
        self.popular_table.setStyleSheet("""
            QTableWidget {
                font-size: 20px;
            }
            QHeaderView::section {
                font-size: 20px;
                padding: 5px;
            }
        """)
        # 设置第一列自动拉伸
        header = self.popular_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.popular_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.popular_table.cellDoubleClicked.connect(self.on_popular_video_clicked)
        self.popular_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.popular_table.customContextMenuRequested.connect(self.show_context_menu)
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

    def show_context_menu(self, pos):
        item = self.popular_table.itemAt(pos)
        if not item:
            return
            
        row = item.row()
        bvid_item = self.popular_table.item(row, 4)
        title_item = self.popular_table.item(row, 0)
        
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
        download_action.triggered.connect(lambda: self.on_popular_video_clicked(row, 0))
        menu.addAction(download_action)
        
        watch_action = QAction("📺 实时观看", self)
        watch_action.triggered.connect(lambda: self.watch_live(bvid, title))
        menu.addAction(watch_action)
        
        menu.exec_(self.popular_table.viewport().mapToGlobal(pos))
        
    def watch_live(self, bvid, title):
        self.player_window = VideoPlayerWindow(bvid, title)
        self.player_window.show()
