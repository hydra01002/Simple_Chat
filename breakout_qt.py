"""شکستن آجرها (Breakout) - PyQt6   |   pip install PyQt6"""
import math
import sys

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

W, H = 600, 480
PW, PH = 90, 12
BR_ROWS, BR_COLS = 6, 10
BW, BH = W // BR_COLS, 22
ROW_COLORS = ["#e64646", "#f09628", "#f0c83c", "#3cc85a", "#3cc8e6", "#4678f0"]


class Breakout(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(W, H)
        self.setWindowTitle("Breakout")
        self.setMouseTracking(True)
        self.pressed = set()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.reset()

    def reset(self):
        self.px = W / 2 - PW / 2
        self.bricks = {(r, c) for r in range(BR_ROWS) for c in range(BR_COLS)}
        self.score, self.lives = 0, 3
        self.state = "ready"   # ready / play / over / win
        self.place_ball()
        self.timer.start(16)

    def place_ball(self):
        self.bx, self.by = self.px + PW / 2, H - 50
        self.vx, self.vy = 3.5, -4.5

    def tick(self):
        if Qt.Key.Key_Left in self.pressed:
            self.px -= 8
        if Qt.Key.Key_Right in self.pressed:
            self.px += 8
        self.px = max(0, min(W - PW, self.px))
        if self.state == "ready":
            self.bx = self.px + PW / 2
        elif self.state == "play":
            self.bx += self.vx
            self.by += self.vy
            if self.bx < 6 or self.bx > W - 6:
                self.vx = -self.vx
            if self.by < 6:
                self.vy = abs(self.vy)
            paddle = QRectF(self.px, H - 30, PW, PH)
            if paddle.contains(self.bx, self.by + 6) and self.vy > 0:
                off = (self.bx - (self.px + PW / 2)) / (PW / 2)
                speed = math.hypot(self.vx, self.vy)
                self.vx = off * 5
                self.vy = -math.sqrt(max(speed ** 2 - self.vx ** 2, 4))
            for (r, c) in list(self.bricks):
                if QRectF(c * BW, 50 + r * BH, BW - 2, BH - 2).contains(self.bx, self.by):
                    self.bricks.discard((r, c))
                    self.vy = -self.vy
                    self.score += 10
                    break
            if not self.bricks:
                self.state = "win"
            if self.by > H:
                self.lives -= 1
                if self.lives == 0:
                    self.state = "over"
                else:
                    self.state = "ready"
                    self.place_ball()
        self.update()

    def launch(self):
        if self.state == "ready":
            self.state = "play"
        elif self.state in ("over", "win"):
            self.reset()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Space:
            self.launch()
        self.pressed.add(e.key())

    def keyReleaseEvent(self, e):
        self.pressed.discard(e.key())

    def mouseMoveEvent(self, e):
        self.px = e.position().x() - PW / 2

    def mousePressEvent(self, e):
        self.launch()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(15, 15, 25))
        p.setPen(Qt.PenStyle.NoPen)
        for r, c in self.bricks:
            p.setBrush(QColor(ROW_COLORS[r]))
            p.drawRect(c * BW, 50 + r * BH, BW - 2, BH - 2)
        p.setBrush(QColor(70, 130, 240))
        p.drawRect(int(self.px), H - 30, PW, PH)
        p.setBrush(QColor(240, 240, 240))
        p.drawEllipse(int(self.bx) - 6, int(self.by) - 6, 12, 12)
        p.setPen(QColor(240, 240, 240))
        p.setFont(QFont("Arial", 13))
        p.drawText(10, 24, f"Score: {self.score}")
        p.drawText(W - 100, 24, f"Lives: {self.lives}")
        if self.state != "play":
            p.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            msg = {"ready": "Space / Click to launch", "over": "Game Over\n(Space = restart)",
                   "win": "You Win!\n(Space = restart)"}[self.state]
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Breakout()
    w.show()
    sys.exit(app.exec())
