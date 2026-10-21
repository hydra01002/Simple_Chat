"""بازی پینگ‌پنگ - PyQt6   |   pip install PyQt6"""
import random
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

W, H, PH, PW = 600, 480, 90, 12


class Pong(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(W, H)
        self.setWindowTitle("Pong")
        self.pressed = set()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.reset()

    def reset(self):
        self.py = self.ay = H / 2 - PH / 2
        self.ps = self.as_ = 0
        self.over = False
        self.serve()
        self.timer.start(16)

    def serve(self):
        self.bx, self.by = W / 2, H / 2
        self.vx = random.choice([-5, 5])
        self.vy = random.choice([-3, 3])

    def tick(self):
        if Qt.Key.Key_Up in self.pressed or Qt.Key.Key_W in self.pressed:
            self.py -= 7
        if Qt.Key.Key_Down in self.pressed or Qt.Key.Key_S in self.pressed:
            self.py += 7
        self.py = max(0, min(H - PH, self.py))
        # هوش مصنوعی ساده
        if self.by > self.ay + PH / 2 + 10:
            self.ay += 4.5
        elif self.by < self.ay + PH / 2 - 10:
            self.ay -= 4.5
        self.ay = max(0, min(H - PH, self.ay))

        self.bx += self.vx
        self.by += self.vy
        if self.by <= 0 or self.by >= H:
            self.vy = -self.vy
        if self.bx <= 30 + PW and self.py <= self.by <= self.py + PH and self.vx < 0:
            self.vx = -self.vx * 1.05
            self.vy += (self.by - (self.py + PH / 2)) / 15
        if self.bx >= W - 30 - PW and self.ay <= self.by <= self.ay + PH and self.vx > 0:
            self.vx = -self.vx * 1.05
        if self.bx < 0 or self.bx > W:
            if self.bx < 0:
                self.as_ += 1
            else:
                self.ps += 1
            self.serve()
            if 5 in (self.ps, self.as_):
                self.over = True
                self.timer.stop()
        self.update()

    def keyPressEvent(self, e):
        if self.over and e.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.reset()
        self.pressed.add(e.key())

    def keyReleaseEvent(self, e):
        self.pressed.discard(e.key())

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(15, 15, 25))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(70, 130, 240))
        p.drawRect(30, int(self.py), PW, PH)
        p.setBrush(QColor(230, 70, 70))
        p.drawRect(W - 30 - PW, int(self.ay), PW, PH)
        p.setBrush(QColor(240, 240, 240))
        p.drawEllipse(int(self.bx) - 8, int(self.by) - 8, 16, 16)
        p.setPen(QColor(240, 240, 240))
        p.setFont(QFont("Arial", 20))
        p.drawText(0, 10, W, 30, Qt.AlignmentFlag.AlignCenter, f"{self.ps}  :  {self.as_}")
        if self.over:
            p.setFont(QFont("Arial", 32, QFont.Weight.Bold))
            msg = "You Win!" if self.ps == 5 else "You Lose"
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{msg}\n(Space = restart)")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Pong()
    w.show()
    sys.exit(app.exec())
