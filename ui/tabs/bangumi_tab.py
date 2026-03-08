import time
import os
import re
import json

from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QGroupBox, QProgressBar, QMessageBox, QListWidget, 
                             QListWidgetItem, QCheckBox, QDialog, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer
from ui.workers import WorkerThread
from ui.message_box import BilibiliMessageBox
from ui.utils.action_executor import ActionExecutor

class HistoryDialog(QDialog):
    def __init__(self, history_file, parent=None):
        super().__init__(parent)
        self.history_file = history_file
        self.setWindowTitle("下载历史")
        self.resize(600, 400)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["番剧名", "集名", "BV号", "下载时间", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)
        
        # Button layout
        btn_layout = QHBoxLayout()
        
        self.redownload_btn = QPushButton("重新下载")
        self.redownload_btn.setCursor(Qt.PointingHandCursor)
        self.redownload_btn.setStyleSheet("background-color: #fb7299; color: white; padding: 5px 15px; border-radius: 4px;")
        self.redownload_btn.clicked.connect(self.redownload_selected)
        btn_layout.addWidget(self.redownload_btn)
        
        self.clear_btn = QPushButton("清空历史")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setStyleSheet("background-color: #f56c6c; color: white; padding: 5px 15px; border-radius: 4px;")
        self.clear_btn.clicked.connect(self.clear_history)
        btn_layout.addWidget(self.clear_btn)
        
        btn_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("background-color: #909399; color: white; padding: 5px 15px; border-radius: 4px;")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        
        self.load_history()
        
    def redownload_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择要下载的记录")
            return
            
        series_title = self.table.item(row, 0).text()
        title = self.table.item(row, 1).text()
        bvid = self.table.item(row, 2).text()
        
        if self.parent():
            self.parent().add_single_download_task(bvid, title, series_title)
            self.accept()
        
    def load_history(self):
        self.table.setRowCount(0)
        if not os.path.exists(self.history_file):
            return
            
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                
            self.table.setRowCount(len(history))
            for i, item in enumerate(reversed(history)): # Show latest first
                # Make items read-only
                s_title = QTableWidgetItem(item.get('series_title', ''))
                s_title.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(i, 0, s_title)
                
                t_item = QTableWidgetItem(item.get('title', ''))
                t_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(i, 1, t_item)
                
                b_item = QTableWidgetItem(item.get('bvid', ''))
                b_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(i, 2, b_item)
                
                tm_item = QTableWidgetItem(item.get('time', ''))
                tm_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(i, 3, tm_item)
                
                status_item = QTableWidgetItem(item.get('status', ''))
                status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                if item.get('status') == '成功':
                    status_item.setForeground(Qt.green)
                else:
                    status_item.setForeground(Qt.red)
                self.table.setItem(i, 4, status_item)
        except Exception as e:
            pass

    def clear_history(self):
        confirm = QMessageBox.question(self, "确认", "确定要清空所有下载历史吗？", 
                                     QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                with open(self.history_file, 'w', encoding='utf-8') as f:
                    f.write('[]')
                self.load_history()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"清空失败: {str(e)}")

