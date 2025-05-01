from PySide6.QtCore    import QRunnable, Slot, QThreadPool, Signal
from PySide6.QtGui     import QPixmap


class IconLoader(QRunnable):
    def __init__(self, url, list_widget, row, signal):
        super().__init__()
        self.url     = url
        self.list_w  = list_widget
        self.row     = row
        self.signal  = signal

    @Slot()
    def run(self):
        try:
            import requests
            resp = requests.get(self.url, timeout=5)
            resp.raise_for_status()
            pix = QPixmap()
            pix.loadFromData(resp.content)
            self.signal.emit(self.row, pix)
        except:
            pass
