from PyQt5.QtCore import QObject, pyqtSignal, QUrl
from PyQt5.QtGui import QPixmap
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

class ImageLoader(QObject):
    """
    通用图片加载器，支持缓存和异步加载
    """
    # 信号：加载完成 (url, pixmap)
    image_loaded = pyqtSignal(str, QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.network_manager = QNetworkAccessManager(self)
        self.cache = {} # 内存缓存: url -> QPixmap
        self._pending_callbacks = {} # url -> list of callbacks

    def load_image(self, url, callback=None):
        """
        加载图片
        :param url: 图片URL
        :param callback: 加载完成后的回调函数 callback(pixmap)
        """
        if not url:
            return

        # 1. 检查缓存
        if url in self.cache:
            pixmap = self.cache[url]
            if callback:
                callback(pixmap)
            self.image_loaded.emit(url, pixmap)
            return

        # 2. 如果正在下载，将回调加入队列
        if url in self._pending_callbacks:
            if callback:
                self._pending_callbacks[url].append(callback)
            return

        # 3. 开始下载
        self._pending_callbacks[url] = []
        if callback:
            self._pending_callbacks[url].append(callback)

        request = QNetworkRequest(QUrl(url))
        # 设置Referer，防止防盗链 (B站图片通常需要)
        request.setRawHeader(b"Referer", b"https://www.bilibili.com/")
        request.setRawHeader(b"User-Agent", b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self._on_download_finished(reply, url))

    def _on_download_finished(self, reply, url):
        reply.deleteLater()
        
        if reply.error() != QNetworkReply.NoError:
            # 下载失败
            if url in self._pending_callbacks:
                del self._pending_callbacks[url]
            return

        data = reply.readAll()
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            # 存入缓存
            self.cache[url] = pixmap
            
            # 执行回调
            callbacks = self._pending_callbacks.get(url, [])
            for cb in callbacks:
                try:
                    cb(pixmap)
                except Exception as e:
                    print(f"Image callback error: {e}")
            
            # 发送信号
            self.image_loaded.emit(url, pixmap)
        
        # 清理等待队列
        if url in self._pending_callbacks:
            del self._pending_callbacks[url]

    def get_from_cache(self, url):
        return self.cache.get(url)

    def clear_cache(self):
        self.cache.clear()
