"""سودوکو - PyQt6   |   pip install PyQt6
کلیک روی خانه، عدد 1-9 برای نوشتن، 0/Backspace برای پاک کردن، N = بازی جدید"""
import random
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

S, TOP = 56, 50
REMOVE = 45


def ok(g, r, c, v):
    if any(g[r][i] == v for i in range(9)) or any(g[i][c] == v for i in range(9)):
        return False
    br, bc = r // 3 * 3, c // 3 * 3
    return all(g[br + i][bc + j] != v for i in range(3) for j in range(3))


def fill(g):
    for r in range(9):
        for c in range(9):
            if g[r][c] == 0:
                nums = list(range(1, 10))
                random.shuffle(nums)
                for v in nums:
                    if ok(g, r, c, v):
                        g[r][c] = v
                        if fill(g):
                            return True
                        g[r][c] = 0
                return False
    return True


class Sudoku(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(9 * S, 9 * S + TOP)
        self.setWindowTitle("Sudoku")
        self.new()

    def new(self):
        sol = [[0] * 9 for _ in range(9)]
        fill(sol)
        self.sol = sol
        self.g = [row[:] for row in sol]
        for i in random.sample(range(81), REMOVE):
            self.g[i // 9][i % 9] = 0
        self.fixed = [[v != 0 for v in row] for row in self.g]
        self.sel = None
        self.update()

    def solved(self):
        return self.g == self.sol

    def conflict(self, r, c):
        v = self.g[r][c]
        if not v:
            return False
        self.g[r][c] = 0
        bad = not ok(self.g, r, c, v)
        self.g[r][c] = v
        return bad

    def mousePressEvent(self, e):
        y = e.position().y() - TOP
        if y >= 0:
            self.sel = (int(y // S), int(e.position().x() // S))
            self.update()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_N:
            self.new()
            return
        if not self.sel or self.solved():
            return
        r, c = self.sel
        if self.fixed[r][c]:
            return
        k = e.key()
        if Qt.Key.Key_1 <= k <= Qt.Key.Key_9:
            self.g[r][c] = k - Qt.Key.Key_0
        elif k in (Qt.Key.Key_0, Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.g[r][c] = 0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(250, 250, 252))
        p.setPen(QColor(30, 30, 40))
        p.setFont(QFont("Arial", 13))
        msg = "Solved! (N = new game)" if self.solved() else "Sudoku  (N = new game)"
        p.drawText(0, 0, 9 * S, TOP, Qt.AlignmentFlag.AlignCenter, msg)
        for r in range(9):
            for c in range(9):
                x, y = c * S, TOP + r * S
                if self.sel == (r, c):
                    p.fillRect(x, y, S, S, QColor(190, 215, 250))
                elif self.fixed[r][c]:
                    p.fillRect(x, y, S, S, QColor(232, 232, 238))
                v = self.g[r][c]
                if v:
                    bad = self.conflict(r, c)
                    p.setPen(QColor(210, 40, 40) if bad else
                             QColor(20, 20, 30) if self.fixed[r][c] else QColor(40, 90, 200))
                    p.setFont(QFont("Arial", 22, QFont.Weight.Bold if self.fixed[r][c] else QFont.Weight.Normal))
                    p.drawText(x, y, S, S, Qt.AlignmentFlag.AlignCenter, str(v))
        for i in range(10):
            p.setPen(QColor(20, 20, 30) if i % 3 == 0 else QColor(180, 180, 190))
            w = 3 if i % 3 == 0 else 1
            pen = p.pen()
            pen.setWidth(w)
            p.setPen(pen)
            p.drawLine(i * S, TOP, i * S, TOP + 9 * S)
            p.drawLine(0, TOP + i * S, 9 * S, TOP + i * S)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Sudoku()
    w.show()
    sys.exit(app.exec())
