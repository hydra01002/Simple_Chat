"""شطرنج ساده (شما سفید، کامپیوتر سیاه) - PyQt6   |   pip install PyQt6
قوانین: حرکت‌های قانونی + کیش و مات. (بدون قلعه، آن‌پاسان؛ پیاده در انتها وزیر می‌شود)
N = بازی جدید"""
import random
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

S, TOP = 70, 40
GLYPH = {"K": "♚", "Q": "♛", "R": "♜", "B": "♝", "N": "♞", "P": "♟"}
VAL = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 200}
KN = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
ROOK = [(1, 0), (-1, 0), (0, 1), (0, -1)]
BISH = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


def start_board():
    back = "RNBQKBNR"
    b = [[""] * 8 for _ in range(8)]
    for c in range(8):
        b[0][c], b[1][c] = "b" + back[c], "bP"
        b[6][c], b[7][c] = "wP", "w" + back[c]
    return b


def inb(r, c):
    return 0 <= r < 8 and 0 <= c < 8


def pseudo(b, r, c):
    p = b[r][c]
    col, t = p[0], p[1]
    out = []
    if t == "P":
        d, start = (-1, 6) if col == "w" else (1, 1)
        if inb(r + d, c) and not b[r + d][c]:
            out.append((r + d, c))
            if r == start and not b[r + 2 * d][c]:
                out.append((r + 2 * d, c))
        for dc in (-1, 1):
            nr, nc = r + d, c + dc
            if inb(nr, nc) and b[nr][nc] and b[nr][nc][0] != col:
                out.append((nr, nc))
    elif t in "NK":
        steps = KN if t == "N" else ROOK + BISH
        for dr, dc in steps:
            nr, nc = r + dr, c + dc
            if inb(nr, nc) and (not b[nr][nc] or b[nr][nc][0] != col):
                out.append((nr, nc))
    else:
        dirs = {"R": ROOK, "B": BISH, "Q": ROOK + BISH}[t]
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            while inb(nr, nc):
                if b[nr][nc]:
                    if b[nr][nc][0] != col:
                        out.append((nr, nc))
                    break
                out.append((nr, nc))
                nr, nc = nr + dr, nc + dc
    return out


def apply(b, m):
    r, c, nr, nc = m
    nb = [row[:] for row in b]
    piece = nb[r][c]
    nb[nr][nc], nb[r][c] = piece, ""
    if piece[1] == "P" and nr in (0, 7):
        nb[nr][nc] = piece[0] + "Q"
    return nb


def in_check(b, col):
    king = next(((r, c) for r in range(8) for c in range(8) if b[r][c] == col + "K"), None)
    if king is None:
        return True
    enemy = "b" if col == "w" else "w"
    return any(king in pseudo(b, r, c) for r in range(8) for c in range(8)
               if b[r][c] and b[r][c][0] == enemy)


def all_moves(b, col, legal=True):
    moves = []
    for r in range(8):
        for c in range(8):
            if b[r][c] and b[r][c][0] == col:
                for nr, nc in pseudo(b, r, c):
                    m = (r, c, nr, nc)
                    if not legal or not in_check(apply(b, m), col):
                        moves.append(m)
    return moves


def material(b):
    s = 0
    for row in b:
        for p in row:
            if p:
                s += VAL[p[1]] * (1 if p[0] == "w" else -1)
    return s


def search(b, col, depth, alpha, beta):
    """امتیاز از دید سفید؛ سفید ماکزیمم، سیاه مینیمم"""
    if depth == 0:
        return material(b)
    moves = all_moves(b, col, legal=False)
    other = "b" if col == "w" else "w"
    best = -10 ** 6 if col == "w" else 10 ** 6
    for m in moves:
        v = search(apply(b, m), other, depth - 1, alpha, beta)
        if col == "w":
            best = max(best, v)
            alpha = max(alpha, best)
        else:
            best = min(best, v)
            beta = min(beta, best)
        if alpha >= beta:
            break
    return best


class Chess(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(8 * S, 8 * S + TOP)
        self.setWindowTitle("Chess")
        self.reset()

    def reset(self):
        self.b = start_board()
        self.turn, self.sel, self.targets, self.busy = "w", None, [], False
        self.msg = "Your move (white)"
        self.update()

    def mousePressEvent(self, e):
        if self.turn != "w" or self.busy or self.msg.startswith(("Checkmate", "Stalemate")):
            return
        r, c = int((e.position().y() - TOP) // S), int(e.position().x() // S)
        if not inb(r, c):
            return
        if self.sel and (r, c) in self.targets:
            self.b = apply(self.b, (*self.sel, r, c))
            self.sel, self.targets = None, []
            self.after_move("b")
            if self.turn == "b":
                self.busy = True
                QTimer.singleShot(60, self.ai_move)
        elif self.b[r][c] and self.b[r][c][0] == "w":
            self.sel = (r, c)
            self.targets = [(m[2], m[3]) for m in all_moves(self.b, "w") if m[:2] == (r, c)]
        else:
            self.sel, self.targets = None, []
        self.update()

    def after_move(self, nxt):
        moves = all_moves(self.b, nxt)
        chk = in_check(self.b, nxt)
        if not moves:
            who = "You win" if nxt == "b" else "Computer wins"
            self.msg = f"Checkmate! {who} (N = new)" if chk else "Stalemate! (N = new)"
            self.turn = ""
        else:
            self.turn = nxt
            self.msg = ("Check! " if chk else "") + ("Your move" if nxt == "w" else "Thinking...")

    def ai_move(self):
        moves = all_moves(self.b, "b")
        random.shuffle(moves)
        best, best_v = moves[0], 10 ** 6
        for m in moves:
            v = search(apply(self.b, m), "w", 1, -10 ** 6, 10 ** 6)
            if v < best_v:
                best, best_v = m, v
        self.b = apply(self.b, best)
        self.busy = False
        self.after_move("w")
        self.update()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_N:
            self.reset()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(25, 25, 35))
        p.setPen(QColor(240, 240, 240))
        p.setFont(QFont("Arial", 14))
        p.drawText(0, 0, 8 * S, TOP, Qt.AlignmentFlag.AlignCenter, self.msg)
        for r in range(8):
            for c in range(8):
                x, y = c * S, TOP + r * S
                light = (r + c) % 2 == 0
                col = QColor(235, 215, 175) if light else QColor(170, 120, 80)
                if self.sel == (r, c):
                    col = QColor(240, 230, 90)
                p.fillRect(x, y, S, S, col)
                if (r, c) in self.targets:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(60, 160, 90, 170))
                    p.drawEllipse(x + S // 2 - 9, y + S // 2 - 9, 18, 18)
                piece = self.b[r][c]
                if piece:
                    p.setFont(QFont("Arial", 40))
                    p.setPen(QColor(250, 250, 250) if piece[0] == "w" else QColor(20, 20, 20))
                    p.drawText(x, y, S, S, Qt.AlignmentFlag.AlignCenter, GLYPH[piece[1]])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Chess()
    w.show()
    sys.exit(app.exec())
