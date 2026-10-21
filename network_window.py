"""Network health dashboard (ping history chart) and network map. Both
are drawn from a snapshot dict supplied by the main window:

    {"me": str, "host": str,
     "members": [{"name", "ip", "status", "ping"}],
     "history": {name: [(timestamp, ms), ...]}}
"""

import math
import time

from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QFont
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout

from tools_common import TOOL_STYLE

STR = {
    "title": {"fa": "سلامت و نقشه‌ی شبکه", "en": "Network health & map"},
    "tab_ping": {"fa": "نمودار پینگ", "en": "Ping history"},
    "tab_map": {"fa": "نقشه‌ی شبکه", "en": "Network map"},
    "no_data": {"fa": "هنوز داده‌ای نیست (هر چند ثانیه یک‌بار پینگ گرفته می‌شه)", "en": "No data yet (a ping is taken every few seconds)"},
    "window": {"fa": "۵ دقیقه‌ی اخیر", "en": "last 5 minutes"},
    "host": {"fa": "میزبان", "en": "host"},
}

PALETTE = ["#55f7ff", "#ff6fb5", "#ffd166", "#3ddc84", "#c77dff", "#ff9f43", "#5b8def"]
STATUS_COLORS = {"online": "#3ddc84", "busy": "#e05a5a", "away": "#f0ad4e"}


class _PingChart(QWidget):
    def __init__(self, lang):
        super().__init__()
        self.lang = lang
        self.data = {}
        self.setMinimumSize(520, 320)

    def set_data(self, snapshot):
        self.data = snapshot.get("history", {})
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#0b1220"))
        left, top, right, bottom = 56, 16, 130, 34
        area = QRectF(left, top, self.width() - left - right, self.height() - top - bottom)
        now = time.time()
        span = 300.0
        series = {n: [(t, ms) for t, ms in pts if now - t <= span] for n, pts in self.data.items()}
        series = {n: pts for n, pts in series.items() if pts}
        p.setPen(QPen(QColor("#243b60"), 1))
        p.drawRect(area)
        if not series:
            p.setPen(QColor("#8798b6"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, STR["no_data"][self.lang])
            p.end()
            return
        ymax = max(50.0, max(ms for pts in series.values() for _t, ms in pts) * 1.25)
        p.setFont(QFont("Segoe UI", 8))
        for i in range(5):
            frac = i / 4
            y = area.bottom() - frac * area.height()
            p.setPen(QPen(QColor("#162540"), 1))
            p.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
            p.setPen(QColor("#8798b6"))
            p.drawText(QRectF(0, y - 8, left - 6, 16), Qt.AlignmentFlag.AlignRight, f"{ymax * frac:.0f} ms")
        p.setPen(QColor("#8798b6"))
        p.drawText(QRectF(area.left(), area.bottom() + 6, area.width(), 18), Qt.AlignmentFlag.AlignRight,
                   STR["window"][self.lang])
        for idx, (name, pts) in enumerate(sorted(series.items())):
            color = QColor(PALETTE[idx % len(PALETTE)])
            pen = QPen(color, 2)
            p.setPen(pen)
            points = [QPointF(area.left() + (1 - (now - t) / span) * area.width(),
                              area.bottom() - min(ms, ymax) / ymax * area.height()) for t, ms in pts]
            for a, b in zip(points, points[1:]):
                p.drawLine(a, b)
            if points:
                p.setBrush(color)
                p.drawEllipse(points[-1], 3, 3)
            ly = area.top() + 6 + idx * 18
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(QRectF(area.right() + 12, ly + 3, 10, 10))
            p.setPen(QColor("#eaf2ff"))
            p.drawText(QRectF(area.right() + 28, ly, right - 30, 16), Qt.AlignmentFlag.AlignLeft,
                       f"{name} ({pts[-1][1]} ms)")
        p.end()


class _NetMap(QWidget):
    def __init__(self, lang):
        super().__init__()
        self.lang = lang
        self.snapshot = {}
        self.setMinimumSize(520, 360)

    def set_data(self, snapshot):
        self.snapshot = snapshot
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#0b1220"))
        members = self.snapshot.get("members", [])
        host = self.snapshot.get("host", "")
        me = self.snapshot.get("me", "")
        if not members:
            p.end()
            return
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - 62
        others = [m for m in members if m["name"] != host]
        host_info = next((m for m in members if m["name"] == host), {"name": host, "ip": "", "status": "online", "ping": None})
        positions = {}
        for i, m in enumerate(others):
            ang = -math.pi / 2 + 2 * math.pi * i / max(1, len(others))
            positions[m["name"]] = QPointF(center.x() + radius * math.cos(ang), center.y() + radius * math.sin(ang))
        p.setPen(QPen(QColor("#2c4468"), 2))
        for pos in positions.values():
            p.drawLine(center, pos)

        def node(pos, m, big):
            r = 26 if big else 20
            color = QColor(STATUS_COLORS.get(m.get("status", "online"), "#3ddc84"))
            p.setBrush(QColor("#101f35"))
            pen = QPen(color, 3 if m["name"] == me else 2)
            p.setPen(pen)
            p.drawEllipse(pos, r, r)
            p.setPen(QColor("#eaf2ff"))
            p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            p.drawText(QRectF(pos.x() - r, pos.y() - r, 2 * r, 2 * r), Qt.AlignmentFlag.AlignCenter,
                       "\U0001F451" if big else m["name"][:1].upper())
            p.setFont(QFont("Segoe UI", 8))
            ping = m.get("ping")
            label = m["name"] + (" \u2022 " + str(ping) + " ms" if ping is not None else "")
            p.drawText(QRectF(pos.x() - 80, pos.y() + r + 2, 160, 14), Qt.AlignmentFlag.AlignCenter, label)
            p.setPen(QColor("#8798b6"))
            p.drawText(QRectF(pos.x() - 80, pos.y() + r + 15, 160, 14), Qt.AlignmentFlag.AlignCenter, m.get("ip", "") or "")

        for m in others:
            node(positions[m["name"]], m, False)
        node(center, host_info, True)
        p.end()


class NetworkWindow(QMainWindow):
    def __init__(self, provider, lang="en"):
        super().__init__()
        self.provider = provider
        self.lang = lang if lang in ("fa", "en") else "en"
        self.resize(640, 460)
        self.tabs = QTabWidget()
        self.chart = _PingChart(self.lang)
        self.map = _NetMap(self.lang)
        self.tabs.addTab(self.chart, "")
        self.tabs.addTab(self.map, "")
        self.setCentralWidget(self.tabs)
        self.setStyleSheet(TOOL_STYLE)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)
        self._retranslate()
        self.refresh()

    def _retranslate(self):
        self.setWindowTitle("\U0001F4F6 " + STR["title"][self.lang])
        self.tabs.setTabText(0, STR["tab_ping"][self.lang])
        self.tabs.setTabText(1, STR["tab_map"][self.lang])
        self.chart.lang = self.map.lang = self.lang

    def set_language(self, lang):
        self.lang = lang if lang in ("fa", "en") else "en"
        self._retranslate()
        self.refresh()

    def refresh(self):
        try:
            snapshot = self.provider()
        except Exception:
            return
        self.chart.set_data(snapshot)
        self.map.set_data(snapshot)
