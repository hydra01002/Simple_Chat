"""Small shared helpers for the side-tool windows (weather, calculator,
unit converter, notes): one dark stylesheet and tiny JSON load/save
helpers that store things next to the chat app's other local settings
(~/.lan_chat_gui). Nothing here touches the network."""

import json
import os

APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".lan_chat_gui")

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٫٬", "0123456789.,")


def normalize_number_text(text):
    """Accept Persian/Arabic-Indic digits and the Persian decimal sign."""
    return text.translate(PERSIAN_DIGITS).replace(",", "").strip()


def load_json(name, default):
    try:
        with open(os.path.join(APP_DATA_DIR, name), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(name, data):
    try:
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        with open(os.path.join(APP_DATA_DIR, name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except Exception:
        pass  # best effort - never crash a tool window over a failed save


TOOL_STYLE = """
QMainWindow, QWidget { background: #0b1220; color: #eaf2ff; font-family: "Segoe UI", Tahoma, Arial; font-size: 10.5pt; }
QLabel { background: transparent; }
QLabel#title { font-size: 15pt; font-weight: 800; }
QLabel#muted { color: #8798b6; font-size: 9pt; }
QLabel#error { color: #ff6b6b; font-size: 9.5pt; }
QFrame#card { background: #101f35; border: 1px solid #1f3454; border-radius: 12px; }
QFrame#card QLabel, QFrame#card QCheckBox { background: transparent; }
QLineEdit, QTextEdit, QDateTimeEdit, QComboBox {
    background: #0e1a2e; color: #eaf2ff; border: 1.5px solid #243b60;
    border-radius: 9px; padding: 7px 10px; selection-background-color: #5369ff;
}
QLineEdit:focus, QTextEdit:focus, QDateTimeEdit:focus, QComboBox:focus { border: 1.5px solid #5369ff; }
QComboBox QAbstractItemView { background: #0e1a2e; color: #eaf2ff; selection-background-color: #5369ff; border: 1px solid #243b60; }
QPushButton {
    background: #1a2c4a; color: #eaf2ff; border: 1px solid #2c4468;
    border-radius: 9px; padding: 8px 14px;
}
QPushButton:hover { border-color: #5369ff; background: #20365a; }
QPushButton:disabled { color: #68768f; background: #121d31; }
QPushButton#primary { background: #5369ff; border: none; font-weight: 700; color: white; }
QPushButton#primary:hover { background: #6579ff; }
QPushButton#primary:disabled { background: #243b60; color: #68768f; }
QPushButton#op { background: #24355a; color: #9fb4ff; font-weight: 700; }
QPushButton#op:hover { background: #2d4373; }
QPushButton#danger { background: #3a1d28; border: 1px solid #5a2a3a; color: #ff8d9a; padding: 4px 9px; }
QPushButton#danger:hover { background: #4d2433; }
QCheckBox { spacing: 8px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
QScrollBar::handle:vertical { background: #243b60; border-radius: 4px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""
