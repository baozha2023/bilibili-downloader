from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal, QSize
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor

class ZoomableImageWidget(QWidget):
    """
    A widget that displays an image and supports:
    - Zooming (Mouse Wheel)
    - Panning (Middle/Right Mouse Drag)
    - Region Selection (Left Mouse Drag)
    """
    rect_selected = pyqtSignal(QRect)  # Emits selected rect in image coordinates

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #000;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Image state
        self.image = None
        self.pixmap = None
        
        # Transform state
        self.scale_factor = 1.0
        self.offset = QPoint(0, 0)
        self.min_scale = 0.1
        self.max_scale = 10.0
        
        # Selection state
        self.selection_rect = QRect()
        self.is_selecting = False
        self.selection_start = QPoint()
        self.selection_enabled = True
        
        # Panning state
        self.is_panning = False
        self.pan_start = QPoint()
        
        # Cursors
        self.setCursor(Qt.CrossCursor)

    def set_image(self, image):
        """Set the image to display (QImage or QPixmap)"""
        if isinstance(image, QImage):
            self.image = image
            self.pixmap = QPixmap.fromImage(image)
        elif isinstance(image, QPixmap):
            self.pixmap = image
            self.image = image.toImage()
        else:
            self.image = None
            self.pixmap = None
            
        if self.pixmap:
            # Reset view to fit
            self.fit_to_window()
        
        self.update()

    def fit_to_window(self):
        """Fit image to current window size"""
        if not self.pixmap or self.pixmap.isNull():
            return
            
        w_ratio = self.width() / self.pixmap.width()
        h_ratio = self.height() / self.pixmap.height()
        self.scale_factor = min(w_ratio, h_ratio)
        
        # Center image
        new_w = self.pixmap.width() * self.scale_factor
        new_h = self.pixmap.height() * self.scale_factor
        
        self.offset = QPoint(
            int((self.width() - new_w) / 2),
            int((self.height() - new_h) / 2)
        )

    def set_selection_enabled(self, enabled):
        self.selection_enabled = enabled
        self.setCursor(Qt.CrossCursor if enabled else Qt.ArrowCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(20, 20, 20)) # Dark background
        
        if self.pixmap and not self.pixmap.isNull():
            painter.save()
            
            # Apply transformation
            painter.translate(self.offset)
            painter.scale(self.scale_factor, self.scale_factor)
            
            # Draw image
            painter.drawPixmap(0, 0, self.pixmap)
            
            # Draw selection rect (in image coordinates)
            if not self.selection_rect.isNull():
                # Draw rect on top of image
                painter.setPen(QPen(QColor(255, 0, 0), 2 / self.scale_factor, Qt.SolidLine)) # Keep line width constant on screen
                painter.drawRect(self.selection_rect)
                painter.setBrush(QColor(255, 0, 0, 50))
                painter.drawRect(self.selection_rect)
                
            painter.restore()

    def wheelEvent(self, event):
        if not self.pixmap:
            return
            
        # Zoom logic
        angle = event.angleDelta().y()
        factor = 1.1 if angle > 0 else 0.9
        
        new_scale = self.scale_factor * factor
        new_scale = max(self.min_scale, min(new_scale, self.max_scale))
        
        if new_scale != self.scale_factor:
            # Zoom centered on mouse position
            mouse_pos = event.pos()
            
            # Calculate mouse position in image coordinates before zoom
            # mouse = offset + image_pos * scale
            # image_pos = (mouse - offset) / scale
            
            img_x = (mouse_pos.x() - self.offset.x()) / self.scale_factor
            img_y = (mouse_pos.y() - self.offset.y()) / self.scale_factor
            
            self.scale_factor = new_scale
            
            # Calculate new offset to keep mouse over same image point
            # new_offset = mouse - image_pos * new_scale
            
            new_offset_x = mouse_pos.x() - img_x * self.scale_factor
            new_offset_y = mouse_pos.y() - img_y * self.scale_factor
            
            self.offset = QPoint(int(new_offset_x), int(new_offset_y))
            self.update()

    def mousePressEvent(self, event):
        if not self.pixmap:
            return
            
        if event.button() == Qt.LeftButton and self.selection_enabled:
            # Start selection
            self.is_selecting = True
            # Map to image coords
            img_pos = self.map_to_image(event.pos())
            self.selection_start = img_pos
            self.selection_rect = QRect(img_pos, img_pos)
            self.update()
            
        elif event.button() in (Qt.MiddleButton, Qt.RightButton):
            # Start panning
            self.is_panning = True
            self.pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if not self.pixmap:
            return
            
        if self.is_selecting:
            img_pos = self.map_to_image(event.pos())
            # Clamp to image bounds
            img_pos.setX(max(0, min(img_pos.x(), self.pixmap.width())))
            img_pos.setY(max(0, min(img_pos.y(), self.pixmap.height())))
            
            self.selection_rect = QRect(self.selection_start, img_pos).normalized()
            self.update()
            
        elif self.is_panning:
            delta = event.pos() - self.pan_start
            self.offset += delta
            self.pan_start = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.is_selecting:
            self.is_selecting = False
            if self.selection_rect.isValid():
                self.rect_selected.emit(self.selection_rect)
                
        elif self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.CrossCursor if self.selection_enabled else Qt.ArrowCursor)

    def map_to_image(self, widget_pos):
        """Map widget coordinates to image coordinates"""
        x = (widget_pos.x() - self.offset.x()) / self.scale_factor
        y = (widget_pos.y() - self.offset.y()) / self.scale_factor
        return QPoint(int(x), int(y))

    def get_selection(self):
        return self.selection_rect
