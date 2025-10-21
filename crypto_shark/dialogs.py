
import requests

from PySide6.QtCore import Qt, QRunnable, Slot, QThreadPool, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QDialog, QScrollArea, QWidget, QGridLayout,
    QVBoxLayout, QPushButton, QLabel, QSizePolicy
)

class IconLoader(QRunnable):
    def __init__(self, url: str, button: QPushButton, signal: Signal):
        super().__init__()
        self.url, self.button, self.signal = url, button, signal

    @Slot()
    def run(self):
        try:
            resp = requests.get(self.url, timeout=5)
            resp.raise_for_status()
            pix = QPixmap(); pix.loadFromData(resp.content)
            icon = QIcon(pix)
            self.signal.emit(self.button, icon)
        except:
            pass

class AddCryptoDialog(QDialog):

    icon_ready = Signal(object, object)

    def __init__(self, parent=None, coins=None):
        super().__init__(parent)
        self.setWindowTitle("Add Crypto")
        self.resize(800,600)
        self.selected = None
        self.coins = coins or []


        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        container = QWidget()
        grid = QGridLayout(container)
        scroll.setWidget(container)


        self.pool = QThreadPool.globalInstance()
        self.icon_ready.connect(self._set_button_icon)


        for idx, coin in enumerate(self.coins):
            row, col = divmod(idx, 5)

            frame = QWidget()
            vbox = QVBoxLayout(frame)
            vbox.setContentsMargins(4,4,4,4)
            vbox.setSpacing(4)
            frame.setStyleSheet("""
                background-color: #3A4D5A;
                border: 2px solid #607D8B;
                border-radius: 8px;""")

            btn = QPushButton()
            btn.setFixedSize(64,64)
            btn.setIconSize(QSize(48,48))
            btn.setStyleSheet("background: transparent; border: none;")
            btn.clicked.connect(lambda _, cid=coin["id"]: self._select(cid))
            vbox.addWidget(btn, alignment=Qt.AlignCenter)

            label = QLabel(coin["symbol"].upper())
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: white; font-weight: bold;")
            vbox.addWidget(label)

            grid.addWidget(frame, row, col)


            loader = IconLoader(coin["image"], btn, self.icon_ready)
            self.pool.start(loader)

    @Slot(object, object)
    def _set_button_icon(self, button: QPushButton, icon: QIcon):
        button.setIcon(icon)

    def _select(self, coin_id: str):
        self.selected = coin_id
        self.accept()
