from PyQt5.QtWidgets import QComboBox

class NoScrollComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(True)  # Ensure it can receive focus

    def wheelEvent(self, event):
        # Ignore wheel event to prevent accidental value change
        event.ignore()
