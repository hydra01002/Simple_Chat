"""A small standalone window showing live exchange rates and crypto prices
(its own QMainWindow, launched from the chat app's menu like the games).

Two tabs:
  - "بازار ایران (تومان)": USD/EUR/GBP/JPY/AED in Toman, from tgju.org's
    public but UNOFFICIAL JSON feed (no official free API exists for the
    free-market rate; it may change or break without notice, so every row
    that fails to parse is simply skipped).
  - "رمزارزها": a handful of major cryptocurrencies in USD with the 24h
    change, from the free, keyless CoinGecko API.

Network calls run on a background thread. The refresh button used to stay
disabled forever because it was re-enabled with QTimer.singleShot from
that background thread (a thread with no Qt event loop never fires such a
timer); now the worker reports back with a normal Qt signal, which is
delivered safely on the GUI thread.
"""

import sys
import json
import threading
import urllib.request
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QTabWidget, QFrame,
)

REFRESH_INTERVAL_MS = 5 * 60 * 1000  # 5 minutes
REQUEST_TIMEOUT = 8  # seconds

IRAN_SOURCE_URL = "https://call1.tgju.org/ajax.json"
# tgju feed key -> (display label, flag emoji)
IRAN_FIELDS = [
    ("price_dollar_rl", "دلار آمریکا (USD)", "\U0001F1FA\U0001F1F8"),
    ("price_eur", "یورو (EUR)", "\U0001F1EA\U0001F1FA"),
    ("price_gbp", "پوند انگلیس (GBP)", "\U0001F1EC\U0001F1E7"),
    ("price_jpy", "۱۰۰ ین ژاپن (JPY)", "\U0001F1EF\U0001F1F5"),
    ("price_aed", "درهم امارات (AED)", "\U0001F1E6\U0001F1EA"),
]

# CoinGecko id, ticker, Persian name, badge color
CRYPTO_COINS = [
    ("bitcoin", "BTC", "بیت‌کوین", "#f7931a"),
    ("ethereum", "ETH", "اتریوم", "#627eea"),
    ("tether", "USDT", "تتر", "#26a17b"),
    ("binancecoin", "BNB", "بایننس‌کوین", "#d9a516"),
    ("ripple", "XRP", "ریپل", "#2a8fd0"),
    ("dogecoin", "DOGE", "دوج‌کوین", "#b9972e"),
]
CRYPTO_SOURCE_URL = (
    "https://api.coingecko.com/api/v3/simple/price?ids="
    + ",".join(c[0] for c in CRYPTO_COINS)
    + "&vs_currencies=usd&include_24hr_change=true"
)

UP_COLOR = "#3ddc84"
DOWN_COLOR = "#ff6b6b"


def _fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def format_usd(price):
    if price >= 1:
        return f"${price:,.2f}"
    return f"${price:,.4f}"


class RatesWorker(QObject):
    """Does the network calls off the GUI thread and reports through
    signals (rows are plain dicts: badge, badge_color, title, subtitle,
    value, change)."""

    iran_ready = pyqtSignal(list)
    iran_failed = pyqtSignal(str)
    crypto_ready = pyqtSignal(list)
    crypto_failed = pyqtSignal(str)
    all_done = pyqtSignal()

    def run(self):
        try:
            self._run_iran()
            self._run_crypto()
        finally:
            self.all_done.emit()

    def _run_iran(self):
        try:
            data = _fetch_json(IRAN_SOURCE_URL)
            rows = []
            for key, label, flag in IRAN_FIELDS:
                try:
                    raw = data["current"][key]["p"]
                    rial = float(str(raw).replace(",", ""))
                    rows.append({
                        "badge": flag, "badge_color": "#1a2c4a", "title": label,
                        "subtitle": "", "value": f"{rial / 10:,.0f} تومان", "change": None,
                    })
                except Exception:
                    continue  # feed format drift on this one field - skip it
            if rows:
                self.iran_ready.emit(rows)
            else:
                self.iran_failed.emit("هیچ قیمتی از منبع ایرانی خونده نشد.")
        except Exception as e:
            self.iran_failed.emit(str(e))

    def _run_crypto(self):
        try:
            data = _fetch_json(CRYPTO_SOURCE_URL)
            rows = []
            for cid, ticker, name, color in CRYPTO_COINS:
                info = data.get(cid)
                if not info or "usd" not in info:
                    continue
                change = info.get("usd_24h_change")
                rows.append({
                    "badge": ticker[:4], "badge_color": color, "title": name,
                    "subtitle": ticker, "value": format_usd(float(info["usd"])),
                    "change": float(change) if change is not None else None,
                })
            if rows:
                self.crypto_ready.emit(rows)
            else:
                self.crypto_failed.emit("هیچ قیمتی برای رمزارزها خونده نشد.")
        except Exception as e:
            self.crypto_failed.emit(str(e))


