from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel, 
                             QPushButton, QListWidget, QStackedWidget, QDoubleSpinBox, 
                             QSpinBox, QAbstractItemView)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QBrush, QPixmap
import os
from ui.widgets.custom_combobox import NoScrollComboBox

class MergeItemWidget(QWidget):
    removed = pyqtSignal(QWidget)
    
    def __init__(self, path, duration=0, fps=30):
        super().__init__()
        self.path = path
        self.duration = duration
        self.fps = fps
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Left colored strip (optional, using a Frame)
        strip = QFrame()
        strip.setFixedWidth(4)
        strip.setStyleSheet("background-color: #fb7299; border-radius: 2px;")
        layout.addWidget(strip)
        
        # Icon
        icon_label = QLabel("🎬")
        icon_label.setStyleSheet("font-size: 24px; background-color: #f0f0f0; border-radius: 4px; padding: 5px;")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(40, 40)
        layout.addWidget(icon_label)
        
        # Info Layout (Name + Duration)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        # Filename
        name_label = QLabel(os.path.basename(self.path))
        name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #333;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        # Duration info
        dur_text = f"时长: {self.duration}s"
        dur_label = QLabel(dur_text)
        dur_label.setStyleSheet("font-size: 12px; color: #888;")
        info_layout.addWidget(dur_label)
        
        layout.addLayout(info_layout, 1)
        
        # Range Selection
        range_group = QFrame()
        range_group.setStyleSheet("background-color: #f9f9f9; border-radius: 6px; padding: 5px; border: 1px solid #eee;")
        range_layout = QHBoxLayout(range_group)
        range_layout.setContentsMargins(5, 5, 5, 5)
        range_layout.setSpacing(8)
        
        range_layout.addWidget(QLabel("截取:"))
        
        # Unit selection
        self.unit_combo = NoScrollComboBox()
        self.unit_combo.addItems(["秒", "帧"])
        self.unit_combo.setFixedWidth(60)
        self.unit_combo.currentIndexChanged.connect(self.update_inputs)
        range_layout.addWidget(self.unit_combo)
        
        # Input Stack
        self.input_stack = QStackedWidget()
        self.input_stack.setFixedHeight(30)
        
        # 1. Time Mode
        self.time_widget = QWidget()
        time_layout = QHBoxLayout(self.time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(5)
        
        self.start_spin = QDoubleSpinBox()
        self.start_spin.setRange(0, 99999)
        self.start_spin.setValue(0)
        self.start_spin.setDecimals(1)
        self.start_spin.setSuffix("s")
        self.start_spin.setFixedWidth(80)
        self.style_spinbox(self.start_spin)
        time_layout.addWidget(self.start_spin)
        
        time_layout.addWidget(QLabel("-"))
        
        self.end_spin = QDoubleSpinBox()
        self.end_spin.setRange(0, 99999)
        self.end_spin.setValue(self.duration if self.duration > 0 else 0)
        self.end_spin.setDecimals(1)
        self.end_spin.setSuffix("s")
        self.end_spin.setFixedWidth(80)
        self.style_spinbox(self.end_spin)
        time_layout.addWidget(self.end_spin)
        
        # 2. Frame Mode
        self.frame_widget = QWidget()
        frame_layout = QHBoxLayout(self.frame_widget)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(5)
        
        self.start_frame = QSpinBox()
        self.start_frame.setRange(0, 999999)
        self.start_frame.setValue(0)
        self.start_frame.setFixedWidth(80)
        self.style_spinbox(self.start_frame)
        frame_layout.addWidget(self.start_frame)
        
        frame_layout.addWidget(QLabel("-"))
        
        total_frames = int(self.duration * self.fps) if self.fps > 0 else 0
        self.end_frame = QSpinBox()
        self.end_frame.setRange(0, 999999)
        self.end_frame.setValue(total_frames)
        self.end_frame.setFixedWidth(80)
        self.style_spinbox(self.end_frame)
        frame_layout.addWidget(self.end_frame)
        
        self.input_stack.addWidget(self.time_widget)
        self.input_stack.addWidget(self.frame_widget)
        
        range_layout.addWidget(self.input_stack)
        
        layout.addWidget(range_group)
        
        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(30, 30)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.setToolTip("移除此项")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ccc;
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 15px;
            }
            QPushButton:hover {
                color: #ff4d4f;
                background-color: #fff1f0;
            }
        """)
        remove_btn.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(remove_btn)
        
        # Main Widget Style
        self.setStyleSheet("""
            MergeItemWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            MergeItemWidget:hover {
                border-color: #fb7299;
                background-color: #fffbfc;
            }
        """)

    def update_inputs(self, index):
        self.input_stack.setCurrentIndex(index)
        
    def get_range(self):
        if self.input_stack.currentIndex() == 0: # Time
             return self.start_spin.value(), self.end_spin.value()
        else: # Frame
             start_f = self.start_frame.value()
             end_f = self.end_frame.value()
             # Convert to seconds
             start = start_f / self.fps if self.fps > 0 else 0
             end = end_f / self.fps if self.fps > 0 else 0
             return start, end

    def style_spinbox(self, spin):
        spin.setStyleSheet("""
            QDoubleSpinBox, QSpinBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 2px 5px;
                background: white;
                selection-background-color: #fb7299;
            }
            QDoubleSpinBox:focus, QSpinBox:focus {
                border-color: #fb7299;
            }
        """)

class VideoFileWidget(QWidget):
    def __init__(self, path, duration=0, size=0):
        super().__init__()
        self.path = path
        self.duration = duration
        self.size = size
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Left colored strip
        strip = QFrame()
        strip.setFixedWidth(4)
        strip.setStyleSheet("background-color: #fb7299; border-radius: 2px;")
        layout.addWidget(strip)
        
        # Icon
        icon_label = QLabel("🎬")
        icon_label.setStyleSheet("font-size: 24px; background-color: #f0f0f0; border-radius: 4px; padding: 5px;")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(40, 40)
        layout.addWidget(icon_label)
        
        # Info Layout
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        # Filename
        name_label = QLabel(os.path.basename(self.path))
        name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #333;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        # Details
        details_text = []
        if self.duration > 0:
            details_text.append(f"时长: {self.duration}s")
        if self.size > 0:
            details_text.append(f"大小: {self.size:.2f}MB")
            
        det_label = QLabel(" | ".join(details_text))
        det_label.setStyleSheet("font-size: 12px; color: #888;")
        info_layout.addWidget(det_label)
        
        layout.addLayout(info_layout, 1)
        
        # Style
        self.setStyleSheet("""
            VideoFileWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            VideoFileWidget:hover {
                border-color: #fb7299;
                background-color: #fffbfc;
            }
        """)

class DragDropListWidget(QListWidget):
    file_dropped = pyqtSignal(str)
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)
        self.setCursor(Qt.PointingHandCursor)  # Add pointer cursor
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
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

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
