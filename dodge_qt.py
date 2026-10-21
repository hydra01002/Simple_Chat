"""بازی جاخالی از بلوک‌ها - PyQt6   |   pip install PyQt6"""
import random
import sys

from PyQt6.QtCore import QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

W, H = 600, 480


class Dodge(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(W, H)
        self.setWindowTitle("Dodge")
        self.pressed = set()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.reset()

    def reset(self):
        self.px = W // 2 - 25
        self.blocks = []
        self.score = self.frames = 0
        self.over = False
        self.timer.start(16)

    def tick(self):
        if Qt.Key.Key_Left in self.pressed or Qt.Key.Key_A in self.pressed:
            self.px -= 8
        if Qt.Key.Key_Right in self.pressed or Qt.Key.Key_D in self.pressed:
            self.px += 8
        self.px = max(0, min(W - 50, self.px))
        self.frames += 1
        if self.frames % max(10, 30 - self.score // 100) == 0:
            self.blocks.append(QRect(random.randrange(W - 40), -40, 40, 40))
        speed = 4 + self.score // 200
        player = QRect(self.px, H - 40, 50, 20)
        for b in self.blocks:
            b.translate(0, speed)
            if b.intersects(player):
                self.over = True
                self.timer.stop()
        self.blocks = [b for b in self.blocks if b.y() < H]
        self.score += 1
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
        p.setBrush(QColor(60, 200, 90))
        p.drawRect(self.px, H - 40, 50, 20)
        p.setBrush(QColor(230, 70, 70))
        for b in self.blocks:
            p.drawRect(b)
        p.setPen(QColor(240, 240, 240))
        p.setFont(QFont("Arial", 14))
        p.drawText(10, 24, f"Score: {self.score}")
        if self.over:
            p.setFont(QFont("Arial", 32, QFont.Weight.Bold))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       f"Game Over\n{self.score}\n(Space = restart)")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Dodge()
    w.show()
    sys.exit(app.exec())
