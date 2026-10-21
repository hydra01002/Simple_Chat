"""Small collaborative dialogs used by the chat: a shared checklist and a
shared whiteboard. They hold no networking themselves - the chat page
passes callbacks and sends the changes as encrypted envelopes."""

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QLineEdit,
    QPushButton, QWidget, QLabel,
)


class ChecklistDialog(QDialog):
    """`items` is a list (shared by reference with the chat page) of dicts
    {"id", "text", "done", "by"}; every local change calls on_change()."""

    def __init__(self, title, items, on_change, me, labels, parent=None):
        super().__init__(parent)
        self.items = items
        self.on_change = on_change
        self.me = me
        self.setWindowTitle(title)
        self.resize(400, 460)
        lay = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.setObjectName("discoverList")
        self.list.itemChanged.connect(self._on_item_changed)
        lay.addWidget(self.list, stretch=1)
        row = QHBoxLayout()
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(labels["placeholder"])
        self.edit.returnPressed.connect(self._add)
        row.addWidget(self.edit, stretch=1)
        add_btn = QPushButton(labels["add"])
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._add)
        row.addWidget(add_btn)
        lay.addLayout(row)
        rm_btn = QPushButton(labels["remove"])
        rm_btn.clicked.connect(self._remove)
        lay.addWidget(rm_btn)
        self._building = False
        self.refresh()

    def refresh(self):
        self._building = True
        self.list.clear()
        for it in self.items:
            item = QListWidgetItem(f"{it['text']}   \u2014 {it.get('by', '')}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if it.get("done") else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, it["id"])
            self.list.addItem(item)
        self._building = False

    def _on_item_changed(self, item):
        if self._building:
            return
        item_id = item.data(Qt.ItemDataRole.UserRole)
        for it in self.items:
            if it["id"] == item_id:
                it["done"] = item.checkState() == Qt.CheckState.Checked
        self.on_change()

    def _add(self):
        text = self.edit.text().strip()
        if not text:
            return
        import uuid
        self.items.append({"id": uuid.uuid4().hex[:8], "text": text[:200], "done": False, "by": self.me})
        self.edit.clear()
        self.refresh()
        self.on_change()

    def _remove(self):
        item = self.list.currentItem()
        if item is None:
            return
        item_id = item.data(Qt.ItemDataRole.UserRole)
        self.items[:] = [it for it in self.items if it["id"] != item_id]
        self.refresh()
        self.on_change()


class _Canvas(QWidget):
    COLORS = ["#ffffff", "#ff5555", "#55a8ff", "#3ddc84", "#ffd166"]

    def __init__(self, strokes, on_stroke, parent=None):
        super().__init__(parent)
        self.strokes = strokes          # [{"c": color, "w": width, "p": [[x, y], ...]}] with x/y in 0..1
        self.on_stroke = on_stroke
        self.color = self.COLORS[0]
        self.current = None
        self.setMinimumSize(420, 320)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _norm(self, pos):
        return [max(0.0, min(1.0, pos.x() / max(1, self.width()))),
                max(0.0, min(1.0, pos.y() / max(1, self.height())))]

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.current = {"c": self.color, "w": 3, "p": [self._norm(event.position())]}

    def mouseMoveEvent(self, event):
        if self.current is not None:
            self.current["p"].append(self._norm(event.position()))
            self.update()

    def mouseReleaseEvent(self, event):
        if self.current is not None and event.button() == Qt.MouseButton.LeftButton:
            stroke, self.current = self.current, None
            if len(stroke["p"]) == 1:
                stroke["p"].append(stroke["p"][0])
            self.strokes.append(stroke)
            self.on_stroke(stroke)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0b1220"))
        painter.setPen(QPen(QColor("#243b60"), 1))
        painter.drawRect(QRectF(0, 0, self.width() - 1, self.height() - 1))
        for stroke in self.strokes + ([self.current] if self.current else []):
            pen = QPen(QColor(stroke.get("c", "#ffffff")), stroke.get("w", 3))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            pts = [QPointF(x * self.width(), y * self.height()) for x, y in stroke.get("p", [])]
            for a, b in zip(pts, pts[1:]):
                painter.drawLine(a, b)
        painter.end()


class BoardDialog(QDialog):
    """Shared whiteboard: strokes you draw are sent to the other people in
    the chat; "Send whole board" lets someone who joined later catch up."""

    def __init__(self, title, strokes, on_stroke, on_clear, on_full, labels, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.on_clear = on_clear
        self.on_full = on_full
        lay = QVBoxLayout(self)
        self.canvas = _Canvas(strokes, on_stroke)
        lay.addWidget(self.canvas, stretch=1)
        row = QHBoxLayout()
        for color in _Canvas.COLORS:
            btn = QPushButton("")
            btn.setFixedSize(26, 26)
            btn.setStyleSheet(f"background: {color}; border: 2px solid #243b60; border-radius: 13px;")
            btn.clicked.connect(lambda checked=False, c=color: setattr(self.canvas, "color", c))
            row.addWidget(btn)
        row.addStretch(1)
        send_btn = QPushButton(labels["send_all"])
        send_btn.clicked.connect(lambda: self.on_full())
        row.addWidget(send_btn)
        clear_btn = QPushButton(labels["clear"])
        clear_btn.clicked.connect(self._clear)
        row.addWidget(clear_btn)
        lay.addLayout(row)

    def _clear(self):
        self.canvas.strokes.clear()
        self.canvas.update()
        self.on_clear()

    def refresh(self):
        self.canvas.update()
