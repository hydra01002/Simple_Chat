import sys
import random

from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout

COLS, ROWS = 10, 20
CELL = 26
BOARD_W, BOARD_H = COLS * CELL, ROWS * CELL

# Each shape is a list of rotation states; each state is a list of (x, y) cells.
SHAPES = {
    "I": {"color": "#55f7ff", "rots": [
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
    ]},
    "O": {"color": "#ffd166", "rots": [
        [(1, 0), (2, 0), (1, 1), (2, 1)],
    ]},
    "T": {"color": "#c77dff", "rots": [
        [(1, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (1, 2)],
        [(1, 0), (0, 1), (1, 1), (1, 2)],
    ]},
    "S": {"color": "#1fbf5c", "rots": [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
    ]},
    "Z": {"color": "#ff5555", "rots": [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(2, 0), (1, 1), (2, 1), (1, 2)],
    ]},
    "J": {"color": "#5577ff", "rots": [
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (0, 2), (1, 2)],
    ]},
    "L": {"color": "#ff9f43", "rots": [
        [(2, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 1), (0, 2)],
        [(0, 0), (1, 0), (1, 1), (1, 2)],
    ]},
}
SHAPE_NAMES = list(SHAPES.keys())

LEVEL_SPEEDS = [800, 650, 520, 420, 340, 270, 220, 180, 150, 120]


class Piece:
    def __init__(self, name):
        self.name = name
        self.color = SHAPES[name]["color"]
        self.rot = 0
        self.x = 3
        self.y = -1

    def cells(self, rot=None):
        rots = SHAPES[self.name]["rots"]
        r = rots[(self.rot if rot is None else rot) % len(rots)]
        return [(self.x + dx, self.y + dy) for dx, dy in r]


