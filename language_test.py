"""
A small standalone English-grammar level test (A1-C2), multiple-choice
(4 options per question), pulled from language_test_questions.json
(parsed once from the question bank + answer key the user supplied).
Opens as its own window, the same way tic_tac_toe.py does, so it can be
launched from the Host/Join screen or from inside the chat app without
entangling with the chat's own networking code at all - it's fully
offline/local.
"""
import json
import os
import random

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QFrame, QProgressBar, QStackedWidget,
)

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
QUESTIONS_PER_ROUND = 10
OPTION_LETTERS = ["A", "B", "C", "D"]

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "language_test_questions.json")


def load_questions():
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {level: [] for level in LEVELS}


class LanguageTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Same reasoning as the Tic Tac Toe window: pin our own font so
        # the chat app's own font-size setting can't leak in here.
        self.setFont(QFont("Segoe UI", 10))
        self.setWindowTitle("English Level Test")
        self.setMinimumSize(640, 500)
        self.resize(680, 540)

        self.bank = load_questions()
        self.round_questions = []
        self.round_index = 0
        self.score = 0
        self.selected_level = "A1"
        self._awaiting_next = False

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        title = QLabel("English Level Test")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        self.pages = QStackedWidget()
        root.addWidget(self.pages, stretch=1)

        self.pages.addWidget(self._build_level_page())
        self.pages.addWidget(self._build_quiz_page())
        self.pages.addWidget(self._build_result_page())

        self._apply_style()

    # ---- page 1: pick a level ----

    def _build_level_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)
        layout.addStretch(1)

        subtitle = QLabel(f"Pick a level - {QUESTIONS_PER_ROUND} random multiple-choice questions.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        grid = QHBoxLayout()
        grid.setSpacing(10)
        self.level_group = QButtonGroup(self)
        self.level_radios = {}
        for level in LEVELS:
            radio = QRadioButton(level)
            radio.setObjectName("levelRadio")
            if level == "A1":
                radio.setChecked(True)
            self.level_group.addButton(radio)
            self.level_radios[level] = radio
            grid.addWidget(radio)
        layout.addLayout(grid)

        start_btn = QPushButton("Start")
        start_btn.setObjectName("primary")
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.clicked.connect(self._start_round)
        layout.addWidget(start_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(2)
        return page

    def _start_round(self):
        for level, radio in self.level_radios.items():
            if radio.isChecked():
                self.selected_level = level
                break
        pool = list(self.bank.get(self.selected_level, []))
        random.shuffle(pool)
        self.round_questions = pool[:QUESTIONS_PER_ROUND]
        self.round_index = 0
        self.score = 0
        if not self.round_questions:
            self.q_label.setText("No questions available for this level.")
            self.pages.setCurrentIndex(1)
            return
        self._show_question()
        self.pages.setCurrentIndex(1)

    # ---- page 2: quiz ----

    def _build_quiz_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        self.progress_lbl = QLabel("")
        self.progress_lbl.setObjectName("subtitle")
        layout.addWidget(self.progress_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(QUESTIONS_PER_ROUND)
        layout.addWidget(self.progress_bar)

        self.q_label = QLabel("")
        self.q_label.setObjectName("question")
        self.q_label.setWordWrap(True)
        self.q_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.q_label)

        self.option_buttons = []
        options_col = QVBoxLayout()
        options_col.setSpacing(8)
        for i in range(4):
            btn = QPushButton("")
            btn.setObjectName("optionButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(42)
            btn.clicked.connect(lambda checked=False, idx=i: self._on_option_clicked(idx))
            options_col.addWidget(btn)
            self.option_buttons.append(btn)
        layout.addLayout(options_col)

        self.feedback_lbl = QLabel("")
        self.feedback_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.feedback_lbl)

        layout.addStretch(1)

        btn_row = QHBoxLayout()
        self.next_btn = QPushButton("Next")
        self.next_btn.setObjectName("primary")
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self._advance)
        btn_row.addWidget(self.next_btn)
        layout.addLayout(btn_row)

        return page

    def _show_question(self):
        item = self.round_questions[self.round_index]
        self.q_label.setText(item["q"])
        self.feedback_lbl.setText("")
        for i, btn in enumerate(self.option_buttons):
            letter = OPTION_LETTERS[i]
            btn.setText(f"{letter})  {item['options'][i]}")
            btn.setEnabled(True)
            btn.setProperty("state", "")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.next_btn.setEnabled(False)
        self.next_btn.setText(
            "Finish" if self.round_index + 1 >= len(self.round_questions) else "Next"
        )
        self.progress_lbl.setText(
            f"{self.selected_level} \u2022 Question {self.round_index + 1} of {len(self.round_questions)} "
            f"\u2022 Score {self.score}"
        )
        self.progress_bar.setValue(self.round_index)
        self._awaiting_next = False

    def _on_option_clicked(self, idx):
        if self._awaiting_next:
            return
        item = self.round_questions[self.round_index]
        correct_idx = item["answer_index"]
        is_correct = idx == correct_idx
        if is_correct:
            self.score += 1
            self.feedback_lbl.setText("\u2713 Correct!")
            self.feedback_lbl.setStyleSheet("color: #3ddc84;")
            self.option_buttons[idx].setProperty("state", "correct")
        else:
            self.feedback_lbl.setText(
                f"\u2717 Correct answer: {OPTION_LETTERS[correct_idx]}) {item['options'][correct_idx]}"
            )
            self.feedback_lbl.setStyleSheet("color: #e05a5a;")
            self.option_buttons[idx].setProperty("state", "wrong")
            self.option_buttons[correct_idx].setProperty("state", "correct")
        for btn in self.option_buttons:
            btn.setEnabled(False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.next_btn.setEnabled(True)
        self._awaiting_next = True

    def _advance(self):
        self.round_index += 1
        if self.round_index >= len(self.round_questions):
            self._show_result()
            self.pages.setCurrentIndex(2)
        else:
            self._show_question()

    # ---- page 3: result ----

    def _build_result_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)
        layout.addStretch(1)

        self.result_lbl = QLabel("")
        self.result_lbl.setObjectName("title")
        self.result_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.result_lbl)

        self.result_note_lbl = QLabel("")
        self.result_note_lbl.setObjectName("subtitle")
        self.result_note_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_note_lbl.setWordWrap(True)
        layout.addWidget(self.result_note_lbl)

        again_btn = QPushButton("Try another level")
        again_btn.setObjectName("primary")
        again_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        again_btn.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        layout.addWidget(again_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(2)
        return page

    def _show_result(self):
        total = len(self.round_questions)
        pct = (self.score / total * 100) if total else 0
        self.result_lbl.setText(f"{self.score} / {total}")
        if pct >= 80:
            note = "Great work - you're solid at this level."
        elif pct >= 50:
            note = "Good - a bit more practice at this level will help."
        else:
            note = "This level needs more practice; maybe try one level down."
        self.result_note_lbl.setText(note)

    def _apply_style(self):
        self.setStyleSheet("""
        QMainWindow, QWidget { background: #0b1220; color: #eaf2ff; font-family: "Segoe UI", Arial; }
        #title { font-size: 28px; font-weight: 800; }
        #subtitle { font-size: 11pt; color: #8798b6; }
        #question { font-size: 15pt; font-weight: 600; padding: 16px; background: #101f35;
                     border: 1px solid #243b60; border-radius: 14px; }
        QRadioButton#levelRadio { font-size: 12pt; padding: 8px 10px; }
        QPushButton#optionButton {
            text-align: left; background: #101f35; border: 1.5px solid #243b60;
            border-radius: 10px; padding: 9px 14px; font-size: 11.5pt; color: #eaf2ff;
        }
        QPushButton#optionButton:hover:enabled { border: 1.5px solid #5369ff; }
        QPushButton#optionButton:disabled { color: #eaf2ff; }
        QPushButton#optionButton[state="correct"] {
            border: 1.5px solid #3ddc84; background: #123324; color: #3ddc84; font-weight: 700;
        }
        QPushButton#optionButton[state="wrong"] {
            border: 1.5px solid #e05a5a; background: #351717; color: #e05a5a; font-weight: 700;
        }
        QPushButton#primary {
            background: #5369ff; border: none; border-radius: 10px;
            padding: 11px 22px; font-weight: 700; font-size: 11pt; color: white;
        }
        QPushButton#primary:hover { background: #6579ff; }
        QPushButton#primary:disabled { background: #243b60; color: #68768f; }
        QProgressBar { background: #101f35; border: 1px solid #243b60; border-radius: 6px; height: 10px; }
        QProgressBar::chunk { background: #5369ff; border-radius: 6px; }
        """)
