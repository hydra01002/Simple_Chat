"""حدس کلمه (Hangman) - PyQt6   |   pip install PyQt6
حرف‌ها را روی کیبورد بزنید. Enter = بازی جدید"""
import random
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget

WORDS = """python keyboard monitor program variable function internet network compiler
database algorithm developer software hardware elephant giraffe mountain
adventure chocolate umbrella bicycle library journey puzzle rainbow""".split()
W, H, MAX_WRONG = 480, 460, 6


class Hangman(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(W, H)
        self.setWindowTitle("Hangman")
        self.reset()

    def reset(self):
        self.word = random.choice(WORDS)
        self.guessed = set()
        self.update()

    @property
    def wrong(self):
        return [ch for ch in self.guessed if ch not in self.word]

    @property
    def state(self):
        if len(self.wrong) >= MAX_WRONG:
            return "lost"
        if all(ch in self.guessed for ch in self.word):
            return "won"
        return "play"

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_Return:
            self.reset()
        elif self.state == "play" and Qt.Key.Key_A <= k <= Qt.Key.Key_Z:
            self.guessed.add(chr(k).lower())
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(20, 20, 30))
        pen = QPen(QColor(220, 220, 230), 4)
        p.setPen(pen)
        p.drawLine(40, 300, 200, 300)
        p.drawLine(80, 300, 80, 60)
        p.drawLine(80, 60, 220, 60)
        p.drawLine(220, 60, 220, 90)
        n = len(self.wrong)
        if n > 0:
            p.drawEllipse(200, 90, 40, 40)
        if n > 1:
            p.drawLine(220, 130, 220, 205)
        if n > 2:
            p.drawLine(220, 145, 190, 180)
        if n > 3:
            p.drawLine(220, 145, 250, 180)
        if n > 4:
            p.drawLine(220, 205, 195, 250)
        if n > 5:
            p.drawLine(220, 205, 245, 250)
        p.setPen(QColor(240, 240, 240))
        p.setFont(QFont("Courier New", 28, QFont.Weight.Bold))
        shown = " ".join(ch if ch in self.guessed or self.state == "lost" else "_" for ch in self.word)
        p.drawText(0, 330, W, 50, Qt.AlignmentFlag.AlignCenter, shown)
        p.setFont(QFont("Arial", 13))
        p.drawText(0, 385, W, 25, Qt.AlignmentFlag.AlignCenter, "Wrong: " + " ".join(sorted(self.wrong)).upper())
        msg = {"play": f"Lives left: {MAX_WRONG - n}", "won": "You won! (Enter = new game)",
               "lost": "You lost! (Enter = new game)"}[self.state]
        p.drawText(0, 415, W, 25, Qt.AlignmentFlag.AlignCenter, msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Hangman()
    w.show()
    sys.exit(app.exec())
