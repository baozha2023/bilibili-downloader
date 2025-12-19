from PyQt5.QtCore import QThread, pyqtSignal

class GenericWorker(QThread):
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
        try:
            success, msg = self.func(*self.args, **self.kwargs)
            self.finished_signal.emit(success, msg)
        except Exception as e:
            self.finished_signal.emit(False, str(e))
