"""Typing-speed game: type the shown sentence as fast and accurately as
you can; you get words-per-minute and accuracy, and the best WPM is kept
in ~/.lan_chat_gui/tools.json. Fully offline."""

import random
import sys
import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox,
)

from tools_common import TOOL_STYLE, load_json, save_json

SENTENCES = {
    "en": [
        "The quick brown fox jumps over the lazy dog near the river bank.",
        "Practice makes perfect, so keep typing until your fingers remember the keys.",
        "A small group of friends can build something much bigger than any one person.",
        "Good software is written twice: once to make it work and once to make it clean.",
        "Never trust a computer you cannot throw out of a window, said a famous engineer.",
        "Encrypted messages travel across the local network and only the receiver can read them.",
    ],
    "fa": [
        "کار امروز را به فردا نینداز و هر روز کمی بیشتر از دیروز تلاش کن.",
        "دانش مانند دریاست و هر کسی به اندازه‌ی ظرفش از آن بهره می‌برد.",
        "تمرین زیاد باعث می‌شود انگشتان تو روی کلیدها خودکار حرکت کنند.",
        "پیام‌های رمزنگاری‌شده فقط توسط گیرنده‌ی اصلی قابل خواندن هستند.",
        "یک برنامه‌ی خوب هم درست کار می‌کند و هم برای خواندن ساده است.",
    ],
}

STR = {
    "title": {"fa": "مسابقه‌ی سرعت تایپ", "en": "Typing speed test"},
    "lang": {"fa": "زبان متن:", "en": "Text language:"},
    "start": {"fa": "شروع / متن جدید", "en": "Start / new text"},
    "hint": {"fa": "روی «شروع» بزنید و جمله رو دقیق تایپ کنید.", "en": "Press Start and type the sentence exactly."},
    "typing": {"fa": "تایپ کنید... (با Enter تموم کنید)", "en": "Type here... (Enter to finish)"},
    "result": {"fa": "سرعت: {wpm} کلمه در دقیقه • دقت: {acc}% • زمان: {sec} ثانیه", "en": "Speed: {wpm} WPM • Accuracy: {acc}% • Time: {sec}s"},
    "best": {"fa": "بهترین: {wpm} WPM", "en": "Best: {wpm} WPM"},
    "newbest": {"fa": "\U0001F389 رکورد جدید!", "en": "\U0001F389 New record!"},
}


class TypingGameWindow(QMainWindow):
    def __init__(self, lang="en"):
        super().__init__()
        self.lang = lang if lang in ("fa", "en") else "en"
        self.setMinimumSize(560, 380)
        self.resize(620, 420)
        self.target = ""
        self.started_at = None
        self.best = int(load_json("tools.json", {}).get("typing_best", 0) or 0)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(10)

        top = QHBoxLayout()
        self.lang_lbl = QLabel("")
        self.lang_lbl.setObjectName("muted")
        top.addWidget(self.lang_lbl)
        self.text_lang_box = QComboBox()
        self.text_lang_box.addItem("English", "en")
        self.text_lang_box.addItem("فارسی", "fa")
        top.addWidget(self.text_lang_box)
        top.addStretch(1)
        self.best_lbl = QLabel("")
        self.best_lbl.setObjectName("muted")
        top.addWidget(self.best_lbl)
        root.addLayout(top)

        self.target_lbl = QLabel("")
        self.target_lbl.setWordWrap(True)
        self.target_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.target_lbl.setStyleSheet(
            "font-size: 15pt; padding: 16px; background: #101f35; border: 1px solid #243b60; border-radius: 12px;"
        )
        root.addWidget(self.target_lbl)

        self.input_edit = QLineEdit()
        self.input_edit.setStyleSheet("font-size: 13pt;")
        self.input_edit.setEnabled(False)
        self.input_edit.textChanged.connect(self._on_text_changed)
        self.input_edit.returnPressed.connect(self._finish)
        root.addWidget(self.input_edit)

        self.result_lbl = QLabel("")
        self.result_lbl.setStyleSheet("font-size: 12pt; font-weight: 700; color: #55f7ff;")
        self.result_lbl.setWordWrap(True)
        root.addWidget(self.result_lbl)

        self.start_btn = QPushButton("")
        self.start_btn.setObjectName("primary")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self._start)
        root.addWidget(self.start_btn)
        root.addStretch(1)

        self.setStyleSheet(TOOL_STYLE)
        self._retranslate()

    def _t(self, key):
        return STR[key][self.lang]

    def _retranslate(self):
        self.setWindowTitle("\u2328 " + self._t("title"))
        self.lang_lbl.setText(self._t("lang"))
        self.start_btn.setText(self._t("start"))
        self.best_lbl.setText(self._t("best").format(wpm=self.best))
        if not self.target:
            self.target_lbl.setText(self._t("hint"))

    def set_language(self, lang):
        self.lang = lang if lang in ("fa", "en") else "en"
        self._retranslate()

    def _start(self):
        self.target = random.choice(SENTENCES[self.text_lang_box.currentData()])
        self.started_at = None
        self.result_lbl.setText("")
        self.input_edit.setEnabled(True)
        self.input_edit.clear()
        self.input_edit.setPlaceholderText(self._t("typing"))
        self.input_edit.setFocus()
        self._render("")

    def _render(self, typed):
        out = []
        for i, ch in enumerate(self.target):
            ch_html = "&nbsp;" if ch == " " else ch.replace("&", "&amp;").replace("<", "&lt;")
            if i < len(typed):
                color = "#3ddc84" if typed[i] == ch else "#ff6b6b"
                out.append(f"<span style='color:{color}'>{ch_html}</span>")
            else:
                out.append(f"<span style='color:#8798b6'>{ch_html}</span>")
        self.target_lbl.setText("".join(out))

    def _on_text_changed(self, text):
        if not self.target:
            return
        if self.started_at is None and text:
            self.started_at = time.time()
        self._render(text)
        if text == self.target:
            self._finish()

    def _finish(self):
        if not self.target or self.started_at is None:
            return
        typed = self.input_edit.text()
        seconds = max(0.5, time.time() - self.started_at)
        correct = sum(1 for a, b in zip(typed, self.target) if a == b)
        accuracy = int(100 * correct / max(1, len(self.target)))
        wpm = int((len(self.target) / 5) / (seconds / 60) * accuracy / 100)
        text = self._t("result").format(wpm=wpm, acc=accuracy, sec=f"{seconds:.1f}")
        if wpm > self.best:
            self.best = wpm
            settings = load_json("tools.json", {})
            if not isinstance(settings, dict):
                settings = {}
            settings["typing_best"] = wpm
            save_json("tools.json", settings)
            text += "   " + self._t("newbest")
        self.result_lbl.setText(text)
        self.best_lbl.setText(self._t("best").format(wpm=self.best))
        self.input_edit.setEnabled(False)
        self.target = ""
        self.started_at = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TypingGameWindow()
    win.show()
    sys.exit(app.exec())
