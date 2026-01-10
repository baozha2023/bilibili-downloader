import time
import os
import PyQt5.QtCore as QtCore
import re

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QGroupBox, QProgressBar, QMessageBox, QDialog)
from PyQt5.QtCore import Qt
from ui.workers import WorkerThread
from ui.message_box import BilibiliMessageBox
from ui.styles import UIStyles

class CheckCollectionThread(QtCore.QThread):
    finished_signal = QtCore.pyqtSignal(dict)
    
    def __init__(self, crawler, bvid):
        super().__init__()
        self.crawler = crawler
        self.bvid = bvid
        
    def run(self):
        try:
            resp = self.crawler.api.get_video_info(self.bvid)
            if resp and resp.get('code') == 0:
                data = resp.get('data', {})
                if 'ugc_season' in data:
                    self.finished_signal.emit({'is_collection': True, 'bvid': self.bvid, 'title': data.get('title', '')})
                else:
                    self.finished_signal.emit({'is_collection': False, 'bvid': self.bvid})
            else:
                 self.finished_signal.emit({'is_collection': False, 'bvid': self.bvid})
        except:
             self.finished_signal.emit({'is_collection': False, 'bvid': self.bvid})

class DownloadTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.crawler = main_window.crawler
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 输入区域
        input_group = QGroupBox("下载选项")
        input_group.setStyleSheet(UIStyles.DOWNLOAD_GROUP_BOX)
        input_layout = QHBoxLayout(input_group)
        
        input_layout.addWidget(QLabel("视频BV号:"))
        self.bvid_input = QLineEdit()
        self.bvid_input.setPlaceholderText("请输入视频BV号或视频地址，例如: BV1xx411c7mD")
        input_layout.addWidget(self.bvid_input)
        
        self.download_btn = QPushButton("开始下载")
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.clicked.connect(lambda: self.download_video())
        self.download_btn.setStyleSheet(UIStyles.DOWNLOAD_BTN)
        input_layout.addWidget(self.download_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet(UIStyles.CANCEL_BTN)
        input_layout.addWidget(self.cancel_btn)
        
        layout.addWidget(input_group)
        
        # 进度显示区域
        progress_group = QGroupBox("下载进度")
        progress_group.setStyleSheet(UIStyles.DOWNLOAD_GROUP_BOX)
        progress_layout = QVBoxLayout(progress_group)
        
        # 视频进度
        video_layout = QHBoxLayout()
        video_layout.addWidget(QLabel("视频:"))
        self.video_progress = QProgressBar()
        video_layout.addWidget(self.video_progress)
        progress_layout.addLayout(video_layout)
        
        # 音频进度
        audio_layout = QHBoxLayout()
        audio_layout.addWidget(QLabel("音频:"))
        self.audio_progress = QProgressBar()
        audio_layout.addWidget(self.audio_progress)
        progress_layout.addLayout(audio_layout)
        
        # 合并进度
        self.merge_container = QWidget()
        merge_layout = QHBoxLayout(self.merge_container)
        merge_layout.setContentsMargins(0, 0, 0, 0)
        merge_layout.addWidget(QLabel("合并:"))
        self.merge_progress = QProgressBar()
        merge_layout.addWidget(self.merge_progress)
        progress_layout.addWidget(self.merge_container)
        
        # 弹幕进度
        self.danmaku_container = QWidget()
        danmaku_layout = QHBoxLayout(self.danmaku_container)
        danmaku_layout.setContentsMargins(0, 0, 0, 0)
        danmaku_layout.addWidget(QLabel("弹幕:"))
        self.danmaku_progress = QProgressBar()
        danmaku_layout.addWidget(self.danmaku_progress)
        progress_layout.addWidget(self.danmaku_container)
        
        # 评论进度
        self.comments_container = QWidget()
        comments_layout = QHBoxLayout(self.comments_container)
        comments_layout.setContentsMargins(0, 0, 0, 0)
        comments_layout.addWidget(QLabel("评论:"))
        self.comments_progress = QProgressBar()
        comments_layout.addWidget(self.comments_progress)
        progress_layout.addWidget(self.comments_container)
        
        # 默认隐藏弹幕和评论进度条
        self.danmaku_container.hide()
        self.comments_container.hide()
        
        # 初始化时更新进度条可见性
        # 使用QTimer.singleShot在下一轮事件循环更新，确保SettingsTab已初始化
        QtCore.QTimer.singleShot(100, self.update_progress_visibility)
        
        # 详细信息
        info_layout = QHBoxLayout()
        self.download_status = QLabel("就绪")
        info_layout.addWidget(self.download_status)
        
        info_layout.addStretch()
        
        self.download_speed_label = QLabel("速度: 0 B/s")
        info_layout.addWidget(self.download_speed_label)
        
        info_layout.addSpacing(20)
        
        self.download_size_label = QLabel("大小: 0 B / 0 B")
        info_layout.addWidget(self.download_size_label)
        
        info_layout.addSpacing(20)
        
        self.download_eta_label = QLabel("剩余时间: --:--")
        info_layout.addWidget(self.download_eta_label)
        
        progress_layout.addLayout(info_layout)
        layout.addWidget(progress_group)
        
        # 历史记录按钮
        history_layout = QHBoxLayout()
        history_layout.addStretch()
        
        history_btn = QPushButton("查看下载历史")
        history_btn.setCursor(Qt.PointingHandCursor)
        history_btn.clicked.connect(self.main_window.show_download_history)
        history_btn.setStyleSheet("font-size: 20px;")
        history_layout.addWidget(history_btn)
        
        open_dir_btn = QPushButton("打开下载目录")
        open_dir_btn.setCursor(Qt.PointingHandCursor)
        open_dir_btn.clicked.connect(lambda: self.main_window.open_download_dir())
        open_dir_btn.setStyleSheet("font-size: 20px;")
        history_layout.addWidget(open_dir_btn)
        
        layout.addLayout(history_layout)
        
        layout.addStretch()

    def update_progress_visibility(self):
        """根据设置更新进度条可见性"""
        if not hasattr(self.main_window, 'settings_tab'):
            return
            
        settings_tab = self.main_window.settings_tab
        
        # 合并进度条
        should_merge = settings_tab.merge_check.isChecked()
        if should_merge:
            self.merge_container.show()
        else:
            self.merge_container.hide()
            
        # 弹幕进度条
        download_danmaku = settings_tab.download_danmaku_check.isChecked()
        if download_danmaku:
            self.danmaku_container.show()
        else:
            self.danmaku_container.hide()
            
        # 评论进度条
        download_comments = settings_tab.download_comments_check.isChecked()
        if download_comments:
            self.comments_container.show()
        else:
            self.comments_container.hide()

    def download_video(self, title=None):
        """下载视频 - 第一步：检查是否为合集"""
        raw_input = self.bvid_input.text().strip()
        if not raw_input:
            BilibiliMessageBox.warning(self, "警告", "请输入视频BV号或链接")
            return
            
        # Extract BV from URL or use as is
        bvid = raw_input
        bv_match = re.search(r'(BV\w{10})', raw_input, re.IGNORECASE)
        if bv_match:
            bvid = bv_match.group(1)
        
        # 检查BV号格式
        if not bvid.startswith("BV") or len(bvid) < 10:
            reply = BilibiliMessageBox.question(
                self, "BV号格式可能不正确", 
                f"提取/输入的BV号 '{bvid}' 格式可能不正确，是否继续？"
            )
            if reply == QDialog.Rejected:
                return
        
        # Disable button during check
        self.download_btn.setEnabled(False)
        self.download_btn.setText("正在检查...")
        
        # Start Check Thread
        self.check_thread = CheckCollectionThread(self.crawler, bvid)
        self.check_thread.finished_signal.connect(lambda res: self.on_check_finished(res, title))
        self.check_thread.start()

    def on_check_finished(self, result, title=None):
        self.download_btn.setEnabled(True)
        self.download_btn.setText("开始下载")
        
        if result.get('is_collection'):
            reply = QMessageBox.question(self, '提示', 
                                       '该BV号属于一个合集，是否前往合集下载以获取完整列表？',
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                # Switch to Bangumi Tab
                self.main_window.tabs.setCurrentWidget(self.main_window.bangumi_tab)
                # Set input
                if result.get('bvid'):
                    self.main_window.bangumi_tab.url_input.setText(result.get('bvid'))
                # Trigger parse
                self.main_window.bangumi_tab.parse_bangumi()
                return

        # Proceed to download single video
        # Use title from result if not provided
        download_title = title if title else result.get('title')
        self.start_download_worker(result['bvid'], download_title)

    def start_download_worker(self, bvid, title=None):
        """实际开始下载任务"""
        # 禁用下载按钮，启用取消按钮
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        # 如果没有提供标题，尝试从输入框的工具提示中获取
        if not title and self.bvid_input.toolTip():
            title = self.bvid_input.toolTip()
        
        # 重置UI状态
        self.download_status.setText("正在获取视频信息...")
        self.reset_progress_bars()
        
        # 记录下载开始时间
        self.download_start_time = time.time()
        
        # 添加日志
        self.main_window.log_to_console(f"开始下载视频: {bvid}", "download")
        if title:
            self.main_window.log_to_console(f"视频标题: {title}", "info")
            # 同时也设置 tooltip 以便取消时使用
            self.bvid_input.setToolTip(title)
        self.main_window.log_to_console("正在获取视频信息...", "info")
        
        # 获取是否合并的选项（从设置界面获取）
        # 访问 SettingsTab 获取配置
        settings_tab = self.main_window.settings_tab
        should_merge = settings_tab.merge_check.isChecked()
        
        # 确保UI状态与设置一致
        self.update_progress_visibility()
        
        if not should_merge:
            self.main_window.log_to_console("已设置不合并视频和音频，将保留原始文件", "info")
        
        # 创建并启动工作线程
        params = settings_tab.get_download_params()
        params["bvid"] = bvid
        if title:
            params["title"] = title
            
        # 收集配置
        config = {
            'cookies': self.crawler.cookies,
            'use_proxy': False,
            'proxies': {},
            'data_dir': settings_tab.data_dir_input.text().strip(),
            'max_retries': settings_tab.retry_count.value()
        }
        
        self.current_thread = WorkerThread("download_video", params, config=config)
        self.current_thread.update_signal.connect(self.update_download_status)
        self.current_thread.finished_signal.connect(self.on_download_finished)
        self.current_thread.progress_signal.connect(self.update_download_progress)
        self.current_thread.start()

    def update_download_status(self, data):
        """更新下载状态"""
        message = data.get("message", "")
        self.download_status.setText(message)
        self.main_window.statusBar().showMessage(message)
        
        status = data.get("status", "")
        if status == "error":
            self.main_window.log_to_console(message, "error")
        elif status == "warning":
            self.main_window.log_to_console(message, "warning")
        elif status == "success":
            self.main_window.log_to_console(message, "success")
        else:
            self.main_window.log_to_console(message, "info")

    def update_download_progress(self, progress_type, current, total):
        """更新下载进度"""
        # 获取合并设置
        settings_tab = self.main_window.settings_tab
        
        # 如果是合并进度，但用户选择不合并，则忽略
        if progress_type == "merge" and not settings_tab.merge_check.isChecked():
            return
            
        # 计算已用时间
        elapsed_time = time.time() - self.download_start_time
        
        # 特殊情况：total=1表示下载完成但无法确定总大小
        if total == 1:
            if progress_type == "video":
                self.video_progress.setValue(100)
            elif progress_type == "audio":
                self.audio_progress.setValue(100)
            elif progress_type == "merge":
                self.merge_progress.setValue(100)
            elif progress_type == "danmaku":
                self.danmaku_progress.setValue(100)
            elif progress_type == "comments":
                self.comments_progress.setValue(100)
            return
        
        if total > 0:
            progress = int(current * 100 / total)
            
            if progress_type == "video":
                self.video_progress.setValue(progress)
            elif progress_type == "audio":
                self.audio_progress.setValue(progress)
            elif progress_type == "merge":
                self.merge_progress.setValue(progress)
            elif progress_type == "danmaku":
                self.danmaku_progress.setValue(progress)
            elif progress_type == "comments":
                self.comments_progress.setValue(progress)
            
            # 格式化大小显示
            formatted_current = self.format_size(current)
            formatted_total = self.format_size(total)
            self.download_size_label.setText(f"大小: {formatted_current} / {formatted_total}")
            
            # 计算下载速度
            if elapsed_time > 0 and progress_type != "merge":
                speed = current / elapsed_time
                # 确保速度只保留两位小数
                if speed < 1024:
                    formatted_speed = f"{speed:.2f} B/s"
                elif speed < 1024 * 1024:
                    formatted_speed = f"{speed/1024:.2f} KB/s"
                elif speed < 1024 * 1024 * 1024:
                    formatted_speed = f"{speed/(1024*1024):.2f} MB/s"
                else:
                    formatted_speed = f"{speed/(1024*1024*1024):.2f} GB/s"
                
                self.download_speed_label.setText(f"速度: {formatted_speed}")
                
                # 更新悬浮窗
                if hasattr(self.main_window, 'floating_window'):
                    self.main_window.floating_window.update_status(progress, formatted_speed)
                
                if speed > 0:
                    remaining_bytes = total - current
                    eta_seconds = int(remaining_bytes / speed)
                    eta = self.format_time(eta_seconds)
                    self.download_eta_label.setText(f"剩余时间: {eta}")

    def on_download_finished(self, result):
        """下载完成后的处理"""
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        execution_time = result.get("execution_time", 0)
        formatted_time = self.format_time(int(execution_time)) if execution_time else "未知"
        
        data = result.get("data", {})
        
        # 修复：从输入框中提取BV号，而不是直接使用文本（可能是URL）
        raw_input = self.bvid_input.text().strip()
        bvid = raw_input
        bv_match = re.search(r'(BV\w{10})', raw_input, re.IGNORECASE)
        if bv_match:
            bvid = bv_match.group(1)
            
        title = data.get("title", "未知视频")
        
        # 只有在非取消状态下才将进度条设为100%
        if result["status"] != "cancelled":
            # 确保所有进度条都显示100%
            self.video_progress.setValue(100)
            self.audio_progress.setValue(100)
            self.merge_progress.setValue(100)
            self.danmaku_progress.setValue(100)
            self.comments_progress.setValue(100)
        
        if result["status"] == "success" or result["status"] == "warning":
            success_message = f"下载完成！用时: {formatted_time}"
            self.download_status.setText(success_message)
            self.main_window.log_to_console(success_message, "success")
            self.main_window.add_download_history(bvid, title, "成功")
            
            # Hide floating window
            if hasattr(self.main_window, 'floating_window'):
                self.main_window.floating_window.reset()
            
            # 完成后操作
            try:
                settings_tab = self.main_window.settings_tab
                complete_action = settings_tab.complete_action.currentIndex()
                if complete_action == 1:  # 打开文件夹
                    video_dir = data.get("download_dir")
                    if video_dir:
                        self.main_window.open_download_dir(video_dir)
                    else:
                        self.main_window.open_download_dir()
                elif complete_action == 2:  # 播放视频
                    merged_file = data.get("merged_file")
                    if merged_file and os.path.exists(merged_file):
                        os.startfile(merged_file)
                elif complete_action == 3:  # 关闭程序
                    self.main_window.close()
            except Exception as e:
                self.main_window.log_to_console(f"执行完成后操作出错: {str(e)}", "error")
                
        elif result["status"] == "cancelled":
            self.download_status.setText("下载已取消")
            self.main_window.log_to_console("下载已取消", "warning")
            
            # Hide floating window
            if hasattr(self.main_window, 'floating_window'):
                self.main_window.floating_window.reset()
                
            # 这里不需要再添加历史记录了，因为在 cancel_download 里已经添加了
            # self.main_window.add_download_history(bvid, title, "已取消")
            
        else:
            error_message = f"下载失败: {result.get('message', '未知错误')}"
            self.download_status.setText(error_message)
            
            # Hide floating window
            if hasattr(self.main_window, 'floating_window'):
                self.main_window.floating_window.reset()
            
            # Log error with traceback if available
            if "error_traceback" in result:
                self.main_window.log_to_console(error_message, "error")
                self.main_window.log_to_console("错误详情已记录到系统日志", "info")
                # The traceback is already logged in WorkerThread, but we ensure it's visible in console log if needed
                # But main_window.log_to_console is for GUI log. 
                # The requirement is "output specific error in system log".
                # WorkerThread already logs to 'logger' (system log).
            else:
                self.main_window.log_to_console(error_message, "error")
                
            self.main_window.add_download_history(bvid, title, "失败")
            QMessageBox.critical(self, "下载失败", error_message)

    def cancel_download(self):
        """取消当前下载任务"""
        if hasattr(self, 'current_thread') and self.current_thread is not None:
            self.main_window.log_to_console("正在取消下载...", "warning")
            self.current_thread.stop()
            self.download_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.download_status.setText("下载已取消")
            self.main_window.log_to_console("下载已取消", "warning")
            
            # Hide floating window
            if hasattr(self.main_window, 'floating_window'):
                self.main_window.floating_window.reset()
            
            # 记录到历史记录（如果能获取到标题）
            raw_input = self.bvid_input.text().strip()
            bvid = raw_input
            bv_match = re.search(r'(BV\w{10})', raw_input, re.IGNORECASE)
            if bv_match:
                bvid = bv_match.group(1)
                
            # 尝试从 bvid_input 的 tooltip 获取标题，或者如果不为空的话
            title = self.bvid_input.toolTip()
            if not title:
                 # 尝试从参数中获取，如果线程保存了的话（这里比较难获取到线程内部状态，除非我们保存了）
                 pass
                 
            # 如果没有标题，就用 BV 号代替或者显示未知
            if not title:
                title = "未知标题 (取消下载)"
            
            self.main_window.add_download_history(bvid, title, "已取消")
            
            # 重置UI状态
            self.reset_progress_bars()

    def reset_progress_bars(self):
        self.video_progress.setMaximum(100)
        self.video_progress.setValue(0)
        self.set_progress_bar_style(self.video_progress, "normal")
        
        self.audio_progress.setMaximum(100)
        self.audio_progress.setValue(0)
        self.set_progress_bar_style(self.audio_progress, "normal")
        
        self.merge_progress.setMaximum(100)
        self.merge_progress.setValue(0)
        self.set_progress_bar_style(self.merge_progress, "normal")
        
        self.danmaku_progress.setMaximum(100)
        self.danmaku_progress.setValue(0)
        self.set_progress_bar_style(self.danmaku_progress, "normal")
        
        self.comments_progress.setMaximum(100)
        self.comments_progress.setValue(0)
        self.set_progress_bar_style(self.comments_progress, "normal")
        
        self.download_status.setText("就绪")
        self.download_speed_label.setText("速度: 0 B/s")
        self.download_eta_label.setText("剩余时间: --:--")
        self.download_size_label.setText("大小: 0 B / 0 B")

    def set_progress_bar_style(self, progress_bar, style="normal"):
        color = "#1890ff" if style == "normal" else "#52c41a" if style == "success" else "#ff4d4f"
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: #f0f0f0;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)
    
    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.1f} MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.2f} GB"

    def format_time(self, seconds):
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds//60}分{seconds%60}秒"
        else:
            return f"{seconds//3600}时{(seconds%3600)//60}分{seconds%60}秒"
