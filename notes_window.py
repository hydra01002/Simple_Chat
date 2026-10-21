"""Quick notes + reminders.

NotesStore owns the data (saved as plain JSON in ~/.lan_chat_gui/notes.json,
local only, never sent over the network) and is created once by the main
window, which also polls store.check_due() on a timer - so reminders fire
even while this window is closed. NotesWindow is just a view on the store.
"""

import html
import sys
import time
import uuid

from PyQt6.QtCore import Qt, QObject, QDateTime, QTime, pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QCheckBox, QDateTimeEdit, QFrame, QScrollArea,
)

from tools_common import TOOL_STYLE, load_json, save_json

STR = {
    "title": {"fa": "یادداشت و یادآور", "en": "Notes & Reminders"},
    "placeholder": {"fa": "یه یادداشت بنویسید...", "en": "Write a note..."},
    "remind": {"fa": "یادآوری در:", "en": "Remind me at:"},
    "add": {"fa": "افزودن", "en": "Add"},
    "p10": {"fa": "+۱۰ دقیقه", "en": "+10 min"},
    "p60": {"fa": "+۱ ساعت", "en": "+1 hour"},
    "ptom": {"fa": "فردا ۹ صبح", "en": "Tomorrow 9:00"},
    "empty": {"fa": "هنوز یادداشتی نیست.", "en": "No notes yet."},
    "past": {"fa": "زمان یادآوری باید در آینده باشه.", "en": "Pick a time in the future."},
    "fired": {"fa": "یادآوری شد", "en": "reminded"},
    "storage": {
        "fa": "ذخیره‌ی محلی روی همین کامپیوتر (رمزنگاری نشده، روی شبکه فرستاده نمی‌شه)",
        "en": "Stored locally on this computer (not encrypted, never sent over the network)",
    },
}


class NotesStore(QObject):
    changed = pyqtSignal()
    reminder_due = pyqtSignal(dict)

    FILE = "notes.json"

    def __init__(self):
        super().__init__()
        data = load_json(self.FILE, [])
        self.items = [i for i in data if isinstance(i, dict)] if isinstance(data, list) else []

    def _save(self):
        save_json(self.FILE, self.items)

    def add(self, text, remind_at=None):
        item = {
            "id": uuid.uuid4().hex[:10], "text": text, "created": time.time(),
            "remind_at": remind_at, "fired": False, "done": False,
        }
        self.items.append(item)
        self._save()
        self.changed.emit()
        return item

    def delete(self, item_id):
        self.items = [i for i in self.items if i.get("id") != item_id]
        self._save()
        self.changed.emit()

    def toggle_done(self, item_id):
        for i in self.items:
            if i.get("id") == item_id:
                i["done"] = not i.get("done", False)
        self._save()
        self.changed.emit()

    def check_due(self):
        """Fire (once) every reminder whose time has come."""
        now = time.time()
        due = [
            i for i in self.items
            if i.get("remind_at") and not i.get("fired") and not i.get("done") and i["remind_at"] <= now
        ]
        if not due:
            return
        for i in due:
            i["fired"] = True
        self._save()
        self.changed.emit()
        for i in due:
            self.reminder_due.emit(i)


