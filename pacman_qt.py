"""پک‌من ساده - PyQt6   |   pip install PyQt6"""
import random
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

MAZE = [
    "###############",
    "#o...........o#",
    "#.###.###.###.#",
    "#.............#",
    "#.###.#.#.###.#",
    "#.....#.#.....#",
    "###.#.....#.###",
    "#...#.###.#...#",
    "#.###.....###.#",
    "#.............#",
    "#.##.#####.##.#",
    "#o...........o#",
    "###############",
]
ROWS, COLS, S = len(MAZE), len(MAZE[0]), 36
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
GHOST_COLORS = ["#e64646", "#f08cc8"]
GHOST_STARTS = [(1, 3), (13, 3)]


class Pacman(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(COLS * S, ROWS * S + 30)
        self.setWindowTitle("Pac-Man")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.reset()

    def reset(self):
        self.walls, self.dots, self.power = set(), set(), set()
        for y, row in enumerate(MAZE):
            for x, ch in enumerate(row):
                if ch == "#":
                    self.walls.add((x, y))
                elif ch == ".":
                    self.dots.add((x, y))
                elif ch == "o":
                    self.power.add((x, y))
        self.pac, self.dir, self.want = (7, 9), (0, 0), (0, 0)
        self.ghosts = [list(g) for g in GHOST_STARTS]
        self.fright = 0
        self.score, self.lives = 0, 3
        self.state = "play"
        self.timer.start(170)
        self.update()

    def free(self, x, y):
        return (x, y) not in self.walls

    def tick(self):
        if self.state != "play":
            return
        x, y = self.pac
        if self.free(x + self.want[0], y + self.want[1]):
            self.dir = self.want
        if self.free(x + self.dir[0], y + self.dir[1]):
            self.pac = (x + self.dir[0], y + self.dir[1])
        if self.pac in self.dots:
            self.dots.discard(self.pac)
            self.score += 10
        if self.pac in self.power:
            self.power.discard(self.pac)
            self.score += 50
            self.fright = 40
        self.fright = max(0, self.fright - 1)
        for i, g in enumerate(self.ghosts):
            self.move_ghost(g)
            self.check_hit(i)
        if not self.dots and not self.power:
            self.state = "win"
        self.update()

    def move_ghost(self, g):
        options = [d for d in DIRS if self.free(g[0] + d[0], g[1] + d[1])]
        if len(options) > 1 and len(g) > 2:
            back = (-g[2][0], -g[2][1])
            options = [d for d in options if d != back] or options
        if random.random() < 0.65:
            sign = -1 if self.fright else 1   # در حالت ترس فرار می‌کند
            options.sort(key=lambda d: sign * (abs(g[0] + d[0] - self.pac[0]) +
                                              abs(g[1] + d[1] - self.pac[1])))
            d = options[0]
        else:
            d = random.choice(options)
        g[0] += d[0]
        g[1] += d[1]
        g[2:] = [d]

    def check_hit(self, i):
        g = self.ghosts[i]
        if (g[0], g[1]) != self.pac:
            return
        if self.fright:
            self.score += 200
            self.ghosts[i] = list(GHOST_STARTS[i])
        else:
            self.lives -= 1
            self.pac, self.dir, self.want = (7, 9), (0, 0), (0, 0)
            self.ghosts = [list(s) for s in GHOST_STARTS]
            if self.lives <= 0:
                self.state = "over"

    def keyPressEvent(self, e):
        keys = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0),
                Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}
        if e.key() in keys:
            self.want = keys[e.key()]
        elif self.state != "play" and e.key() == Qt.Key.Key_Return:
            self.reset()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(10, 10, 25))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(40, 60, 200))
        for x, y in self.walls:
            p.drawRoundedRect(x * S + 1, y * S + 1, S - 2, S - 2, 6, 6)
        p.setBrush(QColor(240, 220, 180))
        for x, y in self.dots:
            p.drawEllipse(x * S + S // 2 - 3, y * S + S // 2 - 3, 6, 6)
        for x, y in self.power:
            p.drawEllipse(x * S + S // 2 - 8, y * S + S // 2 - 8, 16, 16)
        p.setBrush(QColor(250, 220, 40))
        p.drawEllipse(self.pac[0] * S + 4, self.pac[1] * S + 4, S - 8, S - 8)
        for i, g in enumerate(self.ghosts):
            p.setBrush(QColor("#4060ff") if self.fright else QColor(GHOST_COLORS[i]))
            p.drawRoundedRect(g[0] * S + 4, g[1] * S + 4, S - 8, S - 8, 10, 10)
        p.setPen(QColor(240, 240, 240))
        p.setFont(QFont("Arial", 13))
        p.drawText(10, ROWS * S + 22, f"Score: {self.score}    Lives: {self.lives}")
        if self.state != "play":
            p.setFont(QFont("Arial", 26, QFont.Weight.Bold))
            msg = "You Win!" if self.state == "win" else "Game Over"
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, msg + "\n(Enter = restart)")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Pacman()
    w.show()
    sys.exit(app.exec())
