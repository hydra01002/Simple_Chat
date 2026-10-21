"""مهاجمان فضایی (Space Invaders) - PyQt6   |   pip install PyQt6"""
import random
import sys

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

W, H = 600, 520


class Invaders(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(W, H)
        self.setWindowTitle("Space Invaders")
        self.pressed = set()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.reset()

    def reset(self):
        self.px = W / 2 - 20
        self.aliens = [[60 + c * 50, 60 + r * 40] for r in range(4) for c in range(9)]
        self.dir, self.speed = 1, 1.0
        self.bullets, self.enemy_bullets = [], []
        self.cool = 0
        self.score, self.lives = 0, 3
        self.state = "play"
        self.timer.start(16)

    def tick(self):
        if self.state != "play":
            return
        if Qt.Key.Key_Left in self.pressed:
            self.px -= 6
        if Qt.Key.Key_Right in self.pressed:
            self.px += 6
        self.px = max(0, min(W - 40, self.px))
        self.cool = max(0, self.cool - 1)
        if Qt.Key.Key_Space in self.pressed and self.cool == 0:
            self.bullets.append([self.px + 19, H - 50])
            self.cool = 25
        for b in self.bullets:
            b[1] -= 9
        self.bullets = [b for b in self.bullets if b[1] > 0]
        # حرکت بیگانه‌ها
        edge = False
        for a in self.aliens:
            a[0] += self.dir * self.speed
            if a[0] < 10 or a[0] > W - 40:
                edge = True
        if edge:
            self.dir = -self.dir
            for a in self.aliens:
                a[1] += 18
        # شلیک بیگانه‌ها
        if self.aliens and random.random() < 0.03:
            a = random.choice(self.aliens)
            self.enemy_bullets.append([a[0] + 14, a[1] + 20])
        for b in self.enemy_bullets:
            b[1] += 5
        self.enemy_bullets = [b for b in self.enemy_bullets if b[1] < H]
        # برخوردها
        for b in list(self.bullets):
            for a in self.aliens:
                if QRectF(a[0], a[1], 28, 20).contains(b[0], b[1]):
                    self.aliens.remove(a)
                    self.bullets.remove(b)
                    self.score += 10
                    self.speed += 0.04
                    break
        ship = QRectF(self.px, H - 40, 40, 20)
        for b in list(self.enemy_bullets):
            if ship.contains(b[0], b[1]):
                self.enemy_bullets.remove(b)
                self.lives -= 1
        if self.lives <= 0 or any(a[1] > H - 70 for a in self.aliens):
            self.state = "over"
        if not self.aliens:
            self.state = "win"
        self.update()

    def keyPressEvent(self, e):
        if self.state != "play" and e.key() == Qt.Key.Key_Return:
            self.reset()
        self.pressed.add(e.key())

    def keyReleaseEvent(self, e):
        self.pressed.discard(e.key())

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(8, 8, 20))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(60, 200, 90))
        p.drawRect(int(self.px), H - 40, 40, 20)
        p.drawRect(int(self.px) + 16, H - 48, 8, 8)
        p.setBrush(QColor(230, 70, 70))
        for a in self.aliens:
            p.drawRect(int(a[0]), int(a[1]), 28, 20)
        p.setBrush(QColor(240, 240, 100))
        for b in self.bullets:
            p.drawRect(int(b[0]), int(b[1]), 3, 10)
        p.setBrush(QColor(240, 140, 60))
        for b in self.enemy_bullets:
            p.drawRect(int(b[0]), int(b[1]), 3, 10)
        p.setPen(QColor(240, 240, 240))
        p.setFont(QFont("Arial", 13))
        p.drawText(10, 24, f"Score: {self.score}")
        p.drawText(W - 100, 24, f"Lives: {self.lives}")
        if self.state != "play":
            p.setFont(QFont("Arial", 28, QFont.Weight.Bold))
            msg = "You Win!" if self.state == "win" else "Game Over"
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, msg + "\n(Enter = restart)")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Invaders()
    w.show()
    sys.exit(app.exec())