class RateRow(QFrame):
    """One card-like row: round badge, name (+ticker), price, 24h change."""

    def __init__(self, row, parent=None):
        super().__init__(parent)
        self.setObjectName("rateRow")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 14, 9)
        lay.setSpacing(12)

        badge = QLabel(row["badge"])
        badge.setFixedSize(40, 40)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        small = len(row["badge"]) > 2 and row["badge"].isascii()
        badge.setStyleSheet(
            f"background: {row['badge_color']}; border-radius: 20px; color: #ffffff; "
            f"font-weight: 800; font-size: {'8pt' if small else '15pt'};"
        )
        lay.addWidget(badge)

        names = QVBoxLayout()
        names.setSpacing(0)
        title = QLabel(row["title"])
        title.setObjectName("rateName")
        names.addWidget(title)
        if row.get("subtitle"):
            sub = QLabel(row["subtitle"])
            sub.setObjectName("rateSub")
            names.addWidget(sub)
        lay.addLayout(names, stretch=1)

        vals = QVBoxLayout()
        vals.setSpacing(1)
        value = QLabel(row["value"])
        value.setObjectName("rateValue")
        value.setAlignment(Qt.AlignmentFlag.AlignRight)
        vals.addWidget(value)
        change = row.get("change")
        if change is not None:
            up = change >= 0
            chip = QLabel(f"{'▲' if up else '▼'} {abs(change):.2f}%")
            chip.setAlignment(Qt.AlignmentFlag.AlignRight)
            chip.setStyleSheet(
                f"color: {UP_COLOR if up else DOWN_COLOR}; font-size: 9pt; "
                f"font-weight: 700; background: transparent;"
            )
            vals.addWidget(chip)
        lay.addLayout(vals)


class RatesTable(QWidget):
    """A status line, a list of RateRow cards and a small source footer."""

    def __init__(self, footer_text, parent=None):
        super().__init__(parent)
        self.has_rows = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(8)

        self.status_lbl = QLabel("در حال دریافت قیمت‌ها...")
        self.status_lbl.setObjectName("ratesStatus")
        self.status_lbl.setWordWrap(True)
        outer.addWidget(self.status_lbl)

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(7)
        outer.addLayout(self.rows_layout)
        outer.addStretch(1)

        footer = QLabel(footer_text)
        footer.setObjectName("ratesStatus")
        footer.setWordWrap(True)
        outer.addWidget(footer)

    def _clear_rows(self):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def set_loading(self):
        self.status_lbl.setStyleSheet("")
        self.status_lbl.setText("در حال به‌روزرسانی..." if self.has_rows else "در حال دریافت قیمت‌ها...")

    def set_rows(self, rows):
        self._clear_rows()
        for row in rows:
            self.rows_layout.addWidget(RateRow(row))
        self.has_rows = True
        self.status_lbl.setStyleSheet("")
        self.status_lbl.setText(f"آخرین به‌روزرسانی: {datetime.now().strftime('%H:%M:%S')}")

    def set_error(self, message):
        # Keep the previously shown rows (if any) - stale prices plus an
        # error line are more useful than an emptied tab.
        self.status_lbl.setStyleSheet("color: #ff6b6b;")
        self.status_lbl.setText(f"خطا در دریافت قیمت‌ها: {message}")


class RatesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("نرخ ارز و رمزارز")
        self.setMinimumSize(440, 540)
        self.resize(480, 580)
        self._worker = None
        self._loading = False

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(16, 12, 16, 4)
        title = QLabel("نرخ ارز و رمزارز")
        title.setStyleSheet("font-size: 14pt; font-weight: 800; background: transparent;")
        top_bar.addWidget(title)
        top_bar.addStretch(1)
        self.refresh_btn = QPushButton("\U0001F504 به‌روزرسانی")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_now)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        self.tabs = QTabWidget()
        self.iran_tab = RatesTable("منبع: tgju.org (غیررسمی، ممکنه بدون اطلاع قطع بشه)")
        self.crypto_tab = RatesTable("قیمت‌ها به دلار آمریکا • منبع: CoinGecko")
        self.tabs.addTab(self.iran_tab, "بازار ایران (تومان)")
        self.tabs.addTab(self.crypto_tab, "رمزارزها")
        layout.addWidget(self.tabs)

        self.setStyleSheet("""
        QMainWindow, QWidget { background: #0b1220; color: #eaf2ff; font-family: "Segoe UI", Tahoma; }
        QTabWidget::pane { border: none; }
        QTabBar::tab {
            background: #101f35; color: #c6d4ea; padding: 8px 18px;
            border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px;
        }
        QTabBar::tab:selected { background: #1a2c4a; color: #ffffff; font-weight: 600; }
        QPushButton { background: #1a2c4a; border: 1px solid #2c4468; border-radius: 8px; padding: 6px 12px; }
        QPushButton:hover { border-color: #5369ff; }
        QPushButton:disabled { color: #68768f; background: #121d31; }
        QLabel#ratesStatus { color: #8798b6; font-size: 9pt; }
        QFrame#rateRow { background: #101f35; border: 1px solid #1f3454; border-radius: 12px; }
        QFrame#rateRow:hover { border-color: #31507e; }
        QLabel#rateName { color: #eaf2ff; font-size: 11pt; font-weight: 600; }
        QLabel#rateSub { color: #8798b6; font-size: 8.5pt; }
        QLabel#rateValue { color: #55f7ff; font-size: 11.5pt; font-weight: 700; }
        """)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_now)
        self.timer.start(REFRESH_INTERVAL_MS)

        self.refresh_now()

    def refresh_now(self):
        if self._loading:
            return
        self._loading = True
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("\u23F3 در حال دریافت...")
        self.iran_tab.set_loading()
        self.crypto_tab.set_loading()

        worker = RatesWorker()
        worker.iran_ready.connect(self.iran_tab.set_rows)
        worker.iran_failed.connect(self.iran_tab.set_error)
        worker.crypto_ready.connect(self.crypto_tab.set_rows)
        worker.crypto_failed.connect(self.crypto_tab.set_error)
        worker.all_done.connect(self._on_all_done)
        self._worker = worker  # keep a reference alive for the thread's lifetime
        threading.Thread(target=worker.run, daemon=True).start()

    def _on_all_done(self):
        # Runs on the GUI thread (queued signal), so touching widgets here is safe.
        self._loading = False
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("\U0001F504 به‌روزرسانی")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = RatesWindow()
    win.show()
    sys.exit(app.exec())
