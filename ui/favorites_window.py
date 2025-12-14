from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QSpinBox, QMenu, QAction, QComboBox, QFileDialog, QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl, QEvent
from PyQt5.QtGui import QCursor, QPixmap
from ui.message_box import BilibiliMessageBox
from ui.widgets.video_player_window import VideoPlayerWindow
import csv
import logging

logger = logging.getLogger('bilibili_desktop')

class FavoriteWorker(QThread):
    finished_signal = pyqtSignal(list, str) # videos, error_message

    def __init__(self, crawler, media_id, page):
        super().__init__()
        self.crawler = crawler
        self.media_id = media_id
        self.page = page

    def run(self):
        try:
            # Use api directly
            videos = self.crawler.api.get_favorite_resources(self.media_id, self.page)
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
        
        self.export_btn = QPushButton("导出本页")
        self.export_btn.clicked.connect(self.export_current_page)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #409eff;
                color: white;
                border-radius: 5px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
        """)
        control_layout.addWidget(self.export_btn)
        
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
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        # Enable mouse tracking for hover
        self.table.setMouseTracking(True)
        self.table.cellEntered.connect(self.on_cell_entered)
        self.table.installEventFilter(self)
        layout.addWidget(self.table)

        # Status
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        # Tip
        tip = QLabel("双击视频可跳转至下载页面并自动开始下载")
        tip.setStyleSheet("color: #888; font-size: 14px;")
        tip.setAlignment(Qt.AlignRight)
        layout.addWidget(tip)

        # 封面预览Label
        self.cover_label = QLabel(self)
        self.cover_label.setWindowFlags(Qt.ToolTip)
        self.cover_label.setStyleSheet("border: 2px solid white; border-radius: 4px;")
        self.cover_label.setScaledContents(True)
        self.cover_label.resize(320, 200)
        self.cover_label.hide()

    def on_cell_entered(self, row, column):
        if row < 0:
            self.cover_label.hide()
            return
        bvid_item = self.table.item(row, 4)
        if bvid_item:
            cover_url = bvid_item.data(Qt.UserRole)
            if cover_url:
                self.show_cover_preview(cover_url)

    def show_cover_preview(self, url):
        from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
        
        if not hasattr(self, 'network_manager'):
            self.network_manager = QNetworkAccessManager(self)
            self.network_manager.finished.connect(self.on_cover_downloaded)
            
        if not hasattr(self, 'cover_cache'):
            self.cover_cache = {}
            
        if url in self.cover_cache:
            self.display_cover(self.cover_cache[url])
        else:
            self.network_manager.get(QNetworkRequest(QUrl(url)))
            
    def on_cover_downloaded(self, reply):
        url = reply.url().toString()
        if reply.error():
            return
        data = reply.readAll()
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self.cover_cache[url] = pixmap
        self.display_cover(pixmap)
        
    def display_cover(self, pixmap):
        self.cover_label.setPixmap(pixmap)
        cursor_pos = QCursor.pos()
        self.cover_label.move(cursor_pos.x() + 20, cursor_pos.y() + 20)
        self.cover_label.show()
        
    def leaveEvent(self, event):
        self.cover_label.hide()
        super().leaveEvent(event)
        
    def eventFilter(self, source, event):
        if source == self.table and event.type() == QEvent.Leave:
            self.cover_label.hide()
        return super().eventFilter(source, event)
        
    def export_current_page(self):
        """导出当前页数据到Excel (CSV)"""
        if not hasattr(self, 'current_videos') or not self.current_videos:
            BilibiliMessageBox.warning(self, "提示", "当前没有数据可导出")
            return
            
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_name = f"favorites_page_{self.page}_{timestamp}.xlsx"
        
        path, _ = QFileDialog.getSaveFileName(self, "导出数据", default_name, "Excel Files (*.xlsx);;CSV Files (*.csv)")
        
        if not path:
            return
            
        try:
            # 准备数据：导出所有字段
            data = []
            
            # 获取所有可能的键作为表头
            # 为了保证顺序，我们先放已知的常用字段，然后放其他的
            known_headers = ["title", "upper", "duration", "play", "bvid", "intro", "pubtime", "fav_time"]
            all_keys = set()
            for v in self.current_videos:
                all_keys.update(v.keys())
                # 展平嵌套字典 (simple flattening for commonly used nested fields)
                if 'upper' in v and isinstance(v['upper'], dict):
                    all_keys.update([f"upper_{k}" for k in v['upper'].keys()])
                if 'cnt_info' in v and isinstance(v['cnt_info'], dict):
                    all_keys.update([f"cnt_info_{k}" for k in v['cnt_info'].keys()])

            # 构建最终表头
            headers = []
            # 1. 常用字段 (重命名为中文)
            header_map = {
                "title": "标题",
                "upper_name": "UP主",
                "duration": "时长(秒)",
                "cnt_info_play": "播放量",
                "bvid": "BV号",
                "intro": "简介",
                "pubtime": "发布时间",
                "fav_time": "收藏时间"
            }
            
            # 添加常用字段
            for k in ["title", "upper_name", "duration", "cnt_info_play", "bvid", "intro", "pubtime", "fav_time"]:
                headers.append(header_map.get(k, k))
            
            # 添加其他字段 (不翻译)
            processed_keys = set(["title", "upper", "duration", "cnt_info", "bvid", "intro", "pubtime", "fav_time"])
            
            extra_keys = sorted([k for k in all_keys if k not in processed_keys and not k.startswith("upper_") and not k.startswith("cnt_info_")])
            headers.extend(extra_keys)
            
            data.append(headers)
            
            for v in self.current_videos:
                row_data = []
                # 常用字段
                row_data.append(v.get("title", ""))
                row_data.append(v.get("upper", {}).get("name", "") if isinstance(v.get("upper"), dict) else "")
                row_data.append(v.get("duration", ""))
                row_data.append(v.get("cnt_info", {}).get("play", "") if isinstance(v.get("cnt_info"), dict) else "")
                row_data.append(v.get("bvid", ""))
                row_data.append(v.get("intro", ""))
                row_data.append(v.get("pubtime", ""))
                row_data.append(v.get("fav_time", ""))
                
                # 其他字段
                for k in extra_keys:
                    val = v.get(k, "")
                    if isinstance(val, (dict, list)):
                        import json
                        val = json.dumps(val, ensure_ascii=False)
                    row_data.append(str(val))
                data.append(row_data)
                
            if path.endswith('.xlsx'):
                import openpyxl
                wb = openpyxl.Workbook()
                ws = wb.active
                for r_idx, row in enumerate(data, 1):
                    for c_idx, val in enumerate(row, 1):
                        # 处理非法字符
                        val_str = str(val)
                        # 移除非法字符 (Excel 不支持的控制字符)
                        val_str = "".join(ch for ch in val_str if (0x20 <= ord(ch) <= 0xD7FF) or (0xE000 <= ord(ch) <= 0xFFFD) or ch in "\t\r\n")
                        ws.cell(row=r_idx, column=c_idx, value=val_str)
                wb.save(path)
            else:
                # Fallback to CSV
                with open(path, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(data)
                    
            BilibiliMessageBox.information(self, "成功", f"数据已导出到: {path}")
            
        except Exception as e:
            logger.error(f"导出失败: {e}")
            BilibiliMessageBox.error(self, "错误", f"导出失败: {str(e)}")

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
            
        self.current_videos = videos # 保存数据用于导出
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
            
            bvid_item = QTableWidgetItem(bvid)
            # Add cover url to UserRole for tooltip
            cover = v.get("cover", "")
            bvid_item.setData(Qt.UserRole, cover)
            self.table.setItem(i, 4, bvid_item)

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

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
            
        row = item.row()
        bvid_item = self.table.item(row, 4)
        title_item = self.table.item(row, 0)
        
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
        download_action.triggered.connect(lambda: self.on_video_double_clicked(row, 0))
        menu.addAction(download_action)
        
        watch_action = QAction("📺 实时观看", self)
        watch_action.triggered.connect(lambda: self.watch_live(bvid, title))
        menu.addAction(watch_action)

        copy_bv_action = QAction("📋 复制BV号", self)
        copy_bv_action.triggered.connect(lambda: QApplication.clipboard().setText(bvid))
        menu.addAction(copy_bv_action)
        
        menu.exec_(self.table.viewport().mapToGlobal(pos))
        
    def watch_live(self, bvid, title):
        cookies = self.crawler.cookies
        self.player_window = VideoPlayerWindow(bvid, title, cookies)
        self.player_window.show()
