import time
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QGroupBox, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt
from ui.workers import WorkerThread

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
        input_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        input_layout = QHBoxLayout(input_group)
        
        input_layout.addWidget(QLabel("视频BV号:"))
        self.bvid_input = QLineEdit()
        self.bvid_input.setPlaceholderText("请输入视频BV号，例如: BV1xx411c7mD")
        input_layout.addWidget(self.bvid_input)
        
        self.download_btn = QPushButton("开始下载")
        self.download_btn.clicked.connect(lambda: self.download_video())
        self.download_btn.setStyleSheet("background-color: #fb7299; color: white; font-weight: bold; padding: 5px 15px;")
        input_layout.addWidget(self.download_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("background-color: #999; color: white; padding: 5px 15px;")
        input_layout.addWidget(self.cancel_btn)
        
        layout.addWidget(input_group)
        
        # 进度显示区域
        progress_group = QGroupBox("下载进度")
        progress_group.setStyleSheet("QGroupBox { font-weight: bold; }")
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
        merge_layout = QHBoxLayout()
        merge_layout.addWidget(QLabel("合并:"))
        self.merge_progress = QProgressBar()
        merge_layout.addWidget(self.merge_progress)
        progress_layout.addLayout(merge_layout)
        
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
        history_btn.clicked.connect(self.main_window.show_download_history)
        history_layout.addWidget(history_btn)
        
        open_dir_btn = QPushButton("打开下载目录")
        open_dir_btn.clicked.connect(lambda: self.main_window.open_download_dir())
        history_layout.addWidget(open_dir_btn)
        
        layout.addLayout(history_layout)
        
        layout.addStretch()

    def download_video(self, title=None):
        """下载视频"""
        bvid = self.bvid_input.text().strip()
        if not bvid:
            QMessageBox.warning(self, "警告", "请输入视频BV号")
            return
        
        # 检查BV号格式
        if not bvid.startswith("BV") or len(bvid) < 10:
            reply = QMessageBox.question(
                self, "BV号格式可能不正确", 
                f"输入的BV号 '{bvid}' 格式可能不正确，是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
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
        self.main_window.log_to_console("正在获取视频信息...", "info")
        
        # 获取是否合并的选项（从设置界面获取）
        # 访问 SettingsTab 获取配置
        settings_tab = self.main_window.settings_tab
        should_merge = settings_tab.merge_check.isChecked()
        
        # 控制弹幕和评论进度条的显示
        download_danmaku = settings_tab.download_danmaku_check.isChecked()
        download_comments = settings_tab.download_comments_check.isChecked()
        
        if download_danmaku:
            self.danmaku_container.show()
        else:
            self.danmaku_container.hide()
            
        if download_comments:
            self.comments_container.show()
        else:
            self.comments_container.hide()
        
        if not should_merge:
            self.main_window.log_to_console("已设置不合并视频和音频，将保留原始文件", "info")
            # 如果不合并，直接将合并进度条设置为100%
            self.merge_progress.setValue(100)
            self.set_progress_bar_style(self.merge_progress, "success")
        
        # 创建并启动工作线程
        params = {
            "bvid": bvid, 
            "should_merge": should_merge,
            "delete_original": settings_tab.delete_original_check.isChecked(),
            "remove_watermark": settings_tab.remove_watermark_check.isChecked(),
            "download_danmaku": settings_tab.download_danmaku_check.isChecked(),
            "download_comments": settings_tab.download_comments_check.isChecked(),
            "video_quality": settings_tab.quality_combo.currentText()
        }
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
        bvid = self.bvid_input.text().strip()
        title = data.get("title", "未知视频")
        
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
                
        else:
            error_message = f"下载失败: {result.get('message', '未知错误')}"
            self.download_status.setText(error_message)
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
