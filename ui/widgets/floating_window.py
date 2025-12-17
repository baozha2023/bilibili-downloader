from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QApplication
from PyQt5.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QFont, QPixmap, QRegion, QBitmap, QPainterPath, QFontMetrics
import os
import sys

import random

class FloatingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Fixed size: 80x100 (80x80 for image, 20 for progress)
        self.setFixedSize(80, 100)
        
        # Load background images
        self.download_pixmap = None    # Downloading image
        self.rest1_pixmap = None       # Idle image 1
        self.rest2_pixmap = None       # Idle image 2
        self.current_pixmap = None     # Currently displayed image
        
        self.load_resources()
        
        # State
        self.is_dragging = False
        self.drag_position = QPoint()
        self.progress = 0
        self.speed = "0.00 MB/s"
        self.is_visible_setting = False
        self.is_downloading = False # Track download state explicitly
        
        # Animation state
        self.scale_factor = 1.0
        self.hover_timer = QTimer(self)
        self.hover_timer.setInterval(16) # ~60 FPS
        self.hover_timer.timeout.connect(self.update_hover_animation)
        self.target_scale = 1.0
        
        # Timer for dynamic idle image switching
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.switch_idle_image)
        self.idle_timer.start(10000) # Switch every 10 seconds
        
        # Set initial image
        self.switch_idle_image()
        
        # Initial position flag
        self.is_first_show = True

    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def load_resources(self):
        # Helper to load and scale
        def load_and_scale(name):
            path = self.resource_path(f"resource/{name}")
            if os.path.exists(path):
                pix = QPixmap(path)
                return pix.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            return None

        # Load specific images
        self.download_pixmap = load_and_scale("floating_window_download.png")
        # Fallback for download image (backward compatibility)
        if not self.download_pixmap:
             self.download_pixmap = load_and_scale("floating_window.png")
             
        self.rest1_pixmap = load_and_scale("floating_window_rest1.png")
        self.rest2_pixmap = load_and_scale("floating_window_rest2.png")
        
        # Fallback for rest images if not found, try to use download image or old idle image
        if not self.rest1_pixmap:
            self.rest1_pixmap = load_and_scale("floating_window_idle.png") or self.download_pixmap
            
        if not self.rest2_pixmap:
            # If rest2 is missing, just use rest1 (no random switching effect effectively)
            self.rest2_pixmap = self.rest1_pixmap

    def switch_idle_image(self):
        """Randomly switch between rest images if in idle mode"""
        if not self.is_downloading:
            options = []
            if self.rest1_pixmap: options.append(self.rest1_pixmap)
            if self.rest2_pixmap: options.append(self.rest2_pixmap)
            
            if options:
                self.current_pixmap = random.choice(options)
            else:
                self.current_pixmap = self.download_pixmap
            self.update()

    def update_status(self, progress, speed_str):
        self.progress = progress
        self.speed = speed_str
        
        if not self.is_downloading:
            self.is_downloading = True
            self.idle_timer.stop() # Stop idle animation
            self.current_pixmap = self.download_pixmap
            
        self.update()
        
    def reset(self):
        self.progress = 0
        self.speed = "0.00 MB/s"
        self.is_downloading = False
        
        # Resume idle animation
        self.switch_idle_image()
        if not self.idle_timer.isActive():
            self.idle_timer.start(10000)
            
        self.update()

    def set_visibility(self, visible):
        self.is_visible_setting = visible
        if visible:
            if self.is_first_show:
                self.move_to_bottom_right()
                self.is_first_show = False
            self.show()
        else:
            self.hide()
            
    def move_to_bottom_right(self):
        """Move window to bottom right corner of the screen"""
        desktop = QApplication.desktop()
        screen_rect = desktop.availableGeometry(desktop.primaryScreen())
        x = screen_rect.width() - self.width() - 50
        y = screen_rect.height() - self.height() - 50
        self.move(x, y)
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.is_dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        
    def enterEvent(self, event):
        self.target_scale = 1.1
        if not self.hover_timer.isActive():
            self.hover_timer.start()
            
    def leaveEvent(self, event):
        self.target_scale = 1.0
        if not self.hover_timer.isActive():
            self.hover_timer.start()
            
    def update_hover_animation(self):
        """Smoothly interpolate scale factor"""
        step = 0.02
        if self.scale_factor < self.target_scale:
            self.scale_factor = min(self.scale_factor + step, self.target_scale)
        elif self.scale_factor > self.target_scale:
            self.scale_factor = max(self.scale_factor - step, self.target_scale)
            
        self.update()
        
        if abs(self.scale_factor - self.target_scale) < 0.001:
            self.hover_timer.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Apply hover scale animation
        # We scale from the center of the image area (40, 40)
        center_x = 40
        center_y = 40
        painter.translate(center_x, center_y)
        painter.scale(self.scale_factor, self.scale_factor)
        painter.translate(-center_x, -center_y)
        
        # Determine which image to show
        # Logic moved to update_status and switch_idle_image, so we just use self.current_pixmap
        # But ensure we are safe if current_pixmap is None
        if self.current_pixmap is None:
             self.switch_idle_image()
        
        # 1. Draw Background Image (Centered in top 80x80 area)
        img_area_height = 80
        if self.current_pixmap:
            # Calculate centering position
            x = (self.width() - self.current_pixmap.width()) // 2
            y = (img_area_height - self.current_pixmap.height()) // 2
            painter.drawPixmap(x, y, self.current_pixmap)
        else:
            # Fallback drawing if no image
            bg_color = QColor(251, 114, 153, 230) 
            painter.setBrush(QBrush(bg_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, 80, 80, 15, 15)
            
        # Only draw progress info if there is progress and we are downloading
        if self.is_downloading and self.progress > 0:
            # 2. Draw Progress Bar (Bottom 20px area: y=80 to y=100)
            # Center the bar vertically in this 20px area
            bar_area_y = 80
            bar_area_h = 20
            
            bar_w = 70
            bar_h = 6  # Thinner bar
            bar_x = (self.width() - bar_w) // 2
            bar_y = bar_area_y + (bar_area_h - bar_h) // 2
            
            # Bar Background
            painter.setBrush(QBrush(QColor(230, 230, 230)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)
            
            # Bar Foreground
            fill_w = int(bar_w * (self.progress / 100))
            if fill_w > 0:
                painter.setBrush(QBrush(QColor(251, 114, 153)))
                painter.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 3, 3)
                
            # No text as requested

