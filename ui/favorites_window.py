from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QSpinBox, QMenu, QAction, QComboBox, QFileDialog, QApplication,QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl, QEvent
from PyQt5.QtGui import QCursor, QPixmap
from ui.message_box import BilibiliMessageBox
from ui.widgets.video_player_window import VideoPlayerWindow
from ui.utils.image_loader import ImageLoader
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
            videos = self.crawler.api.get_favorite_resources(self.media_id, self.page)
            self.finished_signal.emit(videos, "")
        except Exception as e:
            self.finished_signal.emit([], str(e))

class FavoriteAllWorker(QThread):
    finished_signal = pyqtSignal(list, str) # bvid_list, error_message
    progress_signal = pyqtSignal(str)

    def __init__(self, crawler, media_id):
        super().__init__()
        self.crawler = crawler
        self.media_id = media_id

    def run(self):
        try:
            all_bvids = []
            page = 1
            max_pages = 100 # Safety limit (2000 videos)
            
            while page <= max_pages:
                if self.isInterruptionRequested():
                    break
                    
                self.progress_signal.emit(f"正在获取第 {page} 页...")
                videos = self.crawler.api.get_favorite_resources(self.media_id, page)
                
                if not videos:
                    break
                    
                for v in videos:
                    if 'bvid' in v:
                        all_bvids.append(v['bvid'])
                
                if len(videos) < 20: # Last page
                    break
                    
                page += 1
                QThread.msleep(200) # Nice to API
            
            self.finished_signal.emit(all_bvids, "")
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
        
        self.batch_btn = QPushButton("批量下载")
        self.batch_btn.clicked.connect(self.on_batch_download_clicked)
        self.batch_btn.setCursor(Qt.PointingHandCursor)
        self.batch_btn.setStyleSheet("""
            QPushButton {
                background-color: #67c23a;
                color: white;
                border-radius: 5px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #85ce61;
            }
        """)
        control_layout.addWidget(self.batch_btn)
        
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
        if not hasattr(self, 'image_loader'):
            self.image_loader = ImageLoader(self)
            
        self.image_loader.load_image(url, self.display_cover)
            
    # def on_cover_downloaded(self, reply): ... (Removed)
        
    def display_cover(self, pixmap):
        # 自适应缩放逻辑
        max_width = 320
        max_height = 240
        
        orig_width = pixmap.width()
        orig_height = pixmap.height()
        
        if orig_width == 0 or orig_height == 0:
            return

        aspect_ratio = orig_width / orig_height
        
        if aspect_ratio > 1: # 横屏
            new_width = min(orig_width, max_width)
            new_height = int(new_width / aspect_ratio)
        else: # 竖屏
            new_height = min(orig_height, max_height)
            new_width = int(new_height * aspect_ratio)
            
        scaled_pixmap = pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.cover_label.resize(new_width, new_height)
        self.cover_label.setPixmap(scaled_pixmap)
        
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
        """导出当前页数据到Excel"""
        if not hasattr(self, 'current_videos') or not self.current_videos:
            BilibiliMessageBox.warning(self, "提示", "当前没有数据可导出")
            return
            
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_name = f"favorites_page_{self.page}_{timestamp}.xlsx"
        
        path, _ = QFileDialog.getSaveFileName(self, "导出数据", default_name, "Excel Files (*.xlsx)")
        
        if not path:
            return
            
        try:
            # 准备数据：导出所有字段
            data = []
            
            # 获取所有可能的键作为表头
            known_headers = ["title", "upper", "duration", "play", "intro", "pubtime", "fav_time"]
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
                "intro": "简介",
                "pubtime": "发布时间",
                "fav_time": "收藏时间"
            }
            
            # 添加常用字段
            # 移除 BV号 (bvid)
            for k in ["title", "upper_name", "duration", "cnt_info_play", "intro", "pubtime", "fav_time"]:
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
                # row_data.append(v.get("bvid", "")) # Removed
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
                    
            BilibiliMessageBox.information(self, "成功", f"数据已导出到: {path}")
            
        except Exception as e:
            logger.error(f"导出失败: {e}")
            BilibiliMessageBox.error(self, "错误", f"导出失败: {str(e)}")

    def on_batch_download_clicked(self):
        """批量下载处理"""
        reply = QMessageBox.question(self, "批量下载", 
                                   "是否获取该收藏夹的【所有视频】并前往下载？\n(如果视频较多可能需要一些时间)",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        
        if reply == QMessageBox.Yes:
            self.batch_btn.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.status_label.setText("正在获取所有视频列表...")
            
            self.batch_worker = FavoriteAllWorker(self.crawler, self.media_id)
            self.batch_worker.progress_signal.connect(lambda msg: self.status_label.setText(msg))
            self.batch_worker.finished_signal.connect(self.on_batch_fetched)
            self.batch_worker.start()

    def on_batch_fetched(self, bvids, error):
        self.batch_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        
        if error:
            BilibiliMessageBox.error(self, "错误", f"获取失败: {error}")
            self.status_label.setText("获取失败")
            return
            
        if not bvids:
            BilibiliMessageBox.warning(self, "提示", "未找到视频")
            self.status_label.setText("未找到视频")
            return
            
        self.status_label.setText(f"成功获取 {len(bvids)} 个视频")
        
        # Jump to Collection Download Tab
        bangumi_tab = self.main_window.bangumi_tab
        self.main_window.tabs.setCurrentWidget(bangumi_tab)
        
        # Set input
        bangumi_tab.url_input.setText(','.join(bvids))
        
        # Trigger parse
        bangumi_tab.parse_bangumi()
        
        # Close this window? No, user might want to keep it open.
        # But maybe minimize? No.

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
        
        analyze_action = QAction("📊 视频分析", self)
        analyze_action.triggered.connect(lambda: self.analyze_video(bvid))
        menu.addAction(analyze_action)
        
        menu.exec_(self.table.viewport().mapToGlobal(pos))
        
    def analyze_video(self, bvid):
        self.main_window.tabs.setCurrentIndex(3)
        analysis_tab = self.main_window.analysis_tab
        analysis_tab.bvid_input.setText(bvid)
        analysis_tab.start_analysis()
        
    def watch_live(self, bvid, title):
        cookies = self.crawler.cookies
        self.player_window = VideoPlayerWindow(bvid, title, cookies)
        self.player_window.show()
