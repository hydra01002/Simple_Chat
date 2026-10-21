import sys
import random

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QGridLayout,
    QVBoxLayout, QHBoxLayout, QComboBox, QMessageBox,
)

DIFFICULTIES = {
    "آسان (9x9, 10 مین)": (9, 9, 10),
    "متوسط (16x16, 40 مین)": (16, 16, 40),
    "سخت (16x30, 99 مین)": (16, 30, 99),
}

NUMBER_COLORS = {
    1: "#55a8ff", 2: "#4caf50", 3: "#ff5555", 4: "#8855ff",
    5: "#ff9800", 6: "#26c6da", 7: "#e0e0e0", 8: "#9e9e9e",
}


class Cell(QPushButton):
    def __init__(self, row, col):
        super().__init__()
        self.row = row
        self.col = col
        self.is_mine = False
        self.is_revealed = False
        self.is_flagged = False
        self.adjacent = 0
        self.setFixedSize(28, 28)
        self.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))


class Minesweeper(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مین‌روب")
        self.setMinimumSize(420, 480)

        self.cells = []
        self.rows = 9
        self.cols = 9
        self.mine_count = 10
        self.first_click_done = False
        self.flags_used = 0
        self.game_over = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        title = QLabel("\U0001F4A3 مین‌روب")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18pt; font-weight: 800;")
        outer.addWidget(title)

        top_row = QHBoxLayout()
        self.difficulty_box = QComboBox()
        self.difficulty_box.addItems(DIFFICULTIES.keys())
        top_row.addWidget(self.difficulty_box)
        self.new_game_btn = QPushButton("\U0001F642 بازی جدید")
        self.new_game_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_game_btn.clicked.connect(self.start_new_game)
        top_row.addWidget(self.new_game_btn)
        outer.addLayout(top_row)

        status_row = QHBoxLayout()
        self.mine_lbl = QLabel("")
        status_row.addWidget(self.mine_lbl)
        status_row.addStretch(1)
        self.timer_lbl = QLabel("زمان: 0")
        status_row.addWidget(self.timer_lbl)
        outer.addLayout(status_row)

        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(2)
        outer.addWidget(self.grid_widget)
        outer.addStretch(1)

        self.hint_lbl = QLabel("کلیک چپ: باز کردن \u2014 کلیک راست: پرچم")
        self.hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_lbl.setStyleSheet("color: #8798b6; font-size: 9pt;")
        outer.addWidget(self.hint_lbl)

        self.elapsed = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        self.setStyleSheet("""
            QWidget { background-color: #0b1220; color: #eaf2ff; font-family: "Segoe UI"; }
            QPushButton { background-color: #1a2c4a; border: 1px solid #2c4468; border-radius: 6px; }
            QPushButton:hover { border-color: #5369ff; }
            QComboBox { background-color: #1a2c4a; border: 1px solid #2c4468; border-radius: 6px; padding: 4px; }
        """)

        self.start_new_game()

    def _tick(self):
        self.elapsed += 1
        self.timer_lbl.setText(f"زمان: {self.elapsed}")

    def start_new_game(self):
        self.rows, self.cols, self.mine_count = DIFFICULTIES[self.difficulty_box.currentText()]
        self.first_click_done = False
        self.flags_used = 0
        self.game_over = False
        self.elapsed = 0
        self.timer.stop()
        self.timer_lbl.setText("زمان: 0")
        self.mine_lbl.setText(f"\U0001F6A9 {self.flags_used}/{self.mine_count}")

        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        self.cells = [[None] * self.cols for _ in range(self.rows)]
        for r in range(self.rows):
            for c in range(self.cols):
                cell = Cell(r, c)
                cell.clicked.connect(lambda checked=False, rr=r, cc=c: self._on_left_click(rr, cc))
                cell.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                cell.customContextMenuRequested.connect(
                    lambda pos, rr=r, cc=c: self._on_right_click(rr, cc)
                )
                self.grid.addWidget(cell, r, c)
                self.cells[r][c] = cell

    def _place_mines(self, safe_r, safe_c):
        positions = [
            (r, c) for r in range(self.rows) for c in range(self.cols)
            if abs(r - safe_r) > 1 or abs(c - safe_c) > 1
        ]
        mines = random.sample(positions, min(self.mine_count, len(positions)))
        for r, c in mines:
            self.cells[r][c].is_mine = True
        for r in range(self.rows):
            for c in range(self.cols):
                if self.cells[r][c].is_mine:
                    continue
                count = sum(
                    1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                    if (dr or dc) and 0 <= r + dr < self.rows and 0 <= c + dc < self.cols
                    and self.cells[r + dr][c + dc].is_mine
                )
                self.cells[r][c].adjacent = count

    def _on_left_click(self, r, c):
        if self.game_over:
            return
        cell = self.cells[r][c]
        if cell.is_flagged or cell.is_revealed:
            return
        if not self.first_click_done:
            self._place_mines(r, c)
            self.first_click_done = True
            self.timer.start(1000)
        if cell.is_mine:
            self._reveal_all_mines()
            self._end_game(False)
            return
        self._reveal(r, c)
        if self._check_win():
            self._end_game(True)

    def _on_right_click(self, r, c):
        if self.game_over:
            return
        cell = self.cells[r][c]
        if cell.is_revealed:
            return
        cell.is_flagged = not cell.is_flagged
        self.flags_used += 1 if cell.is_flagged else -1
        cell.setText("\U0001F6A9" if cell.is_flagged else "")
        self.mine_lbl.setText(f"\U0001F6A9 {self.flags_used}/{self.mine_count}")

    def _reveal(self, r, c):
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            cell = self.cells[cr][cc]
            if cell.is_revealed or cell.is_flagged:
                continue
            cell.is_revealed = True
            cell.setEnabled(False)
            if cell.adjacent > 0:
                cell.setText(str(cell.adjacent))
                color = NUMBER_COLORS.get(cell.adjacent, "#eaf2ff")
                cell.setStyleSheet(
                    f"background-color: #101f35; color: {color}; border: 1px solid #1f3454; border-radius: 6px;"
                )
            else:
                cell.setStyleSheet("background-color: #101f35; border: 1px solid #1f3454; border-radius: 6px;")
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        nr, nc = cr + dr, cc + dc
                        if (dr or dc) and 0 <= nr < self.rows and 0 <= nc < self.cols:
                            stack.append((nr, nc))

    def _reveal_all_mines(self):
        for row in self.cells:
            for cell in row:
                if cell.is_mine:
                    cell.setText("\U0001F4A3")
                    cell.setStyleSheet("background-color: #ff5555; border-radius: 6px;")

    def _check_win(self):
        for row in self.cells:
            for cell in row:
                if not cell.is_mine and not cell.is_revealed:
                    return False
        return True

    def _end_game(self, won):
        self.game_over = True
        self.timer.stop()
        for row in self.cells:
            for cell in row:
                cell.setEnabled(False)
        QMessageBox.information(
            self, "مین‌روب",
            f"\U0001F389 بردید! زمان: {self.elapsed} ثانیه" if won else "\U0001F4A5 روی مین رفتید!",
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Minesweeper()
    win.show()
    sys.exit(app.exec())
