"""Real two-player game played over the chat connection: Tic Tac Toe.
The window knows nothing about networking: it calls send_cb(dict) for
every move and is fed the opponent's moves through on_remote()."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton,
)

from tools_common import TOOL_STYLE

STR = {
    "title": {"fa": "تیک‌تاک‌تو آنلاین", "en": "Online Tic Tac Toe"},
    "your_turn": {"fa": "نوبت شماست ({s})", "en": "Your turn ({s})"},
    "their_turn": {"fa": "نوبت {name} ({s})", "en": "{name}'s turn ({s})"},
    "you_win": {"fa": "\U0001F389 بردید!", "en": "\U0001F389 You won!"},
    "they_win": {"fa": "{name} برد.", "en": "{name} won."},
    "draw": {"fa": "مساوی شد.", "en": "It's a draw."},
    "again": {"fa": "بازی دوباره", "en": "Play again"},
    "left": {"fa": "{name} بازی رو ترک کرد.", "en": "{name} left the game."},
    "vs": {"fa": "شما ({s}) در برابر {name}", "en": "You ({s}) vs {name}"},
}

LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


class OnlineTTTWindow(QMainWindow):
    def __init__(self, gid, opponent, my_symbol, send_cb, lang="en"):
        super().__init__()
        self.gid = gid
        self.opponent = opponent
        self.me = my_symbol
        self.them = "O" if my_symbol == "X" else "X"
        self.send_cb = send_cb
        self.lang = lang if lang in ("fa", "en") else "en"
        self.board = [""] * 9
        self.turn = "X"            # X always starts
        self.over = False
        self.opponent_left = False
        self.setMinimumSize(360, 460)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)
        self.vs_lbl = QLabel("")
        self.vs_lbl.setObjectName("muted")
        self.vs_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.vs_lbl)
        grid = QGridLayout()
        grid.setSpacing(8)
        self.cells = []
        for i in range(9):
            btn = QPushButton("")
            btn.setMinimumSize(96, 96)
            btn.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, k=i: self._on_cell(k))
            grid.addWidget(btn, i // 3, i % 3)
            self.cells.append(btn)
        root.addLayout(grid)
        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("font-size: 12pt; font-weight: 700; color: #55f7ff;")
        root.addWidget(self.status_lbl)
        self.again_btn = QPushButton("")
        self.again_btn.setObjectName("primary")
        self.again_btn.clicked.connect(self._request_reset)
        root.addWidget(self.again_btn)
        root.addStretch(1)

        self.setStyleSheet(TOOL_STYLE)
        self._retranslate()
        self._refresh()

    def _t(self, key, **kw):
        return STR[key][self.lang].format(**kw)

    def _retranslate(self):
        self.setWindowTitle("\u274E\u2B55 " + self._t("title"))
        self.vs_lbl.setText(self._t("vs", s=self.me, name=self.opponent))
        self.again_btn.setText(self._t("again"))

    def set_language(self, lang):
        self.lang = lang if lang in ("fa", "en") else "en"
        self._retranslate()
        self._refresh()

    def _winner(self):
        for a, b, c in LINES:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a], (a, b, c)
        return None, None

    def _refresh(self):
        winner, line = self._winner()
        for i, btn in enumerate(self.cells):
            sym = self.board[i]
            btn.setText(sym)
            color = "#55a8ff" if sym == "X" else "#ff54bd"
            hl = "background: #172d4b;" if line and i in line else ""
            btn.setStyleSheet(f"color: {color}; {hl}")
            btn.setEnabled(not self.over and not sym and self.turn == self.me)
        if winner:
            self.status_lbl.setText(self._t("you_win") if winner == self.me else self._t("they_win", name=self.opponent))
        elif self.over:
            self.status_lbl.setText(self._t("draw"))
        elif self.turn == self.me:
            self.status_lbl.setText(self._t("your_turn", s=self.me))
        else:
            self.status_lbl.setText(self._t("their_turn", name=self.opponent, s=self.them))
        if self.opponent_left:
            self.status_lbl.setText(self._t("left", name=self.opponent))
        self.again_btn.setVisible(self.over and not self.opponent_left)

    def _place(self, index, symbol):
        self.board[index] = symbol
        winner, _ = self._winner()
        if winner or all(self.board):
            self.over = True
        else:
            self.turn = "O" if symbol == "X" else "X"
        self._refresh()

    def _on_cell(self, index):
        if self.over or self.turn != self.me or self.board[index]:
            return
        self._place(index, self.me)
        self.send_cb({"game": "ttt", "op": "move", "id": self.gid, "cell": index})

    def _request_reset(self):
        self._reset()
        self.send_cb({"game": "ttt", "op": "reset", "id": self.gid})

    def _reset(self):
        self.board = [""] * 9
        self.turn = "X"
        self.over = False
        self._refresh()

    def on_remote(self, content):
        op = content.get("op")
        if op == "move":
            try:
                index = int(content.get("cell"))
            except (TypeError, ValueError):
                return
            if 0 <= index < 9 and not self.over and self.turn == self.them and not self.board[index]:
                self._place(index, self.them)
        elif op == "reset":
            self._reset()
        elif op == "leave":
            self.opponent_left = True
            self._refresh()

    def closeEvent(self, event):
        if not self.opponent_left:
            self.send_cb({"game": "ttt", "op": "leave", "id": self.gid})
        super().closeEvent(event)


# ---------------- online typing race ----------------

import time as _time

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLineEdit

STR_RACE = {
    "title": {"fa": "مسابقه‌ی تایپ آنلاین", "en": "Online typing race"},
    "get_ready": {"fa": "آماده... {n}", "en": "Get ready... {n}"},
    "go": {"fa": "شروع! جمله رو دقیق تایپ کنید.", "en": "Go! Type the sentence exactly."},
    "you_done": {"fa": "تموم شد: {sec} ثانیه. منتظر {name}...", "en": "Finished in {sec}s. Waiting for {name}..."},
    "you_win": {"fa": "\U0001F389 بردید! شما {a}s، {name} {b}s", "en": "\U0001F389 You win! You {a}s, {name} {b}s"},
    "they_win": {"fa": "{name} برد. شما {a}s، {name} {b}s", "en": "{name} wins. You {a}s, {name} {b}s"},
    "left": {"fa": "{name} بازی رو ترک کرد.", "en": "{name} left the race."},
    "opp_done": {"fa": "{name} تموم کرد ({sec}s)!", "en": "{name} finished ({sec}s)!"},
}


class OnlineTypingWindow(QMainWindow):
    """Both people type the same sentence; the faster correct finish wins."""

    def __init__(self, gid, opponent, sentence, send_cb, lang="en"):
        super().__init__()
        self.gid, self.opponent, self.sentence, self.send_cb = gid, opponent, sentence, send_cb
        self.lang = lang if lang in ("fa", "en") else "en"
        self.started_at = None
        self.my_ms = None
        self.their_ms = None
        self.left = False
        self.setMinimumSize(520, 300)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(10)
        self.target_lbl = QLabel(sentence)
        self.target_lbl.setWordWrap(True)
        self.target_lbl.setStyleSheet(
            "font-size: 14pt; padding: 14px; background: #101f35; border: 1px solid #243b60; border-radius: 12px;"
        )
        root.addWidget(self.target_lbl)
        self.edit = QLineEdit()
        self.edit.setEnabled(False)
        self.edit.setStyleSheet("font-size: 13pt;")
        self.edit.textChanged.connect(self._on_text)
        root.addWidget(self.edit)
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size: 12pt; font-weight: 700; color: #55f7ff;")
        self.status_lbl.setWordWrap(True)
        root.addWidget(self.status_lbl)
        root.addStretch(1)
        self.setStyleSheet(TOOL_STYLE)
        self.setWindowTitle("\u2328 " + STR_RACE["title"][self.lang])

        self._count = 3
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._countdown)
        self._timer.start()
        self._countdown()

    def _t(self, key, **kw):
        return STR_RACE[key][self.lang].format(**kw)

    def set_language(self, lang):
        self.lang = lang if lang in ("fa", "en") else "en"

    def _countdown(self):
        if self._count > 0:
            self.status_lbl.setText(self._t("get_ready", n=self._count))
            self._count -= 1
            return
        self._timer.stop()
        self.edit.setEnabled(True)
        self.edit.setFocus()
        self.started_at = _time.time()
        self.status_lbl.setText(self._t("go"))

    def _on_text(self, text):
        if self.started_at is None or self.my_ms is not None:
            return
        if text == self.sentence:
            self.my_ms = int((_time.time() - self.started_at) * 1000)
            self.edit.setEnabled(False)
            self.send_cb({"game": "type", "op": "done", "id": self.gid, "ms": self.my_ms})
            self._update()

    def _update(self):
        if self.my_ms is not None and self.their_ms is not None:
            a, b = f"{self.my_ms / 1000:.1f}", f"{self.their_ms / 1000:.1f}"
            key = "you_win" if self.my_ms <= self.their_ms else "they_win"
            self.status_lbl.setText(self._t(key, name=self.opponent, a=a, b=b))
        elif self.my_ms is not None:
            self.status_lbl.setText(self._t("you_done", sec=f"{self.my_ms / 1000:.1f}", name=self.opponent))

    def on_remote(self, content):
        op = content.get("op")
        if op == "done":
            try:
                self.their_ms = int(content.get("ms"))
            except (TypeError, ValueError):
                return
            if self.my_ms is None:
                self.status_lbl.setText(self._t("opp_done", name=self.opponent, sec=f"{self.their_ms / 1000:.1f}"))
            else:
                self._update()
        elif op == "leave":
            self.left = True
            self.status_lbl.setText(self._t("left", name=self.opponent))

    def closeEvent(self, event):
        if not self.left:
            self.send_cb({"game": "type", "op": "leave", "id": self.gid})
        super().closeEvent(event)
