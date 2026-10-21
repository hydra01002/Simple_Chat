import sys
import random
from collections import deque

from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QComboBox, QVBoxLayout, QHBoxLayout
)

CELL = 24
COLS = 26
ROWS = 20

MODES = {
    "Calm": {
        "speed": 160,
        "obstacles": 0,
        "wrap": True,
        "bonus": 0.25,
        "time": 0,
    },
    "Classic": {
        "speed": 125,
        "obstacles": 3,
        "wrap": False,
        "bonus": 0.18,
        "time": 0,
    },
    "Challenge": {
        "speed": 100,
        "obstacles": 7,
        "wrap": False,
        "bonus": 0.20,
        "time": 0,
    },
    "Survival": {
        "speed": 110,
        "obstacles": 11,
        "wrap": False,
        "bonus": 0.08,
        "time": 0,
    },
    "Time Attack": {
        "speed": 115,
        "obstacles": 4,
        "wrap": False,
        "bonus": 0.30,
        "time": 60,
    },
}


class NeonSnake(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("NEON SNAKE | Arcade")
        self.resize(850, 720)
        self.setMinimumSize(760, 650)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

        self.clock = QTimer(self)
        self.clock.timeout.connect(self.countdown)

        self.mode_box = QComboBox()
        self.mode_box.addItems(MODES.keys())
        self.mode_box.currentTextChanged.connect(
            self.mode_changed
        )

        self.score_label = QLabel("Score: 0")
        self.best_label = QLabel("Best: 0")
        self.time_label = QLabel("Time: --")
        self.status_label = QLabel("Press Start to begin.")

        self.start_button = QPushButton("\u25b6 Start Game")
        self.start_button.clicked.connect(self.start_game)

        self.pause_button = QPushButton("\u2161 Pause / Resume")
        self.pause_button.clicked.connect(self.toggle_pause)

        self.restart_button = QPushButton("\u21bb Restart")
        self.restart_button.clicked.connect(self.start_game)

        header = QHBoxLayout()
        header.addWidget(QLabel("Mode:"))
        header.addWidget(self.mode_box)
        header.addStretch()
        header.addWidget(self.score_label)
        header.addWidget(self.best_label)
        header.addWidget(self.time_label)

        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.restart_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.make_title())
        layout.addLayout(header)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.setStyleSheet("""
            QWidget {
                background-color: #0b0d16;
                color: #e7f7ff;
                font-family: Segoe UI;
                font-size: 14px;
            }
            QLabel {
                padding: 5px;
            }
            QPushButton, QComboBox {
                background-color: #151a2a;
                color: #55f7ff;
                border: 1px solid #28556a;
                border-radius: 8px;
                padding: 9px;
            }
            QPushButton:hover {
                background-color: #24344a;
                border-color: #55f7ff;
            }
        """)

        self.best_scores = {name: 0 for name in MODES}
        self.reset_game()
        self.mode_changed(self.mode_box.currentText())

    def make_title(self):
        title = QLabel("NEON SNAKE")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            color: #55f7ff;
            font-size: 30px;
            font-weight: bold;
            letter-spacing: 4px;
            padding: 12px;
        """)
        return title

    def current_mode(self):
        return MODES[self.mode_box.currentText()]

    def mode_changed(self, name):
        descriptions = {
            "Calm": "Low speed \u2022 wraps around edges \u2022 no obstacles",
            "Classic": "Medium speed \u2022 standard rules",
            "Challenge": "High speed \u2022 more obstacles",
            "Survival": "Lots of obstacles \u2022 bonus food is rare",
            "Time Attack": "60 seconds to score as much as you can",
        }
        self.status_label.setText(descriptions[name])

        if hasattr(self, "timer") and self.timer.isActive():
            self.start_game()

        self.update()

    def reset_game(self):
        x, y = COLS // 2, ROWS // 2

        self.snake = deque([
            (x, y),
            (x - 1, y),
            (x - 2, y),
        ])

        self.direction = (1, 0)
        self.next_direction = (1, 0)

        self.score = 0
        self.remaining = 60
        self.obstacles = set()

        self.food = None
        self.bonus_food = None

        self.running = False
        self.paused = False
        self.game_over = False

        self.spawn_food()
        self.update_labels()
        self.update()

    def occupied(self):
        return set(self.snake) | self.obstacles

    def random_empty(self):
        occupied = self.occupied()

        available = [
            (x, y)
            for x in range(COLS)
            for y in range(ROWS)
            if (x, y) not in occupied
            and (x, y) != self.food
            and (x, y) != self.bonus_food
        ]

        return random.choice(available) if available else None

    def spawn_food(self):
        self.food = self.random_empty()

        if random.random() < self.current_mode()["bonus"]:
            self.bonus_food = self.random_empty()
        else:
            self.bonus_food = None

    def create_obstacles(self):
        self.obstacles.clear()
        head = self.snake[0]

        for _ in range(self.current_mode()["obstacles"]):
            choices = [
                (x, y)
                for x in range(2, COLS - 2)
                for y in range(2, ROWS - 2)
                if (x, y) not in self.snake
                and abs(x - head[0]) + abs(y - head[1]) > 5
                and (x, y) not in self.obstacles
            ]

            if choices:
                self.obstacles.add(random.choice(choices))

    def start_game(self):
        self.timer.stop()
        self.clock.stop()

        self.reset_game()
        self.create_obstacles()

        self.running = True
        self.status_label.setText("Game started!")

        self.timer.start(self.current_mode()["speed"])

        if self.current_mode()["time"]:
            self.remaining = self.current_mode()["time"]
            self.clock.start(1000)

        self.update_labels()
        self.setFocus()
        self.update()

    def update_labels(self):
        mode = self.mode_box.currentText()

        self.score_label.setText(f"Score: {self.score}")
        self.best_label.setText(
            f"Best: {max(self.best_scores[mode], self.score)}"
        )

        if self.current_mode()["time"]:
            self.time_label.setText(f"Time: {self.remaining}")
        else:
            self.time_label.setText("Time: --")

    def countdown(self):
        if not self.running or self.paused:
            return

        self.remaining -= 1
        self.update_labels()

        if self.remaining <= 0:
            self.finish_game("Time's up!")

    def toggle_pause(self):
        if not self.running:
            return

        self.paused = not self.paused

        if self.paused:
            self.timer.stop()
            self.clock.stop()
            self.status_label.setText("Paused \u2014 press Space to resume")
        else:
            self.timer.start(self.current_mode()["speed"])

            if self.current_mode()["time"]:
                self.clock.start(1000)

            self.status_label.setText("Game running")

        self.update()

    def finish_game(self, message):
        self.running = False
        self.paused = False

        self.timer.stop()
        self.clock.stop()

        mode = self.mode_box.currentText()
        self.best_scores[mode] = max(
            self.best_scores[mode], self.score
        )

        self.status_label.setText(
            f"{message} Final score: {self.score}"
        )

        self.update_labels()
        self.update()

    def tick(self):
        if not self.running or self.paused:
            return

        self.direction = self.next_direction

        hx, hy = self.snake[0]
        dx, dy = self.direction

        nx = hx + dx
        ny = hy + dy

        if self.current_mode()["wrap"]:
            nx %= COLS
            ny %= ROWS
        elif nx < 0 or nx >= COLS or ny < 0 or ny >= ROWS:
            self.finish_game("You hit the wall!")
            return

        new_head = (nx, ny)
        eating = new_head == self.food
        eating_bonus = new_head == self.bonus_food

        body = list(self.snake)

        # If the tail would move out of the way this same step, allow
        # entering the cell it's currently occupying.
        collision_body = body if eating or eating_bonus else body[:-1]

        if new_head in collision_body or new_head in self.obstacles:
            self.finish_game("You crashed!")
            return

        self.snake.appendleft(new_head)

        if eating:
            self.score += 10
            self.spawn_food()

            mode_name = self.mode_box.currentText()

            if mode_name in ("Challenge", "Survival") and self.score % 50 == 0:
                spot = self.random_empty()
                if spot:
                    self.obstacles.add(spot)

        elif eating_bonus:
            self.score += 30
            self.bonus_food = None

        else:
            self.snake.pop()

        mode = self.mode_box.currentText()
        self.best_scores[mode] = max(
            self.best_scores[mode], self.score
        )

        # Speed ramps up slightly as the score climbs.
        base = self.current_mode()["speed"]
        speed = max(55, base - (self.score // 30) * 4)
        self.timer.setInterval(speed)

        self.update_labels()
        self.update()

    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key.Key_Space:
            self.toggle_pause()
            return

        if key in (
            Qt.Key.Key_N,
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        ):
            self.start_game()
            return

        keys = {
            Qt.Key.Key_Up: (0, -1),
            Qt.Key.Key_W: (0, -1),
            Qt.Key.Key_Down: (0, 1),
            Qt.Key.Key_S: (0, 1),
            Qt.Key.Key_Left: (-1, 0),
            Qt.Key.Key_A: (-1, 0),
            Qt.Key.Key_Right: (1, 0),
            Qt.Key.Key_D: (1, 0),
        }

        if key in keys:
            new_dir = keys[key]

            if new_dir != (-self.direction[0], -self.direction[1]):
                self.next_direction = new_dir

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        board_w = min(COLS * CELL, self.width() - 44)
        cell = board_w / COLS
        board_h = cell * ROWS

        x0 = (self.width() - board_w) / 2
        y0 = 175

        if y0 + board_h > self.height() - 20:
            y0 = max(140, (self.height() - board_h) / 2)

        painter.setPen(QPen(QColor("#25344b"), 1))
        painter.setBrush(QColor("#080b13"))
        painter.drawRoundedRect(
            QRectF(x0, y0, board_w, board_h), 10, 10
        )

        painter.setPen(QPen(QColor("#131d2c"), 1))

        for x in range(COLS + 1):
            xx = int(x0 + x * cell)
            painter.drawLine(xx, int(y0), xx, int(y0 + board_h))

        for y in range(ROWS + 1):
            yy = int(y0 + y * cell)
            painter.drawLine(int(x0), yy, int(x0 + board_w), yy)

        def cell_rect(pos, inset=3):
            x, y = pos
            return QRectF(
                x0 + x * cell + inset,
                y0 + y * cell + inset,
                cell - 2 * inset,
                cell - 2 * inset,
            )

        painter.setPen(Qt.PenStyle.NoPen)

        for obstacle in self.obstacles:
            painter.setBrush(QColor("#ff3d71"))
            painter.drawRoundedRect(cell_rect(obstacle, 2), 4, 4)

        if self.food:
            painter.setBrush(QColor("#ff4fd8"))
            painter.drawEllipse(cell_rect(self.food, 5))

        if self.bonus_food:
            painter.setBrush(QColor("#ffd166"))
            painter.drawEllipse(cell_rect(self.bonus_food, 4))

        for index, part in enumerate(self.snake):
            painter.setBrush(
                QColor("#55f7ff") if index == 0
                else QColor("#20b9d0")
            )
            painter.drawRoundedRect(
                cell_rect(part, 2 if index == 0 else 3), 5, 5
            )

        if not self.running or self.paused:
            painter.fillRect(
                QRectF(x0, y0, board_w, board_h),
                QColor(5, 8, 18, 195),
            )

            painter.setPen(QColor("#55f7ff"))
            painter.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))

            if self.paused:
                message = "PAUSED"
            elif self.game_over:
                message = "GAME OVER"
            else:
                message = "NEON SNAKE"

            painter.drawText(
                QRectF(x0, y0 + board_h / 2 - 20, board_w, 50),
                Qt.AlignmentFlag.AlignCenter,
                message,
            )

            painter.setPen(QColor("#a6b6d3"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(
                QRectF(x0, y0 + board_h / 2 + 25, board_w, 30),
                Qt.AlignmentFlag.AlignCenter,
                "Start: click button  |  Space: pause  |  N: restart",
            )

        painter.end()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    game = NeonSnake()
    game.show()
    sys.exit(app.exec())
