from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from ui.message_box import BilibiliMessageBox

class FavoriteWorker(QThread):
    finished_signal = pyqtSignal(list, str) # videos, error_message

    def __init__(self, crawler, media_id, page):
        super().__init__()
        self.crawler = crawler
        self.media_id = media_id
        self.page = page

    def run(self):
        try:
            videos = self.crawler.get_favorite_resources(self.media_id, self.page)
            self.finished_signal.emit(videos, "")
        except Exception as e:
            self.finished_signal.emit([], str(e))

class FavoritesWindow(QDialog):
    def __init__(self, main_window, media_id, title):
        super().__init__(main_window)
        self.main_window = main_window
        self.crawler = main_window.crawler
        self.media_id = media_id
        self.page = 1
        
        self.setWindowTitle(f"收藏夹内容 - {title}")
        self.setMinimumSize(900, 600)
        
        self.init_ui()
        self.load_videos()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Controls
        control_layout = QHBoxLayout()
        
        page_label = QLabel("页数:")
        page_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        control_layout.addWidget(page_label)
        
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(100)
        self.page_spin.setValue(1)
        self.page_spin.setFixedWidth(80)
        self.page_spin.setStyleSheet("font-size: 16px; padding: 5px;")
        control_layout.addWidget(self.page_spin)
        
        self.refresh_btn = QPushButton("刷新/跳转")
        self.refresh_btn.clicked.connect(self.on_refresh_clicked)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #fb7299;
                color: white;
                border-radius: 5px;
                padding: 8px 20px;
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
        control_layout.addWidget(self.refresh_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["标题", "UP主", "时长", "播放量", "BV号"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget { font-size: 16px; }
            QHeaderView::section { font-size: 16px; padding: 6px; font-weight: bold; background-color: #f0f0f0; }
        """)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.cellDoubleClicked.connect(self.on_video_double_clicked)
        layout.addWidget(self.table)
        
        # Status
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        # Tip
        tip = QLabel("双击视频可跳转至下载页面并自动开始下载")
        tip.setStyleSheet("color: #888; font-size: 14px;")
        tip.setAlignment(Qt.AlignRight)
        layout.addWidget(tip)

    def on_refresh_clicked(self):
        self.page = self.page_spin.value()
        self.load_videos()

    def load_videos(self):
        self.status_label.setText(f"正在获取第 {self.page} 页数据...")
        self.refresh_btn.setEnabled(False)
        self.table.setRowCount(0)
        
        self.worker = FavoriteWorker(self.crawler, self.media_id, self.page)
        self.worker.finished_signal.connect(self.on_data_loaded)
        self.worker.start()

    def on_data_loaded(self, videos, error):
        self.refresh_btn.setEnabled(True)
        if error:
            self.status_label.setText(f"获取失败: {error}")
            BilibiliMessageBox.warning(self, "错误", f"获取数据失败: {error}")
            return
            
        self.status_label.setText(f"成功获取 {len(videos)} 个视频")
        self.table.setRowCount(len(videos))
        
        for i, v in enumerate(videos):
            # Extract data
            title = v.get("title", "")
            upper = v.get("upper", {}).get("name", "")
            duration = self.format_duration(v.get("duration", 0))
            cnt_info = v.get("cnt_info", {})
            play = cnt_info.get("play", 0)
            bvid = v.get("bvid", "")
            
            # Tooltips
            title_item = QTableWidgetItem(title)
            title_item.setToolTip(title)
            
            self.table.setItem(i, 0, title_item)
            self.table.setItem(i, 1, QTableWidgetItem(upper))
            self.table.setItem(i, 2, QTableWidgetItem(duration))
            self.table.setItem(i, 3, QTableWidgetItem(str(play)))
            self.table.setItem(i, 4, QTableWidgetItem(bvid))

    def format_duration(self, seconds):
        try:
            seconds = int(seconds)
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            if h > 0:
                return f"{h}:{m:02d}:{s:02d}"
            return f"{m:02d}:{s:02d}"
        except:
            return "--:--"

    def on_video_double_clicked(self, row, col):
        bvid_item = self.table.item(row, 4)
        title_item = self.table.item(row, 0)
        if bvid_item:
            bvid = bvid_item.text()
            title = title_item.text() if title_item else ""
            
            # Call main window to switch tab
            self.main_window.tabs.setCurrentIndex(0)
            download_tab = self.main_window.download_tab
            download_tab.bvid_input.setText(bvid)
            if title:
                download_tab.bvid_input.setToolTip(title)
            
            # Jump to download
            download_tab.download_video(title)