class NotesWindow(QMainWindow):
    def __init__(self, store, lang="en"):
        super().__init__()
        self.store = store
        self.lang = lang if lang in ("fa", "en") else "en"
        self.setMinimumSize(460, 560)
        self.resize(500, 620)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 12)
        root.setSpacing(8)

        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setFixedHeight(76)
        root.addWidget(self.text_edit)

        remind_row = QHBoxLayout()
        self.remind_check = QCheckBox("")
        self.remind_check.toggled.connect(self._on_remind_toggled)
        remind_row.addWidget(self.remind_check)
        self.when_edit = QDateTimeEdit()
        self.when_edit.setCalendarPopup(True)
        self.when_edit.setDisplayFormat("yyyy-MM-dd  HH:mm")
        self.when_edit.setEnabled(False)
        remind_row.addWidget(self.when_edit, stretch=1)
        root.addLayout(remind_row)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        self.p10_btn = QPushButton("")
        self.p60_btn = QPushButton("")
        self.ptom_btn = QPushButton("")
        self.p10_btn.clicked.connect(lambda: self._preset(minutes=10))
        self.p60_btn.clicked.connect(lambda: self._preset(minutes=60))
        self.ptom_btn.clicked.connect(lambda: self._preset(tomorrow=True))
        for b in (self.p10_btn, self.p60_btn, self.ptom_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            preset_row.addWidget(b)
        preset_row.addStretch(1)
        self.add_btn = QPushButton("")
        self.add_btn.setObjectName("primary")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._add)
        preset_row.addWidget(self.add_btn)
        root.addLayout(preset_row)
        QShortcut(QKeySequence("Ctrl+Return"), self, self._add)

        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("error")
        root.addWidget(self.error_lbl)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.list_container)
        root.addWidget(self.scroll, stretch=1)

        self.storage_lbl = QLabel("")
        self.storage_lbl.setObjectName("muted")
        self.storage_lbl.setWordWrap(True)
        root.addWidget(self.storage_lbl)

        self.setStyleSheet(TOOL_STYLE)
        self._reset_when()
        self.store.changed.connect(self._rebuild)
        self._retranslate()

    def _t(self, key):
        return STR[key][self.lang]

    def _retranslate(self):
        self.setWindowTitle("\U0001F4DD " + self._t("title"))
        self.text_edit.setPlaceholderText(self._t("placeholder"))
        self.remind_check.setText(self._t("remind"))
        self.add_btn.setText(self._t("add"))
        self.p10_btn.setText(self._t("p10"))
        self.p60_btn.setText(self._t("p60"))
        self.ptom_btn.setText(self._t("ptom"))
        self.storage_lbl.setText(self._t("storage"))
        self._rebuild()

    def set_language(self, lang):
        self.lang = lang if lang in ("fa", "en") else "en"
        self._retranslate()

    def _reset_when(self):
        self.when_edit.setDateTime(QDateTime.currentDateTime().addSecs(600))

    def _on_remind_toggled(self, checked):
        self.when_edit.setEnabled(checked)
        if checked and self.when_edit.dateTime() < QDateTime.currentDateTime():
            self._reset_when()

    def _preset(self, minutes=None, tomorrow=False):
        now = QDateTime.currentDateTime()
        if tomorrow:
            target = QDateTime(now.date().addDays(1), QTime(9, 0))
        else:
            target = now.addSecs(minutes * 60)
        self.remind_check.setChecked(True)
        self.when_edit.setDateTime(target)

    def _add(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            return
        remind_at = None
        if self.remind_check.isChecked():
            remind_at = float(self.when_edit.dateTime().toSecsSinceEpoch())
            if remind_at <= time.time():
                self.error_lbl.setText(self._t("past"))
                return
        self.error_lbl.setText("")
        self.text_edit.clear()
        self.remind_check.setChecked(False)
        self._reset_when()
        self.store.add(text, remind_at)

    def _rebuild(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        items = sorted(
            self.store.items,
            key=lambda i: (i.get("done", False), i.get("remind_at") or float("inf"), i.get("created", 0)),
        )
        if not items:
            empty = QLabel(self._t("empty"))
            empty.setObjectName("muted")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, empty)
            return
        for pos, it in enumerate(items):
            self.list_layout.insertWidget(pos, self._make_row(it))

    def _make_row(self, it):
        card = QFrame()
        card.setObjectName("card")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)

        done = bool(it.get("done"))
        check = QCheckBox("")
        check.setChecked(done)
        item_id = it.get("id")
        check.clicked.connect(lambda checked=False, i=item_id: self.store.toggle_done(i))
        lay.addWidget(check, alignment=Qt.AlignmentFlag.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(2)
        body = html.escape(it.get("text", "")).replace("\n", "<br>")
        text_lbl = QLabel(f"<s>{body}</s>" if done else body)
        text_lbl.setTextFormat(Qt.TextFormat.RichText)
        text_lbl.setWordWrap(True)
        if done:
            text_lbl.setStyleSheet("color: #68768f;")
        col.addWidget(text_lbl)
        if it.get("remind_at"):
            when = QDateTime.fromSecsSinceEpoch(int(it["remind_at"])).toString("yyyy-MM-dd HH:mm")
            suffix = f"  ({self._t('fired')})" if it.get("fired") else ""
            when_lbl = QLabel(f"\u23F0 {when}{suffix}")
            color = "#68768f" if (done or it.get("fired")) else "#55f7ff"
            when_lbl.setStyleSheet(f"color: {color}; font-size: 9pt;")
            col.addWidget(when_lbl)
        lay.addLayout(col, stretch=1)

        del_btn = QPushButton("\u2715")
        del_btn.setObjectName("danger")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(lambda checked=False, i=item_id: self.store.delete(i))
        lay.addWidget(del_btn, alignment=Qt.AlignmentFlag.AlignTop)
        return card


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = NotesWindow(NotesStore())
    win.show()
    sys.exit(app.exec())
