import logging
from PyQt5.QtCore import QObject, pyqtSignal

class QtLogHandler(logging.Handler, QObject):
    """
    自定义日志处理器，将日志信号发送到UI
    """
    log_signal = pyqtSignal(str, str)  # message, level

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        try:
            # Check if object is still alive (PyQt5)
            # This is a bit tricky in pure Python, but we can catch the specific runtime error
            msg = self.format(record)
            level = record.levelname.lower()
            if level == 'critical':
                level = 'error'
            
            # Avoid infinite loop if logging happens inside log_signal handler
            self.log_signal.emit(msg, level)
        except RuntimeError as e:
            if "wrapped C/C++ object" in str(e):
                # Object is deleted, stop logging
                pass
            else:
                self.handleError(record)
        except Exception:
            self.handleError(record)
