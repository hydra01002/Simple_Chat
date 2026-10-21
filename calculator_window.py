"""A small calculator window. Expressions are parsed with Python's ast
module and only plain arithmetic is evaluated (numbers, + - * / % **,
parentheses, unary minus) - never eval() - so typing arbitrary text into
the box can't run code."""

import ast
import operator
import re
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton,
)

from tools_common import TOOL_STYLE, normalize_number_text

STR = {
    "title": {"fa": "ماشین‌حساب", "en": "Calculator"},
    "error": {"fa": "عبارت نامعتبر", "en": "Invalid expression"},
    "div0": {"fa": "تقسیم بر صفر", "en": "Division by zero"},
}

_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow,
}


def safe_eval(expr):
    expr = normalize_number_text(expr)
    expr = (expr.replace("\u00d7", "*").replace("\u00f7", "/")
                .replace("\u2212", "-").replace("^", "**"))
    expr = re.sub(r"(\d+(?:\.\d+)?)%", r"(\1/100)", expr)  # 50% -> (50/100)
    tree = ast.parse(expr, mode="eval")

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            v = ev(node.operand)
            return v if isinstance(node.op, ast.UAdd) else -v
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                raise ValueError("exponent too large")
            return _BIN_OPS[type(node.op)](left, right)
        raise ValueError("unsupported expression")

    return ev(tree)


def format_number(value):
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return f"{value:.10g}"


class CalculatorWindow(QMainWindow):
    def __init__(self, lang="en"):
        super().__init__()
        self.lang = lang
        self.setMinimumSize(320, 460)
        self.resize(340, 500)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        self.expr_edit = QLineEdit()
        self.expr_edit.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.expr_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.expr_edit.setStyleSheet("font-size: 20pt; padding: 10px 12px;")
        self.expr_edit.returnPressed.connect(self._evaluate)
        self.expr_edit.textChanged.connect(self._update_preview)
        root.addWidget(self.expr_edit)

        self.preview_lbl = QLabel("")
        self.preview_lbl.setObjectName("muted")
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.preview_lbl.setMinimumHeight(22)
        root.addWidget(self.preview_lbl)

        grid = QGridLayout()
        grid.setSpacing(7)
        rows = [
            ["C", "(", ")", "\u232b"],
            ["7", "8", "9", "\u00f7"],
            ["4", "5", "6", "\u00d7"],
            ["1", "2", "3", "\u2212"],
            ["0", ".", "%", "+"],
        ]
        for r, row in enumerate(rows):
            for c, label in enumerate(row):
                btn = QPushButton(label)
                btn.setMinimumHeight(48)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                if label in "C()\u232b\u00f7\u00d7\u2212+%":
                    btn.setObjectName("op")
                btn.clicked.connect(lambda checked=False, t=label: self._on_button(t))
                grid.addWidget(btn, r, c)
        eq = QPushButton("=")
        eq.setObjectName("primary")
        eq.setMinimumHeight(52)
        eq.setCursor(Qt.CursorShape.PointingHandCursor)
        eq.clicked.connect(self._evaluate)
        grid.addWidget(eq, len(rows), 0, 1, 4)
        root.addLayout(grid, stretch=1)

        self.setStyleSheet(TOOL_STYLE)
        self.set_language(lang)

    def set_language(self, lang):
        self.lang = lang if lang in ("fa", "en") else "en"
        self.setWindowTitle("\U0001F9EE " + STR["title"][self.lang])
        self._update_preview()

    def _t(self, key):
        return STR[key][self.lang]

    def _on_button(self, label):
        if label == "C":
            self.expr_edit.clear()
        elif label == "\u232b":
            self.expr_edit.backspace()
        else:
            self.expr_edit.insert(label)
        self.expr_edit.setFocus()

    def _update_preview(self):
        text = self.expr_edit.text().strip()
        if not text:
            self.preview_lbl.setText("")
            return
        try:
            self.preview_lbl.setStyleSheet("")
            self.preview_lbl.setText("= " + format_number(safe_eval(text)))
        except Exception:
            self.preview_lbl.setText("")  # half-typed expression: stay quiet

    def _evaluate(self):
        text = self.expr_edit.text().strip()
        if not text:
            return
        try:
            result = format_number(safe_eval(text))
        except ZeroDivisionError:
            self.preview_lbl.setStyleSheet("color: #ff6b6b;")
            self.preview_lbl.setText(self._t("div0"))
            return
        except Exception:
            self.preview_lbl.setStyleSheet("color: #ff6b6b;")
            self.preview_lbl.setText(self._t("error"))
            return
        self.expr_edit.setText(result)
        self.expr_edit.setCursorPosition(len(result))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.expr_edit.clear()
            return
        super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = CalculatorWindow()
    win.show()
    sys.exit(app.exec())