class Tetris(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TETRIS")
        self.setFixedSize(BOARD_W + 170, BOARD_H + 70)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._drop_tick)

        self.score_label = QLabel("امتیاز: 0")
        self.lines_label = QLabel("خط: 0")
        self.level_label = QLabel("مرحله: 1")
        self.next_label = QLabel("بعدی:")
        self.status_label = QLabel("Space: شروع \u2014 \u2190\u2192 حرکت \u2014 \u2191 چرخش \u2014 \u2193 افت تند")
        self.status_label.setWordWrap(True)
        self.start_button = QPushButton("\u25b6 شروع")
        self.start_button.clicked.connect(self.start_game)

        side = QVBoxLayout()
        side.addWidget(self.score_label)
        side.addWidget(self.lines_label)
        side.addWidget(self.level_label)
        side.addSpacing(10)
        side.addWidget(self.next_label)
        side.addStretch(1)
        side.addWidget(self.start_button)
        side.addWidget(self.status_label)

        root = QHBoxLayout(self)
        root.addStretch(1)
        root.addLayout(side)

        self.setStyleSheet("""
            QWidget { background-color: #0b0d16; color: #e7f7ff; font-family: Segoe UI; font-size: 10.5pt; }
            QLabel { padding: 2px; }
            QPushButton { background-color: #151a2a; color: #55f7ff; border: 1px solid #28556a; border-radius: 8px; padding: 8px; }
            QPushButton:hover { background-color: #24344a; border-color: #55f7ff; }
        """)

        self.reset_game()

    def reset_game(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.bag = []
        self.current = self._next_piece()
        self.next_piece = self._next_piece()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.running = False
        self.game_over = False
        self.update_labels()
        self._update_next_label()
        self.update()

    def _next_piece(self):
        if not self.bag:
            self.bag = SHAPE_NAMES[:]
            random.shuffle(self.bag)
        return Piece(self.bag.pop())

    def start_game(self):
        self.timer.stop()
        self.reset_game()
        self.running = True
        self.status_label.setText("برو که رفتیم!")
        self.timer.start(LEVEL_SPEEDS[0])
        self.setFocus()

    def update_labels(self):
        self.score_label.setText(f"امتیاز: {self.score}")
        self.lines_label.setText(f"خط: {self.lines}")
        self.level_label.setText(f"مرحله: {self.level}")

    def _update_next_label(self):
        self.next_label.setText(f"بعدی: \u25a3 {self.next_piece.name}")
        self.next_label.setStyleSheet(f"color: {self.next_piece.color}; font-weight: 700;")

    def _valid(self, cells):
        for x, y in cells:
            if x < 0 or x >= COLS or y >= ROWS:
                return False
            if y >= 0 and self.board[y][x] is not None:
                return False
        return True

    def _lock_piece(self):
        for x, y in self.current.cells():
            if y < 0:
                self._end_game()
                return
            self.board[y][x] = self.current.color
        self._clear_lines()
        self.current = self.next_piece
        self.next_piece = self._next_piece()
        self._update_next_label()
        if not self._valid(self.current.cells()):
            self._end_game()

    def _clear_lines(self):
        full_rows = [r for r in range(ROWS) if all(self.board[r][c] is not None for c in range(COLS))]
        if not full_rows:
            return
        for r in full_rows:
            del self.board[r]
            self.board.insert(0, [None] * COLS)
        cleared = len(full_rows)
        self.lines += cleared
        self.score += [0, 100, 300, 500, 800][cleared] * self.level
        new_level = 1 + self.lines // 10
        if new_level != self.level:
            self.level = new_level
            self.timer.setInterval(LEVEL_SPEEDS[min(self.level - 1, len(LEVEL_SPEEDS) - 1)])
        self.update_labels()

    def _drop_tick(self):
        if not self.running:
            return
        moved = Piece(self.current.name)
        moved.rot, moved.x, moved.y = self.current.rot, self.current.x, self.current.y + 1
        if self._valid(moved.cells()):
            self.current = moved
        else:
            self._lock_piece()
        self.update()

    def _end_game(self):
        self.running = False
        self.game_over = True
        self.timer.stop()
        self.status_label.setText(f"باختی! امتیاز نهایی: {self.score}")
        self.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Space:
            if not self.running:
                self.start_game()
            else:
                self._hard_drop()
            return
        if not self.running:
            return
        if key in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self._try_move(-1, 0)
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self._try_move(1, 0)
        elif key in (Qt.Key.Key_Down, Qt.Key.Key_S):
            self._try_move(0, 1)
        elif key in (Qt.Key.Key_Up, Qt.Key.Key_W):
            self._try_rotate()

    def _try_move(self, dx, dy):
        moved = Piece(self.current.name)
        moved.rot, moved.x, moved.y = self.current.rot, self.current.x + dx, self.current.y + dy
        if self._valid(moved.cells()):
            self.current = moved
            self.update()

    def _try_rotate(self):
        rotated = Piece(self.current.name)
        rotated.x, rotated.y = self.current.x, self.current.y
        rotated.rot = self.current.rot + 1
        if self._valid(rotated.cells()):
            self.current = rotated
            self.update()
            return
        for kick in (-1, 1, -2, 2):  # simple wall-kick attempts
            kicked = Piece(self.current.name)
            kicked.rot, kicked.x, kicked.y = rotated.rot, rotated.x + kick, rotated.y
            if self._valid(kicked.cells()):
                self.current = kicked
                self.update()
                return

    def _hard_drop(self):
        moved = Piece(self.current.name)
        moved.rot, moved.x, moved.y = self.current.rot, self.current.x, self.current.y
        while True:
            test = Piece(self.current.name)
            test.rot, test.x, test.y = moved.rot, moved.x, moved.y + 1
            if self._valid(test.cells()):
                moved = test
            else:
                break
        self.current = moved
        self._lock_piece()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        x0, y0 = 15, 15

        painter.setPen(QPen(QColor("#25344b"), 1))
        painter.setBrush(QColor("#080b13"))
        painter.drawRect(x0, y0, BOARD_W, BOARD_H)

        painter.setPen(QPen(QColor("#131d2c"), 1))
        for c in range(COLS + 1):
            painter.drawLine(x0 + c * CELL, y0, x0 + c * CELL, y0 + BOARD_H)
        for r in range(ROWS + 1):
            painter.drawLine(x0, y0 + r * CELL, x0 + BOARD_W, y0 + r * CELL)

        painter.setPen(Qt.PenStyle.NoPen)
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c]:
                    painter.setBrush(QColor(self.board[r][c]))
                    painter.drawRect(x0 + c * CELL + 1, y0 + r * CELL + 1, CELL - 2, CELL - 2)

        if self.running or not self.game_over:
            painter.setBrush(QColor(self.current.color))
            for x, y in self.current.cells():
                if y >= 0:
                    painter.drawRect(x0 + x * CELL + 1, y0 + y * CELL + 1, CELL - 2, CELL - 2)

        if not self.running:
            painter.fillRect(QRectF(x0, y0, BOARD_W, BOARD_H), QColor(5, 8, 18, 180))
            painter.setPen(QColor("#55f7ff"))
            painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            msg = "GAME OVER" if self.game_over else "TETRIS"
            painter.drawText(QRectF(x0, y0 + BOARD_H / 2 - 20, BOARD_W, 40), Qt.AlignmentFlag.AlignCenter, msg)

        painter.end()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Tetris()
    win.show()
    sys.exit(app.exec())
