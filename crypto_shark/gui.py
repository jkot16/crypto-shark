
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QFrame, QDialog, QTableWidget, QTableWidgetItem,
    QMessageBox
)
from PySide6.QtCore import Qt, QSize, QRunnable, Slot, QThreadPool, Signal
from PySide6.QtGui import QPixmap, QIcon, QFontDatabase, QFont

from crypto_shark.dialogs import AddCryptoDialog
from crypto_shark.logic import CryptoWatcherLogic


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG = BASE_DIR / "config.json"
CACHE_FILE = BASE_DIR / "coins_cache.json"
LOG_FILE = BASE_DIR / "logs.txt"
STYLE_QSS = BASE_DIR / "style.qss"
ICONS_DIR = BASE_DIR / "icons"
FONTS_DIR = BASE_DIR / "fonts"

CACHE_TTL = 3600
ICON_SZ = 48


class IconLoader(QRunnable):
    def __init__(self, url: str, row: int, sig: Signal):
        super().__init__()
        self.url, self.row, self.sig = url, row, sig

    @Slot()
    def run(self):
        try:
            resp = __import__("requests").get(self.url, timeout=5)
            resp.raise_for_status()
            pix = QPixmap()
            pix.loadFromData(resp.content)
            self.sig.emit(self.row, pix)
        except:
            pass


class CheckWorker(QRunnable):
    def __init__(self, logic: CryptoWatcherLogic, done_signal: Signal):
        super().__init__()
        self.logic = logic
        self.done_signal = done_signal

    @Slot()
    def run(self):
        messages = self.logic.run_checks()
        self.done_signal.emit(messages)


