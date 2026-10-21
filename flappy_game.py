import sys
import random

from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout

WIDTH, HEIGHT = 420, 600
GRAVITY = 0.45
FLAP_STRENGTH = -8.0
PIPE_WIDTH = 60
PIPE_GAP = 165
PIPE_SPEED = 3.2
PIPE_SPACING = 230
BIRD_SIZE = 26


class FlappyBird(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FLAPPY NEON")
        self.setFixedSize(WIDTH, HEIGHT + 110)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

        self.score_label = QLabel("امتیاز: 0")
        self.best_label = QLabel("رکورد: 0")
        self.status_label = QLabel("برای پرش، کلیک یا Space بزن.")
        self.start_button = QPushButton("\u25b6 شروع")
        self.start_button.clicked.connect(self.start_game)

        header = QHBoxLayout()
        header.addWidget(self.score_label)
        header.addStretch()
        header.addWidget(self.best_label)

        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.setStyleSheet("""
            QWidget { background-color: #0b0d16; color: #e7f7ff; font-family: Segoe UI; font-size: 11pt; }
            QLabel { padding: 3px; }
            QPushButton { background-color: #151a2a; color: #55f7ff; border: 1px solid #28556a; border-radius: 8px; padding: 8px; }
            QPushButton:hover { background-color: #24344a; border-color: #55f7ff; }
        """)

        self.best_score = 0
        self.reset_game()

    def reset_game(self):
        self.bird_y = HEIGHT / 2
        self.bird_v = 0.0
        self.pipes = []  # list of dicts: {x, gap_y}
        self.score = 0
        self.running = False
        self.game_over = False
        self._spawn_pipe(WIDTH + 100)
        self.update_labels()
        self.update()

    def _spawn_pipe(self, x):
        gap_y = random.randint(90, HEIGHT - 90 - PIPE_GAP)
        self.pipes.append({"x": x, "gap_y": gap_y, "scored": False})

    def start_game(self):
        self.timer.stop()
        self.reset_game()
        self.running = True
        self.status_label.setText("برو که رفتیم!")
        self.timer.start(16)
        self.setFocus()

    def flap(self):
        if not self.running:
            if not self.game_over:
                self.start_game()
            return
        self.bird_v = FLAP_STRENGTH

    def update_labels(self):
        self.score_label.setText(f"امتیاز: {self.score}")
        self.best_label.setText(f"رکورد: {max(self.best_score, self.score)}")

    def tick(self):
        if not self.running:
            return
        self.bird_v += GRAVITY
        self.bird_y += self.bird_v

        for pipe in self.pipes:
            pipe["x"] -= PIPE_SPEED
        if self.pipes and self.pipes[-1]["x"] < WIDTH - PIPE_SPACING:
            self._spawn_pipe(WIDTH)
        self.pipes = [p for p in self.pipes if p["x"] > -PIPE_WIDTH]

        bird_rect = QRectF(WIDTH / 2 - BIRD_SIZE / 2, self.bird_y - BIRD_SIZE / 2, BIRD_SIZE, BIRD_SIZE)

        if self.bird_y - BIRD_SIZE / 2 < 0 or self.bird_y + BIRD_SIZE / 2 > HEIGHT:
            self._end_game()
            return

        for pipe in self.pipes:
            top_rect = QRectF(pipe["x"], 0, PIPE_WIDTH, pipe["gap_y"])
            bottom_rect = QRectF(pipe["x"], pipe["gap_y"] + PIPE_GAP, PIPE_WIDTH, HEIGHT - pipe["gap_y"] - PIPE_GAP)
            if bird_rect.intersects(top_rect) or bird_rect.intersects(bottom_rect):
                self._end_game()
                return
            if not pipe["scored"] and pipe["x"] + PIPE_WIDTH < WIDTH / 2:
                pipe["scored"] = True
                self.score += 1
                self.update_labels()

        self.update()

    def _end_game(self):
        self.running = False
        self.game_over = True
        self.timer.stop()
        self.best_score = max(self.best_score, self.score)
        self.status_label.setText(f"باختی! امتیاز نهایی: {self.score} \u2014 دوباره امتحان کن")
        self.update_labels()
        self.update()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Up, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.flap()

    def mousePressEvent(self, event):
        self.flap()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        y0 = 110

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#081018"))
        painter.drawRect(0, y0, WIDTH, HEIGHT)

        painter.setBrush(QColor("#1fbf5c"))
        for pipe in self.pipes:
            painter.drawRect(int(pipe["x"]), y0, PIPE_WIDTH, int(pipe["gap_y"]))
            painter.drawRect(
                int(pipe["x"]), int(y0 + pipe["gap_y"] + PIPE_GAP),
                PIPE_WIDTH, int(HEIGHT - pipe["gap_y"] - PIPE_GAP),
            )

        painter.setBrush(QColor("#ffd166"))
        painter.drawEllipse(
            QRectF(WIDTH / 2 - BIRD_SIZE / 2, y0 + self.bird_y - BIRD_SIZE / 2, BIRD_SIZE, BIRD_SIZE)
        )

        if not self.running:
            painter.fillRect(QRectF(0, y0, WIDTH, HEIGHT), QColor(5, 8, 18, 170))
            painter.setPen(QColor("#55f7ff"))
            painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
            msg = "GAME OVER" if self.game_over else "FLAPPY NEON"
            painter.drawText(QRectF(0, y0 + HEIGHT / 2 - 30, WIDTH, 50), Qt.AlignmentFlag.AlignCenter, msg)
            painter.setPen(QColor("#a6b6d3"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(
                QRectF(0, y0 + HEIGHT / 2 + 15, WIDTH, 30), Qt.AlignmentFlag.AlignCenter,
                "کلیک یا Space برای پرش",
            )

        painter.end()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = FlappyBird()
    win.show()
    sys.exit(app.exec())
