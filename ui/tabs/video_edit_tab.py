import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QComboBox, QFileDialog, QProgressBar, QMessageBox, QListWidget, QListWidgetItem,
                             QGraphicsOpacityEffect, QFrame, QStackedWidget, QSplitter, QSpinBox, QDoubleSpinBox,
                             QGroupBox, QScrollArea, QAbstractItemView, QSlider, QRadioButton, QButtonGroup, QStyle, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QUrl
from PyQt5.QtGui import QIcon, QColor, QBrush

class Worker(QThread):
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        def callback(current, total):
            self.progress_signal.emit(current, total)
            
        # Inject callback into kwargs
        self.kwargs['progress_callback'] = callback
        success, msg = self.func(*self.args, **self.kwargs)
        self.finished_signal.emit(success, msg)

class DragDropListWidget(QListWidget):
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #ccc;
                border-radius: 12px;
                font-size: 20px;
                color: #555;
                background-color: #fafafa;
                outline: none;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
                background-color: white;
                margin-bottom: 5px;
                border-radius: 5px;
            }
            QListWidget:focus {
                border-color: #fb7299;
            }
        """)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet("""
                QListWidget {
                    border: 2px dashed #fb7299;
                    border-radius: 12px;
                    font-size: 16px;
                    color: #fb7299;
                    background-color: #fff0f5;
                }
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #ccc;
                border-radius: 12px;
                font-size: 16px;
                color: #555;
                background-color: #fafafa;
            }
        """)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #ccc;
                border-radius: 12px;
                font-size: 16px;
                color: #555;
                background-color: #fafafa;
            }
        """)
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            for url in event.mimeData().urls():
                file_path = str(url.toLocalFile())
                if os.path.isfile(file_path):
                    self.file_dropped.emit(file_path)
        else:
            event.ignore()

class VideoEditTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.processor = main_window.crawler.processor
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left Sidebar
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("""
            QFrame {
                background-color: #f1f2f3;
                border-right: 1px solid #e7e7e7;
            }
            QPushButton {
                text-align: left;
                padding: 15px 20px;
                border: none;
                font-size: 20px;
                color: #61666d;
                background-color: transparent;
                border-radius: 6px;
                margin: 5px 10px;
            }
            QPushButton:hover {
                background-color: #e3e5e7;
                color: #18191c;
            }
            QPushButton:checked {
                background-color: #ffffff;
                color: #fb7299;
                font-weight: bold;
            }
        """)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 0)
        sidebar_layout.setSpacing(5)
        
        self.nav_btns = []
        nav_items = [("格式转换", "convert"), ("视频剪辑", "cut"), ("视频合并", "merge"), ("去水印", "watermark"), ("视频压缩", "compress")]
        
        for text, tag in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=tag: self.switch_page(t))
            sidebar_layout.addWidget(btn)
            self.nav_btns.append((tag, btn))
            
        sidebar_layout.addStretch()
        main_layout.addWidget(self.sidebar)
        
        # Right Content
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: #ffffff;")
        main_layout.addWidget(self.content_stack)
        
        # Initialize pages
        self.pages = {}
        self.pages['convert'] = self.create_convert_page()
        self.pages['cut'] = self.create_cut_page()
        self.pages['merge'] = self.create_merge_page()
        self.pages['watermark'] = self.create_watermark_page()
        self.pages['compress'] = self.create_compress_page()
        
        for tag, page in self.pages.items():
            self.content_stack.addWidget(page)
            
        # Select first page
        self.nav_btns[0][1].click()

    def switch_page(self, tag):
        # Update buttons style
        for t, btn in self.nav_btns:
            btn.setChecked(t == tag)
            
        # Switch stack
        if tag in self.pages:
            self.content_stack.setCurrentWidget(self.pages[tag])
            
            # Animation
            self.fade_in(self.pages[tag])

    def fade_in(self, widget):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.OutQuad)
        anim.start()
        # Keep reference to prevent gc
        widget.anim = anim

    def show_with_animation(self, widget):
        widget.setVisible(True)
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(500)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.OutQuad)
        anim.start()
        # Keep reference to prevent gc
        widget.anim = anim

    # ==========================================
    # 1. Format Conversion Page
    # ==========================================
    def create_convert_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        self.setup_header(layout, "格式转换", "支持 mp4, mp3, mkv, avi, gif 等多种格式互转")
        
        # File List
        self.convert_file_list = DragDropListWidget()
        self.convert_file_list.file_dropped.connect(lambda p: self.set_single_file(p, self.convert_file_list, self.convert_btn))
        layout.addWidget(self.convert_file_list)
        
        # Controls
        controls_frame = self.create_control_frame()
        controls_layout = QHBoxLayout(controls_frame)
        
        select_btn = self.create_button("选择文件", lambda: self.select_single_file(self.convert_file_list, self.convert_btn))
        controls_layout.addWidget(select_btn)
        
        controls_layout.addStretch()
        
        controls_layout.addWidget(QLabel("目标格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mp3", "mkv", "avi", "mov", "gif"])
        self.format_combo.setFixedWidth(100)
        self.style_combo(self.format_combo)
        controls_layout.addWidget(self.format_combo)
        
        controls_layout.addSpacing(20)
        
        self.convert_btn = self.create_primary_button("开始转换", self.start_conversion)
        self.convert_btn.setEnabled(False)
        controls_layout.addWidget(self.convert_btn)
        
        layout.addWidget(controls_frame)
        
        # Progress
        self.convert_progress = self.create_progress_bar()
        layout.addWidget(self.convert_progress)
        
        self.convert_status = QLabel("")
        self.convert_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.convert_status)
        
        layout.addStretch()
        
        self.reset_list(self.convert_file_list, "👇 拖拽视频文件到此处")
        return page

    # ==========================================
    # 2. Video Cut Page
    # ==========================================
    def create_cut_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        self.setup_header(layout, "视频剪辑", "精确裁剪视频片段")

        # Main Layout: Left (File) + Right (Settings)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)

        # Left: File Selection Area
        left_layout = QVBoxLayout()
        
        self.cut_file_list = DragDropListWidget()
        self.cut_file_list.file_dropped.connect(lambda p: self.on_cut_file_dropped(p))
        self.cut_file_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.cut_file_list)
        
        select_btn = self.create_button("📂 选择文件", lambda: self.select_single_file(self.cut_file_list, self.cut_btn, callback=self.on_cut_file_dropped))
        left_layout.addWidget(select_btn)
        
        content_layout.addLayout(left_layout, 2) # 2/3 width
        
        # Right: Settings Area
        right_frame = QFrame()
        right_frame.setStyleSheet("""
            QFrame {
                background-color: #f6f7f8;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setSpacing(20)
        
        # Info Card
        info_group = QGroupBox("当前视频")
        info_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 18px; border: none; margin-top: 10px; }")
        info_layout = QVBoxLayout(info_group)
        self.cut_info_label = QLabel("暂无视频")
        self.cut_info_label.setStyleSheet("color: #666; font-size: 14px; font-weight: normal;")
        self.cut_info_label.setWordWrap(True)
        info_layout.addWidget(self.cut_info_label)
        right_layout.addWidget(info_group)
        
        # Settings
        settings_group = QGroupBox("剪辑参数")
        settings_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 18px; border: none; margin-top: 10px; }")
        settings_inner_layout = QVBoxLayout(settings_group)
        settings_inner_layout.setSpacing(15)
        
        # Mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式:"))
        self.mode_time_rb = QRadioButton("时间 (秒)")
        self.mode_frame_rb = QRadioButton("帧数")
        self.mode_time_rb.setChecked(True)
        self.mode_time_rb.toggled.connect(self.update_cut_ui_mode)
        
        mode_btn_group = QButtonGroup(page)
        mode_btn_group.addButton(self.mode_time_rb)
        mode_btn_group.addButton(self.mode_frame_rb)
        
        mode_layout.addWidget(self.mode_time_rb)
        mode_layout.addWidget(self.mode_frame_rb)
        settings_inner_layout.addLayout(mode_layout)
        
        # Start
        settings_inner_layout.addWidget(QLabel("开始位置:"))
        self.cut_start_stack = QStackedWidget()
        self.cut_start_time = QDoubleSpinBox()
        self.cut_start_time.setRange(0, 99999)
        self.cut_start_time.setDecimals(2)
        self.style_spinbox(self.cut_start_time)
        self.cut_start_frame = QSpinBox()
        self.cut_start_frame.setRange(0, 999999)
        self.style_spinbox(self.cut_start_frame)
        self.cut_start_stack.addWidget(self.cut_start_time)
        self.cut_start_stack.addWidget(self.cut_start_frame)
        settings_inner_layout.addWidget(self.cut_start_stack)
        
        # End
        settings_inner_layout.addWidget(QLabel("结束位置:"))
        self.cut_end_stack = QStackedWidget()
        self.cut_end_time = QDoubleSpinBox()
        self.cut_end_time.setRange(0, 99999)
        self.cut_end_time.setDecimals(2)
        self.style_spinbox(self.cut_end_time)
        self.cut_end_frame = QSpinBox()
        self.cut_end_frame.setRange(0, 999999)
        self.style_spinbox(self.cut_end_frame)
        self.cut_end_stack.addWidget(self.cut_end_time)
        self.cut_end_stack.addWidget(self.cut_end_frame)
        settings_inner_layout.addWidget(self.cut_end_stack)
        
        right_layout.addWidget(settings_group)
        right_layout.addStretch()
        
        # Action Button
        self.cut_btn = self.create_primary_button("✂️ 开始剪辑", self.start_cut)
        self.cut_btn.setEnabled(False)
        self.cut_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        right_layout.addWidget(self.cut_btn)
        
        content_layout.addWidget(right_frame, 1) # 1/3 width
        
        layout.addLayout(content_layout)
        
        self.cut_progress = self.create_progress_bar()
        layout.addWidget(self.cut_progress)
        
        self.cut_status = QLabel("")
        self.cut_status.setAlignment(Qt.AlignCenter)
        self.cut_status.setStyleSheet("color: #666; margin-top: 10px;")
        layout.addWidget(self.cut_status)
        
        # Store current video info
        self.current_cut_fps = 30.0
        
        self.reset_list(self.cut_file_list, "👇 拖拽视频到此处\n支持 mp4, mkv, avi 等格式")
        return page

    def update_cut_ui_mode(self):
        is_time = self.mode_time_rb.isChecked()
        self.cut_start_stack.setCurrentIndex(0 if is_time else 1)
        self.cut_end_stack.setCurrentIndex(0 if is_time else 1)

    # --- Cut ---
    def on_cut_file_dropped(self, file_path):
        self.set_single_file(file_path, self.cut_file_list, self.cut_btn)
        # self.cut_player.load_video(file_path) # Removed
        
        # Get info
        info = self.processor.get_video_info(file_path)
        if info:
            duration = info['duration']
            fps = info['fps']
            self.current_cut_fps = fps if fps > 0 else 30.0
            total_frames = int(duration * self.current_cut_fps)
            
            self.cut_info_label.setText(f"总时长: {duration}秒 / 总帧数: {total_frames}")
            
            # Update Time inputs
            self.cut_start_time.setMaximum(duration)
            self.cut_end_time.setMaximum(duration)
            self.cut_end_time.setValue(duration)
            
            # Update Frame inputs
            self.cut_start_frame.setMaximum(total_frames)
            self.cut_end_frame.setMaximum(total_frames)
            self.cut_end_frame.setValue(total_frames)
        
    def start_cut(self):
        file_path = self.cut_file_list.item(0).text()
        
        if self.mode_time_rb.isChecked():
            start = self.cut_start_time.value()
            end = self.cut_end_time.value()
        else:
            # Convert frame to seconds
            start_frame = self.cut_start_frame.value()
            end_frame = self.cut_end_frame.value()
            start = start_frame / self.current_cut_fps
            end = end_frame / self.current_cut_fps
        
        if start >= end:
            QMessageBox.warning(self, "错误", "开始时间必须小于结束时间")
            return
            
        self.cut_btn.setEnabled(False)
        self.show_with_animation(self.cut_progress)
        self.cut_progress.setValue(0)
        self.cut_status.setText("正在剪辑中...")
        
        self.worker = Worker(self.processor.cut_video, file_path, start, end)
        self.worker.progress_signal.connect(self.cut_progress.setValue)
        self.worker.finished_signal.connect(self.on_cut_finished)
        self.worker.start()
        
    def on_cut_finished(self, success, msg):
        self.cut_btn.setEnabled(True)
        if success:
            self.cut_status.setText(f"✅ 剪辑成功: {os.path.basename(msg)}")
            self.cut_progress.setValue(100)
        else:
            self.cut_status.setText(f"❌ 失败: {msg}")

    # ==========================================
    # 3. Video Merge Page
    # ==========================================
    def create_merge_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        self.setup_header(layout, "视频合并", "将多个视频拼接为一个文件")
        
        # Main Layout
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)
        
        # Left: List
        left_layout = QVBoxLayout()
        self.merge_list = QListWidget()
        self.merge_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.merge_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.merge_list.itemClicked.connect(self.on_merge_item_clicked)
        self.merge_list.setStyleSheet("""
            QListWidget {
                border: 2px dashed #ccc;
                border-radius: 12px;
                font-size: 16px;
                padding: 10px;
                background-color: #fafafa;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #f0f0f0;
                background-color: white;
                margin-bottom: 5px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: #fff0f5;
                color: #fb7299;
                border: 1px solid #fb7299;
            }
        """)
        left_layout.addWidget(self.merge_list)
        
        btns_layout = QHBoxLayout()
        add_btn = self.create_button("➕ 添加视频", self.add_merge_files)
        clear_btn = self.create_button("🗑️ 清空", self.merge_list.clear)
        btns_layout.addWidget(add_btn)
        btns_layout.addWidget(clear_btn)
        left_layout.addLayout(btns_layout)
        
        content_layout.addLayout(left_layout, 2)
        
        # Right: Settings
        right_frame = QFrame()
        right_frame.setStyleSheet("""
            QFrame {
                background-color: #f6f7f8;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setSpacing(20)
        
        right_layout.addWidget(QLabel("选中视频设置"))
        
        self.merge_range_check = QGroupBox("启用裁剪")
        self.merge_range_check.setCheckable(True)
        self.merge_range_check.setChecked(False)
        self.merge_range_check.toggled.connect(self.save_merge_item_settings)
        self.merge_range_check.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #ddd; border-radius: 6px; margin-top: 10px; padding-top: 10px; }")
        
        range_layout = QVBoxLayout(self.merge_range_check)
        range_layout.setSpacing(10)
        
        range_layout.addWidget(QLabel("开始 (秒):"))
        self.merge_start = QDoubleSpinBox()
        self.merge_start.setRange(0, 99999)
        self.merge_start.valueChanged.connect(self.save_merge_item_settings)
        self.style_spinbox(self.merge_start)
        range_layout.addWidget(self.merge_start)
        
        range_layout.addWidget(QLabel("结束 (秒):"))
        self.merge_end = QDoubleSpinBox()
        self.merge_end.setRange(0, 99999)
        self.merge_end.valueChanged.connect(self.save_merge_item_settings)
        self.style_spinbox(self.merge_end)
        range_layout.addWidget(self.merge_end)
        
        right_layout.addWidget(self.merge_range_check)
        right_layout.addStretch()
        
        self.merge_btn = self.create_primary_button("🔗 开始合并", self.start_merge)
        self.merge_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        right_layout.addWidget(self.merge_btn)
        
        content_layout.addWidget(right_frame, 1)
        
        layout.addLayout(content_layout)
        
        self.merge_progress = self.create_progress_bar()
        layout.addWidget(self.merge_progress)
        
        self.merge_status = QLabel("")
        self.merge_status.setAlignment(Qt.AlignCenter)
        self.merge_status.setStyleSheet("color: #666; margin-top: 10px;")
        layout.addWidget(self.merge_status)
        
        return page

    # --- Merge ---
    def on_merge_item_clicked(self, item):
        file_path = item.text().split(' [')[0]
        if os.path.exists(file_path):
            # self.merge_player.load_video(file_path) # Removed
            pass
            data = item.data(Qt.UserRole)
            self.merge_range_check.blockSignals(True)
            self.merge_start.blockSignals(True)
            self.merge_end.blockSignals(True)
            
            if data:
                self.merge_range_check.setChecked(data.get('enabled', False))
                self.merge_start.setValue(data.get('start', 0))
                self.merge_end.setValue(data.get('end', 0))
            else:
                # Default
                self.merge_range_check.setChecked(False)
                info = self.processor.get_video_info(file_path)
                if info:
                    self.merge_start.setValue(0)
                    self.merge_end.setValue(info['duration'])
            
            self.merge_range_check.blockSignals(False)
            self.merge_start.blockSignals(False)
            self.merge_end.blockSignals(False)

    def save_merge_item_settings(self):
        item = self.merge_list.currentItem()
        if item:
            data = {
                'enabled': self.merge_range_check.isChecked(),
                'start': self.merge_start.value(),
                'end': self.merge_end.value()
            }
            item.setData(Qt.UserRole, data)
            base_text = item.text().split(' [')[0]
            if data['enabled']:
                item.setText(f"{base_text} [裁剪: {data['start']}s - {data['end']}s]")
            else:
                item.setText(base_text)

    def add_merge_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", self.main_window.crawler.data_dir,
            "Video Files (*.mp4 *.mkv *.avi *.mov *.flv)"
        )
        if files:
            for f in files:
                item = QListWidgetItem(f)
                # Default data
                info = self.processor.get_video_info(f)
                duration = info['duration'] if info else 0
                item.setData(Qt.UserRole, {'enabled': False, 'start': 0, 'end': duration})
                self.merge_list.addItem(item)
                
    def start_merge(self):
        if self.merge_list.count() < 2:
            QMessageBox.warning(self, "提示", "请至少添加两个文件进行合并")
            return
            
        # Collect files and process cuts if needed
        final_files = []
        temp_files = []
        
        import tempfile
        temp_dir = tempfile.gettempdir()
        
        self.merge_btn.setEnabled(False)
        self.show_with_animation(self.merge_progress)
        self.merge_progress.setValue(0)
        self.merge_status.setText("正在处理...")
        
        try:
            for i in range(self.merge_list.count()):
                item = self.merge_list.item(i)
                file_path = item.text().split(' [')[0]
                data = item.data(Qt.UserRole)
                
                if data and data.get('enabled'):
                    # Need cut
                    start = data['start']
                    end = data['end']
                    
                    self.merge_status.setText(f"正在裁剪第 {i+1} 个视频...")
                    temp_out = os.path.join(temp_dir, f"temp_merge_cut_{i}_{int(time.time())}.mp4")
                    
                    success, msg = self.processor.cut_video(file_path, start, end, temp_out)
                    if success:
                        final_files.append(temp_out)
                        temp_files.append(temp_out)
                    else:
                        raise Exception(f"裁剪失败: {file_path}")
                else:
                    final_files.append(file_path)
            
            # Merge
            self.merge_status.setText("正在合并所有片段...")
            
            merge_dir = os.path.join(self.main_window.crawler.data_dir, "merge")
            if not os.path.exists(merge_dir):
                os.makedirs(merge_dir)
                
            base_name = os.path.splitext(os.path.basename(final_files[0]))[0]
            output_path = os.path.join(merge_dir, f"{base_name}_merged.mp4")
            
            counter = 1
            while os.path.exists(output_path):
                output_path = os.path.join(merge_dir, f"{base_name}_merged_{counter}.mp4")
                counter += 1
                
            self.worker = Worker(self.processor.merge_video_files, final_files, output_path)
            self.worker.progress_signal.connect(self.merge_progress.setValue)
            self.worker.finished_signal.connect(lambda s, m: self.on_merge_finished_cleanup(s, m, merge_dir, temp_files))
            self.worker.start()
            
        except Exception as e:
            self.merge_btn.setEnabled(True)
            self.merge_status.setText(f"❌ 错误: {e}")
            # Cleanup
            for f in temp_files:
                if os.path.exists(f):
                    os.remove(f)

    def on_merge_finished_cleanup(self, success, msg, merge_dir, temp_files):
        # Cleanup temp files
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass
                
        self.on_merge_finished(success, msg, merge_dir)
    def create_watermark_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        self.setup_header(layout, "去水印", "自定义区域去除视频水印")
        
        self.wm_file_list = DragDropListWidget()
        self.wm_file_list.file_dropped.connect(lambda p: self.set_single_file(p, self.wm_file_list, self.wm_btn))
        layout.addWidget(self.wm_file_list)
        
        # Area Selection
        area_group = QGroupBox("水印区域 (像素)")
        area_group.setStyleSheet("QGroupBox { font-size: 20px; color: #333; border: 1px solid #ddd; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        area_layout = QHBoxLayout(area_group)
        
        self.wm_x = QSpinBox()
        self.wm_y = QSpinBox()
        self.wm_w = QSpinBox()
        self.wm_h = QSpinBox()
        
        for label, spin in [("X:", self.wm_x), ("Y:", self.wm_y), ("宽:", self.wm_w), ("高:", self.wm_h)]:
            area_layout.addWidget(QLabel(label))
            spin.setRange(0, 9999)
            self.style_spinbox(spin)
            area_layout.addWidget(spin)
            
        # Default values
        self.wm_x.setValue(10)
        self.wm_y.setValue(10)
        self.wm_w.setValue(200)
        self.wm_h.setValue(60)
            
        layout.addWidget(area_group)
        
        # Controls
        controls_frame = self.create_control_frame()
        controls_layout = QHBoxLayout(controls_frame)
        
        select_btn = self.create_button("选择文件", lambda: self.select_single_file(self.wm_file_list, self.wm_btn))
        controls_layout.addWidget(select_btn)
        
        controls_layout.addStretch()
        
        self.wm_btn = self.create_primary_button("开始去水印", self.start_watermark)
        self.wm_btn.setEnabled(False)
        controls_layout.addWidget(self.wm_btn)
        
        layout.addWidget(controls_frame)
        
        self.wm_progress = self.create_progress_bar()
        layout.addWidget(self.wm_progress)
        
        self.wm_status = QLabel("")
        self.wm_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.wm_status)
        
        layout.addStretch()
        self.reset_list(self.wm_file_list, "👇 拖拽视频文件到此处")
        return page

    # ==========================================
    # 5. Video Compress Page
    # ==========================================
    def create_compress_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        self.setup_header(layout, "视频压缩", "调整分辨率和画质以减小体积")
        
        self.compress_file_list = DragDropListWidget()
        self.compress_file_list.file_dropped.connect(lambda p: self.set_single_file(p, self.compress_file_list, self.compress_btn))
        layout.addWidget(self.compress_file_list)
        
        # Settings
        settings_group = QGroupBox("压缩设置")
        settings_group.setStyleSheet("QGroupBox { font-size: 20px; color: #333; border: 1px solid #ddd; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        settings_layout = QHBoxLayout(settings_group)
        
        settings_layout.addWidget(QLabel("目标分辨率:"))
        self.res_combo = QComboBox()
        self.res_combo.addItems(["1920x1080", "1280x720", "854x480", "640x360"])
        self.style_combo(self.res_combo)
        settings_layout.addWidget(self.res_combo)
        
        settings_layout.addWidget(QLabel("画质 (CRF):"))
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(18, 51)
        self.crf_spin.setValue(23)
        self.crf_spin.setToolTip("数值越小画质越好，体积越大。推荐23。")
        self.style_spinbox(self.crf_spin)
        settings_layout.addWidget(self.crf_spin)
        
        layout.addWidget(settings_group)
        
        # Controls
        controls_frame = self.create_control_frame()
        controls_layout = QHBoxLayout(controls_frame)
        
        select_btn = self.create_button("选择文件", lambda: self.select_single_file(self.compress_file_list, self.compress_btn))
        controls_layout.addWidget(select_btn)
        
        controls_layout.addStretch()
        
        self.compress_btn = self.create_primary_button("开始压缩", self.start_compress)
        self.compress_btn.setEnabled(False)
        controls_layout.addWidget(self.compress_btn)
        
        layout.addWidget(controls_frame)
        
        self.compress_progress = self.create_progress_bar()
        layout.addWidget(self.compress_progress)
        
        self.compress_status = QLabel("")
        self.compress_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.compress_status)
        
        layout.addStretch()
        self.reset_list(self.compress_file_list, "👇 拖拽视频文件到此处")
        return page

    # ==========================================
    # Helper Methods
    # ==========================================
    def setup_header(self, layout, title, subtitle):
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #333;")
        layout.addWidget(title_label)
        
        sub_label = QLabel(subtitle)
        sub_label.setStyleSheet("font-size: 20px; color: #999;")
        layout.addWidget(sub_label)

    def create_control_frame(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #f6f7f8;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        return frame

    def create_button(self, text, callback):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                padding: 10px 20px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                color: #333;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fff0f5;
                border-color: #fb7299;
                color: #fb7299;
            }
        """)
        btn.clicked.connect(callback)
        return btn

    def create_primary_button(self, text, callback):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                padding: 12px 30px;
                background-color: #fb7299;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
            QPushButton:disabled {
                background-color: #e0e0e0;
                color: #999;
            }
            QPushButton:pressed {
                background-color: #e45c84;
            }
        """)
        btn.clicked.connect(callback)
        return btn

    def create_progress_bar(self):
        bar = QProgressBar()
        bar.setVisible(False)
        bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 8px;
                background-color: #e0e0e0;
                text-align: center;
                height: 25px;
                font-size: 18px;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #fb7299;
                border-radius: 8px;
            }
        """)
        return bar

    def style_combo(self, combo):
        combo.setStyleSheet("""
            QComboBox {
                font-size: 20px;
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #fb7299;
            }
        """)

    def style_spinbox(self, spin):
        spin.setStyleSheet("""
            QSpinBox, QDoubleSpinBox {
                font-size: 20px;
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
            }
            QSpinBox:hover, QDoubleSpinBox:hover {
                border-color: #fb7299;
            }
        """)

    def reset_list(self, list_widget, text):
        list_widget.clear()
        item = QListWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        item.setFlags(Qt.NoItemFlags)
        list_widget.addItem(item)
        
    def set_single_file(self, file_path, list_widget, btn):
        list_widget.clear()
        list_widget.addItem(file_path)
        if btn:
            btn.setEnabled(True)
        return file_path
        
    def select_single_file(self, list_widget, btn, callback=None):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", self.main_window.crawler.data_dir, 
            "Video Files (*.mp4 *.mkv *.avi *.mov *.flv);;All Files (*.*)"
        )
        if file_path:
            self.set_single_file(file_path, list_widget, btn)
            if callback:
                callback(file_path)

    # ==========================================
    # Logic Implementation
    # ==========================================
    
    # --- Convert ---
    def start_conversion(self):
        if self.convert_file_list.count() == 0 or not self.convert_file_list.item(0).flags() & Qt.ItemIsEnabled:
            return
        
        file_path = self.convert_file_list.item(0).text()
        fmt = self.format_combo.currentText()
        
        self.convert_btn.setEnabled(False)
        self.show_with_animation(self.convert_progress)
        self.convert_progress.setValue(0)
        self.convert_status.setText("正在转换中...")
        
        self.worker = Worker(self.processor.convert_video, file_path, fmt)
        self.worker.progress_signal.connect(self.convert_progress.setValue)
        self.worker.finished_signal.connect(self.on_convert_finished)
        self.worker.start()
        
    def on_convert_finished(self, success, msg):
        self.convert_btn.setEnabled(True)
        if success:
            self.convert_status.setText(f"✅ 转换成功: {os.path.basename(msg)}")
            self.convert_progress.setValue(100)
        else:
            self.convert_status.setText(f"❌ 失败: {msg}")

    # --- Cut ---
    # (Moved to top)

    # --- Merge ---
    # (Moved to top)

    # --- Watermark ---
    def start_watermark(self):
        if self.wm_file_list.count() == 0 or not self.wm_file_list.item(0).flags() & Qt.ItemIsEnabled:
            return
            
        file_path = self.wm_file_list.item(0).text()
        x = self.wm_x.value()
        y = self.wm_y.value()
        w = self.wm_w.value()
        h = self.wm_h.value()
        
        self.wm_btn.setEnabled(False)
        self.show_with_animation(self.wm_progress)
        self.wm_progress.setValue(0)
        self.wm_status.setText("正在去水印...")
        
        self.worker = Worker(self.processor.remove_watermark_custom, file_path, x, y, w, h)
        self.worker.progress_signal.connect(self.wm_progress.setValue)
        self.worker.finished_signal.connect(self.on_wm_finished)
        self.worker.start()
        
    def on_wm_finished(self, success, msg):
        self.wm_btn.setEnabled(True)
        if success:
            self.wm_status.setText(f"✅ 去水印成功: {os.path.basename(msg)}")
            self.wm_progress.setValue(100)
        else:
            self.wm_status.setText(f"❌ 失败: {msg}")

    # --- Compress ---
    def start_compress(self):
        if self.compress_file_list.count() == 0 or not self.compress_file_list.item(0).flags() & Qt.ItemIsEnabled:
            return
            
        file_path = self.compress_file_list.item(0).text()
        res = self.res_combo.currentText()
        crf = self.crf_spin.value()
        
        self.compress_btn.setEnabled(False)
        self.show_with_animation(self.compress_progress)
        self.compress_progress.setValue(0)
        self.compress_status.setText("正在压缩中...")
        
        self.worker = Worker(self.processor.compress_video, file_path, res, crf)
        self.worker.progress_signal.connect(self.compress_progress.setValue)
        self.worker.finished_signal.connect(self.on_compress_finished)
        self.worker.start()
        
    def on_compress_finished(self, success, msg):
        self.compress_btn.setEnabled(True)
        if success:
            self.compress_status.setText(f"✅ 压缩成功: {os.path.basename(msg)}")
            self.compress_progress.setValue(100)
        else:
            self.compress_status.setText(f"❌ 失败: {msg}")
