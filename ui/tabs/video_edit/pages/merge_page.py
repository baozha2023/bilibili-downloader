import os
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
                             QAbstractItemView, QListWidgetItem, QMessageBox, QGraphicsOpacityEffect, QFileDialog, QDialog)
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtSignal
from ui.widgets.edit_widgets import MergeItemWidget
from ui.message_box import BilibiliMessageBox
from .base_page import BaseEditPage
from ..workers import GenericWorker

class MergeListWidget(QListWidget):
    """支持拖拽文件和内部排序的列表控件"""
    files_dropped = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDefaultDropAction(Qt.MoveAction)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super().dragEnterEvent(event)
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super().dragMoveEvent(event)
            
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            files = []
            for url in event.mimeData().urls():
                file_path = str(url.toLocalFile())
                if os.path.isfile(file_path):
                    files.append(file_path)
            if files:
                self.files_dropped.emit(files)
        else:
            super().dropEvent(event)

class MergePage(BaseEditPage):
    def __init__(self, main_window, processor):
        super().__init__(main_window, processor)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        self.setup_header(layout, "视频合并", "将多个视频拼接为一个文件，前提视频帧率相同")
        
        # Tip
        tip_label = QLabel("💡 提示：支持拖拽调整视频顺序")
        tip_label.setStyleSheet("color: #999; font-size: 14px; margin-bottom: 5px;")
        layout.addWidget(tip_label)
        
        # Merge List
        self.merge_list = MergeListWidget()
        self.merge_list.files_dropped.connect(self.process_dropped_files)
        self.merge_list.setStyleSheet("""
            QListWidget {
                border: 2px dashed #e0e0e0;
                border-radius: 12px;
                font-size: 16px;
                padding: 10px;
                background-color: #fafafa;
                outline: none;
            }
            QListWidget::item {
                margin-bottom: 10px;
                background: transparent;
            }
        """)
        layout.addWidget(self.merge_list)
        
        # Controls
        controls_frame = self.create_control_frame()
        controls_layout = QHBoxLayout(controls_frame)
        
        add_btn = self.create_button("➕ 添加文件", self.add_merge_files)
        add_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                padding: 10px 25px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 6px;
                color: #333;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #fb7299;
                color: #fb7299;
            }
        """)
        controls_layout.addWidget(add_btn)
        
        clear_btn = self.create_button("🗑️ 清空列表", self.clear_merge_list_safe)
        clear_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                padding: 10px 25px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 6px;
                color: #666;
            }
            QPushButton:hover {
                background-color: #fff1f0;
                border-color: #ff4d4f;
                color: #ff4d4f;
            }
        """)
        controls_layout.addWidget(clear_btn)
        
        controls_layout.addStretch()
        
        self.merge_btn = self.create_primary_button("🚀 开始合并", self.start_merge)
        controls_layout.addWidget(self.merge_btn)
        
        layout.addWidget(controls_frame)
        
        self.merge_progress = self.create_progress_bar()
        layout.addWidget(self.merge_progress)
        
        self.merge_status = QLabel("")
        self.merge_status.setAlignment(Qt.AlignCenter)
        self.merge_status.setStyleSheet("font-size: 16px; margin-top: 5px;")
        layout.addWidget(self.merge_status)
        
        layout.addStretch()

    def process_dropped_files(self, files):
        if files:
            for f in files:
                # Check extension
                if not f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv')):
                    continue
                    
                # Get duration
                duration = self.processor.get_video_duration(f)
                fps = self.processor.get_video_fps(f)
                
                item = QListWidgetItem(self.merge_list)
                item.setSizeHint(QSize(0, 95)) 
                
                widget = MergeItemWidget(f, duration, fps)
                widget.removed.connect(lambda w: self.remove_merge_item(w))
                self.merge_list.setItemWidget(item, widget)
                
                # Simple fade in animation for the new item
                opacity = QGraphicsOpacityEffect(widget)
                widget.setGraphicsEffect(opacity)
                anim = QPropertyAnimation(opacity, b"opacity")
                anim.setDuration(400)
                anim.setStartValue(0)
                anim.setEndValue(1)
                anim.setEasingCurve(QEasingCurve.OutQuad)
                anim.finished.connect(lambda: widget.setGraphicsEffect(None))
                anim.start()
                widget.anim = anim # keep ref

    def add_merge_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", self.main_window.crawler.data_dir,
            "Video Files (*.mp4 *.mkv *.avi *.mov *.flv)"
        )
        if files:
            for f in files:
                # Get duration
                duration = self.processor.get_video_duration(f)
                fps = self.processor.get_video_fps(f)
                
                item = QListWidgetItem(self.merge_list)
                item.setSizeHint(QSize(0, 95)) 
                
                widget = MergeItemWidget(f, duration, fps)
                widget.removed.connect(lambda w: self.remove_merge_item(w))
                self.merge_list.setItemWidget(item, widget)
                
                # Simple fade in animation for the new item
                opacity = QGraphicsOpacityEffect(widget)
                widget.setGraphicsEffect(opacity)
                anim = QPropertyAnimation(opacity, b"opacity")
                anim.setDuration(400)
                anim.setStartValue(0)
                anim.setEndValue(1)
                anim.setEasingCurve(QEasingCurve.OutQuad)
                anim.finished.connect(lambda: widget.setGraphicsEffect(None))
                anim.start()
                widget.anim = anim # keep ref

    def remove_merge_item(self, widget):
        for i in range(self.merge_list.count()):
            item = self.merge_list.item(i)
            if self.merge_list.itemWidget(item) == widget:
                self.merge_list.takeItem(i)
                break

    def clear_merge_list_safe(self):
        if self.merge_list.count() > 0:
            reply = QMessageBox.question(self, "确认清空", "确定要清空所有已添加的视频吗？", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.merge_list.clear()

    def start_merge(self):
        count = self.merge_list.count()
        if count < 2:
            QMessageBox.warning(self, "提示", "请至少添加两个文件进行合并")
            return
            
        file_list = []
        for i in range(count):
            item = self.merge_list.item(i)
            widget = self.merge_list.itemWidget(item)
            if widget:
                start, end = widget.get_range()
                file_list.append({
                    'path': widget.path,
                    'start': start,
                    'end': end
                })
        
        # Output path
        merge_dir = os.path.join(self.main_window.crawler.data_dir, "merge")
        if not os.path.exists(merge_dir):
            os.makedirs(merge_dir)
            
        base_name = os.path.splitext(os.path.basename(file_list[0]['path']))[0]
        output_path = os.path.join(merge_dir, f"{base_name}_merged.mp4")
        
        counter = 1
        while os.path.exists(output_path):
            output_path = os.path.join(merge_dir, f"{base_name}_merged_{counter}.mp4")
            counter += 1
            
        self.merge_btn.setEnabled(False)
        self.merge_progress.setVisible(True)
        self.merge_progress.setValue(0)
        self.merge_status.setText("正在合并中...")
        
        self.main_window.log_to_console(f"开始合并 {len(file_list)} 个视频文件", "info")
        
        # Use merge_videos_with_range
        self.worker = GenericWorker(self.processor.merge_videos_with_range, file_list, output_path)
        self.worker.progress_signal.connect(self.merge_progress.setValue)
        self.worker.finished_signal.connect(lambda s, m: self.on_merge_finished(s, m, merge_dir))
        self.worker.start()
        
    def on_merge_finished(self, success, msg, merge_dir):
        self.merge_btn.setEnabled(True)
        if success:
            self.merge_status.setText(f"✅ 合并成功: {os.path.basename(msg)}")
            self.merge_progress.setValue(100)
            self.main_window.log_to_console(f"合并成功: {msg}", "success")
            # Open merge folder
            try:
                os.startfile(merge_dir)
            except Exception as e:
                self.main_window.log_to_console(f"打开文件夹失败: {e}", "error")
        else:
            self.merge_status.setText(f"❌ 失败: {msg}")
            self.main_window.log_to_console(f"合并失败: {msg}", "error")