class BangumiInfoThread(QThread):
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    
    def __init__(self, crawler, ep_id=None, season_id=None, bvid=None, bvid_list=None, fetch_details=True):
        super().__init__()
        self.crawler = crawler
        self.ep_id = ep_id
        self.season_id = season_id
        self.bvid = bvid
        self.bvid_list = bvid_list
        self.fetch_details = fetch_details
        
    def run(self):
        try:
            if self.bvid_list:
                # Handle Multi-BV List (Virtual Collection)
                result = {
                    'title': '批量视频列表',
                    'season_title': f'(共{len(self.bvid_list)}个视频)',
                    'episodes': []
                }
                
                if not self.fetch_details:
                    for index, bvid in enumerate(self.bvid_list):
                        result['episodes'].append({
                            'title': str(bvid),
                            'long_title': '',
                            'bvid': bvid,
                            'cid': 0,
                            'aid': 0
                        })
                else:
                    for index, bvid in enumerate(self.bvid_list):
                        try:
                            resp = self.crawler.api.get_video_info(bvid)
                            if resp and resp.get('code') == 0:
                                data = resp.get('data', {})
                                episode = {
                                    'title': data.get('title', ''),
                                    'long_title': '',
                                    'bvid': data.get('bvid'),
                                    'cid': data.get('cid'),
                                    'aid': data.get('aid')
                                }
                                result['episodes'].append(episode)
                            else:
                                result['episodes'].append({
                                    'title': f'获取失败 ({bvid})',
                                    'long_title': '',
                                    'bvid': bvid,
                                    'cid': 0,
                                    'aid': 0
                                })
                        except Exception:
                            result['episodes'].append({
                                'title': f'获取失败 ({bvid})',
                                'long_title': '',
                                'bvid': bvid,
                                'cid': 0,
                                'aid': 0
                            })
                    
                self.finished_signal.emit(result)

            elif self.bvid:
                # Handle BV input (Check for Collection/Season)
                resp = self.crawler.api.get_video_info(self.bvid)
                if resp and resp.get('code') == 0:
                    data = resp.get('data', {})
                    
                    # Check for UGC Season (Collection)
                    if 'ugc_season' in data:
                        season = data['ugc_season']
                        # Transform to match Bangumi structure
                        result = {
                            'title': season.get('title', data.get('title')),
                            'season_title': '', # UGC seasons usually don't have separate season titles
                            'episodes': []
                        }
                        
                        # Flatten sections into episodes
                        sections = season.get('sections', [])
                        for section in sections:
                            for ep in section.get('episodes', []):
                                # Adapt episode data
                                episode = {
                                    'title': str(ep.get('title', '')),
                                    'long_title': '',
                                    'bvid': ep.get('bvid'),
                                    'cid': ep.get('cid'),
                                    'aid': ep.get('aid')
                                }
                                result['episodes'].append(episode)
                                
                        self.finished_signal.emit(result)
                    else:
                        # It is a single video
                        self.finished_signal.emit({'type': 'single', 'bvid': self.bvid})
                else:
                     msg = resp.get('message', '未知错误') if resp else '网络请求失败'
                     self.error_signal.emit(msg)
            
            else:
                # Handle EP/SS input
                resp = self.crawler.api.get_bangumi_info(self.ep_id, self.season_id)
                if resp and resp.get('code') == 0:
                    result = resp.get('result', {})
                    self.finished_signal.emit(result)
                else:
                    msg = resp.get('message', '未知错误') if resp else '网络请求失败'
                    self.error_signal.emit(msg)
        except Exception as e:
            self.error_signal.emit(str(e))

class BangumiTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.crawler = main_window.crawler
        self.current_series_title = ""
        self.history_file = os.path.join(self.crawler.data_dir, "bangumi_history.json")
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. Input Area
        input_group = QGroupBox("合集/视频列表链接")
        input_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 18px; padding-top: 5px; margin-top: 5px; }")
        input_layout = QHBoxLayout(input_group)
        input_layout.setContentsMargins(10, 20, 10, 10)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入合集链接、BV号，或多个BV号(用逗号分隔)")
        self.url_input.setStyleSheet("font-size: 16px; padding: 8px;")
        input_layout.addWidget(self.url_input)
        
        self.parse_btn = QPushButton("获取合集")
        self.parse_btn.setStyleSheet("background-color: #fb7299; color: white; font-weight: bold; padding: 8px 15px; font-size: 16px; border-radius: 4px;")
        self.parse_btn.setCursor(Qt.PointingHandCursor)
        self.parse_btn.clicked.connect(self.parse_bangumi)
        input_layout.addWidget(self.parse_btn)
        
        layout.addWidget(input_group)

        # 1.5 Extra Controls
        extra_layout = QHBoxLayout()
        extra_layout.setContentsMargins(5, 0, 5, 0)
        
        btn_style = "background-color: #f1f2f3; color: #333; font-weight: bold; padding: 8px 15px; font-size: 16px; border: 1px solid #ddd; border-radius: 4px;"
        
        self.history_btn = QPushButton("查看下载历史")
        self.history_btn.setStyleSheet(btn_style)
        self.history_btn.setCursor(Qt.PointingHandCursor)
        self.history_btn.clicked.connect(self.show_history)
        extra_layout.addWidget(self.history_btn)
        
        self.open_dir_btn = QPushButton("打开下载目录")
        self.open_dir_btn.setStyleSheet(btn_style)
        self.open_dir_btn.setCursor(Qt.PointingHandCursor)
        self.open_dir_btn.clicked.connect(self.open_download_dir)
        extra_layout.addWidget(self.open_dir_btn)
        
        extra_layout.addStretch()
        layout.addLayout(extra_layout)
        
        # 2. Episode List Area
        self.list_group = QGroupBox("合集列表")
        self.list_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 18px; 
                background-color: white; 
                border: 1px solid #e7e7e7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        list_layout = QVBoxLayout(self.list_group)
        
        self.info_label = QLabel("暂无信息")
        self.info_label.setStyleSheet("font-size: 16px; color: #fb7299; font-weight: bold; margin-bottom: 5px;")
        list_layout.addWidget(self.info_label)
        
        self.episode_list = QListWidget()
        self.episode_list.setSelectionMode(QListWidget.NoSelection) # Disable default selection highlight
        self.episode_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                outline: none;
            }
            QListWidget::item {
                background-color: #f6f7f8;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 5px;
                color: #333;
                font-size: 14px;
                border: 1px solid transparent;
            }
            QListWidget::item:hover {
                background-color: #fff;
                border: 1px solid #fb7299;
                color: #fb7299;
            }
        """)
        list_layout.addWidget(self.episode_list)
        
        # Selection Controls
        sel_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setCursor(Qt.PointingHandCursor)
        self.select_all_btn.clicked.connect(self.select_all)
        sel_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.setCursor(Qt.PointingHandCursor)
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        sel_layout.addWidget(self.deselect_all_btn)
        
        sel_layout.addStretch()
        list_layout.addLayout(sel_layout)
        
        layout.addWidget(self.list_group)
        
        # 3. Download Controls
        action_layout = QHBoxLayout()
        
        self.download_btn = QPushButton("下载选中视频")
        self.download_btn.setStyleSheet("background-color: #fb7299; color: white; font-weight: bold; padding: 10px 30px; font-size: 18px;")
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.clicked.connect(self.start_batch_download)
        self.download_btn.setEnabled(False)
        action_layout.addWidget(self.download_btn)
        
        self.stop_btn = QPushButton("停止下载")
        self.stop_btn.setStyleSheet("background-color: #999; color: white; padding: 10px 30px; font-size: 18px;")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self.stop_download)
        self.stop_btn.setEnabled(False)
        action_layout.addWidget(self.stop_btn)
        
        layout.addLayout(action_layout)
        
        # 4. Progress Area
        self.progress_group = QGroupBox("当前任务进度")
        progress_layout = QVBoxLayout(self.progress_group)
        
        self.current_task_label = QLabel("就绪")
        progress_layout.addWidget(self.current_task_label)
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.progress_group)
        
        layout.addStretch()
        
        # Internal state
        self.episodes_data = []
        self.download_queue = []
        self.is_downloading = False

    def parse_bangumi(self):
        text = self.url_input.text().strip()
        if not text:
            BilibiliMessageBox.warning(self, "提示", "请输入链接或BV号")
            return
            
        # Check for multiple BVs
        separators = [',', '，', ';', '；']
        is_multi = False
        for sep in separators:
            if sep in text:
                is_multi = True
                break
        
        bvid_list = []
        if is_multi:
            # Split and clean
            parts = re.split(r'[,，;；]', text)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                # Extract BV from part (it might be a URL)
                bvid_match = re.search(r'(BV\w+)', part, re.IGNORECASE)
                if bvid_match:
                    bvid_list.append(bvid_match.group(1))
                elif part.startswith('BV') or part.startswith('bv'):
                     bvid_list.append(part)
            
            if not bvid_list:
                BilibiliMessageBox.warning(self, "提示", "未从输入中提取到有效的BV号")
                return
                
            self.info_label.setText(f"正在获取 {len(bvid_list)} 个视频的信息...")
            self.parse_btn.setEnabled(False)
            
            self.info_thread = BangumiInfoThread(self.crawler, bvid_list=bvid_list)
            self.info_thread.finished_signal.connect(self.on_info_fetched)
            self.info_thread.error_signal.connect(self.on_info_error)
            self.info_thread.start()
            return

        # Single Item Logic
        url = text
        # Extract ep_id, season_id or bvid
        ep_id = None
        season_id = None
        bvid = None
        
        if url.isdigit():
            ep_id = url
        else:
            ep_match = re.search(r'ep(\d+)', url)
            ss_match = re.search(r'ss(\d+)', url)
            bvid_match = re.search(r'(BV\w+)', url, re.IGNORECASE)
            
            if ep_match:
                ep_id = ep_match.group(1)
            elif ss_match:
                season_id = ss_match.group(1)
            elif bvid_match:
                bvid = bvid_match.group(1)
                
        if not ep_id and not season_id and not bvid:
            BilibiliMessageBox.warning(self, "提示", "无法从输入中提取ep_id, season_id 或 BV号")
            return
            
        self.info_label.setText("正在获取合集信息...")
        self.parse_btn.setEnabled(False)
        
        self.info_thread = BangumiInfoThread(self.crawler, ep_id, season_id, bvid)
        self.info_thread.finished_signal.connect(self.on_info_fetched)
        self.info_thread.error_signal.connect(self.on_info_error)
        self.info_thread.start()

    def start_batch_from_bvid_list(self, bvid_list):
        if not bvid_list:
            BilibiliMessageBox.warning(self, "提示", "未找到有效BV号")
            return
            
        self.info_label.setText(f"正在获取 {len(bvid_list)} 个视频的信息...")
        self.parse_btn.setEnabled(False)
        
        self.info_thread = BangumiInfoThread(self.crawler, bvid_list=bvid_list, fetch_details=False)
        self.info_thread.finished_signal.connect(self.on_info_fetched)
        self.info_thread.error_signal.connect(self.on_info_error)
        self.info_thread.start()

    def on_info_fetched(self, result):
        self.parse_btn.setEnabled(True)
        
        # Check if it is a single video redirect
        if result.get('type') == 'single':
            self.info_label.setText("非番剧/合集")
            reply = QMessageBox.question(self, '提示', 
                                       '该BV号不是合集，是否前往视频下载？',
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                # Switch to Download Tab
                self.main_window.tabs.setCurrentWidget(self.main_window.download_tab)
                # Set input
                if result.get('bvid'):
                    self.main_window.download_tab.bvid_input.setText(result.get('bvid'))
            return

        title = result.get('title', '未知番剧')
        self.current_series_title = title
        season_title = result.get('season_title', '')
        
        self.info_label.setText(f"📺 {title} {season_title}")
        
        self.episodes_data = result.get('episodes', [])
        self.episode_list.clear()
        
        if hasattr(self, '_anim_timer') and self._anim_timer:
            self._anim_timer.stop()
        
        # Animation: add items with slight delay
        self._anim_index = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._add_next_item)
        self._anim_timer.start(50)

    def _add_next_item(self):
        if self._anim_index >= len(self.episodes_data):
            self._anim_timer.stop()
            if self.episode_list.count() > 0:
                self.download_btn.setEnabled(True)
            return
            
        ep = self.episodes_data[self._anim_index]
        ep_title = ep.get('title', '')
        long_title = ep.get('long_title', '')
        item_text = f"P{self._anim_index + 1} - {ep_title} {long_title}"
        
        item = QListWidgetItem(item_text)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        item.setData(Qt.UserRole, ep)
        self.episode_list.addItem(item)
        self.episode_list.scrollToBottom()
        
        self._anim_index += 1

    def on_info_error(self, msg):
        self.parse_btn.setEnabled(True)
        self.info_label.setText("获取失败")
        BilibiliMessageBox.error(self, "错误", f"获取视频信息失败: {msg}")

    def select_all(self):
        for i in range(self.episode_list.count()):
            self.episode_list.item(i).setCheckState(Qt.Checked)
            
    def deselect_all(self):
        for i in range(self.episode_list.count()):
            self.episode_list.item(i).setCheckState(Qt.Unchecked)

    def start_batch_download(self):
        self.download_queue = []
        for i in range(self.episode_list.count()):
            item = self.episode_list.item(i)
            if item.checkState() == Qt.Checked:
                self.download_queue.append(item.data(Qt.UserRole))
                
        if not self.download_queue:
            BilibiliMessageBox.warning(self, "提示", "请选择要下载的视频")
            return
            
        self.total_batch_count = len(self.download_queue)
        self.current_batch_index = 0
            
        self.is_downloading = True
        self.download_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.process_next_download()

    def add_single_download_task(self, bvid, title, series_title):
        """Add a single task from history re-download"""
        # Construct a minimal episode data object
        ep_data = {
            'bvid': bvid,
            'title': title,
            'long_title': '' # Title usually includes index, so leave long_title empty or parse it?
        }
        
        # If queue is empty and not downloading, start immediately
        # If downloading, maybe append? But for simplicity, let's just start a new batch of 1 if idle.
        if self.is_downloading:
            BilibiliMessageBox.warning(self, "提示", "当前有下载任务正在进行，请稍后再试")
            return

        self.download_queue = [ep_data]
        self.total_batch_count = 1
        self.current_batch_index = 0
        
        # We need to set current_series_title so the folder is correct
        self.current_series_title = series_title
        
        self.is_downloading = True
        self.download_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Show progress group
        self.progress_group.show()
        
        self.process_next_download()
        
    def process_next_download(self):
        """处理下一个下载任务"""
        # 如果已停止下载，直接返回
        if not self.is_downloading:
            return

        # 如果队列为空，则结束批量任务
        if not self.download_queue:
            self.finish_batch_download()
            return
            
        ep_data = self.download_queue.pop(0)
        self.current_ep_data = ep_data  # 保存当前视频数据，用于错误处理
        self.current_batch_index += 1
        bvid = ep_data.get('bvid')
        title = f"{ep_data.get('title')} {ep_data.get('long_title')}"
        
        # 更新UI状态
        self.current_task_label.setText(f"正在下载 ({self.current_batch_index}/{self.total_batch_count}): {title}")
        self.progress_bar.setValue(0)
        self.download_start_time = time.time()
        
        # 获取配置信息
        settings_tab = self.main_window.settings_tab
        
        # 计算下载目录: base_dir/bangumi/series_title
        base_dir = settings_tab.data_dir_input.text().strip()
        series_title = self.current_series_title or "其他番剧"
        safe_series_title = re.sub(r'[\\/:*?"<>|]', '_', series_title)
        bangumi_dir = os.path.join(base_dir, 'bangumi', safe_series_title)
        
        # 构建下载参数
        params = settings_tab.get_download_params()
        params["bvid"] = bvid
        params["title"] = title
        
        # 构建配置字典
        config = {
            'cookies': self.crawler.cookies,
            'data_dir': base_dir,
            'download_dir': bangumi_dir,
            'max_retries': settings_tab.retry_count.value(),
            'timeout': settings_tab.timeout_spin.value(),
            'retry_interval': settings_tab.retry_interval_spin.value()
        }
        
        # 启动工作线程
        self.current_thread = WorkerThread("download_video", params, config=config)
        self.current_thread.finished_signal.connect(self.on_single_download_finished)
        self.current_thread.progress_signal.connect(self.update_progress)
        self.current_thread.start()
        
    def update_progress(self, p_type, current, total):
        if total <= 0: return
        
        percent = int(current * 100 / total)
        
        # Calculate speed
        elapsed = time.time() - self.download_start_time
        speed_str = ""
        if elapsed > 0:
            speed = current / elapsed
            if speed < 1024:
                speed_str = f"{speed:.2f} B/s"
            elif speed < 1024**2:
                speed_str = f"{speed/1024:.2f} KB/s"
            elif speed < 1024**3:
                speed_str = f"{speed/1024**2:.2f} MB/s"
            else:
                speed_str = f"{speed/1024**3:.2f} GB/s"
        
        # Update Floating Window
        if hasattr(self.main_window, 'floating_window'):
            self.main_window.floating_window.update_status(percent, speed_str)

        prefix = f"({self.current_batch_index}/{self.total_batch_count})"
        
        if p_type == "video":
            self.current_task_label.setText(f"正在下载视频 {prefix}... {percent}%  速度: {speed_str}")
            self.progress_bar.setValue(percent)
        elif p_type == "audio":
            self.current_task_label.setText(f"正在下载音频 {prefix}... {percent}%  速度: {speed_str}")
            self.progress_bar.setValue(percent)
        elif p_type == "merge":
            self.current_task_label.setText(f"正在合并音视频 {prefix}... {percent}%")
            self.progress_bar.setValue(percent)
        elif p_type == "danmaku":
             self.current_task_label.setText(f"正在下载弹幕 {prefix}... {percent}%")
        elif p_type == "comments":
             self.current_task_label.setText(f"正在下载评论 {prefix}... {percent}%")
            
    def on_single_download_finished(self, result):
        # 如果任务已取消，直接处理下一步（将会在 process_next_download 中终止）
        if result.get('status') == 'cancelled':
            self.process_next_download()
            return

        if result['status'] == 'success':
            title = result['data'].get('title', '未知视频')
            bvid = result['data'].get('bvid', '')
            self.main_window.log_to_console(f"下载完成: {title}", "success")
            
            # Save history
            try:
                output_path = result.get('data', {}).get('output_path', '')
                if not output_path:
                    # Fallback if output_path is not returned
                    settings_tab = self.main_window.settings_tab
                    base_dir = settings_tab.data_dir_input.text().strip()
                    series_title = self.current_series_title or "其他番剧"
                    safe_series_title = re.sub(r'[\\/:*?"<>|]', '_', series_title)
                    bangumi_dir = os.path.join(base_dir, 'bangumi', safe_series_title)
                    output_path = bangumi_dir
                    
                self.save_history(self.current_series_title, title, bvid, "成功", output_path)
            except Exception as e:
                print(f"Failed to save history: {e}")
                
        else:
            self.main_window.log_to_console(f"下载失败: {result.get('message')}", "error")
            # Save failed history
            try:
                title = '未知'
                bvid = ''
                
                # 尝试从结果中获取
                data = result.get('data', {})
                if data and ('bvid' in data or 'title' in data):
                    bvid = data.get('bvid', '')
                    title = data.get('title', '未知')
                # 尝试从当前任务数据中获取
                elif hasattr(self, 'current_ep_data') and self.current_ep_data:
                    title = f"{self.current_ep_data.get('title')} {self.current_ep_data.get('long_title')}"
                    bvid = self.current_ep_data.get('bvid', '')
                
                if bvid or title != '未知':
                    self.save_history(self.current_series_title, title, bvid, "失败", "")
            except Exception as e:
                print(f"Failed to save failed history: {e}")
            
        # Next
        self.process_next_download()
        
    def save_history(self, series_title, title, bvid, status, path):
        entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "series_title": series_title,
            "title": title,
            "bvid": bvid,
            "status": status,
            "path": path
        }
        
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                pass
        
        history.append(entry)
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass
            
    def show_history(self):
        dialog = HistoryDialog(self.history_file, self)
        dialog.exec_()
        
    def open_download_dir(self):
        settings_tab = self.main_window.settings_tab
        base_dir = settings_tab.data_dir_input.text().strip()
        bangumi_dir = os.path.join(base_dir, 'bangumi')
        
        if not os.path.exists(bangumi_dir):
            try:
                os.makedirs(bangumi_dir)
            except:
                pass
                
        try:
            os.startfile(bangumi_dir)
        except Exception as e:
            BilibiliMessageBox.error(self, "错误", f"无法打开文件夹: {str(e)}")
        
    def finish_batch_download(self):
        self.is_downloading = False
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.current_task_label.setText("批量下载完成")
        self.progress_bar.setValue(100)
        
        # Hide floating window
        if hasattr(self.main_window, 'floating_window'):
            self.main_window.floating_window.reset()
            
        BilibiliMessageBox.information(self, "完成", "批量下载任务已完成")
        
        # 执行完成后操作
        settings_tab = self.main_window.settings_tab
        base_dir = settings_tab.data_dir_input.text().strip()
        series_title = self.current_series_title or "其他番剧"
        safe_series_title = re.sub(r'[\\/:*?"<>|]', '_', series_title)
        bangumi_dir = os.path.join(base_dir, 'bangumi', safe_series_title)
        
        ActionExecutor.execute_completion_action(self.main_window, download_dir=bangumi_dir)
        
    def stop_download(self):
        if self.is_downloading:
            self.is_downloading = False
            if hasattr(self, 'current_thread') and self.current_thread.isRunning():
                self.current_thread.stop()
            
            # 保存当前任务状态为已取消
            if hasattr(self, 'current_ep_data') and self.current_ep_data:
                bvid = self.current_ep_data.get('bvid', '')
                title = f"{self.current_ep_data.get('title')} {self.current_ep_data.get('long_title')}"
                if bvid:
                    self.save_history(self.current_series_title, title, bvid, "已取消", "")

            self.download_queue = []
            self.current_task_label.setText("下载已停止")
            self.progress_bar.setValue(0) # 重置进度条
            self.download_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            
            # Hide floating window
            if hasattr(self.main_window, 'floating_window'):
                self.main_window.floating_window.reset()
