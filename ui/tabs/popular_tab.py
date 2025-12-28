from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QMenu, QAction, QApplication)
from PyQt5.QtCore import Qt, QUrl, QEvent
from PyQt5.QtGui import QCursor, QPixmap
from ui.workers import WorkerThread
from ui.widgets.video_player_window import VideoPlayerWindow
from ui.widgets.loading_bar import LoadingBar
from ui.styles import UIStyles
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from ui.utils.image_loader import ImageLoader

class PopularTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.crawler = main_window.crawler
        self.init_ui()
        self.image_loader = ImageLoader(self)
        
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
        self.popular_btn.setStyleSheet(UIStyles.POPULAR_BTN)
        control_layout.addWidget(self.popular_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 加载进度条
        self.loading_bar = LoadingBar(self)
        layout.addWidget(self.loading_bar)
        
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
        # 启用鼠标跟踪，用于显示悬停封面
        self.popular_table.setMouseTracking(True)
        self.popular_table.cellEntered.connect(self.on_cell_entered)
        self.popular_table.installEventFilter(self)
        layout.addWidget(self.popular_table)

        # 封面预览Label (悬浮显示)
        self.cover_label = QLabel(self)
        self.cover_label.setWindowFlags(Qt.ToolTip)
        self.cover_label.setStyleSheet("border: 2px solid white; border-radius: 4px;")
        self.cover_label.setScaledContents(True)
        self.cover_label.resize(320, 200)
        self.cover_label.hide()

    def on_cell_entered(self, row, column):
        """鼠标移入单元格显示封面"""
        if row < 0:
            self.cover_label.hide()
            return
            
        # 获取BV号item，从中获取封面URL
        bvid_item = self.popular_table.item(row, 4)
        if bvid_item:
            cover_url = bvid_item.data(Qt.UserRole)
            if cover_url:
                self.show_cover_preview(cover_url)
                
    def show_cover_preview(self, url):
        self.image_loader.load_image(url, self.display_cover)
            
    # def on_cover_downloaded(self, reply): ... (Removed)
        
    def display_cover(self, pixmap):
        # 自适应缩放逻辑
        max_width = 320
        max_height = 240 # 稍微增加高度限制
        
        # 获取原始尺寸
        orig_width = pixmap.width()
        orig_height = pixmap.height()
        
        if orig_width == 0 or orig_height == 0:
            return

        # 计算宽高比
        aspect_ratio = orig_width / orig_height
        
        # 根据宽高比计算目标尺寸
        if aspect_ratio > 1: # 横屏
            new_width = min(orig_width, max_width)
            new_height = int(new_width / aspect_ratio)
        else: # 竖屏
            new_height = min(orig_height, max_height)
            new_width = int(new_height * aspect_ratio)
            
        # 缩放图片
        scaled_pixmap = pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.cover_label.resize(new_width, new_height)
        self.cover_label.setPixmap(scaled_pixmap)
        
        # 显示在鼠标附近
        cursor_pos = QCursor.pos()
        self.cover_label.move(cursor_pos.x() + 20, cursor_pos.y() + 20)
        self.cover_label.show()
        
    def leaveEvent(self, event):
        self.cover_label.hide()
        super().leaveEvent(event)

    def eventFilter(self, source, event):
        if source == self.popular_table and event.type() == QEvent.Leave:
            self.cover_label.hide()
        return super().eventFilter(source, event)

    def get_popular_videos(self):
        """获取热门视频"""
        self.popular_btn.setEnabled(False)
        self.loading_bar.start()
        self.main_window.log_to_console("正在获取热门视频...", "info")
        
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
        self.main_window.statusBar().showMessage(data.get("message", ""))
    
    def on_popular_finished(self, result):
        self.popular_btn.setEnabled(True)
        self.loading_bar.stop()
        if result["status"] == "success":
            videos = result.get("data", [])
            self.main_window.log_to_console(f"成功获取 {len(videos)} 个热门视频", "success")
            self.popular_table.setRowCount(len(videos))
            for i, video in enumerate(videos):
                title = video.get("title", "")
                upper = video.get("owner", {}).get("name", "")
                play = video.get("stat", {}).get("view", 0)
                like = video.get("stat", {}).get("like", 0)
                bvid = video.get("bvid", "")
                cover = video.get("pic", "")
                
                title_item = QTableWidgetItem(title)
                title_item.setToolTip(title)
                
                self.popular_table.setItem(i, 0, title_item)
                self.popular_table.setItem(i, 1, QTableWidgetItem(upper))
                self.popular_table.setItem(i, 2, QTableWidgetItem(str(play)))
                self.popular_table.setItem(i, 3, QTableWidgetItem(str(like)))
                
                bvid_item = QTableWidgetItem(bvid)
                bvid_item.setData(Qt.UserRole, cover)
                self.popular_table.setItem(i, 4, bvid_item)
        else:
            self.main_window.log_to_console(f"获取热门视频失败: {result['message']}", "error")
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

        copy_bv_action = QAction("📋 复制BV号", self)
        copy_bv_action.triggered.connect(lambda: QApplication.clipboard().setText(bvid))
        menu.addAction(copy_bv_action)
        
        analyze_action = QAction("📊 视频分析", self)
        analyze_action.triggered.connect(lambda: self.analyze_video(bvid))
        menu.addAction(analyze_action)
        
        menu.exec_(self.popular_table.viewport().mapToGlobal(pos))
        
    def analyze_video(self, bvid):
        # Switch to Analysis Tab (Index 3)
        self.main_window.tabs.setCurrentIndex(3)
        analysis_tab = self.main_window.analysis_tab
        analysis_tab.bvid_input.setText(bvid)
        analysis_tab.start_analysis()
        
    def watch_live(self, bvid, title):
        cookies = self.crawler.cookies
        self.player_window = VideoPlayerWindow(bvid, title, cookies)
        self.player_window.show()
