import sys
import random
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QPushButton, QLabel, QVBoxLayout,
    QHBoxLayout, QGridLayout, QFrame, QRadioButton, QButtonGroup, QMessageBox
)


class GlowButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class BoardCell(QPushButton):
    clicked_cell = pyqtSignal(int)

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.setMinimumSize(120, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: self.clicked_cell.emit(self.index))


class TicTacToe(QMainWindow):
    def __init__(self):
        super().__init__()
        # This window can be launched from inside the chat app, which
        # sometimes changes the whole application's default font (its
        # font-size setting). Pin our own font here so that change can
        # never leak in and throw off this window's hand-tuned paddings.
        self.setFont(QFont("Segoe UI", 10))
        self.setWindowTitle("Neon Tic Tac Toe")
        self.setMinimumSize(980, 700)
        self.resize(1100, 760)

        self.board = [""] * 9
        self.current_player = "X"
        self.mode = "computer"
        self.human = "X"
        self.computer = "O"
        self.game_over = False

        self.scores = {"X": 0, "O": 0, "draw": 0}
        self.cells = []

        self.build_ui()
        self.apply_style()
        self.new_game()

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(34, 24, 34, 28)
        root.setSpacing(18)

        title = QLabel("Tic Tac Toe")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Think. Place. Win!")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        root.addWidget(title)
        root.addWidget(subtitle)

        content = QHBoxLayout()
        content.setSpacing(22)

        # Board
        board_frame = QFrame()
        board_frame.setObjectName("boardFrame")
        board_layout = QGridLayout(board_frame)
        board_layout.setContentsMargins(14, 14, 14, 14)
        board_layout.setSpacing(10)

        for i in range(9):
            cell = BoardCell(i)
            cell.clicked_cell.connect(self.play_cell)
            self.cells.append(cell)
            board_layout.addWidget(cell, i // 3, i % 3)

        content.addWidget(board_frame, 3)

        # Side panel
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumWidth(280)
        p = QVBoxLayout(panel)
        p.setContentsMargins(24, 24, 24, 24)
        p.setSpacing(16)

        score_title = QLabel("Score")
        score_title.setObjectName("sectionTitle")
        p.addWidget(score_title)

        self.x_score = self._score_row(p, "scoreX", "\u2715   Player X", "#55a8ff")
        self.o_score = self._score_row(p, "scoreO", "\u25cb   Player O", "#ff54bd")
        self.draw_score = self._score_row(p, "drawScore", "\u2014   Draws", "#aebbd0")

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("line")
        p.addWidget(line)

        mode_title = QLabel("Game Mode")
        mode_title.setObjectName("sectionTitle")
        p.addWidget(mode_title)

        self.mode_group = QButtonGroup(self)
        self.computer_radio = QRadioButton("🤖   Vs Computer")
        self.two_radio = QRadioButton("👥   Two Players")
        self.computer_radio.setChecked(True)

        self.mode_group.addButton(self.computer_radio)
        self.mode_group.addButton(self.two_radio)
        self.computer_radio.toggled.connect(self.mode_changed)

        p.addWidget(self.computer_radio)
        p.addWidget(self.two_radio)

        side_title = QLabel("Your Side")
        side_title.setObjectName("sectionTitle")
        p.addWidget(side_title)

        self.side_group = QButtonGroup(self)
        self.x_radio = QRadioButton("✕   X")
        self.o_radio = QRadioButton("○   O")
        self.x_radio.setChecked(True)
        self.side_group.addButton(self.x_radio)
        self.side_group.addButton(self.o_radio)
        self.x_radio.toggled.connect(self.side_changed)

        p.addWidget(self.x_radio)
        p.addWidget(self.o_radio)

        self.new_btn = GlowButton("▶   New Game")
        self.new_btn.setObjectName("newButton")
        self.new_btn.clicked.connect(self.new_game)
        p.addWidget(self.new_btn)

        p.addStretch()

        self.status = QLabel("Your turn")
        self.status.setObjectName("status")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p.addWidget(self.status)

        content.addWidget(panel, 1)
        root.addLayout(content)

        bottom = QFrame()
        bottom.setObjectName("bottom")
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(18, 12, 18, 12)

        self.result = QLabel("Make your move!")
        self.result.setObjectName("result")
        bottom_layout.addWidget(self.result)

        bottom_layout.addStretch()

        self.reset_score_btn = GlowButton("Reset Score")
        self.reset_score_btn.clicked.connect(self.reset_scores)
        bottom_layout.addWidget(self.reset_score_btn)

        root.addWidget(bottom)

    def _score_row(self, parent_layout, object_name, label_text, color):
        """One 'name ........ count' row, built from two labels in an
        HBox instead of a single hand-padded string - the old
        space-padded single QLabel approach is what caused the score
        rows to render mis-aligned/overlapping on some systems."""
        row = QFrame()
        row.setObjectName(object_name)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 10, 12, 10)
        row_layout.setSpacing(8)
        name_lbl = QLabel(label_text)
        name_lbl.setStyleSheet(f"background: transparent; border: none; color: {color};")
        value_lbl = QLabel("0")
        value_lbl.setStyleSheet(f"background: transparent; border: none; color: {color}; font-weight: 800;")
        row_layout.addWidget(name_lbl, stretch=1)
        row_layout.addWidget(value_lbl)
        parent_layout.addWidget(row)
        return value_lbl

    def apply_style(self):
        self.setStyleSheet("""
        QMainWindow, QWidget {
            background: #07111f;
            color: #eaf2ff;
            font-family: "Segoe UI", Arial, sans-serif;
        }

        #title {
            font-size: 46px;
            font-weight: 800;
            color: #f5f7ff;
        }

        #subtitle {
            font-size: 17px;
            color: #8798b6;
            margin-bottom: 8px;
        }

        #boardFrame, #panel, #bottom {
            background: #0c182b;
            border: 1px solid #1c3150;
            border-radius: 20px;
        }

        BoardCell {
            background: #0a1424;
            border: 1px solid #203655;
            border-radius: 15px;
            font-size: 62px;
            font-weight: 700;
            color: #f4f7ff;
        }

        BoardCell:hover {
            background: #11233c;
            border: 2px solid #3c79d8;
        }

        #panel {
            padding: 8px;
        }

        #sectionTitle {
            color: #a8b8d4;
            font-size: 14px;
            font-weight: 700;
        }

        #scoreX, #scoreO, #drawScore {
            background: #101f35;
            border: 1px solid #1d3557;
            border-radius: 11px;
            padding: 12px;
            font-size: 15px;
        }

        #scoreX { color: #55a8ff; }
        #scoreO { color: #ff54bd; }
        #drawScore { color: #aebbd0; }

        QRadioButton {
            color: #cbd7e9;
            font-size: 14px;
            padding: 8px;
            spacing: 10px;
        }

        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border-radius: 9px;
            border: 2px solid #2b4468;
            background: #101f35;
        }

        QRadioButton::indicator:checked {
            border: 2px solid #5369ff;
            background: #5369ff;
        }

        QRadioButton::indicator:hover {
            border: 2px solid #5369ff;
        }

        #newButton {
            background: #5369ff;
            border: none;
            border-radius: 12px;
            padding: 14px;
            font-size: 16px;
            font-weight: 700;
            color: white;
        }

        #newButton:hover {
            background: #6579ff;
        }

        #status {
            background: #101f35;
            border: 1px solid #243b60;
            border-radius: 12px;
            padding: 11px;
            color: #75b4ff;
            font-weight: 700;
        }

        #result {
            color: #77baff;
            font-size: 17px;
            font-weight: 700;
        }

        #bottom QPushButton {
            background: #101f35;
            border: 1px solid #2b4468;
            border-radius: 9px;
            padding: 8px 14px;
            color: #b9c8dd;
        }

        #bottom QPushButton:hover {
            background: #172943;
        }

        #line {
            color: #203655;
        }
        """)

    def mode_changed(self, checked):
        if checked:
            self.mode = "computer" if self.computer_radio.isChecked() else "two"
            self.new_game()

    def side_changed(self, checked):
        if checked and self.computer_radio.isChecked():
            self.human = "X" if self.x_radio.isChecked() else "O"
            self.computer = "O" if self.human == "X" else "X"
            self.new_game()

    def new_game(self):
        self.board = [""] * 9
        self.game_over = False
        self.current_player = "X"
        self.result.setText("Make your move!")
        self.update_board()

        if self.mode == "computer" and self.current_player == self.computer:
            self.status.setText("Computer is thinking...")
            self.computer_move()
        else:
            self.update_status()

    def reset_scores(self):
        self.scores = {"X": 0, "O": 0, "draw": 0}
        self.update_scores()
        self.new_game()

    def update_scores(self):
        self.x_score.setText(str(self.scores["X"]))
        self.o_score.setText(str(self.scores["O"]))
        self.draw_score.setText(str(self.scores["draw"]))

    def update_board(self):
        for i, cell in enumerate(self.cells):
            cell.setText(self.board[i])
            if self.board[i] == "X":
                cell.setStyleSheet("""
                    background: #0b1729;
                    border: 1px solid #2a4d78;
                    border-radius: 15px;
                    color: #55a8ff;
                    font-size: 62px;
                    font-weight: 800;
                """)
            elif self.board[i] == "O":
                cell.setStyleSheet("""
                    background: #0b1729;
                    border: 1px solid #5a2850;
                    border-radius: 15px;
                    color: #ff54bd;
                    font-size: 62px;
                    font-weight: 800;
                """)
            else:
                cell.setStyleSheet("")

            cell.setEnabled(not self.game_over and self.board[i] == "")

    def update_status(self):
        if self.game_over:
            return
        if self.mode == "two":
            self.status.setText(f"Player {self.current_player}'s turn")
        else:
            if self.current_player == self.human:
                self.status.setText("Your turn")
            else:
                self.status.setText("Computer is thinking...")

    def play_cell(self, index):
        if self.game_over or self.board[index]:
            return

        if self.mode == "computer" and self.current_player != self.human:
            return

        self.board[index] = self.current_player
        self.after_move()

    def after_move(self):
        self.update_board()

        winner, line = self.check_winner(self.board)
        if winner:
            self.finish_game(winner, line)
            return

        if "" not in self.board:
            self.finish_draw()
            return

        self.current_player = "O" if self.current_player == "X" else "X"
        self.update_status()

        if self.mode == "computer" and self.current_player == self.computer:
            self.computer_move()

    def computer_move(self):
        QApplication.processEvents()

        # A short, simple AI: minimax, with a small random preference among
        # equally good moves so games don't always look identical.
        move = self.best_move()
        if move is not None and not self.game_over:
            self.board[move] = self.computer
            self.after_move()

    def best_move(self):
        empty = [i for i, v in enumerate(self.board) if v == ""]
        if not empty:
            return None

        # Opening move: make the computer feel less robotic.
        if len(empty) == 9:
            return random.choice([0, 2, 4, 6, 8])

        best_score = -10
        moves = []
        for i in empty:
            self.board[i] = self.computer
            score = self.minimax(self.board, False, 0)
            self.board[i] = ""
            if score > best_score:
                best_score = score
                moves = [i]
            elif score == best_score:
                moves.append(i)
        return random.choice(moves)

    def minimax(self, board, maximizing, depth):
        winner, _ = self.check_winner(board)
        if winner == self.computer:
            return 10 - depth
        if winner == self.human:
            return depth - 10
        if "" not in board:
            return 0

        empty = [i for i, v in enumerate(board) if v == ""]

        if maximizing:
            best = -100
            for i in empty:
                board[i] = self.computer
                best = max(best, self.minimax(board, False, depth + 1))
                board[i] = ""
            return best
        else:
            best = 100
            for i in empty:
                board[i] = self.human
                best = min(best, self.minimax(board, True, depth + 1))
                board[i] = ""
            return best

    def check_winner(self, board):
        combos = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6)
        ]
        for a, b, c in combos:
            if board[a] and board[a] == board[b] == board[c]:
                return board[a], (a, b, c)
        return None, None

    def finish_game(self, winner, line):
        self.game_over = True
        self.scores[winner] += 1
        self.update_scores()

        if winner == "X":
            self.result.setText("✕  Player X wins!")
            self.status.setText("Winner!")
        else:
            self.result.setText("○  Player O wins!")
            self.status.setText("Winner!")

        for i in line:
            self.cells[i].setStyleSheet("""
                background: #172d4b;
                border: 2px solid #7e8cff;
                border-radius: 15px;
                color: #ffffff;
                font-size: 62px;
                font-weight: 800;
            """)

    def finish_draw(self):
        self.game_over = True
        self.scores["draw"] += 1
        self.update_scores()
        self.result.setText("It's a draw!")
        self.status.setText("No winner this time.")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_N:
            self.new_game()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Neon Tic Tac Toe")
    window = TicTacToe()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
