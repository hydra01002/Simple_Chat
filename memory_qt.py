"""بازی حافظه (پیدا کردن جفت‌ها) - PyQt6   |   pip install PyQt6"""
import random
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QApplication, QGridLayout, QLabel, QPushButton,
                             QVBoxLayout, QWidget)

SYMBOLS = list("ABCDEFGH")
COLORS = ["#e64646", "#f09628", "#c8a000", "#3cb450", "#2aa0c8", "#4678f0", "#a050dc", "#e0509c"]


class Memory(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Memory Match")
        lay = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Arial", 14))
        self.label.setStyleSheet("font-size: 14pt;")
        lay.addWidget(self.label)
        grid = QGridLayout()
        self.btns = []
        for i in range(16):
            b = QPushButton()
            b.setFixedSize(90, 90)
            b.setFont(QFont("Arial", 30, QFont.Weight.Bold))
            b.clicked.connect(lambda _, i=i: self.flip(i))
            grid.addWidget(b, i // 4, i % 4)
            self.btns.append(b)
        lay.addLayout(grid)
        again = QPushButton("New Game")
        again.clicked.connect(self.reset)
        lay.addWidget(again)
        self.reset()

    def reset(self):
        self.cards = SYMBOLS * 2
        random.shuffle(self.cards)
        self.shown, self.matched, self.moves, self.lock = [], set(), 0, False
        for b in self.btns:
            b.setText("?")
            b.setStyleSheet("font-size:30pt;font-weight:bold;")
            b.setEnabled(True)
        self.label.setText("Moves: 0")

    def reveal(self, i):
        self.btns[i].setText(self.cards[i])
        color = COLORS[SYMBOLS.index(self.cards[i])]
        self.btns[i].setStyleSheet(f"background:{color};color:white;font-size:30pt;font-weight:bold;")

    def hide_card(self, i):
        self.btns[i].setText("?")
        self.btns[i].setStyleSheet("font-size:30pt;font-weight:bold;")

    def flip(self, i):
        if self.lock or i in self.shown or i in self.matched:
            return
        self.reveal(i)
        self.shown.append(i)
        if len(self.shown) == 2:
            self.moves += 1
            a, b = self.shown
            if self.cards[a] == self.cards[b]:
                self.matched |= {a, b}
                self.shown = []
                if len(self.matched) == 16:
                    self.label.setText(f"You won in {self.moves} moves!")
                    return
            else:
                self.lock = True
                QTimer.singleShot(700, self.unflip)
            self.label.setText(f"Moves: {self.moves}")

    def unflip(self):
        for i in self.shown:
            self.hide_card(i)
        self.shown, self.lock = [], False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Memory()
    w.show()
    sys.exit(app.exec())
