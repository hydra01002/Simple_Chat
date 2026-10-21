"""Persistent contacts: a private phone-book / notebook about people
(note, phone, birthday MM-DD). Stored locally in ~/.lan_chat_gui/contacts.json
(plain text, never sent over the network). Birthdays are checked by the
main window so you get a notification on the day."""

import re
import sys
import time

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QListWidget, QListWidgetItem,
)

from tools_common import TOOL_STYLE, load_json, save_json

STR = {
    "title": {"fa": "مخاطبین و یادداشت خصوصی", "en": "Contacts & private notes"},
    "name": {"fa": "نام", "en": "Name"},
    "phone": {"fa": "تلفن", "en": "Phone"},
    "birthday": {"fa": "تولد (ماه-روز مثل 03-21)", "en": "Birthday (MM-DD, e.g. 03-21)"},
    "note": {"fa": "یادداشت خصوصی درباره‌ی این آدم...", "en": "Private note about this person..."},
    "save": {"fa": "ذخیره", "en": "Save"},
    "new": {"fa": "مخاطب جدید", "en": "New contact"},
    "delete": {"fa": "حذف", "en": "Delete"},
    "bad_bday": {"fa": "تولد باید به شکل ماه-روز باشه (مثلاً 03-21).", "en": "Birthday must look like MM-DD (e.g. 03-21)."},
    "need_name": {"fa": "یه نام وارد کنید.", "en": "Enter a name."},
    "local": {"fa": "فقط روی همین کامپیوتر ذخیره می‌شه.", "en": "Stored only on this computer."},
}


def normalize_birthday(text):
    text = (text or "").strip()
    if not text:
        return ""
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})$", text)
    if not m:
        return None
    month, day = int(m.group(1)), int(m.group(2))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{month:02d}-{day:02d}"


class ContactsStore(QObject):
    changed = pyqtSignal()
    FILE = "contacts.json"

    def __init__(self):
        super().__init__()
        data = load_json(self.FILE, {})
        self.data = data if isinstance(data, dict) else {}

    def _save(self):
        save_json(self.FILE, self.data)
        self.changed.emit()

    def get(self, name):
        return self.data.get(name, {})

    def set(self, name, phone="", birthday="", note=""):
        self.data[name] = {"phone": phone, "birthday": birthday, "note": note}
        self._save()

    def delete(self, name):
        if self.data.pop(name, None) is not None:
            self._save()

    def birthdays_today(self):
        today = time.strftime("%m-%d")
        return [n for n, c in self.data.items() if c.get("birthday") == today]


class ContactsWindow(QMainWindow):
    def __init__(self, store, lang="en"):
        super().__init__()
        self.store = store
        self.lang = lang if lang in ("fa", "en") else "en"
        self.resize(640, 460)
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(16, 14, 16, 14)

        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_selected)
        left.addWidget(self.list, stretch=1)
        self.new_btn = QPushButton("")
        self.new_btn.clicked.connect(self._new)
        left.addWidget(self.new_btn)
        root.addLayout(left, stretch=1)

        right = QVBoxLayout()
        self.name_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.bday_edit = QLineEdit()
        self.note_edit = QTextEdit()
        self.note_edit.setAcceptRichText(False)
        for w in (self.name_edit, self.phone_edit, self.bday_edit):
            right.addWidget(w)
        right.addWidget(self.note_edit, stretch=1)
        self.msg_lbl = QLabel("")
        self.msg_lbl.setObjectName("muted")
        right.addWidget(self.msg_lbl)
        row = QHBoxLayout()
        self.save_btn = QPushButton("")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self._save)
        row.addWidget(self.save_btn)
        self.del_btn = QPushButton("")
        self.del_btn.setObjectName("danger")
        self.del_btn.clicked.connect(self._delete)
        row.addWidget(self.del_btn)
        right.addLayout(row)
        root.addLayout(right, stretch=2)

        self.setStyleSheet(TOOL_STYLE)
        self.store.changed.connect(self._fill)
        self._retranslate()
        self._fill()

    def _t(self, key):
        return STR[key][self.lang]

    def _retranslate(self):
        self.setWindowTitle("\U0001F4D2 " + self._t("title"))
        self.name_edit.setPlaceholderText(self._t("name"))
        self.phone_edit.setPlaceholderText(self._t("phone"))
        self.bday_edit.setPlaceholderText(self._t("birthday"))
        self.note_edit.setPlaceholderText(self._t("note"))
        self.save_btn.setText(self._t("save"))
        self.del_btn.setText(self._t("delete"))
        self.new_btn.setText(self._t("new"))
        self.msg_lbl.setText(self._t("local"))

    def set_language(self, lang):
        self.lang = lang if lang in ("fa", "en") else "en"
        self._retranslate()

    def _fill(self):
        current = self.name_edit.text().strip()
        self.list.blockSignals(True)
        self.list.clear()
        for name in sorted(self.store.data, key=str.lower):
            bday = self.store.data[name].get("birthday")
            item = QListWidgetItem(name + (f"  \U0001F382 {bday}" if bday else ""))
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list.addItem(item)
            if name == current:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)

    def select(self, name):
        """Open the editor on `name` (creating an empty form if unknown)."""
        c = self.store.get(name)
        self.name_edit.setText(name)
        self.phone_edit.setText(c.get("phone", ""))
        self.bday_edit.setText(c.get("birthday", ""))
        self.note_edit.setPlainText(c.get("note", ""))
        self.msg_lbl.setStyleSheet("")
        self.msg_lbl.setText(self._t("local"))
        self._fill()

    def _on_selected(self, item, _prev):
        if item is not None:
            self.select(item.data(Qt.ItemDataRole.UserRole))

    def _new(self):
        self.list.clearSelection()
        self.name_edit.clear()
        self.phone_edit.clear()
        self.bday_edit.clear()
        self.note_edit.clear()
        self.name_edit.setFocus()

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            self.msg_lbl.setStyleSheet("color: #ff6b6b;")
            self.msg_lbl.setText(self._t("need_name"))
            return
        bday = normalize_birthday(self.bday_edit.text())
        if bday is None:
            self.msg_lbl.setStyleSheet("color: #ff6b6b;")
            self.msg_lbl.setText(self._t("bad_bday"))
            return
        self.store.set(name, self.phone_edit.text().strip(), bday, self.note_edit.toPlainText().strip())
        self.msg_lbl.setStyleSheet("")
        self.msg_lbl.setText(self._t("local"))

    def _delete(self):
        name = self.name_edit.text().strip()
        if name:
            self.store.delete(name)
            self._new()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ContactsWindow(ContactsStore())
    win.show()
    sys.exit(app.exec())
