"""چهار در یک ردیف (Connect Four) - PyQt6   |   pip install PyQt6"""
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

COLS, ROWS, S = 7, 6, 80
HUMAN, AI = 1, 2


def drop(b, c, who):
    for r in range(ROWS - 1, -1, -1):
        if b[r][c] == 0:
            b[r][c] = who
            return r
    return None


def four(b, who):
    for r in range(ROWS):
        for c in range(COLS):
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                cells = [(r + dr * k, c + dc * k) for k in range(4)]
                if all(0 <= y < ROWS and 0 <= x < COLS and b[y][x] == who for y, x in cells):
                    return True
    return False


def score(b):
    s = 0
    for r in range(ROWS):
        for c in range(COLS):
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                cells = [(r + dr * k, c + dc * k) for k in range(4)]
                if all(0 <= y < ROWS and 0 <= x < COLS for y, x in cells):
                    v = [b[y][x] for y, x in cells]
                    if v.count(AI) and not v.count(HUMAN):
                        s += 10 ** v.count(AI)
                    if v.count(HUMAN) and not v.count(AI):
                        s -= 10 ** v.count(HUMAN)
    s += sum(3 for r in range(ROWS) if b[r][3] == AI)
    return s


def search(b, depth, alpha, beta, maxi):
    if four(b, AI):
        return 100000 + depth, None
    if four(b, HUMAN):
        return -100000 - depth, None
    moves = [c for c in (3, 2, 4, 1, 5, 0, 6) if b[0][c] == 0]
    if not moves:
        return 0, None
    if depth == 0:
        return score(b), None
    best_move = moves[0]
    if maxi:
        best = -10 ** 9
        for c in moves:
            r = drop(b, c, AI)
            v, _ = search(b, depth - 1, alpha, beta, False)
            b[r][c] = 0
            if v > best:
                best, best_move = v, c
            alpha = max(alpha, best)
            if alpha >= beta:
                break
    else:
        best = 10 ** 9
        for c in moves:
            r = drop(b, c, HUMAN)
            v, _ = search(b, depth - 1, alpha, beta, True)
            b[r][c] = 0
            if v < best:
                best, best_move = v, c
            beta = min(beta, best)
            if alpha >= beta:
                break
    return best, best_move


class Connect4(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(COLS * S, ROWS * S + 50)
        self.setWindowTitle("Connect Four")
        self.reset()

    def reset(self):
        self.b = [[0] * COLS for _ in range(ROWS)]
        self.msg, self.done, self.busy = "Your move (red) - click a column", False, False
        self.update()

    def mousePressEvent(self, e):
        if self.done:
            self.reset()
            return
        if self.busy:
            return
        c = int(e.position().x() // S)
        if 0 <= c < COLS and drop(self.b, c, HUMAN) is not None:
            if self.finish(HUMAN):
                return
            self.busy, self.msg = True, "Thinking..."
            self.update()
            QTimer.singleShot(50, self.ai_move)

    def ai_move(self):
        _, c = search(self.b, 5, -10 ** 9, 10 ** 9, True)
        drop(self.b, c, AI)
        self.busy = False
        if not self.finish(AI):
            self.msg = "Your move"
        self.update()

    def finish(self, who):
        if four(self.b, who):
            self.msg = ("You win!" if who == HUMAN else "Computer wins!") + " (click = restart)"
        elif all(self.b[0]):
            self.msg = "Draw! (click = restart)"
        else:
            return False
        self.done = True
        self.update()
        return True

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(15, 15, 25))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(30, 60, 180))
        p.drawRect(0, 50, COLS * S, ROWS * S)
        colors = {0: QColor(15, 15, 25), HUMAN: QColor(230, 60, 60), AI: QColor(240, 210, 50)}
        for r in range(ROWS):
            for c in range(COLS):
                p.setBrush(colors[self.b[r][c]])
                p.drawEllipse(c * S + 8, 50 + r * S + 8, S - 16, S - 16)
        p.setPen(QColor(240, 240, 240))
        p.setFont(QFont("Arial", 14))
        p.drawText(0, 0, COLS * S, 50, Qt.AlignmentFlag.AlignCenter, self.msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Connect4()
    w.show()
    sys.exit(app.exec())