class CryptoWatcherGUI(QWidget):
    icon_ready = Signal(int, QPixmap)
    checks_done = Signal(list)

    def __init__(self, rajdhani_family: str, comforter_family: str):
        super().__init__()
        self.rajdhani, self.comforter = rajdhani_family, comforter_family
        self.pool = QThreadPool.globalInstance()
        self.icon_ready.connect(self._set_icon)
        self.checks_done.connect(self._on_checks_done)

        self.setWindowTitle("Crypto Shark")
        self.setMinimumSize(1200, 800)


        self.coins = self._load_or_fetch_top100()
        self.total_market_cap = sum(c.get("market_cap", 0) for c in self.coins)


        self.logic = CryptoWatcherLogic()


        self._init_ui()
        self._load_tickers()

    def _load_or_fetch_top100(self):
        if CACHE_FILE.exists() and time.time() - CACHE_FILE.stat().st_mtime < CACHE_TTL:
            try:
                return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            except:
                pass
        try:
            resp = __import__("requests").get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": 100,
                    "page": 1,
                    "sparkline": "false"
                },
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return data
        except Exception as e:
            print("Error fetching Top-100:", e)
            return []

    def _init_ui(self):
        layout = QHBoxLayout(self)


        sb = QFrame()
        sb.setObjectName("sidebar")
        lb = QVBoxLayout(sb)
        lb.setContentsMargins(20, 20, 20, 20)
        lb.setSpacing(15)


        logo = QLabel()
        logo_path = ICONS_DIR / "logo.jpeg"
        if logo_path.exists():
            logo.setPixmap(
                QPixmap(str(logo_path))
                .scaled(260, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        logo.setAlignment(Qt.AlignCenter)
        lb.addWidget(logo)


        header = QLabel("Crypto Shark")
        header.setAlignment(Qt.AlignCenter)
        header.setFont(QFont(self.comforter, 40))
        header.setStyleSheet("color:white;")
        lb.addWidget(header)
        lb.addSpacing(20)


        for text, slot in [
            ("Add Crypto", self.open_add_dialog),
            ("Remove Selected", self._remove_selected),
            ("Check Now", self._on_check),
            ("Logs", self.open_logs)
        ]:
            btn = QPushButton(text)
            btn.setFont(QFont(self.rajdhani, 14, weight=QFont.Bold))
            btn.clicked.connect(slot)
            lb.addWidget(btn)

        lb.addStretch()
        layout.addWidget(sb, 0)


        main = QWidget()
        ml = QVBoxLayout(main)
        ml.setContentsMargins(20, 20, 20, 20)
        ml.setSpacing(10)
        ml.addWidget(QLabel("Watchlist:"))

        self.crypto_list = QListWidget()
        self.crypto_list.setIconSize(QSize(ICON_SZ, ICON_SZ))
        self.crypto_list.setFocusPolicy(Qt.NoFocus)

        ml.addWidget(self.crypto_list)

        layout.addWidget(main, 1)

    def _load_tickers(self):
        self.crypto_list.clear()
        try:
            cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
            tickers = cfg.get("tickers", [])
        except:
            tickers = []

        for idx, cid in enumerate(tickers):
            obj = next((c for c in self.coins if c["id"] == cid), {})
            mc  = obj.get("market_cap", 0)
            dom = mc / self.total_market_cap * 100 if self.total_market_cap else 0.0
            price = obj.get("current_price", 0.0)
            text = f"{cid.upper()}: ${price:,.2f} — ${int(mc):,} — ({dom:.2f}%)"

            item = QListWidgetItem(text)
            item.setFont(QFont(self.rajdhani, 14, weight=QFont.Bold))
            item.setData(Qt.UserRole, cid)
            item.setSizeHint(QSize(item.sizeHint().width(), ICON_SZ + 16))
            self.crypto_list.addItem(item)

            if (url := obj.get("image")):
                self.pool.start(IconLoader(url, idx, self.icon_ready))

    @Slot(int, QPixmap)
    def _set_icon(self, row, pix):
        if itm := self.crypto_list.item(row):
            itm.setIcon(QIcon(pix))

    @Slot(list)
    def _on_checks_done(self, messages):
        self._load_tickers()
        self.open_logs()

    def open_add_dialog(self):
        dlg = AddCryptoDialog(self, coins=self.coins)
        if dlg.exec() == QDialog.Accepted and getattr(dlg, "selected", None):
            new = dlg.selected
            cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
            if new not in cfg.get("tickers", []):
                cfg["tickers"].append(new)
                CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                self._load_tickers()

    def _remove_selected(self):
        items = self.crypto_list.selectedItems()
        if not items:
            return
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        for it in items:
            cid = it.data(Qt.UserRole)
            if cid in cfg.get("tickers", []):
                cfg["tickers"].remove(cid)
            self.crypto_list.takeItem(self.crypto_list.row(it))
        CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    def _on_check(self):
        self.pool.start(CheckWorker(self.logic, self.checks_done))
        QMessageBox.information(self, "Checking", "Background check started.")

    def open_logs(self):
        try:
            lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        except:
            lines = []

        table = QTableWidget(len(lines), 7, self)
        table.setHorizontalHeaderLabels([
            "Timestamp", "Coin", "Price", "Change", "PosSent", "NegSent", "AlertSent"
        ])
        table.setStyleSheet("""
            QTableWidget { background-color: #2b2b2b; color: white; gridline-color: #444; }
            QHeaderView::section { background-color: #3c3f41; color: white; font-weight: bold; }
            QTableCornerButton::section { background-color: #3c3f41; border: 1px solid #555; }
        """)

        for i, line in enumerate(lines):
            parts = [p.strip() for p in line.split("  ")]
            for j, val in enumerate(parts):
                display = "Yes" if (j == 6 and val == "1") else ("No" if j == 6 else val)
                item = QTableWidgetItem(display)
                item.setForeground(Qt.white)
                table.setItem(i, j, item)

        table.resizeColumnsToContents()
        table.resizeRowsToContents()

        w = sum(table.columnWidth(c) for c in range(table.columnCount())) + table.verticalHeader().width() + 4
        h = sum(table.rowHeight(r) for r in range(table.rowCount())) + table.horizontalHeader().height() + 4

        dlg = QDialog(self)
        dlg.setWindowTitle("Logs History")
        dlg.resize(w + 20, h + 20)
        lay = QVBoxLayout(dlg)
        lay.addWidget(table)
        dlg.exec()


def main():
    app = QApplication(sys.argv)


    r_id = QFontDatabase.addApplicationFont(str(FONTS_DIR / "Rajdhani-Regular.ttf"))
    fam = QFontDatabase.applicationFontFamilies(r_id)
    if r_id != -1 and fam:
        raj = fam[0]
    else:
        raj = QApplication.font().family()

    c_id = QFontDatabase.addApplicationFont(str(FONTS_DIR / "Comforter-Regular.ttf"))
    fam = QFontDatabase.applicationFontFamilies(c_id)
    if c_id != -1 and fam:
        com = fam[0]
    else:
        com = QApplication.font().family()


    app.setStyleSheet(STYLE_QSS.read_text(encoding="utf-8"))

    w = CryptoWatcherGUI(raj, com)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
