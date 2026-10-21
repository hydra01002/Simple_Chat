"""وردل (Wordle) - PyQt6   |   pip install PyQt6
حرف‌ها را تایپ کنید، Enter = ثبت، Backspace = پاک کردن"""
import random
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

WORDS = """apple brave chair dream eagle flame grape house image juice knife lemon money night
ocean piano queen river stone table uncle voice water young zebra beach cloud dance earth field
ghost heart igloo jelly kings light mouse nurse olive plant quiet robot sugar tiger urban vivid
wheel xenon yacht zesty alarm bread candy dairy empty faith giant happy index joker karma laser
magic noble orbit paint quick radio smile train unity video world youth""".split()
S, ROWS = 62, 6


class Wordle(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(5 * S + 40, ROWS * S + 120)
        self.setWindowTitle("Wordle")
        self.reset()

    def reset(self):
        self.word = random.choice(WORDS)
        self.guesses, self.cur, self.state = [], "", "play"
        self.update()

    def score(self, guess):
        res = ["gray"] * 5
        left = list(self.word)
        for i, ch in enumerate(guess):
            if ch == self.word[i]:
                res[i] = "green"
                left.remove(ch)
        for i, ch in enumerate(guess):
            if res[i] == "gray" and ch in left:
                res[i] = "yellow"
                left.remove(ch)
        return res

    def keyPressEvent(self, e):
        if self.state != "play":
            if e.key() == Qt.Key.Key_Return:
                self.reset()
            return
        k = e.key()
        if k == Qt.Key.Key_Backspace:
            self.cur = self.cur[:-1]
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and len(self.cur) == 5:
            self.guesses.append(self.cur)
            if self.cur == self.word:
                self.state = "won"
            elif len(self.guesses) == ROWS:
                self.state = "lost"
            self.cur = ""
        elif Qt.Key.Key_A <= k <= Qt.Key.Key_Z and len(self.cur) < 5:
            self.cur += chr(k).lower()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(18, 18, 24))
        colors = {"green": "#3c9a50", "yellow": "#c8aa28", "gray": "#46464e"}
        for r in range(ROWS):
            word = self.guesses[r] if r < len(self.guesses) else (self.cur if r == len(self.guesses) else "")
            res = self.score(word) if r < len(self.guesses) else None
            for c in range(5):
                x, y = 20 + c * S, 20 + r * S
                p.setPen(QColor(70, 70, 80))
                p.setBrush(QColor(colors[res[c]]) if res else QColor(18, 18, 24))
                p.drawRect(x + 3, y + 3, S - 6, S - 6)
                if c < len(word):
                    p.setPen(QColor(255, 255, 255))
                    p.setFont(QFont("Arial", 24, QFont.Weight.Bold))
                    p.drawText(x, y, S, S, Qt.AlignmentFlag.AlignCenter, word[c].upper())
        p.setPen(QColor(240, 240, 240))
        p.setFont(QFont("Arial", 14))
        msg = {"play": "Type a 5-letter word + Enter",
               "won": "You got it! (Enter = new game)",
               "lost": f"The word was {self.word.upper()} (Enter = new game)"}[self.state]
        p.drawText(0, ROWS * S + 40, self.width(), 40, Qt.AlignmentFlag.AlignCenter, msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Wordle()
    w.show()
    sys.exit(app.exec())
