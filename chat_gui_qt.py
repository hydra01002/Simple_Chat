"""
رابط گرافیکی چت رمزنگاری‌شده در شبکه محلی (LAN) - نسخه PyQt6

امکانات این نسخه:
- بیشتر از دو کامپیوتر (یکی Host، بقیه Join می‌کنن)
- پیام‌های خودم راست، پیام‌های بقیه چپ، با ساعت ارسال
- لیست افراد آنلاین توی پنل کناری
- پیام خصوصی به یک نفر خاص (به‌جای همه)
- امکان Kick کردن یک نفر توسط میزبان
- اگه میزبان قطع بشه، یکی از بقیه خودکار میزبان جدید می‌شه
  (و اگه یه نفر فقط Kick بشه، کسی اشتباهی میزبان جدید نمی‌شه)
- رمز عبور اختیاری برای ورود به چت (توسط میزبان تعیین می‌شه)
- محدود کردن تعداد افراد مجاز توسط میزبان (اختیاری)
- سه تم ظاهری قابل‌انتخاب از تنظیمات: تیره مدرن / روشن تمیز / رنگی
- ظاهر کاملاً بازطراحی‌شده: گوشه‌های گرد، سایه، فاصله‌گذاری بهتر

ذخیره‌سازی پیام‌ها پیش‌فرض خاموشه (فقط در حافظه، موقتی)؛ از تنظیمات قابل‌فعال‌سازیه
(در این حالت، تاریخچه‌ی هر گفتگو به‌صورت فایل متنی ساده - بدون رمزنگاری - کنار برنامه ذخیره می‌شه)
خروجی گرفتن از هر گفتگو به فایل متنی هم با دکمه‌ی ⬇ بالای صفحه‌ی چت ممکنه

این نسخه به‌جای Tkinter با PyQt6 نوشته شده. برای اجرا باید نصب بشه:
    pip install PyQt6
"""

import base64
import zipfile
import hashlib
import html
import json
import os
import random
import re
import socket
import struct
import urllib.parse
import urllib.request
import sys
import threading
import time
import uuid

from PyQt6.QtCore import (
    Qt, QObject, pyqtSignal, QTimer, QPoint, QEvent, QRect, QRectF,
    QPropertyAnimation, QEasingCurve, QBuffer, QByteArray, QIODevice, pyqtProperty,
    QVariantAnimation,
)
from PyQt6.QtGui import (
    QFont, QIcon, QColor, QPainter, QPainterPath, QPixmap, QCursor, QMovie, QTextDocument,
)
from PyQt6.QtGui import QDesktopServices, QShortcut, QKeySequence
from PyQt6.QtCore import QUrl, QDateTime, QSize, QTime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup, QFrame,
    QScrollArea, QComboBox, QMenu, QMenuBar, QMessageBox, QSizePolicy,
    QListWidget, QListWidgetItem,
    QGraphicsDropShadowEffect, QSpacerItem, QToolButton, QStackedWidget,
    QFileDialog, QSystemTrayIcon, QTextEdit, QDialog, QCheckBox, QProgressBar,
    QPlainTextEdit, QInputDialog, QDateTimeEdit, QSpinBox, QTextBrowser, QTabWidget, QTimeEdit,
)

from crypto_utils import (
    generate_keypair,
    public_key_to_pem,
    load_public_key,
    encrypt_message,
    decrypt_message,
    encrypt_with_password,
    decrypt_with_password,
)
from tic_tac_toe import TicTacToe
from tetris_game import Tetris
from flappy_game import FlappyBird
from minesweeper_game import Minesweeper
from typing_game import TypingGameWindow, SENTENCES as TYPING_SENTENCES
from wordle_qt import Wordle
from sudoku_qt import Sudoku
from quiz_qt import Quiz
from pong_qt import Pong
from pacman_qt import Pacman
from memory_qt import Memory
from invaders_qt import Invaders
from hangman_qt import Hangman
from connect4_qt import Connect4
from dodge_qt import Dodge
from breakout_qt import Breakout
from chess_qt import Chess
from language_test import LanguageTestWindow
from snake_game import NeonSnake
from rates_window import RatesWindow
import voice_utils
from collections import deque
from online_games import OnlineTTTWindow, OnlineTypingWindow
from contacts_window import ContactsWindow, ContactsStore
from screen_share import ScreenSharer, ScreenViewerWindow
from shared_player import SharedPlayerWindow
from sync_folder import SyncFolder
from network_window import NetworkWindow
from wol_window import WakeOnLanWindow
from collab_widgets import ChecklistDialog, BoardDialog
from weather_window import WeatherWindow
from calculator_window import CalculatorWindow
from unit_converter_window import UnitConverterWindow
from notes_window import NotesWindow, NotesStore


EVERYONE = "Everyone"
SAVED_MESSAGES_KEY = "__saved__"  # a local-only, not-sent-over-the-network "notes to self" chat
GROUP_PREFIX = "g:"  # chat keys of user-created groups look like "g:<id>"

# Self-destruct timer choices (seconds, string key); 0 = off
TTL_OPTIONS = [(0, "ttl_off"), (10, "ttl_10s"), (60, "ttl_1m"), (3600, "ttl_1h"), (86400, "ttl_1d")]
TTL_SHORT = {10: "10s", 60: "1m", 3600: "1h", 86400: "1d"}
# Packet types that carry one encrypted JSON envelope and are simply
# relayed by the host; the backend hands them to the main window as
# envelope_received(kind, sender, is_private, content).
GENERIC_KINDS = {"vote", "checklist", "game", "board", "screen", "ctl", "capsule", "sync", "ptt", "media"}

STICKERS = [
    "\U0001F600", "\U0001F602", "\U0001F60D", "\U0001F60E", "\U0001F970", "\U0001F914", "\U0001F62D", "\U0001F621",
    "\U0001F44D", "\U0001F44E", "\U0001F44F", "\U0001F64F", "\U0001F4AA", "\U0001F91D", "\u270C\uFE0F", "\U0001F44B",
    "\u2764\uFE0F", "\U0001F494", "\U0001F525", "\u2728", "\U0001F389", "\U0001F381", "\U0001F382", "\U0001F37F",
    "\u2615", "\U0001F355", "\U0001F34E", "\U0001F36B", "\U0001F436", "\U0001F431", "\U0001F984", "\U0001F43C",
    "\U0001F31E", "\U0001F319", "\u2B50", "\U0001F308", "\U0001F680", "\U0001F3AE", "\U0001F4A1", "\U0001F4AF",
]


CHAT_LIST_LINES = [1]   # how many lines of preview each chat-list row shows (1-3)


def is_custom_group(key):
    return isinstance(key, str) and key.startswith(GROUP_PREFIX)


# ---------- Tiny translation layer ----------
# Covers the static chat-screen chrome (sidebar, menus, compose bar, context
# menu, role badges, system join/left notices, empty state). Scoped to the
# chat screen on purpose: the connect screen and rarer backend status/error
# messages stay as they are for now.

CURRENT_LANG = ["en"]  # the first (Connect) screen now defaults to English

STRINGS = {
    "chats_search_placeholder": {"fa": "جستجو", "en": "Search"},
    "menu_saved_messages": {"fa": "\U0001F516 پیام‌های ذخیره‌شده", "en": "\U0001F516 Saved Messages"},
    "menu_settings": {"fa": "\u2699 تنظیمات", "en": "\u2699 Settings"},
    "menu_appearance": {"fa": "ظاهر", "en": "Appearance"},
    "menu_language": {"fa": "زبان", "en": "Language"},
    "menu_night_mode": {"fa": "\U0001F319 حالت شب", "en": "\U0001F319 Night Mode"},
    "lang_fa": {"fa": "فارسی", "en": "Persian"},
    "lang_en": {"fa": "انگلیسی", "en": "English"},
    "group_title": {"fa": "گروه", "en": "Group"},
    "saved_messages_title": {"fa": "پیام‌های ذخیره‌شده", "en": "Saved Messages"},
    "members_suffix": {"fa": "عضو", "en": "members"},
    "role_host": {"fa": "میزبان", "en": "Host"},
    "role_member": {"fa": "عضو", "en": "Member"},
    "you_suffix": {"fa": "شما", "en": "you"},
    "you_prefix": {"fa": "شما", "en": "You"},
    "typing_now": {"fa": "در حال نوشتن...", "en": "typing..."},
    "compose_placeholder": {"fa": "پیام بنویسید...", "en": "Type a message..."},
    "empty_state_text": {
        "fa": "یک گفتگو را برای شروع پیام دادن انتخاب کنید",
        "en": "Select a chat to start messaging",
    },
    "ctx_kick": {"fa": "حذف از چت", "en": "Remove from chat"},
    "ctx_mute": {"fa": "میوت کردن", "en": "Mute"},
    "ctx_unmute": {"fa": "لغو میوت", "en": "Unmute"},
    "sys_joined": {"fa": "{name} به چت پیوست.", "en": "{name} joined the chat."},
    "sys_left": {"fa": "{name} چت را ترک کرد.", "en": "{name} left the chat."},
    "ctx_copy": {"fa": "کپی پیام", "en": "Copy message"},
    "menu_font_size": {"fa": "اندازه‌ی فونت", "en": "Font size"},
    "search_in_chat_placeholder": {"fa": "جستجو در این گفتگو...", "en": "Search in this chat..."},
    "search_in_chat_no_match": {"fa": "چیزی پیدا نشد", "en": "No matches"},
    "search_in_chat_match": {"fa": "{current} از {total}", "en": "{current} of {total}"},
    "read_tick_sent": {"fa": "ارسال شد", "en": "sent"},
    "read_tick_read": {"fa": "دیده شد", "en": "read"},
    "connect_title": {"fa": "چت رمزنگاری‌شده‌ی لوکال", "en": "Encrypted LAN Chat"},
    "connect_subtitle": {
        "fa": "پیام‌رسانی خصوصی و رمزنگاری‌شده برای شبکه‌ی محلی شما",
        "en": "Private, end-to-end encrypted messaging for your local network",
    },
    "connect_mode_host": {"fa": "میزبانی (منتظر بقیه بمانید)", "en": "Host (wait for other computers)"},
    "connect_mode_join": {"fa": "پیوستن (وصل شدن به میزبان)", "en": "Join (connect to the host)"},
    "connect_field_name": {"fa": "اسم شما:", "en": "Your name:"},
    "connect_field_ip": {"fa": "آی‌پی میزبان:", "en": "Host IP:"},
    "connect_field_port": {"fa": "پورت:", "en": "Port:"},
    "connect_field_password_host": {"fa": "تعیین رمز (اجباری):", "en": "Set a password (required):"},
    "connect_field_password_join": {"fa": "رمز (در صورت نیاز):", "en": "Password (if required):"},
    "connect_err_password": {
        "fa": "برای میزبانی، تعیین رمز اجباری است.",
        "en": "A password is required to host a chat.",
    },
    "connect_clear_selection_link": {
        "fa": "یا یک چت جدید میزبانی کنید",
        "en": "Or host a new chat instead",
    },
    "connect_field_max": {"fa": "حداکثر تعداد افراد (اختیاری):", "en": "Max participants (optional):"},
    "connect_field_avatar": {"fa": "عکس پروفایل (اختیاری):", "en": "Profile picture (optional):"},
    "connect_btn_choose_picture": {"fa": "انتخاب عکس...", "en": "Choose Picture..."},
    "connect_btn_host": {"fa": "میزبانی چت", "en": "Host Chat"},
    "connect_btn_join": {"fa": "اتصال", "en": "Connect"},
    "connect_err_name": {"fa": "لطفاً اسمتون رو وارد کنید.", "en": "Please enter your name."},
    "connect_err_port": {"fa": "پورت باید عدد باشه.", "en": "Port must be a number."},
    "connect_err_max": {
        "fa": "حداکثر تعداد افراد باید یه عدد مثبت باشه.",
        "en": "Max participants must be a positive number.",
    },
    "connect_err_ip": {"fa": "لطفاً آی‌پی میزبان رو وارد کنید.", "en": "Please enter the host's IP address."},
    "connect_err_no_host_selected": {
        "fa": "یه میزبان از لیست انتخاب کنید، یا آی‌پی رو دستی وارد کنید.",
        "en": "Select a host from the list, or enter an IP manually.",
    },
    "connect_err_avatar": {"fa": "نتونستم این فایل تصویری رو بخونم.", "en": "Could not read that image file."},
    "connect_pick_avatar_title": {"fa": "انتخاب عکس پروفایل", "en": "Choose Profile Picture"},
    "status_connecting": {"fa": "در حال اتصال...", "en": "Connecting..."},
    "status_starting_host": {"fa": "در حال راه‌اندازی میزبان...", "en": "Starting host..."},
    "status_hosting": {
        "fa": "در حال میزبانی روی پورت {port}. منتظر بقیه...",
        "en": "Hosting on port {port}. Waiting for others...",
    },
    "status_connected": {"fa": "به {host} وصل شد", "en": "Connected to {host}"},
    "err_failed_host": {"fa": "میزبانی انجام نشد: {error}", "en": "Failed to host: {error}"},
    "err_host_gone_no_backup": {
        "fa": "میزبان قطع شد و جایگزینی پیدا نشد.",
        "en": "The host disconnected and no backup could be found.",
    },
    "err_reconnect_failed": {"fa": "اتصال مجدد ممکن نشد: {error}", "en": "Could not reconnect: {error}"},
    "err_reconnect_failed_restart": {
        "fa": "اتصال مجدد بعد از قطع‌شدن میزبان ممکن نشد. لطفاً برنامه را دوباره باز کنید.",
        "en": "Could not reconnect after the host disconnected. Please restart the app.",
    },
    "err_send_failed": {
        "fa": "ارسال پیام به {name} ناموفق بود: {error}",
        "en": "Failed to send message to {name}: {error}",
    },
    "font_small": {"fa": "کوچیک", "en": "Small"},
    "font_medium": {"fa": "متوسط", "en": "Medium"},
    "font_large": {"fa": "بزرگ", "en": "Large"},
    "tray_show": {"fa": "نمایش پنجره", "en": "Show window"},
    "tray_quit": {"fa": "خروج", "en": "Quit"},
    "tray_hint_title": {"fa": "برنامه هنوز اجراست", "en": "Still running"},
    "tray_hint_body": {
        "fa": "برنامه بسته نشد، فقط به تری رفت. برای خروج کامل از همین‌جا کلیک راست کنید.",
        "en": "The app didn't close, it just went to the tray. Right-click here to quit for good.",
    },
    "reconnect_banner": {"fa": "در حال اتصال مجدد...", "en": "Reconnecting..."},
    "new_host_banner": {"fa": "شما میزبان جدید شدید", "en": "You are now the host"},
    "sys_kicked_other": {"fa": "{name} توسط میزبان از چت حذف شد.", "en": "{name} was removed by the host."},
    "sys_reconnected": {"fa": "اتصال مجدد برقرار شد. {host} میزبان جدیده.", "en": "Reconnected. {host} is now the host."},
    "sys_became_host": {
        "fa": "میزبان قطع شد. شما میزبان جدید شدید — منتظر اتصال مجدد بقیه...",
        "en": "The host disconnected. You are now the host — waiting for the others to reconnect...",
    },
    "sys_reconnecting_through": {
        "fa": "میزبان قطع شد. در حال اتصال مجدد از طریق {name}...",
        "en": "The host disconnected. Reconnecting through {name}...",
    },
    "kicked_dialog_title": {"fa": "حذف شدید", "en": "Removed"},
    "kicked_dialog_body": {
        "fa": "شما توسط میزبان از چت حذف شدید.",
        "en": "You were removed from the chat by the host.",
    },
    "reply_preview_label": {"fa": "در پاسخ به {name}", "en": "Replying to {name}"},
    "editing_label": {"fa": "در حال ویرایش پیام", "en": "Editing message"},
    "edited_suffix": {"fa": " (ویرایش‌شده)", "en": " (edited)"},
    "deleted_placeholder": {"fa": "این پیام حذف شد", "en": "This message was deleted"},
    "ctx_reply": {"fa": "پاسخ", "en": "Reply"},
    "ctx_edit": {"fa": "ویرایش", "en": "Edit"},
    "ctx_delete": {"fa": "حذف", "en": "Delete"},
    "ctx_forward": {"fa": "فوروارد", "en": "Forward"},
    "ctx_pin": {"fa": "پین کردن", "en": "Pin"},
    "ctx_react": {"fa": "واکنش", "en": "React"},
    "export_chat_tooltip": {"fa": "خروجی گرفتن از این گفتگو", "en": "Export this chat"},
    "export_chat_empty": {"fa": "هنوز پیامی برای خروجی گرفتن نیست.", "en": "There's nothing to export yet."},
    "export_chat_done_title": {"fa": "خروجی گرفته شد", "en": "Chat exported"},
    "export_chat_done_body": {
        "fa": "گفتگو ذخیره شد در:\n{path}",
        "en": "Chat saved to:\n{path}",
    },
    "export_chat_deleted_marker": {"fa": "[پیام حذف شد]", "en": "[message deleted]"},
    "menu_privacy": {"fa": "حریم خصوصی", "en": "Privacy"},
    "menu_save_history": {
        "fa": "ذخیره‌ی تاریخچه‌ی چت روی این دستگاه",
        "en": "Save chat history on this device",
    },
    "history_divider": {
        "fa": "\u2014 پیام‌های قبلی (ذخیره‌شده روی این دستگاه) \u2014",
        "en": "\u2014 Earlier messages (saved on this device) \u2014",
    },
    "ctx_unpin": {"fa": "برداشتن پین", "en": "Unpin"},
    "forward_to_title": {"fa": "فوروارد به...", "en": "Forward to..."},
    "pinned_label": {"fa": "پیام پین‌شده", "en": "Pinned message"},
    "forwarded_prefix": {"fa": "فوروارد شده از {name}", "en": "Forwarded from {name}"},
    "cancel_action": {"fa": "\u2715", "en": "\u2715"},
    "discover_scanning": {"fa": "در حال جستجوی میزبان‌های شبکه...", "en": "Scanning the network for hosts..."},
    "discover_none_found": {"fa": "هیچ میزبانی پیدا نشد", "en": "No hosts found"},
    "discover_manual_link": {"fa": "وارد کردن آی‌پی به‌صورت دستی", "en": "Enter IP manually"},
    "discover_auto_link": {"fa": "جستجوی خودکار میزبان", "en": "Auto-discover hosts"},
    "discover_refresh": {"fa": "جستجوی دوباره", "en": "Scan again"},
    "change_avatar_hint": {"fa": "تغییر عکس پروفایل", "en": "Change profile picture"},
    "status_online": {"fa": "آنلاین", "en": "Online"},
    "status_busy": {"fa": "مشغول", "en": "Busy"},
    "status_away": {"fa": "غایب", "en": "Away"},
    "security_code_btn": {"fa": "\U0001F512 کد امنیتی", "en": "\U0001F512 Security code"},
    "security_code_title": {"fa": "کد امنیتی", "en": "Security code"},
    "security_code_desc": {
        "fa": "این کد از کلید رمزنگاری شما و {name} ساخته شده. اگه هر دو طرف همین کد رو ببینید (مثلاً تلفنی یا حضوری مقایسه کنید)، مطمئنید کسی وسط این گفتگو نیست.",
        "en": "This code is derived from your encryption key and {name}'s. If you both see the exact same code (compare by phone or in person), you can be sure no one is in the middle of this chat.",
    },
    "ping_ms": {"fa": "{ms} میلی‌ثانیه", "en": "{ms} ms"},
    "chat_row_action_pin": {"fa": "سنجاق کردن / برداشتن", "en": "Pin / Unpin"},
    "chat_row_action_read": {"fa": "خوانده‌شده / نشده", "en": "Mark read / unread"},
    "attach_file_btn": {"fa": "\U0001F4CE", "en": "\U0001F4CE"},
    "file_too_large": {
        "fa": "حجم فایل بیشتر از {max} مگابایته. فایل‌های بزرگ‌تر پشتیبانی نمی‌شن.",
        "en": "File is larger than {max} MB. Bigger files aren't supported.",
    },
    "file_save_btn": {"fa": "ذخیره", "en": "Save"},
    "file_save_dialog_title": {"fa": "ذخیره‌ی فایل", "en": "Save file"},
    "file_card_size": {"fa": "{size} کیلوبایت", "en": "{size} KB"},
    "extras_games_btn": {"fa": "\U0001F3AE بازی‌ها", "en": "\U0001F3AE Games"},
    "extras_language_test_btn": {"fa": "\U0001F5E3 تست زبان", "en": "\U0001F5E3 Language test"},
    "extras_rates_btn": {"fa": "\U0001F4B1 نرخ ارز", "en": "\U0001F4B1 Exchange rates"},
    "extras_games_menu_ttt": {"fa": "تیک‌تاک‌تو", "en": "Tic Tac Toe"},
    "extras_games_menu_snake": {"fa": "مار", "en": "Snake"},
    "extras_games_menu_tetris": {"fa": "تتریس", "en": "Tetris"},
    "extras_games_menu_flappy": {"fa": "فلپی", "en": "Flappy"},
    "extras_games_menu_mines": {"fa": "مین‌روب", "en": "Minesweeper"},
    "extras_games_menu_typing": {"fa": "سرعت تایپ", "en": "Typing speed"},
    "extras_games_menu_wordle": {"fa": "وردل", "en": "Wordle"},
    "extras_games_menu_sudoku": {"fa": "سودوکو", "en": "Sudoku"},
    "extras_games_menu_quiz": {"fa": "مسابقه‌ی سؤال", "en": "Quiz"},
    "extras_games_menu_pong": {"fa": "پینگ‌پنگ", "en": "Pong"},
    "extras_games_menu_pacman": {"fa": "پک‌من", "en": "Pac-Man"},
    "extras_games_menu_memory": {"fa": "حافظه", "en": "Memory"},
    "extras_games_menu_invaders": {"fa": "مهاجمان فضایی", "en": "Space Invaders"},
    "extras_games_menu_hangman": {"fa": "حدس کلمه", "en": "Hangman"},
    "extras_games_menu_connect4": {"fa": "چهار در یک ردیف", "en": "Connect Four"},
    "extras_games_menu_dodge": {"fa": "جاخالی", "en": "Dodge"},
    "extras_games_menu_breakout": {"fa": "شکستن آجر", "en": "Breakout"},
    "extras_games_menu_chess": {"fa": "شطرنج", "en": "Chess"},
    "games_picker_title": {"fa": "بازی‌ها", "en": "Games"},
    "games_picker_more_soon": {
        "fa": "بازی‌های بیشتر بعداً اضافه می‌شن",
        "en": "More games will be added later",
    },
    "attach_menu_file": {"fa": "\U0001F4CE فایل", "en": "\U0001F4CE File"},
    "attach_menu_poll": {"fa": "\U0001F4CA نظرسنجی", "en": "\U0001F4CA Poll"},
    "attach_menu_yesno": {"fa": "\U0001F44D رأی‌گیری سریع بله/خیر", "en": "\U0001F44D Quick yes/no vote"},
    "poll_title": {"fa": "نظرسنجی جدید", "en": "New poll"},
    "poll_question_label": {"fa": "سؤال:", "en": "Question:"},
    "poll_options_label": {"fa": "گزینه‌ها (هر خط یکی، ۲ تا ۸ تا):", "en": "Options (one per line, 2 to 8):"},
    "poll_create_btn": {"fa": "ارسال", "en": "Send"},
    "poll_err": {"fa": "یه سؤال و حداقل دو گزینه لازمه.", "en": "A question and at least two options are needed."},
    "poll_yes": {"fa": "بله", "en": "Yes"},
    "poll_no": {"fa": "خیر", "en": "No"},
    "voice_tooltip": {"fa": "ضبط پیام صوتی (کلیک برای شروع/ارسال)", "en": "Record a voice message (click to start/send)"},
    "voice_title": {"fa": "پیام صوتی", "en": "Voice message"},
    "voice_err": {"fa": "ضبط ممکن نشد: {error}", "en": "Could not record: {error}"},
    "voice_play_err": {"fa": "پخش صدا ممکن نیست (QtMultimedia در دسترس نیست).", "en": "Playback isn't available (QtMultimedia missing)."},
    "sticker_tooltip": {"fa": "استیکر و GIF", "en": "Stickers & GIFs"},
    "chat_menu_tooltip": {"fa": "تنظیمات این گفتگو", "en": "Chat settings"},
    "chat_bg_menu": {"fa": "\U0001F3A8 پس‌زمینه‌ی گفتگو", "en": "\U0001F3A8 Chat background"},
    "chat_bg_default": {"fa": "پیش‌فرض", "en": "Default"},
    "chat_bg_image": {"fa": "انتخاب عکس...", "en": "Choose image..."},
    "chat_notify_toggle": {"fa": "\U0001F514 اعلان این گفتگو", "en": "\U0001F514 Notifications for this chat"},
    "chat_sound_toggle": {"fa": "\U0001F50A صدای این گفتگو", "en": "\U0001F50A Sound for this chat"},
    "chat_sound_custom": {"fa": "\U0001F3B5 صدای اختصاصی...", "en": "\U0001F3B5 Custom sound..."},
    "chat_sound_reset": {"fa": "برگشت به صدای پیش‌فرض", "en": "Reset to default sound"},
    "menu_theme_mode": {"fa": "حالت تم", "en": "Theme mode"},
    "theme_mode_manual": {"fa": "دستی", "en": "Manual"},
    "theme_mode_system": {"fa": "هماهنگ با تم ویندوز", "en": "Follow Windows theme"},
    "theme_mode_time": {"fa": "بر اساس ساعت روز", "en": "By time of day"},
    "theme_mode_occasion": {"fa": "تم مناسبتی خودکار", "en": "Seasonal / occasion themes"},
    "menu_backup": {"fa": "پشتیبان‌گیری", "en": "Backup"},
    "backup_export": {"fa": "ذخیره‌ی پشتیبان تنظیمات...", "en": "Back up app settings..."},
    "backup_restore": {"fa": "بازگردانی تنظیمات...", "en": "Restore settings..."},
    "backup_done": {"fa": "پشتیبان ذخیره شد:\n{path}", "en": "Backup saved to:\n{path}"},
    "backup_restore_confirm": {
        "fa": "تنظیمات فعلی (یادداشت‌ها، ترجیحات و...) با محتوای این فایل جایگزین می‌شه. ادامه بدیم؟",
        "en": "Your current settings (notes, preferences, ...) will be replaced by this file's content. Continue?",
    },
    "backup_restore_done": {"fa": "بازگردانی انجام شد. برای اعمال کامل، برنامه را دوباره باز کنید.", "en": "Restored. Restart the app to apply everything."},
    "backup_restore_bad": {"fa": "این فایل پشتیبان معتبر نیست.", "en": "That isn't a valid backup file."},
    "ctx_select": {"fa": "\u2611 انتخاب", "en": "\u2611 Select"},
    "select_count": {"fa": "{n} پیام انتخاب شد", "en": "{n} selected"},
    "select_forward": {"fa": "فوروارد", "en": "Forward"},
    "select_copy": {"fa": "کپی", "en": "Copy"},
    "select_delete": {"fa": "حذف", "en": "Delete"},
    "select_delete_confirm": {"fa": "پیام‌های خودتون از بین انتخاب‌شده‌ها حذف بشن؟", "en": "Delete your own messages among the selected ones?"},
    "attach_menu_schedule": {"fa": "\U0001F552 ارسال زمان‌بندی‌شده (متن نوشته‌شده)", "en": "\U0001F552 Schedule the typed message"},
    "schedule_title": {"fa": "زمان ارسال", "en": "Send at"},
    "schedule_need_text": {"fa": "اول متن پیام رو توی کادر بنویسید.", "en": "Type the message in the box first."},
    "schedule_past": {"fa": "زمان باید در آینده باشه.", "en": "Pick a time in the future."},
    "schedule_ok": {"fa": "تأیید", "en": "OK"},
    "schedule_list": {"fa": "\U0001F552 پیام‌های زمان‌بندی‌شده", "en": "\U0001F552 Scheduled messages"},
    "schedule_remove": {"fa": "حذف انتخاب‌شده", "en": "Remove selected"},
    "gallery_menu": {"fa": "\U0001F5BC رسانه و فایل‌های این گفتگو", "en": "\U0001F5BC Media & files in this chat"},
    "gallery_all": {"fa": "\U0001F4C2 فایل‌های همه‌ی گفتگوها", "en": "\U0001F4C2 Files from all chats"},
    "gallery_title": {"fa": "رسانه و فایل‌ها", "en": "Media & files"},
    "gallery_filter_all": {"fa": "همه", "en": "All"},
    "gallery_filter_images": {"fa": "عکس‌ها", "en": "Images"},
    "gallery_filter_voice": {"fa": "صوتی", "en": "Voice"},
    "gallery_filter_files": {"fa": "فایل‌ها", "en": "Files"},
    "gallery_empty": {"fa": "چیزی نیست", "en": "Nothing here"},
    "menu_link_preview": {"fa": "پیش‌نمایش لینک (به سایت وصل می‌شه)", "en": "Link previews (contacts the site)"},
    "bio_placeholder": {"fa": "وضعیت متنی دلخواه...", "en": "Custom status text..."},
    "mentions_title": {"fa": "@ منشن‌های من", "en": "@ My mentions"},
    "mentions_row": {"fa": "@ منشن‌ها", "en": "@ Mentions"},
    "mentions_none": {"fa": "کسی شما رو منشن نکرده", "en": "Nobody mentioned you yet"},
    "collab_checklist": {"fa": "\U0001F5D2 چک‌لیست مشترک", "en": "\U0001F5D2 Shared checklist"},
    "collab_board": {"fa": "\U0001F3A8 تخته‌وایت‌برد مشترک", "en": "\U0001F3A8 Shared whiteboard"},
    "collab_placeholder": {"fa": "مورد جدید...", "en": "New item..."},
    "collab_add": {"fa": "افزودن", "en": "Add"},
    "collab_remove": {"fa": "حذف مورد انتخاب‌شده", "en": "Remove selected item"},
    "collab_send_all": {"fa": "ارسال کل تخته", "en": "Send whole board"},
    "collab_clear": {"fa": "پاک کردن", "en": "Clear"},
    "collab_updated": {"fa": "چک‌لیست به‌روز شد", "en": "checklist updated"},
    "menu_security": {"fa": "امنیت", "en": "Security"},
    "security_pin": {"fa": "قفل برنامه با پین...", "en": "App lock PIN..."},
    "security_autolock": {"fa": "قفل خودکار بعد از بی‌کاری...", "en": "Auto-lock when idle..."},
    "security_lock_now": {"fa": "قفل کردن همین حالا", "en": "Lock now"},
    "enc_export_all": {"fa": "پشتیبان رمزگذاری‌شده از همه‌ی گفتگوها...", "en": "Encrypted backup of all chats..."},
    "enc_open": {"fa": "باز کردن فایل رمزگذاری‌شده...", "en": "Open an encrypted export..."},
    "enc_export_chat": {"fa": "\U0001F510 خروجی رمزگذاری‌شده از این گفتگو...", "en": "\U0001F510 Encrypted export of this chat..."},
    "enc_password_new": {"fa": "یه رمز برای فایل انتخاب کنید (حداقل ۴ حرف):", "en": "Choose a password for the file (4+ characters):"},
    "enc_password_repeat": {"fa": "رمز رو دوباره وارد کنید:", "en": "Repeat the password:"},
    "enc_password_mismatch": {"fa": "رمزها یکی نبودن یا خیلی کوتاهه.", "en": "Passwords differ or are too short."},
    "enc_password_ask": {"fa": "رمز فایل:", "en": "File password:"},
    "enc_nothing": {"fa": "هنوز پیامی برای خروجی گرفتن نیست.", "en": "There are no messages to export yet."},
    "enc_saved": {"fa": "ذخیره شد:\n{path}", "en": "Saved:\n{path}"},
    "enc_bad": {"fa": "باز نشد: رمز اشتباهه یا فایل خرابه.", "en": "Could not open: wrong password or damaged file."},
    "pin_set": {"fa": "تنظیم پین", "en": "Set PIN"},
    "pin_change": {"fa": "تغییر پین", "en": "Change PIN"},
    "pin_remove": {"fa": "حذف قفل", "en": "Remove lock"},
    "pin_ask_new": {"fa": "پین جدید (حداقل ۴ کاراکتر):", "en": "New PIN (4+ characters):"},
    "pin_ask_repeat": {"fa": "پین رو دوباره وارد کنید:", "en": "Repeat the PIN:"},
    "pin_ask_current": {"fa": "پین فعلی:", "en": "Current PIN:"},
    "pin_mismatch": {"fa": "پین‌ها یکی نبودن یا خیلی کوتاهه.", "en": "PINs differ or are too short."},
    "pin_wrong": {"fa": "پین اشتباهه.", "en": "Wrong PIN."},
    "pin_need_first": {"fa": "اول از تنظیمات یه پین برای برنامه تعیین کنید.", "en": "Set an app PIN in Settings first."},
    "autolock_off": {"fa": "خاموش", "en": "Off"},
    "autolock_min": {"fa": "بعد از {n} دقیقه", "en": "After {n} min"},
    "lock_title": {"fa": "برنامه قفله", "en": "App locked"},
    "lock_unlock": {"fa": "باز کردن", "en": "Unlock"},
    "lock_wait": {"fa": "چند بار اشتباه زدید؛ {n} ثانیه صبر کنید.", "en": "Too many tries; wait {n} s."},
    "lock_new_message": {"fa": "پیام جدید", "en": "New message"},
    "menu_display": {"fa": "نمایش و اعلان‌ها", "en": "Display & notifications"},
    "list_lines_row": {"fa": "خط‌های پیش‌نمایش لیست چت...", "en": "Chat list preview lines..."},
    "list_lines_opt": {"fa": "{n} خط", "en": "{n} line(s)"},
    "dnd_row": {"fa": "\U0001F319 مزاحم نشوید (زمان‌بندی)...", "en": "\U0001F319 Do not disturb (schedule)..."},
    "dnd_title": {"fa": "مزاحم نشوید", "en": "Do not disturb"},
    "dnd_enable": {"fa": "فعال باشه (بدون صدا و اعلان در این بازه)", "en": "Enabled (no sounds or notifications in this window)"},
    "dnd_from": {"fa": "از ساعت:", "en": "From:"},
    "dnd_to": {"fa": "تا ساعت:", "en": "To:"},
    "ctx_star": {"fa": "\u2B50 ستاره‌دار / برداشتن ستاره", "en": "\u2B50 Star / unstar"},
    "star_row": {"fa": "\u2B50 پیام‌های ستاره‌دار", "en": "\u2B50 Starred messages"},
    "star_title": {"fa": "پیام‌های ستاره‌دار", "en": "Starred messages"},
    "star_remove": {"fa": "برداشتن ستاره‌ی انتخاب‌شده", "en": "Unstar selected"},
    "star_none": {"fa": "هنوز پیامی ستاره‌دار نشده", "en": "No starred messages yet"},
    "online_row": {"fa": "\U0001F465 چه کسانی آنلاینن", "en": "\U0001F465 Who's online"},
    "online_title": {"fa": "افراد آنلاین", "en": "Who's online"},
    "role_admin": {"fa": "مدیر", "en": "Admin"},
    "ctx_make_admin": {"fa": "ارتقا به مدیر", "en": "Make admin"},
    "ctx_remove_admin": {"fa": "برداشتن مدیریت", "en": "Remove admin"},
    "group_readonly_label": {"fa": "\U0001F4E2 کانال اعلانات (فقط من می‌تونم پیام بدم)", "en": "\U0001F4E2 Announcement channel (only I can post)"},
    "adv_row": {"fa": "\U0001F50E جستجوی پیشرفته", "en": "\U0001F50E Advanced search"},
    "adv_title": {"fa": "جستجوی پیشرفته", "en": "Advanced search"},
    "adv_text": {"fa": "متن (اختیاری)", "en": "Text (optional)"},
    "adv_any": {"fa": "همه", "en": "Any"},
    "adv_hour": {"fa": "یک ساعت اخیر", "en": "Last hour"},
    "adv_today": {"fa": "۲۴ ساعت اخیر", "en": "Last 24 hours"},
    "adv_week": {"fa": "۷ روز اخیر", "en": "Last 7 days"},
    "adv_files_only": {"fa": "فقط فایل‌ها", "en": "Files only"},
    "adv_search": {"fa": "جستجو", "en": "Search"},
    "adv_sender": {"fa": "فرستنده", "en": "Sender"},
    "adv_chat": {"fa": "گفتگو", "en": "Chat"},
    "adv_when": {"fa": "زمان", "en": "Time"},
    "ctx_translate": {"fa": "\U0001F310 ترجمه", "en": "\U0001F310 Translate"},
    "attach_menu_capsule": {"fa": "\u23F3 کپسول زمانی (متن نوشته‌شده)", "en": "\u23F3 Time capsule (typed message)"},
    "capsule_title": {"fa": "باز شدن کپسول", "en": "Capsule opens at"},
    "capsule_locked": {"fa": "\U0001F512 کپسول زمانی \u2014 باز می‌شه در {when}", "en": "\U0001F512 Time capsule \u2014 opens {when}"},
    "game_challenge": {"fa": "\U0001F3AE چالش تیک‌تاک‌تو آنلاین", "en": "\U0001F3AE Challenge to online Tic Tac Toe"},
    "game_invite_text": {"fa": "{name} شما رو به یه دست تیک‌تاک‌تو آنلاین دعوت کرده. قبول می‌کنید؟", "en": "{name} challenges you to online Tic Tac Toe. Accept?"},
    "game_invite_sent": {"fa": "دعوت بازی ارسال شد", "en": "Game invite sent"},
    "clipboard_share": {"fa": "\U0001F4CB ارسال کلیپ‌بورد من", "en": "\U0001F4CB Send my clipboard"},
    "clipboard_empty": {"fa": "کلیپ‌بوردتون خالیه.", "en": "Your clipboard is empty."},
    "sync_menu": {"fa": "\U0001F4C1 پوشه‌ی هم‌گام مشترک...", "en": "\U0001F4C1 Shared sync folder..."},
    "sync_title": {"fa": "پوشه‌ی هم‌گام مشترک", "en": "Shared sync folder"},
    "sync_none": {"fa": "پوشه‌ای انتخاب نشده.", "en": "No folder selected."},
    "sync_current": {"fa": "پوشه: {path}", "en": "Folder: {path}"},
    "sync_choose": {"fa": "انتخاب پوشه...", "en": "Choose folder..."},
    "sync_send_all": {"fa": "ارسال همه‌ی فایل‌ها الان", "en": "Send all files now"},
    "sync_stop": {"fa": "توقف هم‌گام‌سازی", "en": "Stop syncing"},
    "sync_note": {"fa": "فایل‌های جدید/تغییرکرده خودکار برای بقیه‌ی این گفتگو فرستاده می‌شن (تا ۲۰ مگابایت، بدون حذف). دیگران هم باید همین‌جا یه پوشه انتخاب کنن تا دریافت کنن.", "en": "New/changed files are sent automatically to everyone in this chat (up to 20 MB, deletions aren't synced). Others must pick a folder here too to receive them."},
    "tools_wol": {"fa": "بیدارکردن (WoL)", "en": "Wake-on-LAN"},
    "tools_network": {"fa": "سلامت شبکه", "en": "Network health"},
    "ptt_tooltip": {"fa": "نگه دارید و صحبت کنید (Push-to-talk)", "en": "Hold to talk (push-to-talk)"},
    "ptt_err": {"fa": "میکروفون در دسترس نیست: {error}", "en": "Microphone unavailable: {error}"},
    "screen_start": {"fa": "\U0001F5A5 شروع اشتراک صفحه‌نمایش", "en": "\U0001F5A5 Start sharing my screen"},
    "screen_stop": {"fa": "\u23F9 توقف اشتراک صفحه‌نمایش", "en": "\u23F9 Stop sharing my screen"},
    "screen_confirm": {"fa": "کل صفحه‌نمایش شما برای {n} نفر نشون داده می‌شه (حدود هر ثانیه یک تصویر). ادامه بدیم؟", "en": "Your whole screen will be shown to {n} people (about one picture per second). Continue?"},
    "screen_sharing_now": {"fa": "در حال اشتراک صفحه‌نمایش...", "en": "Sharing your screen..."},
    "screen_viewer_title": {"fa": "صفحه‌نمایش {name}", "en": "{name}'s screen"},
    "screen_stopped": {"fa": "اشتراک متوقف شد.", "en": "Sharing stopped."},
    "hand_raise": {"fa": "\u270B بلند کردن دست", "en": "\u270B Raise hand"},
    "hand_lower": {"fa": "\u270B پایین آوردن دست", "en": "\u270B Lower hand"},
    "hands_clear": {"fa": "پایین آوردن دست‌های همه", "en": "Lower everyone's hands"},
    "media_menu": {"fa": "\U0001F3B5 پخش‌کننده‌ی مشترک...", "en": "\U0001F3B5 Shared player..."},
    "role_guest": {"fa": "مهمان", "en": "Guest"},
    "ctx_make_guest": {"fa": "مهمان موقت (۳۰ دقیقه)", "en": "Temporary guest (30 min)"},
    "ctx_remove_guest": {"fa": "لغو مهمان موقت", "en": "Cancel guest timer"},
    "slash_help_title": {"fa": "دستورات سریع", "en": "Slash commands"},
    "slash_help": {
        "fa": "/me متن \u2014 پیام حالت‌دار\n/shrug \u2014 ¯\\_(ツ)_/¯\n/roll [N] \u2014 تاس\n/flip \u2014 شیر یا خط\n/time \u2014 ساعت الان\n/poll سؤال | گزینه۱ | گزینه۲ \u2014 نظرسنجی\n/focus [دقیقه] \u2014 حالت تمرکز\n/lock \u2014 قفل برنامه\n/present \u2014 حالت ارائه\n/help",
        "en": "/me text \u2014 action message\n/shrug \u2014 ¯\\_(ツ)_/¯\n/roll [N] \u2014 dice\n/flip \u2014 coin\n/time \u2014 current time\n/poll Question | opt1 | opt2 \u2014 poll\n/focus [minutes] \u2014 focus mode\n/lock \u2014 lock the app\n/present \u2014 presentation mode\n/help",
    },
    "slash_unknown": {"fa": "دستور ناشناخته. /help رو بزنید.", "en": "Unknown command. Try /help."},
    "ctx_tag": {"fa": "\U0001F3F7 برچسب...", "en": "\U0001F3F7 Tag..."},
    "tag_important": {"fa": "\u2757 مهم", "en": "\u2757 Important"},
    "tag_todo": {"fa": "\u2705 کار", "en": "\u2705 To-do"},
    "tag_idea": {"fa": "\U0001F4A1 ایده", "en": "\U0001F4A1 Idea"},
    "tag_question": {"fa": "\u2753 سؤال", "en": "\u2753 Question"},
    "tag_remove": {"fa": "برداشتن برچسب", "en": "Remove tag"},
    "tagged_row": {"fa": "\U0001F3F7 پیام‌های برچسب‌دار", "en": "\U0001F3F7 Tagged messages"},
    "tagged_title": {"fa": "پیام‌های برچسب‌دار", "en": "Tagged messages"},
    "ctx_remind": {"fa": "\u23F0 یادآور پاسخ دادن", "en": "\u23F0 Remind me to reply"},
    "remind_min": {"fa": "{n} دقیقه دیگه", "en": "In {n} min"},
    "reply_reminder_text": {"fa": "\u21A9 پاسخ به {name}: {text}", "en": "\u21A9 Reply to {name}: {text}"},
    "attach_menu_location": {"fa": "\U0001F4CD ارسال موقعیت (ساختمان/اتاق)", "en": "\U0001F4CD Send location (building/room)"},
    "loc_title": {"fa": "موقعیت مکانی", "en": "Location"},
    "loc_building": {"fa": "ساختمان", "en": "Building"},
    "loc_floor": {"fa": "طبقه", "en": "Floor"},
    "loc_room": {"fa": "اتاق", "en": "Room"},
    "loc_note": {"fa": "توضیح (اختیاری)", "en": "Note (optional)"},
    "loc_copy": {"fa": "کپی", "en": "Copy"},
    "incognito_toggle": {"fa": "\U0001F576 حالت ناشناس (با خروج از گفتگو پاک می‌شه)", "en": "\U0001F576 Incognito (erased when you leave this chat)"},
    "tempro_menu": {"fa": "\U0001F512 فقط‌خواندنی موقت", "en": "\U0001F512 Temporary read-only"},
    "tempro_off": {"fa": "لغو فقط‌خواندنی", "en": "Cancel read-only"},
    "pdf_export": {"fa": "\U0001F4C4 خروجی PDF از این گفتگو...", "en": "\U0001F4C4 Export this chat as PDF..."},
    "person_note": {"fa": "\U0001F4D3 یادداشت خصوصی درباره‌ی این فرد", "en": "\U0001F4D3 Private note about this person"},
    "race_challenge": {"fa": "\u2328 چالش سرعت تایپ", "en": "\u2328 Typing race challenge"},
    "race_invite_text": {"fa": "{name} شما رو به مسابقه‌ی سرعت تایپ دعوت کرده. قبول می‌کنید؟", "en": "{name} challenges you to a typing race. Accept?"},
    "stats_row": {"fa": "\U0001F4CA آمار گفتگوها", "en": "\U0001F4CA Chat stats"},
    "stats_title": {"fa": "آمار سرگرم‌کننده", "en": "Fun stats"},
    "random_row": {"fa": "\U0001F3B2 گفتگوی تصادفی", "en": "\U0001F3B2 Random chat"},
    "focus_row": {"fa": "\U0001F3AF حالت تمرکز...", "en": "\U0001F3AF Focus mode..."},
    "focus_off": {"fa": "خاموش", "en": "Off"},
    "focus_banner": {"fa": "\U0001F3AF حالت تمرکز تا {t} \u2014 برای پایان کلیک کنید", "en": "\U0001F3AF Focus mode until {t} \u2014 click to end"},
    "presentation_row": {"fa": "\U0001F4FD حالت ارائه (F11)", "en": "\U0001F4FD Presentation mode (F11)"},
    "waiting_row": {"fa": "اتاق انتظار (میزبان تأیید می‌کنه)", "en": "Waiting room (host approves joiners)"},
    "join_request_text": {"fa": "{name} می‌خواد به چت بپیونده. اجازه بدید؟", "en": "{name} wants to join the chat. Let them in?"},
    "autoreply_row": {"fa": "پیام غیابی خودکار...", "en": "Auto-reply when away..."},
    "autoreply_enable": {"fa": "وقتی وضعیتم «غایب»ه به پیام‌های خصوصی پاسخ بده", "en": "Reply to private messages while my status is Away"},
    "autoreply_default": {"fa": "الان نیستم، بعداً جواب می‌دم.", "en": "I'm away right now, I'll reply later."},
    "contacts_row": {"fa": "\U0001F4D2 مخاطبین", "en": "\U0001F4D2 Contacts"},
    "birthday_today": {"fa": "\U0001F382 امروز تولد {name} هست", "en": "\U0001F382 It's {name}'s birthday today"},
    "qr_hint": {"fa": "کد QR: طرف مقابل می‌تونه با گوشی اسکن کنه و با کد خودش مقایسه کنه.", "en": "QR code: the other person can scan it with a phone and compare with their own."},
    "qr_missing": {"fa": "برای نمایش QR یک‌بار اجرا کنید: pip install qrcode", "en": "To show a QR code run once: pip install qrcode"},
    "extras_tools_btn": {"fa": "\U0001F9F0 ابزارها", "en": "\U0001F9F0 Tools"},
    "menu_notes": {"fa": "\U0001F4DD یادداشت و یادآور", "en": "\U0001F4DD Notes & Reminders"},
    "tools_picker_title": {"fa": "ابزارها", "en": "Tools"},
    "tools_weather": {"fa": "آب‌وهوا", "en": "Weather"},
    "tools_calculator": {"fa": "ماشین‌حساب", "en": "Calculator"},
    "tools_converter": {"fa": "مبدل واحد", "en": "Unit converter"},
    "reminder_title": {"fa": "\u23F0 یادآوری", "en": "\u23F0 Reminder"},
    "ttl_tooltip": {"fa": "پیام‌های خودتخریب‌شونده", "en": "Self-destructing messages"},
    "ttl_menu_title": {"fa": "پیام‌های بعدی من در این گفتگو حذف می‌شن بعد از:", "en": "My next messages in this chat disappear after:"},
    "ttl_off": {"fa": "خاموش", "en": "Off"},
    "ttl_10s": {"fa": "۱۰ ثانیه", "en": "10 seconds"},
    "ttl_1m": {"fa": "۱ دقیقه", "en": "1 minute"},
    "ttl_1h": {"fa": "۱ ساعت", "en": "1 hour"},
    "ttl_1d": {"fa": "۱ روز", "en": "1 day"},
    "ttl_placeholder_suffix": {"fa": "  \U0001F525 حذف خودکار بعد از {t}", "en": "  \U0001F525 auto-deletes after {t}"},
    "new_group_tooltip": {"fa": "گروه جدید", "en": "New group"},
    "new_group_title": {"fa": "گروه جدید", "en": "New group"},
    "group_name_label": {"fa": "نام گروه:", "en": "Group name:"},
    "group_desc_label": {"fa": "توضیحات (اختیاری):", "en": "Description (optional):"},
    "group_members_label": {"fa": "اعضا (از بین افراد آنلاین):", "en": "Members (from people online):"},
    "group_photo_btn": {"fa": "انتخاب عکس گروه...", "en": "Choose group photo..."},
    "group_create_btn": {"fa": "ساخت گروه", "en": "Create group"},
    "group_err_name": {"fa": "یه نام برای گروه وارد کنید.", "en": "Enter a name for the group."},
    "group_err_members": {"fa": "حداقل یک عضو انتخاب کنید.", "en": "Select at least one member."},
    "group_no_one_online": {"fa": "فعلاً کس دیگه‌ای آنلاین نیست.", "en": "Nobody else is online right now."},
    "group_info_tooltip": {"fa": "اطلاعات گروه", "en": "Group info"},
    "group_info_title": {"fa": "اطلاعات گروه", "en": "Group info"},
    "group_info_members": {"fa": "اعضا ({n}):", "en": "Members ({n}):"},
    "group_owner_tag": {"fa": " (مدیر)", "en": " (owner)"},
    "group_host_tag": {"fa": " (میزبان)", "en": " (host)"},
    "group_save_btn": {"fa": "ذخیره", "en": "Save"},
    "group_close_btn": {"fa": "بستن", "en": "Close"},
    "group_leave_btn": {"fa": "ترک گروه", "en": "Leave group"},
    "group_desc_placeholder": {"fa": "توضیحاتی برای گروه بنویسید...", "en": "Describe this group..."},
    "group_only_owner_edit": {"fa": "فقط مدیر گروه می‌تونه اینا رو تغییر بدهد.", "en": "Only the group owner can change these."},
    "group_only_host_edit": {"fa": "فقط میزبان می‌تونه توضیحات و عکس گروه اصلی رو تغییر بدهد.", "en": "Only the host can change the main group's description and photo."},
    "group_choose_photo_btn": {"fa": "تغییر عکس...", "en": "Change photo..."},
    "search_global_no_results": {"fa": "چیزی پیدا نشد", "en": "No results"},
    "extras_language_test_placeholder": {
        "fa": "تست زبان هنوز آماده نیست — به‌زودی اضافه می‌شه.",
        "en": "The language test isn't ready yet — coming soon.",
    },
}


def T(key):
    return STRINGS[key][CURRENT_LANG[0]]


class RoomRejected(Exception):
    """Raised on the client side when the host turns the join attempt down
    (wrong password, or the room is already full)."""
    pass


# ---------- Low level framing helpers (unchanged networking protocol) ----------

def send_framed(sock, data: bytes):
    sock.sendall(struct.pack(">I", len(data)) + data)


def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed")
        buf += chunk
    return buf


def recv_framed(sock):
    length_bytes = recv_exact(sock, 4)
    (length,) = struct.unpack(">I", length_bytes)
    return recv_exact(sock, length)


def send_json(sock, obj):
    send_framed(sock, json.dumps(obj).encode("utf-8"))


def recv_json(sock):
    return json.loads(recv_framed(sock).decode("utf-8"))


def get_local_ip():
    """آی‌پی این کامپیوتر رو توی شبکه محلی پیدا می‌کند (برای معرفی به بقیه)"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.3)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


# ---------- Color themes ----------
# Three selectable looks. Each theme supplies both the raw palette (used by
# the hand-painted chat bubbles) and a full Qt stylesheet for every normal
# widget, so switching themes re-skins the entire app, not just the bubbles.

THEMES = {
    "dark_modern": {
        "label": "تیره مدرن",
        "window_bg": "#15171c",
        "panel_bg": "#1c1f26",
        "card_bg": "#20242c",
        "border": "#2b2f3a",
        "fg": "#eef0f4",
        "muted_fg": "#8b93a7",
        "accent": "#6c8cff",
        "accent_hover": "#8aa2ff",
        "accent_text": "#ffffff",
        "entry_bg": "#262a33",
        "entry_fg": "#eef0f4",
        "entry_border": "#343a47",
        "own_bubble": "#6c8cff",
        "own_text": "#ffffff",
        "other_bubble": "#2a2e38",
        "other_text": "#eef0f4",
        "private_bubble": "#8a6d2f",
        "private_text": "#ffe9a8",
        "system_fg": "#6f7791",
        "danger": "#ff5d6c",
        "danger_hover": "#ff7883",
        "online_dot": "#39d98a",
        "sidebar_bg": "#191c22",
    },
    "light_clean": {
        "label": "روشن تمیز",
        "window_bg": "#f4f5f8",
        "panel_bg": "#ffffff",
        "card_bg": "#ffffff",
        "border": "#e4e7ee",
        "fg": "#1c2027",
        "muted_fg": "#848c9c",
        "accent": "#3a6df0",
        "accent_hover": "#5583f5",
        "accent_text": "#ffffff",
        "entry_bg": "#ffffff",
        "entry_fg": "#1c2027",
        "entry_border": "#d9deea",
        "own_bubble": "#3a6df0",
        "own_text": "#ffffff",
        "other_bubble": "#eef1f7",
        "other_text": "#1c2027",
        "private_bubble": "#fff1c2",
        "private_text": "#6b5200",
        "system_fg": "#9aa1b0",
        "danger": "#e23c3c",
        "danger_hover": "#ef5a5a",
        "online_dot": "#2ecc71",
        "sidebar_bg": "#f8f9fc",
    },
    "vivid": {
        "label": "رنگی",
        "window_bg": "#1a1330",
        "panel_bg": "#231a42",
        "card_bg": "#2a2050",
        "border": "#3c2d6b",
        "fg": "#f5f1ff",
        "muted_fg": "#b3a3e0",
        "accent": "#ff6fb5",
        "accent_hover": "#ff8ec4",
        "accent_text": "#1a1330",
        "entry_bg": "#2d2456",
        "entry_fg": "#f5f1ff",
        "entry_border": "#473a7d",
        "own_bubble": "#ff6fb5",
        "own_text": "#1a1330",
        "other_bubble": "#352a61",
        "other_text": "#f5f1ff",
        "private_bubble": "#ffb648",
        "private_text": "#3a2400",
        "system_fg": "#8f80c0",
        "danger": "#ff5468",
        "danger_hover": "#ff7284",
        "online_dot": "#4ee6a6",
        "sidebar_bg": "#1f1740",
    },
}

THEMES["nowruz"] = dict(
    THEMES["light_clean"], label="نوروزی \U0001F331", window_bg="#f3f8ee", panel_bg="#ffffff",
    card_bg="#ffffff", border="#d8e8cc", accent="#2f9e44", accent_hover="#40b457",
    own_bubble="#2f9e44", other_bubble="#e8f3dc", private_bubble="#ffe9a8", private_text="#6b5200",
    sidebar_bg="#eaf4e0", online_dot="#2f9e44",
)
THEMES["yalda"] = dict(
    THEMES["dark_modern"], label="شب یلدا \U0001F349", window_bg="#1c0f14", panel_bg="#26141b",
    card_bg="#301a23", border="#4a2634", accent="#e63950", accent_hover="#f0566b",
    entry_bg="#341d27", entry_border="#54303f", own_bubble="#c9283f", other_bubble="#38202a",
    private_bubble="#8a6d2f", sidebar_bg="#21121a", muted_fg="#b58a97", system_fg="#8f6a76",
)
THEMES["winter"] = dict(
    THEMES["light_clean"], label="زمستانی \u2744\uFE0F", window_bg="#eef4fb", panel_bg="#ffffff",
    card_bg="#ffffff", border="#d3e1f0", accent="#3b82c4", accent_hover="#5598d6",
    own_bubble="#3b82c4", other_bubble="#e1ecf8", sidebar_bg="#e6eef8",
)

DEFAULT_THEME = "dark_modern"

# Base point size for the app's default font; message bubbles and most
# plain labels inherit this (only a few sidebar labels have their own
# fixed CSS font-size and don't scale with it).
FONT_SIZES = {"small": 9, "medium": 10, "large": 12}

# UDP port used only for "is anyone hosting on this network?" broadcast
# discovery - separate from the TCP port the chat itself runs on.
DISCOVERY_PORT = 54777

# Files travel as a single JSON frame (no chunking), so this is a hard
# cap on what can be attached - raised from the original 8 MB to cover
# photos, documents and small video clips.
FILE_SIZE_CAP_MB = 100

# Base app font size in points; changed live from the drawer's Settings
# page (small/normal/large) and re-applied via build_stylesheet().
CURRENT_FONT_PT = [10.5]
FONT_SIZE_PRESETS = {"small": 9.0, "normal": 10.5, "large": 12.5}

# ---------------------------------------------------------------------
# Optional local chat history (off by default - a privacy choice, not a
# technical one). When turned on from Settings, every text message gets
# appended as one JSON line to a small per-conversation file under the
# user's home folder, and read back the first time that conversation is
# opened in a later run. Nothing here is encrypted at rest (unlike the
# network traffic): it's plain local storage, same as any chat app's
# local cache, so the Settings toggle and HOW_TO_RUN.md both say so.
APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".lan_chat_gui")
HISTORY_DIR = os.path.join(APP_DATA_DIR, "history")
APP_SETTINGS_PATH = os.path.join(APP_DATA_DIR, "settings.json")


def load_app_settings():
    try:
        with open(APP_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_app_settings(settings):
    try:
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        with open(APP_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False)
    except Exception:
        pass  # best-effort only - a failed save here shouldn't crash the chat


def hash_pin(pin, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), bytes.fromhex(salt_hex), 200000).hex()


def get_setting(key, default=None):
    return load_app_settings().get(key, default)


def set_setting(key, value):
    settings = load_app_settings()
    settings[key] = value
    save_app_settings(settings)


def system_prefers_dark():
    """True / False for the Windows (or OS) dark/light app setting, None if unknown."""
    try:
        scheme = QApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
    except Exception:
        pass
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return None


def occasion_theme_for_today():
    """A seasonal theme key for today's date, or None."""
    now = time.localtime()
    md = (now.tm_mon, now.tm_mday)
    if (3, 19) <= md <= (4, 3):
        return "nowruz"
    if (12, 20) <= md <= (12, 22):
        return "yalda"
    if md >= (12, 23) or md <= (1, 5):
        return "winter"
    return None


# Chat background presets: (id, color, Persian name, English name)
BG_PRESETS = [
    ("ocean", "#10202f", "اقیانوس", "Ocean"), ("forest", "#0f2a1f", "جنگل", "Forest"),
    ("wine", "#2a1020", "شراب", "Wine"), ("sand", "#2d2a10", "شن", "Sand"),
    ("charcoal", "#1a1a1a", "زغال", "Charcoal"), ("paper", "#f5efe0", "کاغذ", "Paper"),
]


def _safe_history_name(text):
    return re.sub(r"[^A-Za-z0-9_\-\u0600-\u06FF]+", "_", text)[:80] or "chat"


def history_file_path(my_name, chat_key):
    fname = f"{_safe_history_name(my_name)}__{_safe_history_name(chat_key)}.jsonl"
    return os.path.join(HISTORY_DIR, fname)


def append_history(my_name, chat_key, record):
    try:
        os.makedirs(HISTORY_DIR, exist_ok=True)
        with open(history_file_path(my_name, chat_key), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def load_history(my_name, chat_key, limit=300):
    path = history_file_path(my_name, chat_key)
    records = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return records[-limit:]


def build_stylesheet(t):
    """Build the full Qt stylesheet (QSS) for a theme dict."""
    return f"""
    QWidget {{
        background-color: {t['window_bg']};
        color: {t['fg']};
        font-family: "Segoe UI", "Vazirmatn", "Tahoma", sans-serif;
        font-size: {CURRENT_FONT_PT[0]}pt;
    }}
    QMainWindow {{
        background-color: {t['window_bg']};
    }}
    QFrame#card {{
        background-color: {t['card_bg']};
        border: 1px solid {t['border']};
        border-radius: 14px;
    }}
    QFrame#topBar {{
        background-color: {t['panel_bg']};
        border-bottom: 1px solid {t['border']};
    }}
    QFrame#sidebar {{
        background-color: {t['sidebar_bg']};
        border-right: 1px solid {t['border']};
    }}
    QFrame#composeBar {{
        background-color: {t['panel_bg']};
        border-top: 1px solid {t['border']};
    }}
    QLabel {{
        background-color: transparent;
        color: {t['fg']};
    }}
    QLabel#titleLabel {{
        font-size: 19pt;
        font-weight: 600;
        color: {t['fg']};
    }}
    QLabel#subtitleLabel {{
        color: {t['muted_fg']};
        font-size: 10pt;
    }}
    QLabel#mutedLabel {{
        color: {t['muted_fg']};
        font-size: 8.5pt;
    }}
    QLabel#roomLabel {{
        font-size: 11pt;
        font-weight: 600;
        color: {t['fg']};
    }}
    QLabel#chatRowTitle {{
        font-size: 10pt;
        font-weight: 600;
        color: {t['fg']};
    }}
    QToolButton#backButton {{
        background-color: transparent;
        color: {t['fg']};
        border: none;
        font-size: 18pt;
        font-weight: 700;
        padding: 0px 4px;
    }}
    QToolButton#backButton:hover {{
        color: {t['accent']};
    }}
    QLabel#fieldLabel {{
        color: {t['muted_fg']};
        font-size: 9.5pt;
    }}
    QLineEdit {{
        background-color: {t['entry_bg']};
        color: {t['entry_fg']};
        border: 1.5px solid {t['entry_border']};
        border-radius: 10px;
        padding: 9px 12px;
        selection-background-color: {t['accent']};
    }}
    QLineEdit:focus {{
        border: 1.5px solid {t['accent']};
    }}
    QTextEdit#messageEdit {{
        background-color: {t['entry_bg']};
        color: {t['entry_fg']};
        border: 1.5px solid {t['entry_border']};
        border-radius: 10px;
        padding: 7px 12px;
        selection-background-color: {t['accent']};
    }}
    QTextEdit#messageEdit:focus {{
        border: 1.5px solid {t['accent']};
    }}
    QComboBox {{
        background-color: {t['entry_bg']};
        color: {t['entry_fg']};
        border: 1.5px solid {t['entry_border']};
        border-radius: 10px;
        padding: 7px 10px;
        min-width: 110px;
    }}
    QComboBox:focus {{
        border: 1.5px solid {t['accent']};
    }}
    QComboBox QAbstractItemView {{
        background-color: {t['entry_bg']};
        color: {t['entry_fg']};
        selection-background-color: {t['accent']};
        selection-color: {t['accent_text']};
        border: 1px solid {t['entry_border']};
        outline: none;
    }}
    QPushButton#primaryButton {{
        background-color: {t['accent']};
        color: {t['accent_text']};
        border: none;
        border-radius: 11px;
        padding: 11px 18px;
        font-weight: 600;
        font-size: 11pt;
    }}
    QPushButton#primaryButton:hover {{
        background-color: {t['accent_hover']};
    }}
    QPushButton#primaryButton:disabled {{
        background-color: {t['border']};
        color: {t['muted_fg']};
    }}
    QPushButton#extraButton {{
        background-color: transparent;
        color: {t['muted_fg']};
        border: 1.5px solid {t['border']};
        border-radius: 10px;
        padding: 7px 14px;
        font-size: 9.5pt;
    }}
    QPushButton#extraButton:hover {{
        border: 1.5px solid {t['accent']};
        color: {t['accent']};
    }}
    QPushButton#sendButton {{
        background-color: {t['accent']};
        color: {t['accent_text']};
        border: none;
        border-radius: 19px;
        min-width: 38px;
        max-width: 38px;
        min-height: 38px;
        max-height: 38px;
        font-size: 14pt;
        padding-left: 2px;
    }}
    QPushButton#sendButton:hover {{
        background-color: {t['accent_hover']};
    }}
    QToolButton#hamburgerButton {{
        background-color: transparent;
        color: {t['fg']};
        border: none;
        border-radius: 8px;
        font-size: 14pt;
        padding: 4px 8px;
    }}
    QToolButton#hamburgerButton:hover {{
        background-color: {t['card_bg']};
    }}
    QToolButton#hamburgerButton::menu-indicator {{
        image: none;
    }}
    QMenu {{
        background-color: {t['card_bg']};
        color: {t['fg']};
        border: 1px solid {t['border']};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 7px 14px;
        border-radius: 7px;
    }}
    QMenu::item:selected {{
        background-color: {t['accent']};
        color: {t['accent_text']};
    }}
    QRadioButton {{
        color: {t['fg']};
        spacing: 8px;
        padding: 3px 0;
    }}
    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 8px;
        border: 2px solid {t['entry_border']};
        background-color: {t['entry_bg']};
    }}
    QRadioButton::indicator:checked {{
        border: 2px solid {t['accent']};
        background-color: {t['accent']};
    }}
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {t['border']};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t['muted_fg']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QProgressBar {{
        background-color: {t['border']};
        border: none;
        border-radius: 3px;
    }}
    QProgressBar::chunk {{
        background-color: {t['accent']};
        border-radius: 3px;
    }}
    QFrame#sideDrawer {{
        background-color: {t['panel_bg']};
        border-right: 1px solid {t['border']};
    }}
    QWidget#drawerOverlay {{
        background-color: rgba(0, 0, 0, 110);
    }}
    QFrame#drawerProfile {{
        background-color: {t['card_bg']};
    }}
    QLabel#drawerName {{
        font-size: 12pt;
        font-weight: 600;
        color: {t['fg']};
    }}
    QFrame#drawerRow {{
        background-color: transparent;
        border-radius: 8px;
    }}
    QFrame#drawerRow:hover {{
        background-color: {t['card_bg']};
    }}
    QLabel#drawerRowLabel {{
        font-size: 10.5pt;
        color: {t['fg']};
    }}
    QLabel#drawerSectionLabel {{
        font-size: 9pt;
        color: {t['accent']};
        font-weight: 600;
    }}
    QLabel#drawerCheck {{
        color: {t['accent']};
        font-size: 11pt;
        font-weight: 700;
    }}
    QToolButton#drawerBackButton {{
        background-color: transparent;
        color: {t['fg']};
        border: none;
        font-size: 16pt;
        font-weight: 700;
    }}
    QToolButton#drawerBackButton:hover {{
        color: {t['accent']};
    }}
    QLabel[searchHit="true"], QLabel[picked="true"] {{
        border: 2px solid {t['accent']};
        border-radius: 16px;
    }}
    QLabel#unreadBadge {{
        background-color: {t['accent']};
        color: #ffffff;
        font-size: 7.5pt;
        font-weight: 700;
        border-radius: 8px;
        min-width: 16px;
        max-height: 16px;
        padding: 1px 5px;
    }}
    QLabel#readTick {{
        font-size: 8pt;
        background: transparent;
    }}
    QWidget#chatListRowContent {{
        background: transparent;
    }}
    QWidget#chatRowActions {{
        background-color: #b5568f;
        border-radius: 8px;
    }}
    QToolButton#chatRowActionBtn {{
        background: transparent;
        border: none;
        color: #ffffff;
        font-size: 15pt;
        padding: 2px 6px;
    }}
    QToolButton#chatRowActionBtn:hover {{
        background-color: rgba(255, 255, 255, 40);
        border-radius: 6px;
    }}
    QToolButton#reactionChip {{
        background-color: {t['card_bg']};
        border: 1px solid {t['border']};
        border-radius: 11px;
        padding: 1px 7px;
        font-size: 9.5pt;
    }}
    QToolButton#reactionChip:hover {{
        border-color: {t['accent']};
    }}
    QToolButton#reactionChipMine {{
        background-color: {t['accent']};
        border: 1px solid {t['accent']};
        border-radius: 11px;
        padding: 1px 7px;
        font-size: 9.5pt;
        color: #ffffff;
    }}
    QPushButton#emptyStateCard {{
        background-color: {t['card_bg']};
        color: {t['fg']};
        border: 1.5px solid {t['border']};
        border-radius: 14px;
        padding: 14px 22px;
        font-size: 10.5pt;
        font-weight: 600;
    }}
    QPushButton#emptyStateCard:hover {{
        border: 1.5px solid {t['accent']};
        color: {t['accent']};
    }}
    QFrame#fileCard {{
        background-color: {t['card_bg']};
        border: 1px solid {t['border']};
        border-radius: 12px;
        padding: 8px;
    }}
    QLabel#replyQuote {{
        border-left: 3px solid {t['accent']};
        background-color: {t['card_bg']};
        color: {t['muted_fg']};
        font-size: 9pt;
        padding: 3px 8px;
        border-radius: 4px;
    }}
    QFrame#pinBanner {{
        background-color: {t['card_bg']};
        border-bottom: 1px solid {t['border']};
    }}
    QLabel#pinBannerLabel {{
        color: {t['fg']};
        font-size: 9.5pt;
    }}
    QFrame#composeBanner {{
        background-color: {t['card_bg']};
        border-top: 1px solid {t['border']};
    }}
    QLabel#composeBannerLabel {{
        color: {t['accent']};
        font-size: 9pt;
        font-weight: 600;
    }}
    QListWidget#discoverList, QListWidget#searchResults {{
        background-color: {t['entry_bg']};
        color: {t['entry_fg']};
        border: 1.5px solid {t['entry_border']};
        border-radius: 10px;
        padding: 4px;
    }}
    QListWidget#discoverList::item, QListWidget#searchResults::item {{
        padding: 7px 8px;
        border-radius: 6px;
    }}
    QListWidget#discoverList::item:selected, QListWidget#searchResults::item:selected {{
        background-color: {t['accent']};
        color: #ffffff;
    }}
    QLabel#linkLabel {{
        color: {t['accent']};
        font-size: 9pt;
    }}
    QLabel#reconnectBanner {{
        background-color: {t['accent']};
        color: #ffffff;
        font-size: 9pt;
        font-weight: 600;
        padding: 6px 0px;
    }}
    """


# ---------- Custom painted widgets ----------

# A small, fixed picker of common reactions - like WhatsApp/Telegram's
# quick-react row - rather than a full emoji keyboard, to keep this simple.
REACTION_EMOJIS = ["\U0001F44D", "\u2764\uFE0F", "\U0001F602", "\U0001F62E", "\U0001F622", "\U0001F64F"]


class BubbleLabel(QLabel):
    """A chat bubble with properly rounded corners, drawn by hand so it
    looks crisp instead of relying on stylesheet border-radius on a QLabel
    (which clips text oddly with wordwrap in Qt)."""

    reply_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    forward_requested = pyqtSignal(str)
    pin_requested = pyqtSignal(str)
    react_requested = pyqtSignal(str, str)  # msg_id, emoji
    select_requested = pyqtSignal(str)
    star_requested = pyqtSignal(str)
    translate_requested = pyqtSignal(str)
    tag_requested = pyqtSignal(str)
    remind_requested = pyqtSignal(str, int)
    select_toggled = pyqtSignal(str)

    def __init__(self, text, bg_color, fg_color, mention_names=None,
                 msg_id=None, is_own=False, parent=None, sticker=False):
        super().__init__(parent)
        self.sticker = sticker
        self.select_mode = False
        self.raw_text = text
        self.mention_names = list(mention_names or [])
        self.bg_color = QColor(bg_color)
        self.fg_color = fg_color
        self.msg_id = msg_id
        self.is_own = is_own
        self.is_deleted = False
        self.is_edited = False
        self.setWordWrap(True)
        self.setContentsMargins(14, 9, 14, 9)
        self.setMaximumWidth(420)
        self.setStyleSheet(f"color: {fg_color}; background: transparent;")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setOpenExternalLinks(True)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self._apply_rich_text(fg_color, mention_names or [])

    def _apply_rich_text(self, fg_color, mention_names):
        if self.sticker and not self.is_deleted:
            self.setText(f'<span style="font-size:38pt;">{html.escape(self.raw_text)}</span>')
            return
        if self.is_deleted:
            body = f'<i style="opacity:0.75;">{html.escape(self.raw_text)}</i>'
        else:
            body = to_rich_text(self.raw_text, fg_color, mention_names)
            if self.is_edited:
                body += f' <span style="font-size:8pt; opacity:0.7;">{html.escape(T("edited_suffix"))}</span>'
        self.setText(body)

    def set_colors(self, bg_color, fg_color):
        self.bg_color = QColor(bg_color)
        self.fg_color = fg_color
        self.setStyleSheet(f"color: {fg_color}; background: transparent;")
        self._apply_rich_text(fg_color, self.mention_names)
        self.update()

    def mark_edited(self, new_text):
        self.raw_text = new_text
        self.is_edited = True
        self._apply_rich_text(self.fg_color, self.mention_names)

    def mark_deleted(self):
        self.raw_text = T("deleted_placeholder")
        self.is_deleted = True
        self._apply_rich_text(self.fg_color, self.mention_names)

    def set_capsule(self, until, real_text):
        """Time capsule: show a lock instead of the text until `until`."""
        self._capsule_real = real_text
        self._capsule_until = until
        self.raw_text = T("capsule_locked").format(
            when=time.strftime("%Y-%m-%d %H:%M", time.localtime(until))
        )
        self._apply_rich_text(self.fg_color, self.mention_names)
        self._schedule_reveal()

    def _schedule_reveal(self):
        ms = int(max(0.0, self._capsule_until - time.time()) * 1000) + 300
        QTimer.singleShot(min(ms, 2 ** 31 - 1), self._reveal_capsule)

    def _reveal_capsule(self):
        try:
            if time.time() < self._capsule_until:
                self._schedule_reveal()   # longer than one timer can wait: check again later
                return
            self.raw_text = self._capsule_real
            self._apply_rich_text(self.fg_color, self.mention_names)
        except RuntimeError:
            pass  # message deleted meanwhile

    def text(self):
        # Overridden so copy/search see the original plain message, not
        # the HTML we render links and @mentions with.
        return self.raw_text

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), 16.0, 16.0)
        if not self.sticker:
            painter.fillPath(path, self.bg_color)
        painter.end()
        super().paintEvent(event)

    def mousePressEvent(self, event):
        if self.select_mode and self.msg_id and event.button() == Qt.MouseButton.LeftButton:
            self.select_toggled.emit(self.msg_id)
            return
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        if self.is_deleted or not self.msg_id:
            return
        menu = QMenu(self)
        select_action = menu.addAction(T("ctx_select"))
        star_action = menu.addAction(T("ctx_star"))
        translate_action = menu.addAction(T("ctx_translate"))
        tag_action = menu.addAction(T("ctx_tag"))
        remind_menu = menu.addMenu(T("ctx_remind"))
        remind_actions = {remind_menu.addAction(T("remind_min").format(n=n)): n for n in (10, 30, 60)}
        copy_action = menu.addAction(T("ctx_copy"))
        reply_action = menu.addAction(T("ctx_reply"))
        forward_action = menu.addAction(T("ctx_forward"))
        pin_action = menu.addAction(T("ctx_pin"))
        react_menu = menu.addMenu(T("ctx_react"))
        emoji_actions = {}
        for emo in REACTION_EMOJIS:
            a = react_menu.addAction(emo)
            emoji_actions[a] = emo
        edit_action = menu.addAction(T("ctx_edit")) if self.is_own else None
        delete_action = menu.addAction(T("ctx_delete")) if self.is_own else None
        chosen = menu.exec(event.globalPos())
        if chosen == copy_action:
            QApplication.clipboard().setText(self.raw_text)
        elif chosen == tag_action:
            self.tag_requested.emit(self.msg_id)
        elif chosen in remind_actions:
            self.remind_requested.emit(self.msg_id, remind_actions[chosen])
        elif chosen == translate_action:
            self.translate_requested.emit(self.msg_id)
        elif chosen == star_action:
            self.star_requested.emit(self.msg_id)
        elif chosen == select_action:
            self.select_requested.emit(self.msg_id)
        elif chosen == reply_action:
            self.reply_requested.emit(self.msg_id)
        elif chosen == forward_action:
            self.forward_requested.emit(self.msg_id)
        elif chosen == pin_action:
            self.pin_requested.emit(self.msg_id)
        elif chosen in emoji_actions:
            self.react_requested.emit(self.msg_id, emoji_actions[chosen])
        elif edit_action is not None and chosen == edit_action:
            self.edit_requested.emit(self.msg_id)
        elif delete_action is not None and chosen == delete_action:
            self.delete_requested.emit(self.msg_id)


# Fixed, theme-independent palette used to color each person's avatar circle
# (the same idea Telegram uses for contacts with no profile photo).
AVATAR_COLORS = ["#e17076", "#eda86c", "#a695e7", "#7bc862", "#6ec9cb", "#65aadd", "#ee7aae"]
GROUP_AVATAR_COLOR = "#5b8def"
STATUS_COLORS = {"online": "#3ddc84", "busy": "#e05a5a", "away": "#f0ad4e"}


def avatar_color_for(name):
    return AVATAR_COLORS[sum(ord(c) for c in name) % len(AVATAR_COLORS)]


URL_RE = re.compile(r'(https?://[^\s<>"]+)')


def _format_inline(escaped):
    """Tiny Markdown-ish formatting applied to already-HTML-escaped text:
    `code`, **bold**, *italic*, ~~strike~~."""
    codes = []

    def stash(m):
        codes.append(m.group(1))
        return "\x00%d\x00" % (len(codes) - 1)

    t = re.sub(r"`([^`\n]+)`", stash, escaped)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"~~(.+?)~~", r"<s>\1</s>", t)
    return re.sub(
        "\x00(\\d+)\x00",
        lambda m: '<span style="font-family:Consolas,monospace; background-color:rgba(127,127,127,70);">'
                  '&nbsp;' + codes[int(m.group(1))] + '&nbsp;</span>',
        t,
    )


def to_rich_text(text, fg_color, mention_names):
    """Turn a plain chat message into the small bit of HTML QLabel needs to
    make http(s) links clickable, highlight @mentions of known member
    names and apply the simple inline formatting - everything else is
    escaped/plain."""
    segments = []
    pos = 0
    for m in URL_RE.finditer(text):
        if m.start() > pos:
            segments.append(("text", text[pos:m.start()]))
        segments.append(("url", m.group(1)))
        pos = m.end()
    if pos < len(text):
        segments.append(("text", text[pos:]))

    names = sorted({n for n in mention_names if n}, key=len, reverse=True)
    mention_re = re.compile(
        r'@(' + '|'.join(re.escape(n) for n in names) + r')\b'
    ) if names else None

    html_parts = []
    for kind, chunk in segments:
        if kind == "url":
            safe = html.escape(chunk, quote=True)
            html_parts.append(f'<a href="{safe}" style="color:{fg_color};">{safe}</a>')
            continue
        parts = []
        if mention_re:
            p = 0
            for mm in mention_re.finditer(chunk):
                parts.append(html.escape(chunk[p:mm.start()]))
                parts.append(
                    f'<span style="font-weight:700; text-decoration: underline;">'
                    f'@{html.escape(mm.group(1))}</span>'
                )
                p = mm.end()
            parts.append(html.escape(chunk[p:]))
        else:
            parts.append(html.escape(chunk))
        html_parts.append(_format_inline("".join(parts)))
    return "".join(html_parts).replace("\n", "<br>")


class TranslateWorker(QObject):
    """Translates one message with the free MyMemory API (internet needed)."""
    ready = pyqtSignal(object, str)

    def __init__(self, label, text, src, tgt):
        super().__init__()
        self.label, self.text, self.src, self.tgt = label, text, src, tgt

    def run(self):
        try:
            url = ("https://api.mymemory.translated.net/get?q=" + urllib.parse.quote(self.text[:480])
                   + f"&langpair={self.src}|{self.tgt}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            out = html.unescape(data["responseData"]["translatedText"])
            self.ready.emit(self.label, "\U0001F310 " + out)
        except Exception as e:
            self.ready.emit(self.label, "\U0001F310 \u26A0 " + str(e)[:80])


class LinkPreviewWorker(QObject):
    """Fetches a page's title/description on a background thread (opt-in:
    this contacts the linked website from your computer)."""
    ready = pyqtSignal(object, str)

    def __init__(self, label, url):
        super().__init__()
        self.label = label
        self.url = url

    def run(self):
        try:
            if not self.url.lower().startswith(("http://", "https://")):
                return
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                if "html" not in resp.headers.get("Content-Type", "").lower():
                    return
                raw = resp.read(200000)
            page = raw.decode("utf-8", errors="ignore")
            title = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
            desc = re.search(
                r'<meta[^>]+(?:property|name)=["\'](?:og:description|description)["\'][^>]*content=["\']([^"\']*)',
                page, re.I,
            )
            host = urllib.parse.urlparse(self.url).netloc
            lines = ["\U0001F517 " + host]
            if title:
                lines.append(html.unescape(" ".join(title.group(1).split()))[:120])
            if desc:
                lines.append(html.unescape(" ".join(desc.group(1).split()))[:160])
            if len(lines) > 1:
                self.ready.emit(self.label, "\n".join(lines))
        except Exception:
            pass


def compute_safety_number(pem_a: bytes, pem_b: bytes) -> str:
    """A Signal-style 'safety number': a fingerprint of both sides' public
    keys that both people can read aloud or compare side by side to be
    sure no one is relaying/tampering with the connection between them.
    Order-independent (sorting first) so both sides compute the same
    string regardless of who is 'self' and who is 'them'."""
    combined = b"||".join(sorted([pem_a, pem_b]))
    digest = hashlib.sha256(combined).hexdigest().upper()
    groups = [digest[i:i + 5] for i in range(0, 40, 5)]
    return " ".join(groups)


def pixmap_from_b64(b64_text):
    """Decode an optional base64 PNG avatar into a QPixmap, or None if
    there isn't one / it fails to decode."""
    if not b64_text:
        return None
    try:
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(b64_text))
        return pixmap if not pixmap.isNull() else None
    except Exception:
        return None


def group_color(gid):
    return AVATAR_COLORS[sum(ord(c) for c in gid) % len(AVATAR_COLORS)]


def choose_avatar_b64(parent):
    """Ask for an image file, shrink it to 128x128 and return
    (QPixmap, base64 PNG) - or None if cancelled / unreadable."""
    path, _ = QFileDialog.getOpenFileName(
        parent, T("connect_pick_avatar_title"), "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
    )
    if not path:
        return None
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return None
    pixmap = pixmap.scaled(
        128, 128, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    buf = QByteArray()
    qbuf = QBuffer(buf)
    qbuf.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(qbuf, "PNG")
    return pixmap, base64.b64encode(bytes(buf)).decode("ascii")


class AvatarLabel(QLabel):
    """A small circular avatar, hand-painted so it stays crisp at any size
    (used both in the sidebar chat list and in the chat header). Shows
    whichever of these the caller last set:
    - a real picture (set_image), clipped to a circle, if the person chose
      a profile picture when they connected;
    - otherwise a colored circle with one initial letter;
    - or, if text is empty, just a plain colored circle with no letter at
      all (used for the group's default avatar, left intentionally blank)."""

    def __init__(self, text, color, size=36, parent=None):
        super().__init__(parent)
        self.bg_color = QColor(color)
        self.initial = text[:1].upper() if text else ""
        self.pixmap_img = None
        self.setFixedSize(size, size)

    def set_identity(self, text, color):
        self.pixmap_img = None
        self.bg_color = QColor(color)
        self.initial = text[:1].upper() if text else ""
        self.update()

    def set_image(self, pixmap):
        """Show a real picture instead of the colored-circle/letter avatar.
        Pass None to go back to the colored-circle/letter look."""
        self.pixmap_img = pixmap
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.pixmap_img is not None and not self.pixmap_img.isNull():
            path = QPainterPath()
            path.addEllipse(0, 0, self.width(), self.height())
            painter.setClipPath(path)
            scaled = self.pixmap_img.scaled(
                self.width(), self.height(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(-x, -y, scaled)
            painter.end()
            return
        painter.setBrush(self.bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, self.width(), self.height())
        if self.initial:
            painter.setPen(QColor("#ffffff"))
            font = QFont("Segoe UI", max(8, int(self.height() * 0.4)))
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.initial)
        painter.end()


class ToggleSwitch(QWidget):
    """A real sliding on/off switch, hand-painted and animated, the way
    Telegram's own day/night switch works - not a checkbox pretending to
    be one."""

    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, on_color="#6c8cff", parent=None):
        super().__init__(parent)
        self._checked = checked
        self._slide = 1.0 if checked else 0.0
        self._on_color = QColor(on_color)
        self._off_color = QColor("#5a6472")
        self.setFixedSize(42, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"slide", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked, animate=True, emit=False):
        checked = bool(checked)
        target = 1.0 if checked else 0.0
        self._checked = checked
        self._anim.stop()
        if animate:
            self._anim.setStartValue(self._slide)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._slide = target
            self.update()
        if emit:
            self.toggled.emit(checked)

    def set_on_color(self, color):
        self._on_color = QColor(color)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked, animate=True, emit=True)
        super().mousePressEvent(event)

    def getSlide(self):
        return self._slide

    def setSlide(self, value):
        self._slide = value
        self.update()

    slide = pyqtProperty(float, getSlide, setSlide)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        r = self._off_color.red() + (self._on_color.red() - self._off_color.red()) * self._slide
        g = self._off_color.green() + (self._on_color.green() - self._off_color.green()) * self._slide
        b = self._off_color.blue() + (self._on_color.blue() - self._off_color.blue()) * self._slide
        painter.setBrush(QColor(int(r), int(g), int(b)))
        painter.drawRoundedRect(0, 0, self.width(), self.height(),
                                 self.height() / 2, self.height() / 2)
        knob_d = self.height() - 4
        x = 2 + self._slide * (self.width() - knob_d - 4)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QRectF(x, 2, knob_d, knob_d))
        painter.end()


class DrawerOverlay(QWidget):
    """The dimmed backdrop behind the slide-in drawer; clicking anywhere on
    it closes the drawer, same as tapping outside Telegram's own menu."""
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class DrawerRow(QFrame):
    """One clickable row inside the slide-in hamburger drawer: a label and
    an optional thing on the right (a chevron to drill into a sub-page, a
    checkmark, or a real ToggleSwitch) - click-to-activate only, no hover
    auto-expansion anywhere."""
    clicked = pyqtSignal()

    def __init__(self, text, right_widget=None, chevron=False, parent=None):
        super().__init__(parent)
        self.setObjectName("drawerRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 11, 16, 11)
        layout.setSpacing(10)
        self.label = QLabel(text)
        self.label.setObjectName("drawerRowLabel")
        layout.addWidget(self.label)
        layout.addStretch(1)
        self.check_label = None
        if right_widget is not None:
            layout.addWidget(right_widget)
        elif chevron:
            chevron_lbl = QLabel("\u2039")
            chevron_lbl.setStyleSheet("background: transparent; font-size: 13pt;")
            layout.addWidget(chevron_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ComposeTextEdit(QTextEdit):
    """The message compose box: Enter sends, Shift+Enter inserts a newline,
    and the box grows a little as you type more lines (up to a cap)."""

    send_triggered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("messageEdit")
        self.setAcceptRichText(False)
        self.setTabChangesFocus(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFixedHeight(40)
        self.document().contentsChanged.connect(self._auto_resize)

    def _auto_resize(self):
        doc_h = self.document().size().height()
        self.setFixedHeight(int(min(max(doc_h + 16, 40), 110)))

    def _wrap_selection(self, marker):
        cursor = self.textCursor()
        selected = cursor.selectedText()
        if selected:
            cursor.insertText(marker + selected + marker)
        else:
            cursor.insertText(marker * 2)
            cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.MoveAnchor, len(marker))
        self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            marker = {Qt.Key.Key_B: "**", Qt.Key.Key_I: "*", Qt.Key.Key_E: "`"}.get(event.key())
            if marker:
                self._wrap_selection(marker)
                return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.send_triggered.emit()
            return
        super().keyPressEvent(event)

    def text(self):
        return self.toPlainText()

    def clear(self):
        super().clear()
        self.setFixedHeight(40)


class ChatListRow(QFrame):
    """One row in the Telegram-style chat list on the left: an avatar, a
    title line (with an online dot and a host/member badge for members),
    and a second line showing either the last message preview or a
    "typing..." notice. Used for the pinned Group row, the pinned Saved
    Messages row, and one row per online member.

    Click behaviour is intentionally the opposite of the usual web
    convention, per how this project's owner wants it: a left click on a
    member opens the kick/mute menu, a right click opens the private chat
    with them. (The Group and Saved Messages rows just open on either
    click, since they have no such menu.)"""

    ACTION_PANEL_WIDTH = 104
    DRAG_THRESHOLD = 6

    def __init__(self, key, avatar_text, avatar_color, title, subtitle,
                 clickable, show_status, role_badge, role_color,
                 on_left_click, on_right_click, theme, avatar_image=None,
                 status="online", parent=None, on_pin_toggle=None,
                 on_read_toggle=None):
        super().__init__(parent)
        self.key = key
        self.clickable = clickable
        self.on_left_click = on_left_click
        self.on_right_click = on_right_click
        self.on_pin_toggle = on_pin_toggle
        self.on_read_toggle = on_read_toggle
        self.theme = theme
        self.setObjectName("chatListRow")
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if clickable else Qt.CursorShape.ArrowCursor
        )

        # Swipe-to-reveal: self._actions is a REAL item in self's own
        # QHBoxLayout, docked after self._content, starting at width 0 (so
        # it takes no space and is fully hidden). Dragging/animating just
        # changes its fixed width - the layout then automatically shrinks
        # self._content to make room, which is what produces the
        # "sliding left" look. This (rather than manually positioning
        # overlapping widgets with setGeometry/raise_) is what keeps it
        # from ever being stuck half-open or painted in the wrong place.
        self._drag_start_x = None
        self._drag_start_width = 0
        self._dragging = False
        self._open = False
        self._anim = None

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._content = QWidget(self)
        self._content.setObjectName("chatListRowContent")
        layout = QHBoxLayout(self._content)
        layout.setContentsMargins(10, 7, 8, 7)
        layout.setSpacing(10)

        self.avatar = AvatarLabel(avatar_text, avatar_color, size=38)
        if avatar_image is not None:
            self.avatar.set_image(avatar_image)
        layout.addWidget(self.avatar)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("chatRowTitle")
        top_row.addWidget(title_lbl)
        top_row.addStretch(1)
        self.status_dot = None
        if show_status:
            self.status_dot = QLabel("\u25cf")
            top_row.addWidget(self.status_dot)
            self.set_status(status)
        self.ping_lbl = QLabel("")
        self.ping_lbl.setStyleSheet(
            f"color: {theme['muted_fg']}; font-size: 7.5pt; background: transparent;"
        )
        self.ping_lbl.setVisible(False)
        top_row.addWidget(self.ping_lbl)
        if role_badge:
            role_lbl = QLabel(role_badge)
            role_lbl.setStyleSheet(
                f"color: {role_color}; font-size: 8pt; font-weight: 600; background: transparent;"
            )
            top_row.addWidget(role_lbl)
        text_col.addLayout(top_row)

        self.subtitle_lbl = QLabel("")
        self.subtitle_lbl.setWordWrap(False)
        text_col.addWidget(self.subtitle_lbl)
        self.set_subtitle(subtitle)

        layout.addLayout(text_col, stretch=1)

        self.badge_lbl = QLabel("")
        self.badge_lbl.setObjectName("unreadBadge")
        self.badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge_lbl.setVisible(False)
        layout.addWidget(self.badge_lbl)

        main_layout.addWidget(self._content, 1)

        self._actions = QWidget(self)
        self._actions.setObjectName("chatRowActions")
        self._actions.setFixedWidth(0)
        actions_layout = QHBoxLayout(self._actions)
        actions_layout.setContentsMargins(4, 6, 8, 6)
        actions_layout.setSpacing(2)
        self.pin_btn = QToolButton(self._actions)
        self.pin_btn.setObjectName("chatRowActionBtn")
        self.pin_btn.setText("\U0001F4CC")
        self.pin_btn.setToolTip(T("chat_row_action_pin"))
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.clicked.connect(self._on_pin_clicked)
        actions_layout.addWidget(self.pin_btn)
        self.read_btn = QToolButton(self._actions)
        self.read_btn.setObjectName("chatRowActionBtn")
        self.read_btn.setText("\U0001F441")
        self.read_btn.setToolTip(T("chat_row_action_read"))
        self.read_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.read_btn.clicked.connect(self._on_read_clicked)
        actions_layout.addWidget(self.read_btn)
        main_layout.addWidget(self._actions, 0)

        self.set_selected(False)

    def _animate_panel_to(self, target_w):
        anim = QVariantAnimation(self)
        anim.setDuration(150)
        anim.setStartValue(float(self._actions.width()))
        anim.setEndValue(float(target_w))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(lambda v: self._actions.setFixedWidth(int(v)))
        anim.start()
        self._anim = anim  # keep a reference so it isn't garbage-collected mid-animation

    def close_swipe(self):
        if self._open:
            self._open = False
            self._animate_panel_to(0)

    def _on_pin_clicked(self):
        self.close_swipe()
        if self.on_pin_toggle:
            self.on_pin_toggle(self.key)

    def _on_read_clicked(self):
        self.close_swipe()
        if self.on_read_toggle:
            self.on_read_toggle(self.key)

    def set_status(self, status):
        if self.status_dot is None:
            return
        color = STATUS_COLORS.get(status, STATUS_COLORS["online"])
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 8pt; background: transparent;")

    def set_ping(self, ms):
        if ms is None:
            self.ping_lbl.setVisible(False)
        else:
            self.ping_lbl.setText(T("ping_ms").format(ms=ms))
            self.ping_lbl.setVisible(True)

    def set_badge(self, count):
        if count and count > 0:
            self.badge_lbl.setText(str(count) if count < 100 else "99+")
            self.badge_lbl.setVisible(True)
        else:
            self.badge_lbl.setVisible(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            if self.clickable:
                self.on_right_click(self.key, event.globalPosition().toPoint())
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_x = event.position().x()
            self._drag_start_width = self._actions.width()
            self._dragging = False

    def mouseMoveEvent(self, event):
        if self._drag_start_x is None:
            return
        dx = event.position().x() - self._drag_start_x
        if not self._dragging and abs(dx) > self.DRAG_THRESHOLD:
            self._dragging = True
        if self._dragging:
            # Dragging left (negative dx) widens the actions panel.
            new_w = self._drag_start_width - dx
            new_w = max(0, min(self.ACTION_PANEL_WIDTH, new_w))
            self._actions.setFixedWidth(int(new_w))

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        was_dragging = self._dragging
        had_start = self._drag_start_x is not None
        self._dragging = False
        self._drag_start_x = None
        if was_dragging:
            self._open = self._actions.width() > self.ACTION_PANEL_WIDTH / 2
            self._animate_panel_to(self.ACTION_PANEL_WIDTH if self._open else 0)
            return
        if self._open:
            # Tapping the row while it's swiped open just closes it again,
            # same as Telegram, instead of opening the chat underneath.
            self.close_swipe()
            return
        if self.clickable and had_start:
            self.on_left_click(self.key, event.globalPosition().toPoint())

    def set_subtitle(self, text, emphasize=False):
        self.subtitle_lbl.setText(text)
        lines = max(1, min(3, CHAT_LIST_LINES[0]))
        self.subtitle_lbl.setWordWrap(lines > 1)
        self.subtitle_lbl.setMaximumHeight(15 * lines if lines > 1 else 16777215)
        if emphasize:
            self.subtitle_lbl.setStyleSheet(
                f"color: {self.theme['accent']}; font-size: 8.5pt; "
                f"font-style: italic; background: transparent;"
            )
        else:
            self.subtitle_lbl.setStyleSheet(
                f"color: {self.theme['muted_fg']}; font-size: 8.5pt; background: transparent;"
            )

    def set_selected(self, selected):
        if selected:
            self.setStyleSheet(
                f"QFrame#chatListRow {{ background-color: {self.theme['card_bg']}; "
                f"border-right: 3px solid {self.theme['accent']}; border-radius: 8px; }}"
            )
        else:
            self.setStyleSheet(
                "QFrame#chatListRow { background-color: transparent; border-radius: 8px; }"
            )


# ---------- Networking backend ----------
# This mirrors the exact same wire protocol as before (unchanged: hello /
# peer_list / new_peer / peer_left / message / kicked / auth_failed /
# room_full), just reporting back to the GUI through Qt signals instead of
# a polled queue, since that is the correct thread-safe pattern in Qt.

class ChatBackend(QObject):
    status = pyqtSignal(str)
    switch_to_chat = pyqtSignal()
    message_received = pyqtSignal(str, dict, bool)  # sender, content envelope, is_private
    message_edited = pyqtSignal(str, str)           # msg_id, new text
    message_deleted = pyqtSignal(str)                # msg_id
    message_reacted = pyqtSignal(str, str, str, str)  # from_name, msg_id, emoji, action
    pin_updated = pyqtSignal(bool, str, object)      # is_private, from, content dict or None
    ping_updated = pyqtSignal(str, int)              # peer name, round-trip time in ms
    file_received = pyqtSignal(str, dict, bool)      # sender, file content dict, is_private
    system_message = pyqtSignal(str)
    refresh_members = pyqtSignal()
    error = pyqtSignal(str)
    kicked = pyqtSignal()
    connect_failed = pyqtSignal(str)
    typing_received = pyqtSignal(str, bool, str)  # sender, is_private, group id ('' if none)
    message_seen = pyqtSignal(str)  # peer who just told us they saw our messages
    reconnect_status = pyqtSignal(str)  # "start" | "new_host" | "done"
    group_event = pyqtSignal(str, dict)  # sender, {action: create/update/leave, gid, ...}
    main_group_info_updated = pyqtSignal(str, str)  # description, avatar (base64 PNG)
    envelope_received = pyqtSignal(str, str, bool, dict)  # kind, sender, is_private, content
    roles_updated = pyqtSignal(list)  # names of admins
    guests_updated = pyqtSignal(list)  # names of temporary guests (host only)
    join_request = pyqtSignal(str, str)  # name, token (host waiting room)

    def __init__(self):
        super().__init__()
        self.private_key, self.public_key = generate_keypair()
        self.my_name = "Me"
        self.my_avatar = ""  # base64 PNG, optional
        self.my_status = "online"  # "online" | "busy" | "away"
        self.my_bio = ""      # free-text status line
        self.admins = set()   # members the host promoted to admin (can remove people)
        self.guests = {}      # host only: name -> threading.Timer that removes the guest
        self.waiting_room = False   # host only: new joiners need the host's OK
        self._join_decisions = {}
        self.peer_bios = {}   # name -> their free-text status line
        self.peer_ping = {}  # name -> last round-trip time in ms
        self._ping_thread_started = False
        self.my_ip = get_local_ip()
        self.is_host = True
        self.running = False
        self.port = 5000

        # Host-only
        self.server_sock = None
        self.discovery_sock = None
        self.kicked_names = set()

        # Client-only
        self.host_conn = None
        self.host_name = None
        self.was_kicked = False
        self.join_password = ""

        # Room rules (set by whoever is hosting; carried along to the next
        # host too, in case of a failover, so they keep being enforced)
        self.room_password_hash = ""
        self.max_members = 0
        # Description / picture of the main (everyone) group; set by the
        # host, handed to every new joiner in the peer_list packet.
        self.main_group_info = {"desc": "", "avatar": ""}

        # peers: name -> {"pubkey": <key obj>, "ip": str, "conn": <socket or None>}
        self.peers = {}
        self.peers_lock = threading.Lock()

    # ----- Host side: accept any number of computers -----

    def run_host(self, port):
        bound = False
        last_error = None
        for attempt in range(10):
            try:
                self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_sock.bind(("0.0.0.0", port))
                self.server_sock.listen(8)
                bound = True
                break
            except OSError as e:
                last_error = e
                try:
                    self.server_sock.close()
                except Exception:
                    pass
                self.server_sock = None
                time.sleep(0.5)
        if not bound:
            self.error.emit(T("err_failed_host").format(error=last_error))
            return

        self.running = True
        self.status.emit(T("status_hosting").format(port=port))
        self.switch_to_chat.emit()
        threading.Thread(target=self._run_discovery_responder, args=(port,), daemon=True).start()
        threading.Thread(target=self._run_ping_loop, daemon=True).start()

        while self.running:
            try:
                conn, addr = self.server_sock.accept()
            except OSError:
                break
            threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()

    def _run_discovery_responder(self, tcp_port):
        """While hosting, answer any 'is anyone hosting?' broadcast on the
        LAN so Join mode can find this room automatically instead of the
        other person having to type an IP."""
        try:
            self.discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.discovery_sock.bind(("0.0.0.0", DISCOVERY_PORT))
        except OSError:
            self.discovery_sock = None
            return
        while self.running:
            try:
                data, addr = self.discovery_sock.recvfrom(2048)
            except OSError:
                break
            try:
                req = json.loads(data.decode("utf-8"))
                if req.get("type") != "chat_host_discover":
                    continue
                with self.peers_lock:
                    member_count = len(self.peers) + 1
                reply = json.dumps({
                    "type": "chat_host_announce",
                    "name": self.my_name,
                    "port": tcp_port,
                    "has_password": bool(self.room_password_hash),
                    "members": member_count,
                }).encode("utf-8")
                self.discovery_sock.sendto(reply, addr)
            except Exception:
                continue

    def _run_ping_loop(self):
        """Every few seconds, ping whoever this side has a direct
        connection to, so 'connection quality' has something to show. The
        host pings each client directly (it has a real connection to
        each); a regular client only has a connection to the host, so it
        only ever measures its own ping to the host - it has no way to
        measure its ping to other members directly in this relayed
        design."""
        while self.running:
            time.sleep(6)
            if not self.running:
                break
            ts = time.time()
            ping_packet = {"type": "ping", "from": self.my_name, "ts": ts}
            if self.is_host:
                with self.peers_lock:
                    conns = [info["conn"] for info in self.peers.values() if info.get("conn") is not None]
                for conn in conns:
                    try:
                        send_json(conn, ping_packet)
                    except Exception:
                        pass
            else:
                try:
                    send_json(self.host_conn, ping_packet)
                except Exception:
                    pass

    @staticmethod
    def discover_hosts(timeout=2.0):
        """Client-side: broadcast a discovery ping and collect replies for
        `timeout` seconds. Returns a list of dicts: ip, name, port,
        has_password, members. Best-effort - some networks (guest wifi
        with client isolation, some routers) block broadcast traffic, in
        which case this simply finds nothing and the person can still
        enter an IP manually."""
        found = {}
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.3)
            ping = json.dumps({"type": "chat_host_discover"}).encode("utf-8")
            sock.sendto(ping, ("255.255.255.255", DISCOVERY_PORT))
        except OSError:
            return []

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                reply = json.loads(data.decode("utf-8"))
                if reply.get("type") != "chat_host_announce":
                    continue
                key = (addr[0], reply.get("port"))
                found[key] = {
                    "ip": addr[0],
                    "port": reply.get("port"),
                    "name": reply.get("name", "?"),
                    "has_password": bool(reply.get("has_password")),
                    "members": reply.get("members", 1),
                }
            except Exception:
                continue
        try:
            sock.close()
        except Exception:
            pass
        return list(found.values())

    def handle_client(self, conn, addr):
        try:
            hello = recv_json(conn)
            peer_name = hello["name"]
            peer_ip = hello.get("ip", addr[0])
            peer_avatar = hello.get("avatar", "")
            peer_status = hello.get("status", "online")
            peer_pubkey = load_public_key(hello["pubkey"].encode("utf-8"))
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return

        if self.room_password_hash and hello.get("password_hash", "") != self.room_password_hash:
            try:
                send_json(conn, {"type": "auth_failed"})
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            return

        if self.waiting_room:
            with self.peers_lock:
                returning = peer_name in self.peers and self.peers[peer_name].get("conn") is None
            if not returning:   # members reconnecting after a host failover are let straight in
                token = uuid.uuid4().hex[:8]
                event, box = threading.Event(), [False]
                self._join_decisions[token] = (event, box)
                self.join_request.emit(peer_name, token)
                event.wait(60)
                self._join_decisions.pop(token, None)
                if not box[0]:
                    try:
                        send_json(conn, {"type": "join_denied"})
                    except Exception:
                        pass
                    try:
                        conn.close()
                    except Exception:
                        pass
                    return

        with self.peers_lock:
            original_name = peer_name
            counter = 2
            while peer_name in self.peers and self.peers[peer_name].get("conn") is not None:
                peer_name = f"{original_name} ({counter})"
                counter += 1

            is_reclaim = peer_name in self.peers and self.peers[peer_name].get("conn") is None
            room_full = (
                self.max_members and not is_reclaim and len(self.peers) >= self.max_members
            )

            if not room_full:
                existing_peers = {}
                for name, info in self.peers.items():
                    existing_peers[name] = {
                        "pubkey": public_key_to_pem_cache(info["pubkey"]),
                        "ip": info["ip"],
                        "avatar": info.get("avatar", ""),
                        "status": info.get("status", "online"),
                    }
                self.peers[peer_name] = {
                    "pubkey": peer_pubkey, "ip": peer_ip, "conn": conn,
                    "avatar": peer_avatar, "status": peer_status,
                }

        if room_full:
            try:
                send_json(conn, {"type": "room_full"})
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            return

        try:
            send_json(conn, {
                "type": "peer_list",
                "host_name": self.my_name,
                "host_ip": self.my_ip,
                "host_pubkey": public_key_to_pem(self.public_key).decode("utf-8"),
                "host_avatar": self.my_avatar,
                "host_status": self.my_status,
                "peers": existing_peers,
                "room_password_hash": self.room_password_hash,
                "max_members": self.max_members,
                "group_info": self.main_group_info,
                "admins": sorted(self.admins),
            })
        except Exception:
            pass

        self.broadcast_control({
            "type": "new_peer",
            "name": peer_name,
            "pubkey": hello["pubkey"],
            "ip": peer_ip,
            "avatar": peer_avatar,
            "status": peer_status,
        }, exclude=peer_name)

        self.system_message.emit(T("sys_joined").format(name=peer_name))
        self.refresh_members.emit()

        self.client_receive_loop(conn, peer_name)

    def client_receive_loop(self, conn, peer_name):
        while self.running:
            try:
                packet = recv_json(conn)
            except Exception:
                break
            self.handle_incoming_packet(packet, origin=peer_name)

        with self.peers_lock:
            self.peers.pop(peer_name, None)
            was_kicked = peer_name in self.kicked_names
            self.kicked_names.discard(peer_name)
        try:
            conn.close()
        except Exception:
            pass

        if not was_kicked:
            self.system_message.emit(T("sys_left").format(name=peer_name))
            self.refresh_members.emit()
            self.broadcast_control({"type": "peer_left", "name": peer_name})

    def broadcast_control(self, packet, exclude=None):
        with self.peers_lock:
            targets = [info["conn"] for name, info in self.peers.items()
                       if name != exclude and info.get("conn") is not None]
        for conn in targets:
            try:
                send_json(conn, packet)
            except Exception:
                pass

    def resolve_join(self, token, accepted):
        entry = self._join_decisions.get(token)
        if entry:
            entry[1][0] = bool(accepted)
            entry[0].set()

    def toggle_guest(self, name, minutes=30):
        """Host only: mark someone as a temporary guest (removed automatically
        after `minutes`), or cancel that."""
        if not self.is_host:
            return
        timer = self.guests.pop(name, None)
        if timer is not None:
            timer.cancel()
        else:
            timer = threading.Timer(minutes * 60, self._guest_expired, args=(name,))
            timer.daemon = True
            timer.start()
            self.guests[name] = timer
        self.guests_updated.emit(sorted(self.guests))

    def _guest_expired(self, name):
        self.guests.pop(name, None)
        self.guests_updated.emit(sorted(self.guests))
        self.kick_peer(name)

    def toggle_admin(self, name):
        if not self.is_host:
            return
        if name in self.admins:
            self.admins.discard(name)
        else:
            self.admins.add(name)
        self.broadcast_control({"type": "roles", "admins": sorted(self.admins)})
        self.roles_updated.emit(sorted(self.admins))

    def request_kick(self, name):
        """An admin (not the host) asks the host to remove someone."""
        try:
            send_json(self.host_conn, {"type": "kick_request", "target": name, "from": self.my_name})
        except Exception:
            pass

    def kick_peer(self, name):
        if not self.is_host:
            return
        with self.peers_lock:
            info = self.peers.pop(name, None)
            if info is not None:
                self.kicked_names.add(name)
        if info is None:
            return
        conn = info.get("conn")
        if conn is not None:
            def close_after_delay():
                try:
                    send_json(conn, {"type": "kicked"})
                except Exception:
                    pass
                time.sleep(0.5)
                try:
                    conn.close()
                except Exception:
                    pass
            threading.Thread(target=close_after_delay, daemon=True).start()
        self.system_message.emit(T("sys_kicked_other").format(name=name))
        self.refresh_members.emit()
        self.broadcast_control({"type": "peer_left", "name": name})

    # ----- Client side: connect to the host (first time, or after failover) -----

    def connect_to_host_safe(self, host_ip, port, announce_switch, password):
        """Thread entry point for the initial join - unlike a failover retry,
        this one only ever gets attempted once, so any failure (wrong
        password, full room, bad IP, ...) needs to be reported right away
        instead of silently dying in a background thread."""
        try:
            self.connect_to_host(host_ip, port, announce_switch, password)
        except RoomRejected as e:
            self.connect_failed.emit(str(e))
        except Exception as e:
            self.connect_failed.emit(f"Could not connect: {e}")

    def connect_to_host(self, host_ip, port, announce_switch, password=""):
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.settimeout(5)
        conn.connect((host_ip, port))
        conn.settimeout(None)

        send_json(conn, {
            "name": self.my_name,
            "pubkey": public_key_to_pem(self.public_key).decode("utf-8"),
            "ip": self.my_ip,
            "avatar": self.my_avatar,
            "status": self.my_status,
            "password_hash": hashlib.sha256(password.encode("utf-8")).hexdigest() if password else "",
        })

        reply = recv_json(conn)

        if reply.get("type") == "auth_failed":
            conn.close()
            raise RoomRejected("Wrong password.")
        if reply.get("type") == "join_denied":
            conn.close()
            raise RoomRejected("The host did not let you in.")
        if reply.get("type") == "room_full":
            conn.close()
            raise RoomRejected("This room has already reached its maximum number of participants.")

        host_name = reply.get("host_name", "Host")
        host_ip_reported = reply.get("host_ip", host_ip)
        host_pubkey = load_public_key(reply["host_pubkey"].encode("utf-8"))
        self.room_password_hash = reply.get("room_password_hash", "")
        self.max_members = reply.get("max_members", 0) or 0
        gi = reply.get("group_info")
        self.main_group_info = gi if isinstance(gi, dict) else {"desc": "", "avatar": ""}
        self.admins = set(reply.get("admins") or [])

        with self.peers_lock:
            self.peers = {}
            self.peers[host_name] = {
                "pubkey": host_pubkey, "ip": host_ip_reported, "conn": None,
                "avatar": reply.get("host_avatar", ""), "status": reply.get("host_status", "online"),
            }
            for name, info in reply["peers"].items():
                self.peers[name] = {
                    "pubkey": load_public_key(info["pubkey"].encode("utf-8")),
                    "ip": info["ip"],
                    "conn": None,
                    "avatar": info.get("avatar", ""),
                    "status": info.get("status", "online"),
                }

        self.host_conn = conn
        self.host_name = host_name
        self.is_host = False
        self.running = True
        if not self._ping_thread_started:
            self._ping_thread_started = True
            threading.Thread(target=self._run_ping_loop, daemon=True).start()

        if announce_switch:
            self.status.emit(T("status_connected").format(host=host_ip))
            self.switch_to_chat.emit()
        else:
            self.system_message.emit(T("sys_reconnected").format(host=host_name))
            self.reconnect_status.emit("done")
        self.refresh_members.emit()
        self.main_group_info_updated.emit(
            self.main_group_info.get("desc", ""), self.main_group_info.get("avatar", "")
        )
        self.roles_updated.emit(sorted(self.admins))

        threading.Thread(target=self.join_receive_loop, daemon=True).start()

    def join_receive_loop(self):
        while self.running:
            try:
                packet = recv_json(self.host_conn)
            except Exception:
                if self.running and not self.was_kicked:
                    threading.Thread(target=self.perform_failover, daemon=True).start()
                break
            self.handle_incoming_packet(packet)

    # ----- Automatic host failover -----

    def perform_failover(self):
        if self.was_kicked:
            return
        self.reconnect_status.emit("start")
        with self.peers_lock:
            self.peers.pop(self.host_name, None)
            candidates = list(self.peers.keys()) + [self.my_name]
            peers_snapshot = dict(self.peers)

        new_host_name = sorted(candidates, key=lambda n: n.lower())[0]

        if new_host_name == self.my_name:
            self.is_host = True
            self.system_message.emit(T("sys_became_host"))
            self.reconnect_status.emit("new_host")
            self.run_host(self.port)
            return

        new_host_ip = peers_snapshot.get(new_host_name, {}).get("ip")
        if not new_host_ip:
            self.error.emit(T("err_host_gone_no_backup"))
            return

        self.system_message.emit(T("sys_reconnecting_through").format(name=new_host_name))

        for _ in range(10):
            time.sleep(1)
            try:
                self.connect_to_host(
                    new_host_ip, self.port, announce_switch=False, password=self.join_password
                )
                return
            except RoomRejected as e:
                self.error.emit(T("err_reconnect_failed").format(error=e))
                return
            except Exception:
                continue

        self.error.emit(T("err_reconnect_failed_restart"))

    # ----- Shared packet handling (host + client) -----

    def handle_incoming_packet(self, packet, origin=None):
        kind = packet.get("type")

        if kind in GENERIC_KINDS:
            if packet.get("to") == self.my_name:
                try:
                    data = base64.b64decode(packet["payload"])
                    content = json.loads(decrypt_message(data, self.private_key))
                    self.envelope_received.emit(
                        kind, packet["from"], packet.get("private", False), content
                    )
                except Exception:
                    pass
            elif self.is_host:
                with self.peers_lock:
                    dest = self.peers.get(packet.get("to"))
                if dest and dest.get("conn") is not None:
                    try:
                        send_json(dest["conn"], packet)
                    except Exception:
                        pass
            return

        if kind == "message":
            if packet["to"] == self.my_name:
                try:
                    data = base64.b64decode(packet["payload"])
                    content = json.loads(decrypt_message(data, self.private_key))
                    content.setdefault("time", packet.get("time", ""))
                    self.message_received.emit(
                        packet["from"], content, packet.get("private", False)
                    )
                except Exception:
                    pass
            elif self.is_host:
                with self.peers_lock:
                    dest = self.peers.get(packet["to"])
                if dest and dest.get("conn") is not None:
                    try:
                        send_json(dest["conn"], packet)
                    except Exception:
                        pass

        elif kind == "file":
            if packet["to"] == self.my_name:
                try:
                    data = base64.b64decode(packet["payload"])
                    content = json.loads(decrypt_message(data, self.private_key))
                    content.setdefault("time", packet.get("time", ""))
                    self.file_received.emit(
                        packet["from"], content, packet.get("private", False)
                    )
                except Exception:
                    pass
            elif self.is_host:
                with self.peers_lock:
                    dest = self.peers.get(packet["to"])
                if dest and dest.get("conn") is not None:
                    try:
                        send_json(dest["conn"], packet)
                    except Exception:
                        pass

        elif kind == "edit":
            if packet["to"] == self.my_name:
                try:
                    data = base64.b64decode(packet["payload"])
                    content = json.loads(decrypt_message(data, self.private_key))
                    self.message_edited.emit(content["msg_id"], content["text"])
                except Exception:
                    pass
            elif self.is_host:
                with self.peers_lock:
                    dest = self.peers.get(packet["to"])
                if dest and dest.get("conn") is not None:
                    try:
                        send_json(dest["conn"], packet)
                    except Exception:
                        pass

        elif kind == "delete":
            if packet["to"] == self.my_name:
                self.message_deleted.emit(packet["msg_id"])
            elif self.is_host:
                with self.peers_lock:
                    dest = self.peers.get(packet["to"])
                if dest and dest.get("conn") is not None:
                    try:
                        send_json(dest["conn"], packet)
                    except Exception:
                        pass

        elif kind == "pin":
            if packet["to"] == self.my_name:
                try:
                    data = base64.b64decode(packet["payload"])
                    content = json.loads(decrypt_message(data, self.private_key))
                    is_private = packet.get("private", False)
                    self.pin_updated.emit(is_private, packet["from"], content)
                except Exception:
                    pass
            elif self.is_host:
                with self.peers_lock:
                    dest = self.peers.get(packet["to"])
                if dest and dest.get("conn") is not None:
                    try:
                        send_json(dest["conn"], packet)
                    except Exception:
                        pass

        elif kind == "group":
            if packet["to"] == self.my_name:
                try:
                    data = base64.b64decode(packet["payload"])
                    content = json.loads(decrypt_message(data, self.private_key))
                    self.group_event.emit(packet["from"], content)
                except Exception:
                    pass
            elif self.is_host:
                with self.peers_lock:
                    dest = self.peers.get(packet["to"])
                if dest and dest.get("conn") is not None:
                    try:
                        send_json(dest["conn"], packet)
                    except Exception:
                        pass

        elif kind == "main_group_info":
            if not self.is_host:
                self.main_group_info = {
                    "desc": packet.get("desc", ""), "avatar": packet.get("avatar", ""),
                }
                self.main_group_info_updated.emit(
                    self.main_group_info["desc"], self.main_group_info["avatar"]
                )

        elif kind == "reaction":
            if packet["to"] == self.my_name:
                try:
                    data = base64.b64decode(packet["payload"])
                    content = json.loads(decrypt_message(data, self.private_key))
                    self.message_reacted.emit(
                        packet["from"], content["msg_id"], content["emoji"], content["action"]
                    )
                except Exception:
                    pass
            elif self.is_host:
                with self.peers_lock:
                    dest = self.peers.get(packet["to"])
                if dest and dest.get("conn") is not None:
                    try:
                        send_json(dest["conn"], packet)
                    except Exception:
                        pass

        elif kind == "new_peer":
            with self.peers_lock:
                self.peers[packet["name"]] = {
                    "pubkey": load_public_key(packet["pubkey"].encode("utf-8")),
                    "ip": packet.get("ip"),
                    "conn": None,
                    "avatar": packet.get("avatar", ""),
                    "status": packet.get("status", "online"),
                }
            self.system_message.emit(T("sys_joined").format(name=packet["name"]))
            self.refresh_members.emit()

        elif kind == "peer_left":
            with self.peers_lock:
                self.peers.pop(packet["name"], None)
            self.system_message.emit(T("sys_left").format(name=packet["name"]))
            self.refresh_members.emit()

        elif kind == "typing":
            if packet["to"] == self.my_name:
                self.typing_received.emit(
                    packet["from"], packet.get("private", False), packet.get("group", "") or ""
                )
            elif self.is_host:
                with self.peers_lock:
                    dest = self.peers.get(packet["to"])
                if dest and dest.get("conn") is not None:
                    try:
                        send_json(dest["conn"], packet)
                    except Exception:
                        pass

        elif kind == "seen":
            if packet["to"] == self.my_name:
                self.message_seen.emit(packet["from"])
            elif self.is_host:
                with self.peers_lock:
                    dest = self.peers.get(packet["to"])
                if dest and dest.get("conn") is not None:
                    try:
                        send_json(dest["conn"], packet)
                    except Exception:
                        pass

        elif kind == "avatar_update":
            name = packet.get("name")
            avatar = packet.get("avatar", "")
            if name and name != self.my_name:
                with self.peers_lock:
                    if name in self.peers:
                        self.peers[name]["avatar"] = avatar
                self.refresh_members.emit()
            if self.is_host:
                self.broadcast_control(packet, exclude=name)

        elif kind == "status_update":
            name = packet.get("name")
            status = packet.get("status", "online")
            if name and name != self.my_name:
                with self.peers_lock:
                    if name in self.peers:
                        self.peers[name]["status"] = status
                if packet.get("bio") is not None:
                    self.peer_bios[name] = str(packet.get("bio"))[:120]
                self.refresh_members.emit()
            if self.is_host:
                self.broadcast_control(packet, exclude=name)

        elif kind == "roles":
            if not self.is_host:
                self.admins = set(str(a) for a in (packet.get("admins") or []))
                self.roles_updated.emit(sorted(self.admins))

        elif kind == "kick_request":
            # `origin` is the connection the packet really arrived on (not a
            # name the sender claims), so a normal member can't fake it.
            target = packet.get("target")
            if self.is_host and origin in self.admins and target and target != origin:
                self.kick_peer(target)

        elif kind == "ping":
            # Always point-to-point on whichever direct connection it
            # arrived on (client<->host) - just echo it straight back,
            # never relayed any further.
            reply = {"type": "pong", "ts": packet.get("ts"), "from": self.my_name}
            try:
                if self.is_host:
                    with self.peers_lock:
                        dest = self.peers.get(packet.get("from"))
                    if dest and dest.get("conn") is not None:
                        send_json(dest["conn"], reply)
                else:
                    send_json(self.host_conn, reply)
            except Exception:
                pass

        elif kind == "pong":
            ts = packet.get("ts")
            sender = packet.get("from")
            if ts is not None and sender:
                rtt_ms = max(0, int((time.time() - ts) * 1000))
                self.peer_ping[sender] = rtt_ms
                self.ping_updated.emit(sender, rtt_ms)

        elif kind == "kicked":
            # Mark this *before* touching the socket at all: it's the
            # authoritative guard against this computer mistaking its own
            # removal for the host crashing and trying to become the new
            # host itself.
            self.was_kicked = True
            self.running = False
            self.kicked.emit()
            try:
                self.host_conn.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.host_conn.close()
            except Exception:
                pass

    # ----- Sending a message -----

    def _resolve_targets(self, recipient):
        # `recipient` is EVERYONE, one member's name, or a list of names
        # (the members of a user-created group: sent to each one
        # separately, encrypted for each, exactly like a normal message).
        with self.peers_lock:
            peers_snapshot = list(self.peers.items())
        if isinstance(recipient, (list, tuple, set)):
            wanted = set(recipient)
            return False, [(n, info) for n, info in peers_snapshot if n in wanted]
        is_private = recipient != EVERYONE
        targets = peers_snapshot if not is_private else [
            (n, info) for n, info in peers_snapshot if n == recipient
        ]
        return is_private, targets

    def _send_envelope_to_targets(self, packet_type, recipient, content, extra_fields=None):
        """Encrypt `content` (a JSON-able dict) separately for every
        recipient of this chat and send it as `packet_type`. Used for
        messages, edits and pins - anything that carries chat content and
        therefore has to stay inside the same per-recipient encryption as
        a normal message."""
        is_private, targets = self._resolve_targets(recipient)
        plain = json.dumps(content, ensure_ascii=False)
        for name, info in targets:
            try:
                encrypted = encrypt_message(plain, info["pubkey"])
                packet = {
                    "type": packet_type,
                    "to": name,
                    "from": self.my_name,
                    "payload": base64.b64encode(encrypted).decode("ascii"),
                    "private": is_private,
                }
                if extra_fields:
                    packet.update(extra_fields)
                if self.is_host:
                    send_json(info["conn"], packet)
                else:
                    send_json(self.host_conn, packet)
            except Exception as e:
                self.error.emit(T("err_send_failed").format(name=name, error=e))

    def send_message(self, text, recipient, reply_to=None, reply_from=None,
                      reply_text=None, forward_from=None, ttl=0, group=None, extra=None):
        if not self.running:
            return None, None
        ts = time.strftime("%H:%M")
        msg_id = uuid.uuid4().hex[:12]
        content = {
            "text": text, "msg_id": msg_id, "time": ts,
            "reply_to": reply_to, "reply_from": reply_from, "reply_text": reply_text,
            "forward_from": forward_from, "ttl": ttl, "group": group,
        }
        if extra:
            content.update(extra)
        self._send_envelope_to_targets("message", recipient, content, {"time": ts})
        return ts, msg_id

    def send_file(self, file_path, recipient, ttl=0, group=None, raw=None, kind=None, extra=None):
        """Reads a local file, base64-encodes it, and sends it through the
        same per-recipient encrypted envelope as a text message. Capped at
        FILE_SIZE_CAP_MB since the whole thing travels as one JSON frame
        (no chunking) - big enough for photos and small documents, not
        videos. Returns (ts, msg_id) on success, or (None, None) with
        self.error emitted on failure (unreadable file or too big)."""
        if raw is None:
            try:
                with open(file_path, "rb") as f:
                    raw = f.read()
            except OSError as e:
                self.error.emit(T("err_send_failed").format(name=recipient, error=e))
                return None, None, None
        if len(raw) > FILE_SIZE_CAP_MB * 1024 * 1024:
            self.error.emit(T("file_too_large").format(max=FILE_SIZE_CAP_MB))
            return None, None, None

        filename = os.path.basename(file_path)
        if kind is None:
            kind = "image" if filename.lower().endswith(
                (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
            ) else "file"
        ts = time.strftime("%H:%M")
        msg_id = uuid.uuid4().hex[:12]
        content = {
            "msg_id": msg_id, "time": ts, "filename": filename, "kind": kind,
            "size": len(raw), "data": base64.b64encode(raw).decode("ascii"),
            "ttl": ttl, "group": group, "sha256": hashlib.sha256(raw).hexdigest(),
        }
        if extra:
            content.update(extra)
        if recipient is not None:
            self._send_envelope_to_targets("file", recipient, content, {"time": ts})
        return ts, msg_id, content

    def send_edit(self, msg_id, new_text, recipient):
        content = {"msg_id": msg_id, "text": new_text}
        self._send_envelope_to_targets("edit", recipient, content)

    def send_delete(self, msg_id, recipient):
        is_private, targets = self._resolve_targets(recipient)
        for name, info in targets:
            try:
                packet = {
                    "type": "delete", "to": name, "from": self.my_name,
                    "msg_id": msg_id, "private": is_private,
                }
                if self.is_host:
                    send_json(info["conn"], packet)
                else:
                    send_json(self.host_conn, packet)
            except Exception:
                pass

    def send_pin(self, recipient, msg_id, sender, text, group=None, unpin=False):
        """text=None (with msg_id=None) means 'unpin'."""
        content = {"msg_id": msg_id, "sender": sender, "text": text, "group": group, "unpin": unpin}
        self._send_envelope_to_targets("pin", recipient, content)

    def send_reaction(self, recipient, msg_id, emoji, action):
        """action is 'add' or 'remove' - toggling one emoji reaction of
        ours on a message, the same way WhatsApp/Telegram reactions work."""
        content = {"msg_id": msg_id, "emoji": emoji, "action": action}
        self._send_envelope_to_targets("reaction", recipient, content)

    def send_avatar_update(self, b64):
        """Announce a new profile picture to everyone currently in the
        room - not secret content, so this travels the same way presence
        info (new_peer) already does, unencrypted."""
        self.my_avatar = b64
        packet = {"type": "avatar_update", "name": self.my_name, "avatar": b64}
        if self.is_host:
            self.broadcast_control(packet)
        else:
            try:
                send_json(self.host_conn, packet)
            except Exception:
                pass

    def send_status_update(self, status, bio=None):
        self.my_status = status
        if bio is not None:
            self.my_bio = bio
        packet = {"type": "status_update", "name": self.my_name, "status": status, "bio": self.my_bio}
        if self.is_host:
            self.broadcast_control(packet)
        else:
            try:
                send_json(self.host_conn, packet)
            except Exception:
                pass

    def send_group_event(self, members, content):
        """Create / update / leave notices for user-created groups; they
        carry the group's name, description and picture, so they travel in
        the same per-recipient encrypted envelope as messages."""
        if not self.running:
            return
        self._send_envelope_to_targets("group", list(members), content)

    def send_envelope(self, kind, recipient, content):
        """Send any GENERIC_KINDS packet (vote, checklist, game, ...)."""
        if not self.running:
            return
        self._send_envelope_to_targets(kind, recipient, content)

    def send_main_group_info(self, desc, avatar):
        """Host only: change the main group's description / picture and
        tell everyone (plain control packet, same as profile pictures)."""
        if not self.is_host:
            return
        self.main_group_info = {"desc": desc, "avatar": avatar}
        self.broadcast_control({"type": "main_group_info", "desc": desc, "avatar": avatar})

    def send_typing(self, target, group_id=None):
        """Fire-and-forget 'I'm typing' notice. No encryption needed (it
        carries no message content), unlike send_message. `target` may be
        a list of names (a user-created group) together with its id."""
        if not self.running:
            return
        is_private, targets = self._resolve_targets(target)

        for name, info in targets:
            try:
                packet = {"type": "typing", "to": name, "from": self.my_name, "private": is_private}
                if group_id:
                    packet["group"] = group_id
                if self.is_host:
                    send_json(info["conn"], packet)
                else:
                    send_json(self.host_conn, packet)
            except Exception:
                pass

    def send_seen(self, peer):
        """Fire-and-forget 'I've seen your messages' notice for a private
        chat, used to flip the sender's tick to a double tick. Same
        unencrypted, best-effort pattern as send_typing."""
        if not self.running:
            return
        with self.peers_lock:
            info = self.peers.get(peer)
        if not info:
            return
        try:
            packet = {"type": "seen", "to": peer, "from": self.my_name}
            if self.is_host:
                send_json(info["conn"], packet)
            else:
                send_json(self.host_conn, packet)
        except Exception:
            pass

    def shutdown(self):
        self.running = False
        try:
            if self.host_conn:
                self.host_conn.close()
        except Exception:
            pass
        try:
            with self.peers_lock:
                for info in self.peers.values():
                    if info.get("conn") is not None:
                        info["conn"].close()
        except Exception:
            pass
        try:
            if self.server_sock:
                self.server_sock.close()
        except Exception:
            pass
        try:
            if getattr(self, "discovery_sock", None):
                self.discovery_sock.close()
        except Exception:
            pass


# small cache so we don't re-serialize the same public key object repeatedly
_pem_cache = {}


def public_key_to_pem_cache(pubkey_obj):
    key = id(pubkey_obj)
    if key not in _pem_cache:
        _pem_cache[key] = public_key_to_pem(pubkey_obj).decode("utf-8")
    return _pem_cache[key]


# A small 64x64 padlock-on-bubble PNG, embedded so the whole app stays one file.
APP_ICON_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABqElEQVR4nO1bS3bDIAxU+rpJ2qOmp0mO"
    "mjbLdkUfJpAIW9IYodnFn6AZRgh4mCgwNw5bXv64/PxKBbIV31+nVVy6X9oT6RZ6xGA/OALxEhwh3jh/"
    "NCJ5Il7cTxUalXgNLTc0HeCJPFGbDysFPKMqgLfeT6jxehDAK/mEkl+kQP7De+8n5DzDAegA0PgXYBb7"
    "JyS+4QB0AGiEAOgA0HhHNXw7Hx+ufV7v5nGYC1AjXt6zFMI0BZ6RX/OcBMwE6CVlJYJJCnDzvXzudj6q"
    "p4O6A3oGO44o0jAvg6961LoSqAog1XuaLjB1ALd33ZbBPUKtCtRsu8XKWhVBXADNfNWYKU6fAqICWM3e"
    "JNsJB6ADQAO2H0C0HMwsV4A5YA4oR3LEZggRSICexZA2ph8DQgBEo60BDzEQwhxQ2/1BAFoGUaRzxBiA"
    "DgCNEAAdABqiAljN5GJDRBCL87OSx2Q0Spxkz6ezw2rzANTqrhfTp8BCgLWfnYyGnGc4oLzg3QUlv6oD"
    "vIpQ4xUp0LrhzQUtPiySI58jftWRrBQY1Q2cuOPL0S0N7UmMUV0Kxx8ZqJaI01IL2gAAAABJRU5ErkJg"
    "gg=="
)


# ---------- Connect screen ----------

class GamesHubWindow(QMainWindow):
    """A 'choose a game' screen laid out as a grid of tiles. Launching a
    game opens it in its own separate window (each game is a whole
    QMainWindow/QWidget of its own), so this hub stays open and can launch
    more than one. Extra tiles (e.g. the online two-player game) can be
    added by the main window with add_tile()."""

    GAMES = [
        ("ttt", "\u274E\u2B55", "extras_games_menu_ttt", TicTacToe),
        ("snake", "\U0001F40D", "extras_games_menu_snake", NeonSnake),
        ("tetris", "\U0001F9F1", "extras_games_menu_tetris", Tetris),
        ("flappy", "\U0001F426", "extras_games_menu_flappy", FlappyBird),
        ("mines", "\U0001F4A3", "extras_games_menu_mines", Minesweeper),
        ("typing", "\u2328", "extras_games_menu_typing", TypingGameWindow),
        ("wordle", "\U0001F524", "extras_games_menu_wordle", Wordle),
        ("sudoku", "\U0001F522", "extras_games_menu_sudoku", Sudoku),
        ("quiz", "\u2753", "extras_games_menu_quiz", Quiz),
        ("pong", "\U0001F3D3", "extras_games_menu_pong", Pong),
        ("pacman", "\U0001F47B", "extras_games_menu_pacman", Pacman),
        ("memory", "\U0001F9E0", "extras_games_menu_memory", Memory),
        ("invaders", "\U0001F47E", "extras_games_menu_invaders", Invaders),
        ("hangman", "\U0001F4DD", "extras_games_menu_hangman", Hangman),
        ("connect4", "\U0001F534", "extras_games_menu_connect4", Connect4),
        ("dodge", "\U0001F7E5", "extras_games_menu_dodge", Dodge),
        ("breakout", "\U0001F4A5", "extras_games_menu_breakout", Breakout),
        ("chess", "\u265F", "extras_games_menu_chess", Chess),
    ]

    def __init__(self):
        super().__init__()
        self._windows = {}
        self._tile_buttons = []
        self.setWindowTitle(T("games_picker_title"))
        self.setMinimumSize(520, 360)
        self.resize(580, 540)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(16)

        title = QLabel(T("games_picker_title"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 19pt; font-weight: 800; background: transparent;")
        layout.addWidget(title)

        # 18+ tiles don't fit a small window, so the grid scrolls.
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setSpacing(14)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.grid_host)
        layout.addWidget(scroll, stretch=1)
        for key, emoji, str_key, factory in self.GAMES:
            self._add_game_tile(key, emoji, str_key, factory)

        more_lbl = QLabel(T("games_picker_more_soon"))
        more_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        more_lbl.setStyleSheet("color: #8798b6; font-size: 9pt; background: transparent;")
        layout.addWidget(more_lbl)

        self.setStyleSheet("""
        QMainWindow, QWidget { background: #0b1220; color: #eaf2ff; font-family: "Segoe UI", Arial; }
        QPushButton#gameTile {
            background: #101f35; border: 1.5px solid #243b60; border-radius: 14px;
            font-size: 11pt; font-weight: 600;
        }
        QPushButton#gameTile:hover { border: 1.5px solid #5369ff; background: #142548; }
        """)

    def _place(self, btn):
        i = len(self._tile_buttons)
        self.grid.addWidget(btn, i // 3, i % 3)
        self._tile_buttons.append(btn)

    def _add_game_tile(self, key, emoji, str_key, factory):
        btn = QPushButton(f"{emoji}\n{T(str_key)}")
        btn.setObjectName("gameTile")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumSize(140, 100)
        btn.clicked.connect(lambda checked=False, k=key, f=factory: self._launch(k, f))
        self._place(btn)

    def add_tile(self, text, callback):
        """Add an extra tile (a callable is run on click, no window caching)."""
        btn = QPushButton(text)
        btn.setObjectName("gameTile")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumSize(140, 100)
        btn.clicked.connect(lambda checked=False: callback())
        self._place(btn)

    def _launch(self, key, factory):
        win = self._windows.get(key)
        if win is not None and not win.isVisible():
            # The game window was closed: drop it (stops its timers) and start fresh.
            win.deleteLater()
            win = None
        if win is None:
            win = factory()
            self._windows[key] = win
            try:
                win.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            except Exception:
                pass
        if hasattr(win, "set_language"):
            win.set_language(CURRENT_LANG[0])
        win.show()
        win.raise_()
        win.activateWindow()
        win.setFocus()


class HostDiscoveryWorker(QObject):
    """Runs ChatBackend.discover_hosts() off the GUI thread and reports
    back through a signal, the same cross-thread pattern ChatBackend
    itself already uses everywhere else in this file."""
    hosts_found = pyqtSignal(list)

    def run(self):
        hosts = ChatBackend.discover_hosts()
        self.hosts_found.emit(hosts)


class ConnectPage(QWidget):
    """The first screen. There's no explicit Host/Join choice any more:
    whoever opens the app first just hosts (password now required), and
    anyone who opens it after that sees them in the auto-discovered list
    below and connects to them instead - picking a discovered host and
    hosting are just two outcomes of the same single form."""

    connect_requested = pyqtSignal(dict)
    language_change_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(2)

        center = QVBoxLayout()
        center.setSpacing(6)
        center.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.title_lbl = QLabel(T("connect_title"))
        self.title_lbl.setObjectName("titleLabel")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(self.title_lbl)

        self.subtitle_lbl = QLabel(T("connect_subtitle"))
        self.subtitle_lbl.setObjectName("subtitleLabel")
        self.subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(self.subtitle_lbl)
        center.addSpacing(22)

        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(380)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 24, 26, 24)
        card_layout.setSpacing(12)

        self.name_label, self.name_edit = self._field(
            card_layout, T("connect_field_name"), return_label=True
        )

        # Always-on auto-discovery: found via a UDP broadcast, no IP to
        # type. Picking a host from this list is how you "join"; picking
        # none and pressing the button at the bottom is how you "host" -
        # there's no separate mode switch for it any more. A small link
        # falls back to a manual-IP field for networks where broadcast
        # discovery doesn't reach (e.g. client-isolated wifi).
        self.manual_ip_mode = False
        self.selected_host = None
        self._discovery_worker = None

        self.discover_row = QHBoxLayout()
        self.discover_status_lbl = QLabel(T("discover_scanning"))
        self.discover_status_lbl.setObjectName("fieldLabel")
        self.discover_row.addWidget(self.discover_status_lbl, stretch=1)
        self.discover_scan_btn = QPushButton(T("discover_refresh"))
        self.discover_scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.discover_scan_btn.clicked.connect(self._start_discovery)
        self.discover_row.addWidget(self.discover_scan_btn)
        card_layout.addLayout(self.discover_row)

        self.discovered_list = QListWidget()
        self.discovered_list.setObjectName("discoverList")
        self.discovered_list.setFixedHeight(90)
        self.discovered_list.itemClicked.connect(self._on_host_item_clicked)
        card_layout.addWidget(self.discovered_list)

        self.clear_selection_lbl = QLabel(T("connect_clear_selection_link"))
        self.clear_selection_lbl.setObjectName("linkLabel")
        self.clear_selection_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_selection_lbl.mousePressEvent = lambda e: self._clear_selected_host()
        self.clear_selection_lbl.setVisible(False)
        card_layout.addWidget(self.clear_selection_lbl)

        self.manual_toggle_lbl = QLabel(T("discover_manual_link"))
        self.manual_toggle_lbl.setObjectName("linkLabel")
        self.manual_toggle_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manual_toggle_lbl.mousePressEvent = lambda e: self._toggle_manual_ip()
        card_layout.addWidget(self.manual_toggle_lbl)

        self.ip_label, self.ip_edit = self._field(card_layout, T("connect_field_ip"), return_label=True)
        self.port_label, self.port_edit = self._field(
            card_layout, T("connect_field_port"), return_label=True
        )
        self.port_edit.setText("5000")
        self.password_label, self.password_edit = self._field(
            card_layout, T("connect_field_password_host"), return_label=True
        )
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.max_label, self.max_edit = self._field(
            card_layout, T("connect_field_max"), return_label=True
        )

        self.avatar_path = None
        self.avatar_pixmap = None
        self.avatar_label = QLabel(T("connect_field_avatar"))
        self.avatar_label.setObjectName("fieldLabel")
        card_layout.addWidget(self.avatar_label)
        avatar_row = QHBoxLayout()
        avatar_row.setSpacing(10)
        self.avatar_preview = AvatarLabel("", "#6c7a8f", size=40)
        avatar_row.addWidget(self.avatar_preview)
        self.avatar_btn = QPushButton(T("connect_btn_choose_picture"))
        self.avatar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avatar_btn.clicked.connect(self._on_choose_avatar)
        avatar_row.addWidget(self.avatar_btn, stretch=1)
        card_layout.addLayout(avatar_row)

        card_layout.addSpacing(8)
        self.connect_btn = QPushButton(T("connect_btn_host"))
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        card_layout.addWidget(self.connect_btn)

        self.status_label = QLabel("")
        self.status_label.setObjectName("subtitleLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        card_layout.addWidget(self.status_label)

        center.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Language switch lives here now instead of the old Games /
        # Language-test shortcuts, which were moved out of this first
        # screen entirely (still reachable from inside the chat).
        center.addSpacing(14)
        extras_row = QHBoxLayout()
        extras_row.setSpacing(10)
        extras_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.lang_en_btn = QPushButton(T("lang_en"))
        self.lang_en_btn.setObjectName("extraButton")
        self.lang_en_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_en_btn.clicked.connect(lambda: self.language_change_requested.emit("en"))
        extras_row.addWidget(self.lang_en_btn)
        self.lang_fa_btn = QPushButton(T("lang_fa"))
        self.lang_fa_btn.setObjectName("extraButton")
        self.lang_fa_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_fa_btn.clicked.connect(lambda: self.language_change_requested.emit("fa"))
        extras_row.addWidget(self.lang_fa_btn)
        center.addLayout(extras_row)

        outer.addLayout(center)
        outer.addStretch(3)

        self._update_fields_visibility()
        self._start_discovery()

    def _field(self, layout, label_text, return_label=False):
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        edit = QLineEdit()
        layout.addWidget(edit)
        if return_label:
            return label, edit
        return edit

    def _is_host_state(self):
        return self.selected_host is None and not self.manual_ip_mode

    def _update_fields_visibility(self):
        is_host = self._is_host_state()
        self.max_label.setVisible(is_host)
        self.max_edit.setVisible(is_host)
        self.clear_selection_lbl.setVisible(self.selected_host is not None)
        self.ip_label.setVisible(self.manual_ip_mode)
        self.ip_edit.setVisible(self.manual_ip_mode)
        self.port_label.setVisible(is_host or self.manual_ip_mode)
        self.port_edit.setVisible(is_host or self.manual_ip_mode)
        self.password_label.setText(
            T("connect_field_password_host") if is_host else T("connect_field_password_join")
        )
        self.connect_btn.setText(T("connect_btn_host") if is_host else T("connect_btn_join"))

    def _toggle_manual_ip(self):
        self.manual_ip_mode = not self.manual_ip_mode
        if self.manual_ip_mode:
            self.selected_host = None
            self.discovered_list.clearSelection()
        self.manual_toggle_lbl.setText(
            T("discover_auto_link") if self.manual_ip_mode else T("discover_manual_link")
        )
        self._update_fields_visibility()

    def _clear_selected_host(self):
        self.selected_host = None
        self.discovered_list.clearSelection()
        self._update_fields_visibility()

    def _start_discovery(self):
        self.discovered_list.clear()
        self.selected_host = None
        self.discover_status_lbl.setText(T("discover_scanning"))
        self.discover_status_lbl.setVisible(True)
        worker = HostDiscoveryWorker()
        worker.hosts_found.connect(self._on_hosts_found)
        self._discovery_worker = worker  # keep a reference alive for the thread's lifetime
        threading.Thread(target=worker.run, daemon=True).start()
        self._update_fields_visibility()

    def _on_hosts_found(self, hosts):
        self.discovered_list.clear()
        if not hosts:
            self.discover_status_lbl.setText(T("discover_none_found"))
            self.discover_status_lbl.setVisible(True)
            return
        self.discover_status_lbl.setVisible(False)
        for h in hosts:
            lock = "\U0001F512 " if h["has_password"] else ""
            item = QListWidgetItem(f"{lock}{h['name']} \u2014 {h['ip']}")
            item.setData(Qt.ItemDataRole.UserRole, h)
            self.discovered_list.addItem(item)

    def _on_host_item_clicked(self, item):
        self.selected_host = item.data(Qt.ItemDataRole.UserRole)
        self.manual_ip_mode = False
        self._update_fields_visibility()

    def retranslate_ui(self):
        self.title_lbl.setText(T("connect_title"))
        self.subtitle_lbl.setText(T("connect_subtitle"))
        self.name_label.setText(T("connect_field_name"))
        self.ip_label.setText(T("connect_field_ip"))
        self.port_label.setText(T("connect_field_port"))
        self.max_label.setText(T("connect_field_max"))
        self.avatar_label.setText(T("connect_field_avatar"))
        self.avatar_btn.setText(T("connect_btn_choose_picture"))
        self.discover_scan_btn.setText(T("discover_refresh"))
        self.clear_selection_lbl.setText(T("connect_clear_selection_link"))
        self.manual_toggle_lbl.setText(
            T("discover_auto_link") if self.manual_ip_mode else T("discover_manual_link")
        )
        self.lang_en_btn.setText(T("lang_en"))
        self.lang_fa_btn.setText(T("lang_fa"))
        self._update_fields_visibility()

    def _on_choose_avatar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, T("connect_pick_avatar_title"), "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.set_status(T("connect_err_avatar"), is_error=True)
            return
        # Downscaled small and square-ish before sending anywhere over the
        # network later, so an avatar never costs more than a few KB.
        pixmap = pixmap.scaled(
            128, 128, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.avatar_path = path
        self.avatar_pixmap = pixmap
        self.avatar_preview.set_image(pixmap)

    def _avatar_b64(self):
        if self.avatar_pixmap is None:
            return ""
        buf = QByteArray()
        qbuf = QBuffer(buf)
        qbuf.open(QIODevice.OpenModeFlag.WriteOnly)
        self.avatar_pixmap.save(qbuf, "PNG")
        return base64.b64encode(bytes(buf)).decode("ascii")

    def set_status(self, text, is_error=False):
        color = "#ff6b6b" if is_error else ""
        self.status_label.setText(text)
        if color:
            self.status_label.setStyleSheet(f"color: {color};")
        else:
            self.status_label.setStyleSheet("")

    def set_busy(self, busy):
        self.connect_btn.setEnabled(not busy)

    def _on_connect_clicked(self):
        name = self.name_edit.text().strip()
        if not name:
            self.set_status(T("connect_err_name"), is_error=True)
            return
        is_host = self._is_host_state()

        max_members = 0
        ip = ""
        port = 5000

        if is_host:
            if not self.password_edit.text():
                self.set_status(T("connect_err_password"), is_error=True)
                return
            port_text = self.port_edit.text().strip() or "5000"
            try:
                port = int(port_text)
            except ValueError:
                self.set_status(T("connect_err_port"), is_error=True)
                return
            max_text = self.max_edit.text().strip()
            if max_text:
                try:
                    max_members = int(max_text)
                    if max_members <= 0:
                        raise ValueError
                except ValueError:
                    self.set_status(T("connect_err_max"), is_error=True)
                    return
        elif self.manual_ip_mode:
            if not self.ip_edit.text().strip():
                self.set_status(T("connect_err_ip"), is_error=True)
                return
            ip = self.ip_edit.text().strip()
            port_text = self.port_edit.text().strip() or "5000"
            try:
                port = int(port_text)
            except ValueError:
                self.set_status(T("connect_err_port"), is_error=True)
                return
        else:
            if not self.selected_host:
                self.set_status(T("connect_err_no_host_selected"), is_error=True)
                return
            ip = self.selected_host["ip"]
            port = self.selected_host["port"]

        self.set_status("")
        self.connect_requested.emit({
            "is_host": is_host,
            "name": name,
            "ip": ip,
            "port": port,
            "password": self.password_edit.text(),
            "max_members": max_members,
            "avatar_b64": self._avatar_b64(),
        })


class CreateGroupDialog(QDialog):
    """Name, description, photo and members (picked from whoever is online)
    for a new group."""

    def __init__(self, candidates, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("new_group_title"))
        self.setMinimumWidth(380)
        self.avatar_b64 = ""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)

        top = QHBoxLayout()
        self.avatar_preview = AvatarLabel("", GROUP_AVATAR_COLOR, size=56)
        top.addWidget(self.avatar_preview)
        pick_btn = QPushButton(T("group_photo_btn"))
        pick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pick_btn.clicked.connect(self._pick_photo)
        top.addWidget(pick_btn, stretch=1)
        lay.addLayout(top)

        name_lbl = QLabel(T("group_name_label"))
        name_lbl.setObjectName("fieldLabel")
        lay.addWidget(name_lbl)
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(40)
        lay.addWidget(self.name_edit)

        desc_lbl = QLabel(T("group_desc_label"))
        desc_lbl.setObjectName("fieldLabel")
        lay.addWidget(desc_lbl)
        self.desc_edit = QTextEdit()
        self.desc_edit.setAcceptRichText(False)
        self.desc_edit.setFixedHeight(60)
        lay.addWidget(self.desc_edit)

        members_lbl = QLabel(T("group_members_label"))
        members_lbl.setObjectName("fieldLabel")
        lay.addWidget(members_lbl)
        self.members_list = QListWidget()
        self.members_list.setObjectName("discoverList")
        self.members_list.setFixedHeight(130)
        for name in candidates:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.members_list.addItem(item)
        lay.addWidget(self.members_list)

        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: #ff6b6b;")
        lay.addWidget(self.error_lbl)

        self.readonly_check = QCheckBox(T("group_readonly_label"))
        lay.addWidget(self.readonly_check)

        create_btn = QPushButton(T("group_create_btn"))
        create_btn.setObjectName("primaryButton")
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.clicked.connect(self._try_accept)
        lay.addWidget(create_btn)

    def _pick_photo(self):
        res = choose_avatar_b64(self)
        if res:
            pixmap, b64 = res
            self.avatar_b64 = b64
            self.avatar_preview.set_image(pixmap)

    def _try_accept(self):
        if not self.name_edit.text().strip():
            self.error_lbl.setText(T("group_err_name"))
            return
        if not self.values()[3]:
            self.error_lbl.setText(T("group_err_members"))
            return
        self.accept()

    def values(self):
        members = [
            self.members_list.item(i).text()
            for i in range(self.members_list.count())
            if self.members_list.item(i).checkState() == Qt.CheckState.Checked
        ]
        return (self.name_edit.text().strip(), self.desc_edit.toPlainText().strip(),
                self.avatar_b64, members)


class GroupInfoDialog(QDialog):
    """Shows a group's picture, name, description and members. Editable
    (description + picture, and the name for user-created groups) only
    when `can_edit` is set; user-created groups can also be left."""

    def __init__(self, title, desc, avatar_b64, member_lines, can_edit, editable_name,
                 can_leave, edit_denied_text, color=GROUP_AVATAR_COLOR, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("group_info_title"))
        self.setMinimumWidth(380)
        self.avatar_b64 = avatar_b64
        self.leave_requested = False
        self.can_edit = can_edit

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(12)
        self.avatar_preview = AvatarLabel(title, color, size=64)
        self.avatar_preview.set_image(pixmap_from_b64(avatar_b64))
        top.addWidget(self.avatar_preview)
        if can_edit:
            pick_btn = QPushButton(T("group_choose_photo_btn"))
            pick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            pick_btn.clicked.connect(self._pick_photo)
            top.addWidget(pick_btn)
        top.addStretch(1)
        lay.addLayout(top)

        self.name_edit = QLineEdit(title)
        self.name_edit.setMaxLength(40)
        self.name_edit.setReadOnly(not (can_edit and editable_name))
        lay.addWidget(self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setAcceptRichText(False)
        self.desc_edit.setPlainText(desc)
        self.desc_edit.setPlaceholderText(T("group_desc_placeholder"))
        self.desc_edit.setReadOnly(not can_edit)
        self.desc_edit.setFixedHeight(80)
        lay.addWidget(self.desc_edit)

        if not can_edit:
            note = QLabel(edit_denied_text)
            note.setObjectName("mutedLabel")
            note.setWordWrap(True)
            lay.addWidget(note)

        members_lbl = QLabel(T("group_info_members").format(n=len(member_lines)))
        members_lbl.setObjectName("fieldLabel")
        lay.addWidget(members_lbl)
        members_box = QLabel("\n".join(member_lines))
        members_box.setWordWrap(True)
        lay.addWidget(members_box)

        btn_row = QHBoxLayout()
        if can_leave:
            leave_btn = QPushButton(T("group_leave_btn"))
            leave_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            leave_btn.clicked.connect(self._leave)
            btn_row.addWidget(leave_btn)
        btn_row.addStretch(1)
        close_btn = QPushButton(T("group_close_btn"))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)
        if can_edit:
            save_btn = QPushButton(T("group_save_btn"))
            save_btn.setObjectName("primaryButton")
            save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            save_btn.clicked.connect(self.accept)
            btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

    def _pick_photo(self):
        res = choose_avatar_b64(self)
        if res:
            pixmap, b64 = res
            self.avatar_b64 = b64
            self.avatar_preview.set_image(pixmap)

    def _leave(self):
        self.leave_requested = True
        self.accept()

    def values(self):
        return (self.name_edit.text().strip(), self.desc_edit.toPlainText().strip(), self.avatar_b64)


class MediaGalleryDialog(QDialog):
    """Every image / voice message / file shared in one chat (or all chats),
    with a type filter. Double-click opens an image, plays a voice message
    or offers to save a file."""

    def __init__(self, items, save_cb, play_cb, parent=None):
        super().__init__(parent)
        self.items = items
        self.save_cb = save_cb
        self.play_cb = play_cb
        self.setWindowTitle(T("gallery_title"))
        self.resize(560, 460)
        lay = QVBoxLayout(self)
        self.filter_box = QComboBox()
        for key, label in (("all", "gallery_filter_all"), ("image", "gallery_filter_images"),
                           ("voice", "gallery_filter_voice"), ("file", "gallery_filter_files")):
            self.filter_box.addItem(T(label), key)
        self.filter_box.currentIndexChanged.connect(self._refill)
        lay.addWidget(self.filter_box)
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setIconSize(QSize(96, 96))
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setWordWrap(True)
        self.list.setGridSize(QSize(120, 140))
        self.list.itemDoubleClicked.connect(self._open_item)
        lay.addWidget(self.list, stretch=1)
        self.empty_lbl = QLabel(T("gallery_empty"))
        self.empty_lbl.setObjectName("mutedLabel")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.empty_lbl)
        self._refill()

    def _refill(self):
        want = self.filter_box.currentData()
        self.list.clear()
        for title, sender, content in self.items:
            kind = content.get("kind", "file")
            if want != "all" and kind != want:
                continue
            name = content.get("filename", "file")
            if kind == "image":
                pm = pixmap_from_b64(content.get("data", ""))
                icon = QIcon(pm.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)) if pm else QIcon()
            else:
                pm = QPixmap(96, 96)
                pm.fill(QColor(0, 0, 0, 0))
                painter = QPainter(pm)
                painter.setFont(QFont("Segoe UI Emoji", 40))
                painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter,
                                 "\U0001F3A4" if kind == "voice" else "\U0001F4C4")
                painter.end()
                icon = QIcon(pm)
            item = QListWidgetItem(icon, f"{name}\n{sender}")
            item.setToolTip(f"{title} \u2022 {sender} \u2022 {content.get('time', '')}\nSHA-256: "
                            f"{content.get('sha256', '')[:16]}")
            item.setData(Qt.ItemDataRole.UserRole, content)
            self.list.addItem(item)
        self.empty_lbl.setVisible(self.list.count() == 0)

    def _open_item(self, item):
        content = item.data(Qt.ItemDataRole.UserRole)
        kind = content.get("kind", "file")
        name = content.get("filename", "file")
        data = content.get("data", "")
        if kind == "voice":
            self.play_cb(data)
        elif kind == "image":
            viewer = QDialog(self)
            viewer.setWindowTitle(name)
            vl = QVBoxLayout(viewer)
            img = QLabel()
            pm = pixmap_from_b64(data)
            if pm:
                img.setPixmap(pm.scaled(720, 520, Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation))
            img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl.addWidget(img)
            save = QPushButton(T("file_save_btn"))
            save.clicked.connect(lambda: self.save_cb(name, data))
            vl.addWidget(save)
            viewer.exec()
        else:
            self.save_cb(name, data)


class QRCodeWidget(QWidget):
    """Draws a QR code from a boolean matrix (made with the optional `qrcode` package)."""

    def __init__(self, matrix, parent=None):
        super().__init__(parent)
        self.matrix = matrix
        self.setMinimumSize(200, 200)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        n = len(self.matrix)
        if not n:
            painter.end()
            return
        cell = min(self.width(), self.height()) / (n + 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#000000"))
        for y, row in enumerate(self.matrix):
            for x, on in enumerate(row):
                if on:
                    painter.drawRect(QRectF((x + 1) * cell, (y + 1) * cell, cell + 0.5, cell + 0.5))
        painter.end()


class LockOverlay(QWidget):
    """Full-window cover asking for the PIN; everything underneath is disabled."""
    unlock_attempt = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("lockOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#lockOverlay { background-color: #0b1220; } "
                           "QLabel { color: #eaf2ff; background: transparent; }")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel("\U0001F512")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 40pt;")
        lay.addWidget(icon)
        self.title_lbl = QLabel("")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setStyleSheet("font-size: 16pt; font-weight: 700;")
        lay.addWidget(self.title_lbl)
        self.entry = QLineEdit()
        self.entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.entry.setFixedWidth(240)
        self.entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry.returnPressed.connect(self._submit)
        lay.addWidget(self.entry, alignment=Qt.AlignmentFlag.AlignCenter)
        self.btn = QPushButton("")
        self.btn.setObjectName("primaryButton")
        self.btn.setFixedWidth(240)
        self.btn.clicked.connect(self._submit)
        lay.addWidget(self.btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.msg_lbl = QLabel("")
        self.msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_lbl.setStyleSheet("color: #ff6b6b;")
        lay.addWidget(self.msg_lbl)
        self.retranslate()

    def retranslate(self):
        self.title_lbl.setText(T("lock_title"))
        self.btn.setText(T("lock_unlock"))

    def _submit(self):
        pin = self.entry.text()
        self.entry.clear()
        self.unlock_attempt.emit(pin)

    def set_message(self, text):
        self.msg_lbl.setText(text)

    def set_busy(self, busy):
        self.entry.setEnabled(not busy)
        self.btn.setEnabled(not busy)
        if not busy:
            self.entry.setFocus()


class PollDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("poll_title"))
        self.setMinimumWidth(360)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)
        q_lbl = QLabel(T("poll_question_label"))
        q_lbl.setObjectName("fieldLabel")
        lay.addWidget(q_lbl)
        self.question_edit = QLineEdit()
        lay.addWidget(self.question_edit)
        o_lbl = QLabel(T("poll_options_label"))
        o_lbl.setObjectName("fieldLabel")
        lay.addWidget(o_lbl)
        self.options_edit = QPlainTextEdit()
        self.options_edit.setFixedHeight(120)
        lay.addWidget(self.options_edit)
        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: #ff6b6b;")
        lay.addWidget(self.error_lbl)
        btn = QPushButton(T("poll_create_btn"))
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self._try_accept)
        lay.addWidget(btn)

    def values(self):
        options = [ln.strip() for ln in self.options_edit.toPlainText().splitlines() if ln.strip()]
        return self.question_edit.text().strip(), options[:8]

    def _try_accept(self):
        question, options = self.values()
        if not question or len(options) < 2:
            self.error_lbl.setText(T("poll_err"))
            return
        self.accept()


class ToolsHubWindow(QMainWindow):
    """A small 'choose a tool' screen laid out like the games picker. Each
    tool opens in its own window; the main window listens to tool_requested."""

    tool_requested = pyqtSignal(str)

    TOOLS = [
        ("weather", "\U0001F324", "tools_weather"),
        ("calculator", "\U0001F9EE", "tools_calculator"),
        ("converter", "\U0001F4D0", "tools_converter"),
        ("wol", "\u23FB", "tools_wol"),
        ("network", "\U0001F4F6", "tools_network"),
    ]

    def __init__(self):
        super().__init__()
        self.setMinimumSize(520, 340)
        self.resize(560, 360)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(16)

        self.title_lbl = QLabel("")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setStyleSheet("font-size: 19pt; font-weight: 800; background: transparent;")
        layout.addWidget(self.title_lbl)

        grid = QGridLayout()
        grid.setSpacing(14)
        layout.addLayout(grid)
        self.buttons = []
        for i, (key, emoji, str_key) in enumerate(self.TOOLS):
            btn = QPushButton("")
            btn.setObjectName("gameTile")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumSize(140, 100)
            btn.clicked.connect(lambda checked=False, k=key: self.tool_requested.emit(k))
            grid.addWidget(btn, i // 3, i % 3)
            self.buttons.append((btn, emoji, str_key))
        layout.addStretch(1)

        self.setStyleSheet("""
        QMainWindow, QWidget { background: #0b1220; color: #eaf2ff; font-family: "Segoe UI", Arial; }
        QPushButton#gameTile {
            background: #101f35; border: 1.5px solid #243b60; border-radius: 14px;
            font-size: 11pt; font-weight: 600;
        }
        QPushButton#gameTile:hover { border: 1.5px solid #5369ff; background: #142548; }
        """)
        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(T("tools_picker_title"))
        self.title_lbl.setText(T("tools_picker_title"))
        for btn, emoji, str_key in self.buttons:
            btn.setText(emoji + "\n" + T(str_key))


# ---------- Chat screen ----------

class ChatPage(QWidget):
    """Telegram-style layout: a chat list on the left (Group and Saved
    Messages pinned at the top, then one row per online member), and on the
    right a single panel that switches between whichever chat is open — the
    group, a private chat, or an empty "pick a chat" state right after
    connecting — with its own back button, exactly like opening a DM in
    Telegram and tapping back to return to the chat list's main view."""

    send_requested = pyqtSignal(str, str, dict)  # text, target, extra (reply_to/reply_from/reply_text or {})
    edit_submit_requested = pyqtSignal(str, str, str)   # msg_id, chat_key, new_text
    delete_requested = pyqtSignal(str, str)             # msg_id, chat_key
    forward_to_requested = pyqtSignal(str, str, str)    # original_sender, text, target_chat_key
    pin_toggle_requested = pyqtSignal(str, str)         # msg_id, chat_key
    reaction_toggle_requested = pyqtSignal(str, str, str, str)  # msg_id, chat_key, emoji, action
    unpin_requested = pyqtSignal(str)                   # chat_key
    avatar_change_requested = pyqtSignal()
    status_change_requested = pyqtSignal(str)
    file_send_requested = pyqtSignal(str)                # local file path to attach
    security_code_requested = pyqtSignal(str)             # peer name
    games_requested = pyqtSignal()
    language_test_requested = pyqtSignal()
    rates_requested = pyqtSignal()
    kick_requested = pyqtSignal(str)
    theme_change_requested = pyqtSignal(str)
    language_change_requested = pyqtSignal(str)
    typing_requested = pyqtSignal(str)          # target currently being typed to
    seen_requested = pyqtSignal(str)            # peer whose messages we just viewed
    font_size_change_requested = pyqtSignal(str)
    group_create_requested = pyqtSignal(str, str, str, list, bool)  # name, description, avatar b64, members, read-only
    group_update_requested = pyqtSignal(str, str, str, str)   # gid, name, description, avatar b64
    group_leave_requested = pyqtSignal(str)                   # gid
    main_group_info_change_requested = pyqtSignal(str, str)   # description, avatar b64
    tools_requested = pyqtSignal()
    notes_requested = pyqtSignal()
    bio_change_requested = pyqtSignal(str)
    slash_command_requested = pyqtSignal(str, str)
    reply_reminder_requested = pyqtSignal(str, str, int)   # sender, text, minutes
    location_requested = pyqtSignal(str, dict)
    race_invite_requested = pyqtSignal(str)
    person_note_requested = pyqtSignal(str)
    contacts_requested = pyqtSignal()
    focus_requested = pyqtSignal(int)
    presentation_toggle_requested = pyqtSignal()
    waiting_room_toggled = pyqtSignal(bool)
    autoreply_requested = pyqtSignal()
    incognito_view_changed = pyqtSignal(bool)
    ptt_chunk = pyqtSignal(str, bytes)            # chat key, raw PCM
    screen_share_toggled = pyqtSignal(str, bool)  # chat key, start?
    hand_toggle_requested = pyqtSignal()
    hands_clear_requested = pyqtSignal()
    guest_toggle_requested = pyqtSignal(str)
    media_player_requested = pyqtSignal(str)
    game_invite_requested = pyqtSignal(str)
    clipboard_share_requested = pyqtSignal(str)
    capsule_requested = pyqtSignal(str, str, float)   # chat key, text, unlock epoch
    sync_file_requested = pyqtSignal(str, str, str, str)  # chat key, rel path, base64 data, sha256
    admin_toggle_requested = pyqtSignal(str)
    dnd_requested = pyqtSignal()
    checklist_changed = pyqtSignal(str, list)     # chat key, items
    board_event = pyqtSignal(str, dict)           # chat key, {op: stroke/clear/full, ...}
    security_pin_requested = pyqtSignal()
    security_autolock_requested = pyqtSignal()
    security_lock_requested = pyqtSignal()
    theme_mode_change_requested = pyqtSignal(str)
    backup_requested = pyqtSignal()
    restore_requested = pyqtSignal()
    poll_create_requested = pyqtSignal(str, str, list)   # chat key, question, options
    poll_vote_requested = pyqtSignal(str, str, int)      # chat key, msg_id, choice (-1 = withdraw)
    sticker_requested = pyqtSignal(str, str)             # chat key, sticker
    voice_recorded = pyqtSignal(str, bytes, float)       # chat key, wav bytes, seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bubbles = []  # (label_widget, kind) kind in own/other/private, for re-theming
        self.groups = {}            # gid -> {"id","name","desc","avatar","owner","members":[...]}
        self.main_group_info = {"desc": "", "avatar": ""}
        self.chat_ttl = {}          # chat key -> self-destruct seconds for MY next messages (0 = off)
        self.last_message_id = {}   # chat key -> msg_id of its newest message (for the sidebar preview)
        self.current_host_name = ""
        self.chat_prefs = dict(get_setting("chat_prefs", {}) or {})   # chat key -> {bg, notify, sound, sound_file, ...}
        self.chat_menu_builders = []   # extra (menu, chat_key) callables added by feature modules
        self.polls = {}             # msg_id -> poll card info
        self.poll_votes = {}        # msg_id -> {voter: option index}
        self.recorder = None
        self.tagged = {x["id"]: x for x in (get_setting("tagged", []) or []) if isinstance(x, dict) and x.get("id")}
        self.readonly_until = {}    # chat key -> epoch until which I voluntarily can't post
        self.incognito_ids = {}     # chat key -> [(msg_id, container)] erased when leaving the chat
        self._incognito_view = False
        self.group_typers = {}      # chat key -> {name: typing-until epoch}
        self._base_desc = ""
        self.hands = set()          # names with a raised hand
        self.guests = set()         # (host only) names currently marked as temporary guests
        self.sharing_keys = set()   # chats I'm sharing my screen with
        self._ptt = None
        self._ptt_target = None
        self.sync_folders = {}      # chat key -> SyncFolder
        for _k, _p in dict(get_setting("sync_folders", {}) or {}).items():
            if isinstance(_p, str) and os.path.isdir(_p):
                _sf = SyncFolder(_p)
                _sf.prime()
                self.sync_folders[_k] = _sf
        self.admins = set()
        self.peer_statuses = {}
        self._pin_index = {}
        self.starred = {x["id"]: x for x in (get_setting("starred", []) or []) if isinstance(x, dict) and x.get("id")}
        CHAT_LIST_LINES[0] = int(get_setting("list_lines", 1) or 1)
        self.my_bio = str(get_setting("bio", "") or "")
        self.peer_bios = {}
        self.checklists = {}        # chat key -> shared checklist items
        self.boards = {}            # chat key -> shared whiteboard strokes
        self._collab_dialogs = {}
        self.select_mode = False
        self.selected_ids = set()
        self.scheduled = list(get_setting("scheduled", []) or [])
        self.chat_files = {}        # chat key -> [(sender, file content dict), ...]
        self.link_preview_enabled = bool(get_setting("link_previews", False))
        self._link_workers = []
        self._rec_timer = None
        self._rec_target = None
        self._sticker_popup = None
        self.member_names = []
        self.setAcceptDrops(True)  # drag a file anywhere onto the chat screen to send it
        self.sidebar_rows = {}      # key -> ChatListRow
        self.private_pages = {}     # name/SAVED_MESSAGES_KEY -> {"scroll", "container", "layout"}
        self.last_messages = {}     # key -> preview text for the sidebar's second line
        self.typing_until = {}      # key -> monotonic timestamp until which "typing..." shows
        self.muted_names = set()
        self.is_host_flag = False
        self.peer_avatars = {}
        self.my_name = ""
        self.my_avatar_pixmap = None
        self.chat_bubbles = {}       # key -> [BubbleLabel, ...] for this chat only, in order
        self.chat_search_matches = []
        self.chat_search_index = -1
        self.unread_counts = {}      # key -> unread message count, reset on open
        self.pinned_chat_keys = set()  # member names pinned to the top of the chat list
        self._last_update_members_args = None
        self.my_name = ""
        self.reactions_by_msg = {}   # msg_id -> {emoji: set(names)}
        self.theme = THEMES[DEFAULT_THEME]
        self.save_history_enabled = bool(load_app_settings().get("save_history", False))
        self._history_loaded_keys = set()  # chat_keys already replayed from disk this run
        self.own_tick_labels = {}    # peer -> [tick QLabel, ...] for private read-receipt ticks
        self.peer_seen = {}          # peer -> True once they've acked seeing our latest messages
        self.font_size_key = "medium"
        self.messages_by_id = {}     # msg_id -> {bubble, sender, is_own, chat_key, deleted}
        self.replying_to = None      # {"msg_id","sender","text"} or None
        self.editing_msg_id = None
        self.pinned_by_chat = {}     # chat_key -> {"msg_id","sender","text"} or absent
        self.peer_pings = {}         # name -> last round-trip time in ms
        self.current_target = None  # None = empty state, EVERYONE = group, else a name/SAVED_MESSAGES_KEY
        self._room_title = T("group_title")
        self._room_is_host = None
        self._room_host_name = ""
        self._last_typing_sent = 0.0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Thin strip shown only while automatic host failover is under way,
        # so a dropped host reads as "reconnecting" instead of a silent
        # freeze.
        self.reconnect_banner = QLabel(T("reconnect_banner"))
        self.reconnect_banner.setObjectName("reconnectBanner")
        self.reconnect_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reconnect_banner.setVisible(False)
        root.addWidget(self.reconnect_banner)

        self.focus_banner = QLabel("")
        self.focus_banner.setObjectName("reconnectBanner")
        self.focus_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.focus_banner.setCursor(Qt.CursorShape.PointingHandCursor)
        self.focus_banner.setVisible(False)
        self.focus_banner.mousePressEvent = lambda e: self.focus_requested.emit(0)
        root.addWidget(self.focus_banner)

        # Top bar: back button (non-group chats only) + avatar + title
        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 10, 16, 10)
        top_layout.setSpacing(10)

        self.back_btn = QToolButton()
        self.back_btn.setObjectName("backButton")
        self.back_btn.setText("\u2039")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self.open_group)
        top_layout.addWidget(self.back_btn)

        self.chat_avatar = AvatarLabel("", GROUP_AVATAR_COLOR, size=34)
        self.chat_avatar.setVisible(False)
        top_layout.addWidget(self.chat_avatar)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        self.chat_title = QLabel("")
        self.chat_title.setObjectName("roomLabel")
        title_col.addWidget(self.chat_title)
        self.chat_desc_lbl = QLabel("")
        self.chat_desc_lbl.setObjectName("mutedLabel")
        self.chat_desc_lbl.setVisible(False)
        title_col.addWidget(self.chat_desc_lbl)
        top_layout.addLayout(title_col)
        top_layout.addStretch(1)

        self.chat_search_btn = QToolButton()
        self.chat_search_btn.setObjectName("backButton")
        self.chat_search_btn.setText("\U0001F50D")
        self.chat_search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chat_search_btn.clicked.connect(self._toggle_chat_search)
        top_layout.addWidget(self.chat_search_btn)

        self.export_chat_btn = QToolButton()
        self.export_chat_btn.setObjectName("backButton")
        self.export_chat_btn.setText("\u2B07")
        self.export_chat_btn.setToolTip(T("export_chat_tooltip"))
        self.export_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_chat_btn.clicked.connect(self._on_export_chat_clicked)
        self.export_chat_btn.setVisible(False)
        top_layout.addWidget(self.export_chat_btn)

        self.security_code_btn = QToolButton()
        self.security_code_btn.setObjectName("backButton")
        self.security_code_btn.setText("\U0001F512")
        self.security_code_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.security_code_btn.setVisible(False)
        self.security_code_btn.clicked.connect(self._on_security_code_clicked)
        top_layout.addWidget(self.security_code_btn)

        self.group_info_btn = QToolButton()
        self.group_info_btn.setObjectName("backButton")
        self.group_info_btn.setText("\u24D8")
        self.group_info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.group_info_btn.setVisible(False)
        self.group_info_btn.clicked.connect(self._on_group_info_clicked)
        top_layout.addWidget(self.group_info_btn)

        self.ttl_btn = QToolButton()
        self.ttl_btn.setObjectName("backButton")
        self.ttl_btn.setText("\u23F1")
        self.ttl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ttl_btn.setVisible(False)
        self.ttl_btn.clicked.connect(self._on_ttl_clicked)
        top_layout.addWidget(self.ttl_btn)

        self.chat_menu_btn = QToolButton()
        self.chat_menu_btn.setObjectName("backButton")
        self.chat_menu_btn.setText("\u22EE")
        self.chat_menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chat_menu_btn.setVisible(False)
        self.chat_menu_btn.clicked.connect(self._on_chat_menu_clicked)
        top_layout.addWidget(self.chat_menu_btn)

        root.addWidget(top_bar)

        # In-chat message search bar: hidden until the magnifier is clicked;
        # searches only the currently open chat's own messages.
        self.chat_search_bar = QFrame()
        self.chat_search_bar.setObjectName("topBar")
        self.chat_search_bar.setVisible(False)
        search_bar_layout = QHBoxLayout(self.chat_search_bar)
        search_bar_layout.setContentsMargins(12, 6, 12, 6)
        search_bar_layout.setSpacing(8)
        self.chat_search_edit = QLineEdit()
        self.chat_search_edit.setPlaceholderText(T("search_in_chat_placeholder"))
        self.chat_search_edit.textChanged.connect(self._on_chat_search_changed)
        search_bar_layout.addWidget(self.chat_search_edit, stretch=1)
        self.chat_search_status = QLabel("")
        self.chat_search_status.setObjectName("mutedLabel")
        search_bar_layout.addWidget(self.chat_search_status)
        self.chat_search_prev_btn = QToolButton()
        self.chat_search_prev_btn.setText("\u2039")
        self.chat_search_prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chat_search_prev_btn.clicked.connect(lambda: self._step_chat_search(-1))
        search_bar_layout.addWidget(self.chat_search_prev_btn)
        self.chat_search_next_btn = QToolButton()
        self.chat_search_next_btn.setText("\u203a")
        self.chat_search_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chat_search_next_btn.clicked.connect(lambda: self._step_chat_search(1))
        search_bar_layout.addWidget(self.chat_search_next_btn)
        self.chat_search_close_btn = QToolButton()
        self.chat_search_close_btn.setText("\u2715")
        self.chat_search_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chat_search_close_btn.clicked.connect(self._toggle_chat_search)
        search_bar_layout.addWidget(self.chat_search_close_btn)
        root.addWidget(self.chat_search_bar)

        # Body: chat list (sidebar, with its own hamburger+search header) + panel
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        self.sidebar_frame = sidebar
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 10, 0, 10)
        sidebar_layout.setSpacing(2)

        sidebar_header = QHBoxLayout()
        sidebar_header.setContentsMargins(12, 2, 12, 10)
        sidebar_header.setSpacing(8)

        self.menu_btn = QToolButton()
        self.menu_btn.setObjectName("hamburgerButton")
        self.menu_btn.setText("\u2630")
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.clicked.connect(self._toggle_drawer)
        sidebar_header.addWidget(self.menu_btn)

        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self._on_search_changed)
        sidebar_header.addWidget(self.search_edit, stretch=1)

        self.new_group_btn = QToolButton()
        self.new_group_btn.setObjectName("hamburgerButton")
        self.new_group_btn.setText("\uFF0B")
        self.new_group_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_group_btn.clicked.connect(self._on_new_group_clicked)
        sidebar_header.addWidget(self.new_group_btn)
        sidebar_layout.addLayout(sidebar_header)

        self.members_scroll = QScrollArea()
        self.members_scroll.setWidgetResizable(True)
        self.members_container = QWidget()
        self.members_layout = QVBoxLayout(self.members_container)
        self.members_layout.setContentsMargins(6, 0, 6, 0)
        self.members_layout.setSpacing(2)
        self.members_layout.addStretch(1)
        self.members_scroll.setWidget(self.members_container)
        sidebar_layout.addWidget(self.members_scroll)

        # Global search results (messages from every chat + matching chat
        # names) replace the chat list while the search box has text.
        self.search_results = QListWidget()
        self.search_results.setObjectName("searchResults")
        self.search_results.setWordWrap(True)
        self.search_results.setVisible(False)
        self.search_results.itemClicked.connect(self._on_search_result_clicked)
        sidebar_layout.addWidget(self.search_results, stretch=1)
        body.addWidget(sidebar)

        chat_col = QVBoxLayout()
        chat_col.setContentsMargins(0, 0, 0, 0)
        chat_col.setSpacing(0)

        # Pinned-message banner for whichever chat is currently open (one
        # pin per chat); hidden when that chat has nothing pinned.
        self.pin_banner = QFrame()
        self.pin_banner.setObjectName("pinBanner")
        self.pin_banner.setVisible(False)
        pin_layout = QHBoxLayout(self.pin_banner)
        pin_layout.setContentsMargins(14, 6, 10, 6)
        pin_layout.setSpacing(8)
        pin_icon = QLabel("\U0001F4CC")
        pin_icon.setStyleSheet("background: transparent;")
        pin_layout.addWidget(pin_icon)
        self.pin_banner_label = QLabel("")
        self.pin_banner_label.setObjectName("pinBannerLabel")
        self.pin_banner_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_banner_label.mousePressEvent = lambda e: self._jump_to_pinned()
        pin_layout.addWidget(self.pin_banner_label, stretch=1)
        self.pin_unpin_btn = QToolButton()
        self.pin_unpin_btn.setText("\u2715")
        self.pin_unpin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_unpin_btn.clicked.connect(self._on_unpin_clicked)
        pin_layout.addWidget(self.pin_unpin_btn)
        chat_col.addWidget(self.pin_banner)

        # Stacked panel: empty state, then the group chat; private/saved
        # pages are added lazily the first time each one is opened.
        self.chat_stack = QStackedWidget()

        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon = QLabel("\U0001F4AC")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setStyleSheet("font-size: 46pt; background: transparent;")
        empty_layout.addWidget(empty_icon)
        self.empty_text = QLabel(T("empty_state_text"))
        self.empty_text.setObjectName("mutedLabel")
        self.empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_text)

        empty_layout.addSpacing(22)
        empty_extras_row = QHBoxLayout()
        empty_extras_row.setSpacing(14)
        empty_extras_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_games_btn = QPushButton(T("extras_games_btn"))
        self.empty_games_btn.setObjectName("emptyStateCard")
        self.empty_games_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.empty_games_btn.clicked.connect(lambda: self.games_requested.emit())
        empty_extras_row.addWidget(self.empty_games_btn)
        self.empty_language_test_btn = QPushButton(T("extras_language_test_btn"))
        self.empty_language_test_btn.setObjectName("emptyStateCard")
        self.empty_language_test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.empty_language_test_btn.clicked.connect(lambda: self.language_test_requested.emit())
        empty_extras_row.addWidget(self.empty_language_test_btn)
        self.empty_rates_btn = QPushButton(T("extras_rates_btn"))
        self.empty_rates_btn.setObjectName("emptyStateCard")
        self.empty_rates_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.empty_rates_btn.clicked.connect(lambda: self.rates_requested.emit())
        empty_extras_row.addWidget(self.empty_rates_btn)
        self.empty_tools_btn = QPushButton(T("extras_tools_btn"))
        self.empty_tools_btn.setObjectName("emptyStateCard")
        self.empty_tools_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.empty_tools_btn.clicked.connect(lambda: self.tools_requested.emit())
        empty_extras_row.addWidget(self.empty_tools_btn)
        empty_layout.addLayout(empty_extras_row)

        self.chat_stack.addWidget(self.empty_state)

        self.group_scroll = QScrollArea()
        self.group_scroll.setWidgetResizable(True)
        self.group_container = QWidget()
        self.group_layout = QVBoxLayout(self.group_container)
        self.group_layout.setContentsMargins(18, 14, 18, 14)
        self.group_layout.setSpacing(10)
        self.group_layout.addStretch(1)
        self.group_scroll.setWidget(self.group_container)
        self.chat_stack.addWidget(self.group_scroll)

        chat_col.addWidget(self.chat_stack, stretch=1)

        # Shown above the compose bar while replying to or editing a
        # message; hidden the rest of the time.
        self.compose_banner = QFrame()
        self.compose_banner.setObjectName("composeBanner")
        self.compose_banner.setVisible(False)
        cb_layout = QHBoxLayout(self.compose_banner)
        cb_layout.setContentsMargins(14, 6, 10, 6)
        cb_layout.setSpacing(8)
        self.compose_banner_label = QLabel("")
        self.compose_banner_label.setObjectName("composeBannerLabel")
        self.compose_banner_label.setWordWrap(True)
        cb_layout.addWidget(self.compose_banner_label, stretch=1)
        self.compose_banner_cancel_btn = QToolButton()
        self.compose_banner_cancel_btn.setText("\u2715")
        self.compose_banner_cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.compose_banner_cancel_btn.clicked.connect(self._cancel_reply_edit)
        cb_layout.addWidget(self.compose_banner_cancel_btn)
        chat_col.addWidget(self.compose_banner)

        self.select_bar = QFrame()
        self.select_bar.setObjectName("composeBanner")
        self.select_bar.setVisible(False)
        sb_layout = QHBoxLayout(self.select_bar)
        sb_layout.setContentsMargins(14, 6, 10, 6)
        sb_layout.setSpacing(8)
        self.select_count_lbl = QLabel("")
        self.select_count_lbl.setObjectName("composeBannerLabel")
        sb_layout.addWidget(self.select_count_lbl, stretch=1)
        self.select_forward_btn = QPushButton(T("select_forward"))
        self.select_forward_btn.clicked.connect(self._forward_selected)
        sb_layout.addWidget(self.select_forward_btn)
        self.select_copy_btn = QPushButton(T("select_copy"))
        self.select_copy_btn.clicked.connect(self._copy_selected)
        sb_layout.addWidget(self.select_copy_btn)
        self.select_delete_btn = QPushButton(T("select_delete"))
        self.select_delete_btn.clicked.connect(self._delete_selected)
        sb_layout.addWidget(self.select_delete_btn)
        self.select_cancel_btn = QToolButton()
        self.select_cancel_btn.setText("\u2715")
        self.select_cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_cancel_btn.clicked.connect(self._exit_select_mode)
        sb_layout.addWidget(self.select_cancel_btn)
        chat_col.addWidget(self.select_bar)

        self.compose_bar = compose_bar = QFrame()
        compose_bar.setObjectName("composeBar")
        compose_layout = QHBoxLayout(compose_bar)
        compose_layout.setContentsMargins(16, 10, 16, 10)
        compose_layout.setSpacing(8)

        self.attach_btn = QToolButton()
        self.attach_btn.setObjectName("backButton")
        self.attach_btn.setText(T("attach_file_btn"))
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.clicked.connect(self._on_attach_clicked)
        compose_layout.addWidget(self.attach_btn)
        self.attach_menu_items = [
            ("attach_menu_file", self._attach_file),
            ("attach_menu_poll", self._attach_poll),
            ("attach_menu_yesno", self._attach_yesno),
            ("attach_menu_schedule", self._attach_schedule),
            ("attach_menu_capsule", self._attach_capsule),
            ("attach_menu_location", self._attach_location),
        ]

        self.sticker_btn = QToolButton()
        self.sticker_btn.setObjectName("backButton")
        self.sticker_btn.setText("\U0001F600")
        self.sticker_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sticker_btn.clicked.connect(self._on_sticker_clicked)
        compose_layout.addWidget(self.sticker_btn)

        self.mic_btn = QToolButton()
        self.mic_btn.setObjectName("backButton")
        self.mic_btn.setText("\U0001F3A4")
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.clicked.connect(self._on_mic_clicked)
        compose_layout.addWidget(self.mic_btn)

        self.ptt_btn = QToolButton()
        self.ptt_btn.setObjectName("backButton")
        self.ptt_btn.setText("\U0001F4FB")
        self.ptt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ptt_btn.pressed.connect(self._ptt_start)
        self.ptt_btn.released.connect(self._ptt_stop)
        compose_layout.addWidget(self.ptt_btn)

        self.message_edit = ComposeTextEdit()
        self.message_edit.send_triggered.connect(self._on_send_clicked)
        self.message_edit.textChanged.connect(self._on_text_changed)
        compose_layout.addWidget(self.message_edit, stretch=1)

        self.send_btn = QPushButton("\u27A4")
        self.send_btn.setObjectName("sendButton")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._on_send_clicked)
        compose_layout.addWidget(self.send_btn)

        chat_col.addWidget(compose_bar)
        body.addLayout(chat_col, stretch=1)
        root.addLayout(body, stretch=1)

        self._typing_sweep_timer = QTimer(self)
        self._typing_sweep_timer.setInterval(1000)
        self._typing_sweep_timer.timeout.connect(self._sweep_typing)
        self._typing_sweep_timer.start()

        self._schedule_timer = QTimer(self)
        self._schedule_timer.setInterval(5000)
        self._schedule_timer.timeout.connect(self._check_scheduled)
        self._schedule_timer.start()
        self.chat_menu_builders.append(self._menu_scheduled)
        self.chat_menu_builders.append(self._menu_collab)
        self.chat_menu_builders.append(self._menu_extras)
        self.chat_menu_builders.append(self._menu_live)
        self.chat_menu_builders.append(self._menu_privacy)
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(8000)
        self._sync_timer.timeout.connect(self._sync_tick)
        self._sync_timer.start()
        self.chat_menu_builders.append(self._menu_gallery)

        self._build_drawer()
        self.retranslate_ui()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "drawer_open", False):
            self.drawer.setGeometry(0, 0, self.drawer.width(), self.height())
            self.drawer_overlay.setGeometry(0, 0, self.width(), self.height())

    # ----- hamburger menu: Telegram-style slide-in drawer -----
    # A real side panel (not a QMenu) that slides in from the left over a
    # dimmed backdrop. Its own list (profile, Settings, Saved Messages,
    # Night Mode switch) is page 1 of a tiny internal stack; tapping
    # "Settings" swaps to page 2 (appearance + language) with a back row -
    # everything click-to-open, nothing ever expands on hover.

    def _build_drawer(self):
        self.drawer_open = False

        self.drawer_overlay = DrawerOverlay(self)
        self.drawer_overlay.setObjectName("drawerOverlay")
        self.drawer_overlay.hide()
        self.drawer_overlay.clicked.connect(self._close_drawer)

        self.drawer = QFrame(self)
        self.drawer.setObjectName("sideDrawer")
        self.drawer.hide()
        drawer_layout = QVBoxLayout(self.drawer)
        drawer_layout.setContentsMargins(0, 0, 0, 0)
        drawer_layout.setSpacing(0)

        self.drawer_stack = QStackedWidget()
        drawer_layout.addWidget(self.drawer_stack)

        # ---- page 1: profile + main items ----
        page_main = QWidget()
        main_layout = QVBoxLayout(page_main)
        main_layout.setContentsMargins(0, 0, 0, 10)
        main_layout.setSpacing(4)

        profile = QFrame()
        profile.setObjectName("drawerProfile")
        profile_layout = QVBoxLayout(profile)
        profile_layout.setContentsMargins(18, 22, 18, 18)
        profile_layout.setSpacing(10)
        self.drawer_avatar = AvatarLabel("", GROUP_AVATAR_COLOR, size=60)
        self.drawer_avatar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drawer_avatar.mousePressEvent = lambda e: self.avatar_change_requested.emit()
        profile_layout.addWidget(self.drawer_avatar, alignment=Qt.AlignmentFlag.AlignLeft)
        self.drawer_name_lbl = QLabel("")
        self.drawer_name_lbl.setObjectName("drawerName")
        profile_layout.addWidget(self.drawer_name_lbl)
        self.drawer_avatar_hint_lbl = QLabel(T("change_avatar_hint"))
        self.drawer_avatar_hint_lbl.setObjectName("mutedLabel")
        self.drawer_avatar_hint_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drawer_avatar_hint_lbl.mousePressEvent = lambda e: self.avatar_change_requested.emit()
        profile_layout.addWidget(self.drawer_avatar_hint_lbl)

        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self.my_status = "online"
        self.status_chip_buttons = {}
        for key, color in (("online", "#3ddc84"), ("busy", "#e05a5a"), ("away", "#f0ad4e")):
            chip = QToolButton()
            chip.setText(T(f"status_{key}"))
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setCheckable(True)
            chip.setChecked(key == self.my_status)
            chip.setStyleSheet(
                f"QToolButton {{ border-radius: 9px; padding: 3px 9px; font-size: 8pt; "
                f"background: transparent; border: 1px solid {color}; color: {color}; }}"
                f"QToolButton:checked {{ background: {color}; color: #ffffff; }}"
            )
            chip.clicked.connect(lambda checked=False, k=key: self._on_status_chip_clicked(k))
            status_row.addWidget(chip)
            self.status_chip_buttons[key] = chip
        status_row.addStretch(1)
        profile_layout.addLayout(status_row)
        self.bio_edit = QLineEdit(self.my_bio)
        self.bio_edit.setMaxLength(80)
        self.bio_edit.setPlaceholderText(T("bio_placeholder"))
        self.bio_edit.editingFinished.connect(
            lambda: self.bio_change_requested.emit(self.bio_edit.text().strip())
        )
        profile_layout.addWidget(self.bio_edit)
        main_layout.addWidget(profile)
        main_layout.addSpacing(6)

        self.drawer_settings_row = DrawerRow(T("menu_settings"), chevron=True)
        self.drawer_settings_row.clicked.connect(
            lambda: self.drawer_stack.setCurrentWidget(self.drawer_settings_page)
        )
        main_layout.addWidget(self.drawer_settings_row)

        self.drawer_saved_row = DrawerRow(T("menu_saved_messages"))
        self.drawer_saved_row.clicked.connect(self._on_drawer_saved_clicked)
        main_layout.addWidget(self.drawer_saved_row)

        self.drawer_notes_row = DrawerRow(T("menu_notes"))
        self.drawer_notes_row.clicked.connect(lambda: self.notes_requested.emit())
        main_layout.addWidget(self.drawer_notes_row)

        self.drawer_files_row = DrawerRow(T("gallery_all"))
        self.drawer_files_row.clicked.connect(lambda: (self._close_drawer(), self._open_gallery(True)))
        main_layout.addWidget(self.drawer_files_row)

        self.drawer_mentions_row = DrawerRow(T("mentions_row"))
        self.drawer_mentions_row.clicked.connect(lambda: (self._close_drawer(), self._show_mentions()))
        main_layout.addWidget(self.drawer_mentions_row)

        self.drawer_star_row = DrawerRow(T("star_row"))
        self.drawer_star_row.clicked.connect(lambda: (self._close_drawer(), self._show_starred()))
        main_layout.addWidget(self.drawer_star_row)

        self.drawer_online_row = DrawerRow(T("online_row"))
        self.drawer_online_row.clicked.connect(lambda: (self._close_drawer(), self._show_online_panel()))
        main_layout.addWidget(self.drawer_online_row)

        self.drawer_adv_row = DrawerRow(T("adv_row"))
        self.drawer_adv_row.clicked.connect(lambda: (self._close_drawer(), self._show_advanced_search()))
        main_layout.addWidget(self.drawer_adv_row)

        self.drawer_tagged_row = DrawerRow(T("tagged_row"))
        self.drawer_tagged_row.clicked.connect(lambda: (self._close_drawer(), self._show_tagged()))
        main_layout.addWidget(self.drawer_tagged_row)

        self.drawer_contacts_row = DrawerRow(T("contacts_row"))
        self.drawer_contacts_row.clicked.connect(lambda: (self._close_drawer(), self.contacts_requested.emit()))
        main_layout.addWidget(self.drawer_contacts_row)

        self.drawer_stats_row = DrawerRow(T("stats_row"))
        self.drawer_stats_row.clicked.connect(lambda: (self._close_drawer(), self._show_stats()))
        main_layout.addWidget(self.drawer_stats_row)

        self.drawer_random_row = DrawerRow(T("random_row"))
        self.drawer_random_row.clicked.connect(lambda: (self._close_drawer(), self._random_chat()))
        main_layout.addWidget(self.drawer_random_row)

        self.drawer_games_row = DrawerRow(T("extras_games_btn"))
        self.drawer_games_row.clicked.connect(lambda: self.games_requested.emit())
        main_layout.addWidget(self.drawer_games_row)

        self.drawer_language_test_row = DrawerRow(T("extras_language_test_btn"))
        self.drawer_language_test_row.clicked.connect(lambda: self.language_test_requested.emit())
        main_layout.addWidget(self.drawer_language_test_row)

        self.drawer_rates_row = DrawerRow(T("extras_rates_btn"))
        self.drawer_rates_row.clicked.connect(lambda: self.rates_requested.emit())
        main_layout.addWidget(self.drawer_rates_row)

        self.drawer_tools_row = DrawerRow(T("extras_tools_btn"))
        self.drawer_tools_row.clicked.connect(lambda: self.tools_requested.emit())
        main_layout.addWidget(self.drawer_tools_row)

        self.night_switch = ToggleSwitch(checked=False)
        self.night_switch.toggled.connect(self._on_night_toggle)
        self.drawer_night_row = DrawerRow(T("menu_night_mode"), right_widget=self.night_switch)
        self.drawer_night_row.clicked.connect(
            lambda: self.night_switch.setChecked(
                not self.night_switch.isChecked(), animate=True, emit=True
            )
        )
        main_layout.addWidget(self.drawer_night_row)

        main_layout.addStretch(1)
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setFrameShape(QFrame.Shape.NoFrame)
        main_scroll.setWidget(page_main)
        self.drawer_stack.addWidget(main_scroll)
        self.drawer_main_page = main_scroll

        # ---- page 2: settings (appearance + language) ----
        page_settings = QWidget()
        settings_layout = QVBoxLayout(page_settings)
        settings_layout.setContentsMargins(0, 0, 0, 10)
        settings_layout.setSpacing(4)

        back_row = DrawerRow(T("menu_settings"))
        back_row.label.setStyleSheet("font-size: 11pt; font-weight: 600; background: transparent;")
        back_btn = QToolButton()
        back_btn.setObjectName("drawerBackButton")
        back_btn.setText("\u2039")
        back_btn.clicked.connect(
            lambda: self.drawer_stack.setCurrentWidget(self.drawer_main_page)
        )
        back_row.layout().insertWidget(0, back_btn)
        back_row.clicked.connect(lambda: self.drawer_stack.setCurrentWidget(self.drawer_main_page))
        self.drawer_settings_title_lbl = back_row.label
        settings_layout.addWidget(back_row)
        settings_layout.addSpacing(6)

        self.drawer_appearance_lbl = QLabel(T("menu_appearance"))
        self.drawer_appearance_lbl.setObjectName("drawerSectionLabel")
        self.drawer_appearance_lbl.setContentsMargins(16, 6, 16, 2)
        settings_layout.addWidget(self.drawer_appearance_lbl)

        self.drawer_theme_rows = {}
        for key, t in THEMES.items():
            check = QLabel("")
            check.setObjectName("drawerCheck")
            row = DrawerRow(t["label"], right_widget=check)
            row.clicked.connect(lambda checked=False, k=key: self.theme_change_requested.emit(k))
            settings_layout.addWidget(row)
            self.drawer_theme_rows[key] = (row, check)

        settings_layout.addSpacing(10)
        self.drawer_thememode_lbl = QLabel(T("menu_theme_mode"))
        self.drawer_thememode_lbl.setObjectName("drawerSectionLabel")
        self.drawer_thememode_lbl.setContentsMargins(16, 6, 16, 2)
        settings_layout.addWidget(self.drawer_thememode_lbl)
        self.drawer_thememode_rows = {}
        for mode, key in (("manual", "theme_mode_manual"), ("system", "theme_mode_system"),
                          ("time", "theme_mode_time"), ("occasion", "theme_mode_occasion")):
            check = QLabel("")
            check.setObjectName("drawerCheck")
            row = DrawerRow(T(key), right_widget=check)
            row.clicked.connect(lambda checked=False, m=mode: self.theme_mode_change_requested.emit(m))
            settings_layout.addWidget(row)
            self.drawer_thememode_rows[mode] = (row, check)

        settings_layout.addSpacing(10)
        self.drawer_language_lbl = QLabel(T("menu_language"))
        self.drawer_language_lbl.setObjectName("drawerSectionLabel")
        self.drawer_language_lbl.setContentsMargins(16, 6, 16, 2)
        settings_layout.addWidget(self.drawer_language_lbl)

        self.drawer_lang_rows = {}
        for code, key in (("fa", "lang_fa"), ("en", "lang_en")):
            check = QLabel("\u2713" if code == CURRENT_LANG[0] else "")
            check.setObjectName("drawerCheck")
            row = DrawerRow(T(key), right_widget=check)
            row.clicked.connect(lambda checked=False, c=code: self.language_change_requested.emit(c))
            settings_layout.addWidget(row)
            self.drawer_lang_rows[code] = (row, check)

        settings_layout.addSpacing(10)
        self.drawer_fontsize_lbl = QLabel(T("menu_font_size"))
        self.drawer_fontsize_lbl.setObjectName("drawerSectionLabel")
        self.drawer_fontsize_lbl.setContentsMargins(16, 6, 16, 2)
        settings_layout.addWidget(self.drawer_fontsize_lbl)

        self.drawer_fontsize_rows = {}
        for key, label_key in (("small", "font_small"), ("medium", "font_medium"), ("large", "font_large")):
            check = QLabel("\u2713" if key == self.font_size_key else "")
            check.setObjectName("drawerCheck")
            row = DrawerRow(T(label_key), right_widget=check)
            row.clicked.connect(lambda checked=False, k=key: self.font_size_change_requested.emit(k))
            settings_layout.addWidget(row)
            self.drawer_fontsize_rows[key] = (row, check)

        settings_layout.addSpacing(10)
        self.drawer_display_lbl = QLabel(T("menu_display"))
        self.drawer_display_lbl.setObjectName("drawerSectionLabel")
        self.drawer_display_lbl.setContentsMargins(16, 6, 16, 2)
        settings_layout.addWidget(self.drawer_display_lbl)
        self.drawer_lines_row = DrawerRow(T("list_lines_row"))
        self.drawer_lines_row.clicked.connect(self._on_list_lines_clicked)
        settings_layout.addWidget(self.drawer_lines_row)
        self.drawer_dnd_row = DrawerRow(T("dnd_row"))
        self.drawer_dnd_row.clicked.connect(lambda: (self._close_drawer(), self.dnd_requested.emit()))
        settings_layout.addWidget(self.drawer_dnd_row)
        self.drawer_focus_row = DrawerRow(T("focus_row"))
        self.drawer_focus_row.clicked.connect(self._on_focus_row_clicked)
        settings_layout.addWidget(self.drawer_focus_row)
        self.drawer_present_row = DrawerRow(T("presentation_row"))
        self.drawer_present_row.clicked.connect(lambda: (self._close_drawer(), self.presentation_toggle_requested.emit()))
        settings_layout.addWidget(self.drawer_present_row)
        self.drawer_autoreply_row = DrawerRow(T("autoreply_row"))
        self.drawer_autoreply_row.clicked.connect(lambda: (self._close_drawer(), self.autoreply_requested.emit()))
        settings_layout.addWidget(self.drawer_autoreply_row)

        settings_layout.addSpacing(10)
        self.drawer_privacy_lbl = QLabel(T("menu_privacy"))
        self.drawer_privacy_lbl.setObjectName("drawerSectionLabel")
        self.drawer_privacy_lbl.setContentsMargins(16, 6, 16, 2)
        settings_layout.addWidget(self.drawer_privacy_lbl)

        self.save_history_switch = ToggleSwitch(checked=self.save_history_enabled)
        self.save_history_switch.toggled.connect(self._on_save_history_toggled)
        self.drawer_save_history_row = DrawerRow(
            T("menu_save_history"), right_widget=self.save_history_switch
        )
        self.drawer_save_history_row.clicked.connect(
            lambda: self.save_history_switch.setChecked(
                not self.save_history_switch.isChecked(), animate=True, emit=True
            )
        )
        settings_layout.addWidget(self.drawer_save_history_row)

        self.linkprev_switch = ToggleSwitch(checked=self.link_preview_enabled)
        self.linkprev_switch.toggled.connect(self._on_link_preview_toggled)
        self.drawer_linkprev_row = DrawerRow(T("menu_link_preview"), right_widget=self.linkprev_switch)
        self.drawer_linkprev_row.clicked.connect(
            lambda: self.linkprev_switch.setChecked(
                not self.linkprev_switch.isChecked(), animate=True, emit=True
            )
        )
        settings_layout.addWidget(self.drawer_linkprev_row)

        settings_layout.addSpacing(10)
        self.drawer_backup_lbl = QLabel(T("menu_backup"))
        self.drawer_backup_lbl.setObjectName("drawerSectionLabel")
        self.drawer_backup_lbl.setContentsMargins(16, 6, 16, 2)
        settings_layout.addWidget(self.drawer_backup_lbl)
        self.drawer_backup_row = DrawerRow(T("backup_export"))
        self.drawer_backup_row.clicked.connect(lambda: self.backup_requested.emit())
        settings_layout.addWidget(self.drawer_backup_row)
        self.drawer_restore_row = DrawerRow(T("backup_restore"))
        self.drawer_restore_row.clicked.connect(lambda: self.restore_requested.emit())
        settings_layout.addWidget(self.drawer_restore_row)
        self.drawer_enc_all_row = DrawerRow(T("enc_export_all"))
        self.drawer_enc_all_row.clicked.connect(lambda: (self._close_drawer(), self._export_encrypted(True)))
        settings_layout.addWidget(self.drawer_enc_all_row)
        self.drawer_enc_open_row = DrawerRow(T("enc_open"))
        self.drawer_enc_open_row.clicked.connect(lambda: (self._close_drawer(), self._open_encrypted_export()))
        settings_layout.addWidget(self.drawer_enc_open_row)

        settings_layout.addSpacing(10)
        self.drawer_security_lbl = QLabel(T("menu_security"))
        self.drawer_security_lbl.setObjectName("drawerSectionLabel")
        self.drawer_security_lbl.setContentsMargins(16, 6, 16, 2)
        settings_layout.addWidget(self.drawer_security_lbl)
        self.drawer_pin_row = DrawerRow(T("security_pin"))
        self.drawer_pin_row.clicked.connect(lambda: self.security_pin_requested.emit())
        settings_layout.addWidget(self.drawer_pin_row)
        self.drawer_autolock_row = DrawerRow(T("security_autolock"))
        self.drawer_autolock_row.clicked.connect(lambda: self.security_autolock_requested.emit())
        settings_layout.addWidget(self.drawer_autolock_row)
        self.drawer_locknow_row = DrawerRow(T("security_lock_now"))
        self.drawer_locknow_row.clicked.connect(lambda: (self._close_drawer(), self.security_lock_requested.emit()))
        settings_layout.addWidget(self.drawer_locknow_row)
        self.waiting_switch = ToggleSwitch(checked=bool(get_setting("waiting_room", False)))
        self.waiting_switch.toggled.connect(lambda v: self.waiting_room_toggled.emit(v))
        self.drawer_waiting_row = DrawerRow(T("waiting_row"), right_widget=self.waiting_switch)
        self.drawer_waiting_row.clicked.connect(
            lambda: self.waiting_switch.setChecked(not self.waiting_switch.isChecked(), animate=True, emit=True)
        )
        settings_layout.addWidget(self.drawer_waiting_row)

        settings_layout.addStretch(1)
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        settings_scroll.setWidget(page_settings)
        self.drawer_stack.addWidget(settings_scroll)
        self.drawer_settings_page = settings_scroll

        self.set_theme_checked(DEFAULT_THEME)

    def _toggle_drawer(self):
        self._close_drawer() if self.drawer_open else self._open_drawer()

    def _open_drawer(self):
        self.drawer_name_lbl.setText(self.my_name)
        self.drawer_avatar.set_identity(self.my_name or "", avatar_color_for(self.my_name or "?"))
        self.drawer_avatar.set_image(self.my_avatar_pixmap)
        self.drawer_stack.setCurrentWidget(self.drawer_main_page)

        width = max(240, int(self.width() * 0.56))
        height = self.height()
        self.drawer_overlay.setGeometry(0, 0, self.width(), height)
        self.drawer_overlay.show()
        self.drawer.setGeometry(-width, 0, width, height)
        self.drawer.show()
        self.drawer_overlay.raise_()
        self.drawer.raise_()

        anim = QPropertyAnimation(self.drawer, b"geometry", self)
        anim.setDuration(220)
        anim.setStartValue(QRect(-width, 0, width, height))
        anim.setEndValue(QRect(0, 0, width, height))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._drawer_anim = anim
        self.drawer_open = True

    def _close_drawer(self):
        if not self.drawer_open:
            return
        self.drawer_open = False
        self.drawer_overlay.hide()
        width = self.drawer.width()
        anim = QPropertyAnimation(self.drawer, b"geometry", self)
        anim.setDuration(180)
        anim.setStartValue(self.drawer.geometry())
        anim.setEndValue(QRect(-width, 0, width, self.drawer.height()))
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.finished.connect(self.drawer.hide)
        anim.start()
        self._drawer_anim = anim

    def _on_drawer_saved_clicked(self):
        self._close_drawer()
        self.open_private(SAVED_MESSAGES_KEY)

    def _on_night_toggle(self, checked):
        self.theme_change_requested.emit("dark_modern" if checked else "light_clean")

    def _on_save_history_toggled(self, checked):
        self.save_history_enabled = checked
        settings = load_app_settings()
        settings["save_history"] = checked
        save_app_settings(settings)

    def set_theme_checked(self, key):
        for k, (row, check) in self.drawer_theme_rows.items():
            check.setText("\u2713" if k == key else "")
        self.night_switch.set_on_color(THEMES[key]["accent"])
        if key in ("dark_modern", "light_clean"):
            self.night_switch.setChecked(key == "dark_modern", animate=True, emit=False)

    def set_theme_mode_checked(self, mode):
        for m, (row, check) in self.drawer_thememode_rows.items():
            check.setText("\u2713" if m == mode else "")

    def set_reconnecting(self, is_reconnecting):
        self.reconnect_banner.setVisible(is_reconnecting)

    def set_font_size_checked(self, key):
        self.font_size_key = key
        for k, (row, check) in self.drawer_fontsize_rows.items():
            check.setText("\u2713" if k == key else "")

    def _on_status_chip_clicked(self, key):
        self.my_status = key
        for k, chip in self.status_chip_buttons.items():
            chip.setChecked(k == key)
        self.status_change_requested.emit(key)

    # ----- language -----

    def retranslate_ui(self):
        self.search_edit.setPlaceholderText(T("chats_search_placeholder"))
        self.chat_search_edit.setPlaceholderText(T("search_in_chat_placeholder"))
        self.drawer_settings_row.label.setText(T("menu_settings"))
        self.drawer_saved_row.label.setText(T("menu_saved_messages"))
        self.drawer_games_row.label.setText(T("extras_games_btn"))
        self.drawer_language_test_row.label.setText(T("extras_language_test_btn"))
        self.drawer_rates_row.label.setText(T("extras_rates_btn"))
        self.drawer_tools_row.label.setText(T("extras_tools_btn"))
        self.drawer_notes_row.label.setText(T("menu_notes"))
        self.drawer_files_row.label.setText(T("gallery_all"))
        self.drawer_mentions_row.label.setText(T("mentions_row"))
        self.drawer_star_row.label.setText(T("star_row"))
        self.drawer_online_row.label.setText(T("online_row"))
        self.drawer_adv_row.label.setText(T("adv_row"))
        self.drawer_tagged_row.label.setText(T("tagged_row"))
        self.drawer_contacts_row.label.setText(T("contacts_row"))
        self.drawer_stats_row.label.setText(T("stats_row"))
        self.drawer_random_row.label.setText(T("random_row"))
        self.bio_edit.setPlaceholderText(T("bio_placeholder"))
        self.select_forward_btn.setText(T("select_forward"))
        self.select_copy_btn.setText(T("select_copy"))
        self.select_delete_btn.setText(T("select_delete"))
        self.drawer_linkprev_row.label.setText(T("menu_link_preview"))
        self.new_group_btn.setToolTip(T("new_group_tooltip"))
        self.chat_menu_btn.setToolTip(T("chat_menu_tooltip"))
        self.sticker_btn.setToolTip(T("sticker_tooltip"))
        self.mic_btn.setToolTip(T("voice_tooltip"))
        self.ptt_btn.setToolTip(T("ptt_tooltip"))
        self.group_info_btn.setToolTip(T("group_info_tooltip"))
        self.drawer_night_row.label.setText(T("menu_night_mode"))
        self.drawer_settings_title_lbl.setText(T("menu_settings"))
        self.drawer_appearance_lbl.setText(T("menu_appearance"))
        self.drawer_language_lbl.setText(T("menu_language"))
        self.drawer_fontsize_lbl.setText(T("menu_font_size"))
        for code, (row, check) in self.drawer_lang_rows.items():
            row.label.setText(T("lang_fa" if code == "fa" else "lang_en"))
            check.setText("\u2713" if code == CURRENT_LANG[0] else "")
        for key, (row, check) in self.drawer_fontsize_rows.items():
            row.label.setText(T({"small": "font_small", "medium": "font_medium", "large": "font_large"}[key]))
        self.drawer_privacy_lbl.setText(T("menu_privacy"))
        self.drawer_display_lbl.setText(T("menu_display"))
        self.drawer_lines_row.label.setText(T("list_lines_row"))
        self.drawer_dnd_row.label.setText(T("dnd_row"))
        self.drawer_focus_row.label.setText(T("focus_row"))
        self.drawer_present_row.label.setText(T("presentation_row"))
        self.drawer_autoreply_row.label.setText(T("autoreply_row"))
        self.drawer_thememode_lbl.setText(T("menu_theme_mode"))
        for mode, key in (("manual", "theme_mode_manual"), ("system", "theme_mode_system"),
                          ("time", "theme_mode_time"), ("occasion", "theme_mode_occasion")):
            self.drawer_thememode_rows[mode][0].label.setText(T(key))
        self.drawer_backup_lbl.setText(T("menu_backup"))
        self.drawer_backup_row.label.setText(T("backup_export"))
        self.drawer_restore_row.label.setText(T("backup_restore"))
        self.drawer_enc_all_row.label.setText(T("enc_export_all"))
        self.drawer_enc_open_row.label.setText(T("enc_open"))
        self.drawer_security_lbl.setText(T("menu_security"))
        self.drawer_pin_row.label.setText(T("security_pin"))
        self.drawer_autolock_row.label.setText(T("security_autolock"))
        self.drawer_locknow_row.label.setText(T("security_lock_now"))
        self.drawer_waiting_row.label.setText(T("waiting_row"))
        self.drawer_save_history_row.label.setText(T("menu_save_history"))
        self.export_chat_btn.setToolTip(T("export_chat_tooltip"))
        self.empty_text.setText(T("empty_state_text"))
        self.empty_games_btn.setText(T("extras_games_btn"))
        self.empty_language_test_btn.setText(T("extras_language_test_btn"))
        self.empty_rates_btn.setText(T("extras_rates_btn"))
        self.empty_tools_btn.setText(T("extras_tools_btn"))
        self.reconnect_banner.setText(T("reconnect_banner"))
        self._update_ttl_ui()
        if self._room_is_host is not None:
            self._update_room_title()
        elif self.current_target == EVERYONE:
            self.chat_title.setText(self._room_title)
        if self.current_target == SAVED_MESSAGES_KEY:
            self.chat_title.setText(T("saved_messages_title"))

    def _on_sidebar_select(self, key):
        # kept for backward references; not used directly any more
        pass

    # ----- global search (across every chat) -----

    def _chat_title_for(self, key):
        if key == EVERYONE:
            return T("group_title")
        if key == SAVED_MESSAGES_KEY:
            return T("saved_messages_title")
        if is_custom_group(key):
            return self.groups.get(key[len(GROUP_PREFIX):], {}).get("name", key)
        return key

    @staticmethod
    def _snippet(text, needle, width=70):
        flat = " ".join(text.split())
        idx = max(0, flat.lower().find(needle))
        start = max(0, idx - 20)
        piece = flat[start:start + width]
        return ("\u2026" if start > 0 else "") + piece + ("\u2026" if start + width < len(flat) else "")

    def _on_search_changed(self, text):
        needle = text.strip().lower()
        self.search_results.clear()
        if not needle:
            self.search_results.setVisible(False)
            self.members_scroll.setVisible(True)
            return
        self.members_scroll.setVisible(False)
        self.search_results.setVisible(True)

        for key in list(self.sidebar_rows.keys()):
            title = self._chat_title_for(key)
            if needle in title.lower():
                item = QListWidgetItem("\U0001F4AC " + title)
                item.setData(Qt.ItemDataRole.UserRole, {"key": key, "msg_id": None, "needle": needle})
                self.search_results.addItem(item)

        shown = 0
        for mid, info in reversed(list(self.messages_by_id.items())):
            if info["deleted"]:
                continue
            raw = info["bubble"].raw_text
            if needle not in raw.lower():
                continue
            title = self._chat_title_for(info["chat_key"])
            item = QListWidgetItem(
                f"{title} \u00b7 {info['sender']} \u00b7 {info.get('ts', '')}\n{self._snippet(raw, needle)}"
            )
            item.setData(Qt.ItemDataRole.UserRole, {"key": info["chat_key"], "msg_id": mid, "needle": needle})
            self.search_results.addItem(item)
            shown += 1
            if shown >= 60:
                break

        if self.search_results.count() == 0:
            empty = QListWidgetItem(T("search_global_no_results"))
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.search_results.addItem(empty)

    def _on_search_result_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        key = data["key"]
        if key == EVERYONE:
            self.open_group()
        else:
            self.open_private(key)
        msg_id = data.get("msg_id")
        if msg_id:
            # Reuse the in-chat search bar to highlight the hit and jump to it.
            self.chat_search_bar.setVisible(True)
            self.chat_search_edit.setText(data["needle"])
            info = self.messages_by_id.get(msg_id)
            if info and info["bubble"] in self.chat_search_matches:
                self.chat_search_index = self.chat_search_matches.index(info["bubble"])
                self._show_chat_search_match()
        if msg_id:
            QTimer.singleShot(80, lambda m=msg_id: self._scroll_to_message(m))

    # ----- self-destructing messages -----

    def _ttl_label(self, secs):
        for value, key in TTL_OPTIONS:
            if value == secs:
                return T(key)
        return ""

    def _update_ttl_ui(self):
        ttl = self.chat_ttl.get(self.current_target, 0) if self.current_target is not None else 0
        self.ttl_btn.setText("\u23F1" + (f" {TTL_SHORT.get(ttl, '')}" if ttl else ""))
        self.ttl_btn.setToolTip(T("ttl_tooltip"))
        placeholder = T("compose_placeholder")
        if ttl:
            placeholder += T("ttl_placeholder_suffix").format(t=self._ttl_label(ttl))
        self.message_edit.setPlaceholderText(placeholder)

    def _on_ttl_clicked(self):
        if self.current_target is None:
            return
        current = self.chat_ttl.get(self.current_target, 0)
        menu = QMenu(self)
        title_action = menu.addAction(T("ttl_menu_title"))
        title_action.setEnabled(False)
        menu.addSeparator()
        actions = {}
        for value, key in TTL_OPTIONS:
            label = ("\u2713 " if value == current else "") + T(key)
            actions[menu.addAction(label)] = value
        chosen = menu.exec(QCursor.pos())
        if chosen in actions:
            self.chat_ttl[self.current_target] = actions[chosen]
            self._update_ttl_ui()

    def _schedule_expiry(self, chat_key, msg_id, ttl, container):
        QTimer.singleShot(
            int(ttl * 1000), lambda: self._expire_message(chat_key, msg_id, container)
        )

    def _expire_message(self, chat_key, msg_id, container):
        """Remove a self-destructing message (or file) from the screen and
        forget it everywhere on this computer."""
        try:
            container.hide()
            container.deleteLater()
        except RuntimeError:
            return  # already gone
        if not msg_id:
            return
        info = self.messages_by_id.pop(msg_id, None)
        self.reactions_by_msg.pop(msg_id, None)
        if info:
            bubble = info["bubble"]
            self.bubbles = [(w, k) for (w, k) in self.bubbles if w is not bubble]
            lst = self.chat_bubbles.get(chat_key, [])
            if bubble in lst:
                lst.remove(bubble)
            if bubble in self.chat_search_matches:
                self.chat_search_matches = [b for b in self.chat_search_matches if b is not bubble]
                self.chat_search_index = min(self.chat_search_index, len(self.chat_search_matches) - 1)
            tick = info.get("tick")
            if tick is not None:
                for ticks in self.own_tick_labels.values():
                    if tick in ticks:
                        ticks.remove(tick)
        if any(p["msg_id"] == msg_id for p in self.pinned_by_chat.get(chat_key, [])):
            self.apply_pin_local(chat_key, msg_id, None, None, unpin=True)
        if self.replying_to and self.replying_to.get("msg_id") == msg_id:
            self._cancel_reply_edit()
        if self.last_message_id.get(chat_key) == msg_id:
            self.last_messages[chat_key] = ""
            self._update_row_preview(chat_key)

    # ----- groups -----

    def _set_chat_desc(self, text):
        text = (text or "").strip()
        self._base_desc = text
        if len(text) > 90:
            text = text[:90] + "\u2026"
        self.chat_desc_lbl.setText(text)
        self.chat_desc_lbl.setVisible(bool(text))

    def _rebuild_sidebar(self):
        if self._last_update_members_args is not None:
            self.update_members(*self._last_update_members_args)

    def register_group(self, group):
        self.groups[group["id"]] = group
        self._rebuild_sidebar()

    def remove_group(self, gid):
        key = GROUP_PREFIX + gid
        self.groups.pop(gid, None)
        self.last_messages.pop(key, None)
        if self.current_target == key:
            self.open_group()
        self._rebuild_sidebar()

    def group_changed(self, gid):
        key = GROUP_PREFIX + gid
        if self.current_target == key:
            self._show_group_header(key)
        self._rebuild_sidebar()

    def set_main_group_info(self, desc, avatar):
        self.main_group_info = {"desc": desc, "avatar": avatar}
        if self.current_target == EVERYONE:
            self.chat_avatar.set_identity("", GROUP_AVATAR_COLOR)
            self.chat_avatar.set_image(pixmap_from_b64(avatar))
            self._set_chat_desc(desc)
        self._rebuild_sidebar()

    def _show_group_header(self, key):
        g = self.groups.get(key[len(GROUP_PREFIX):], {})
        self.chat_avatar.set_identity(g.get("name", ""), group_color(g.get("id", "g")))
        self.chat_avatar.set_image(pixmap_from_b64(g.get("avatar", "")))
        self.chat_title.setText(g.get("name", "") + (" \U0001F4E2" if g.get("readonly") else ""))
        self._set_chat_desc(g.get("desc", ""))
        self.compose_bar.setVisible(not self._is_readonly(key))

    def _on_new_group_clicked(self):
        candidates = [n for n in self.member_names if n != self.my_name]
        if not candidates:
            QMessageBox.information(self, T("new_group_title"), T("group_no_one_online"))
            return
        dlg = CreateGroupDialog(candidates, self)
        if dlg.exec():
            name, desc, avatar, members = dlg.values()
            self.group_create_requested.emit(name, desc, avatar, members, dlg.readonly_check.isChecked())

    def _on_group_info_clicked(self):
        target = self.current_target
        if target == EVERYONE:
            lines = [
                n + (T("group_host_tag") if n == self.current_host_name else "")
                for n in self.member_names
            ]
            can_edit = self.is_host_flag
            dlg = GroupInfoDialog(
                T("group_title"), self.main_group_info.get("desc", ""),
                self.main_group_info.get("avatar", ""), lines, can_edit=can_edit,
                editable_name=False, can_leave=False,
                edit_denied_text=T("group_only_host_edit"), parent=self,
            )
            if dlg.exec() and can_edit:
                _name, desc, avatar = dlg.values()
                self.main_group_info_change_requested.emit(desc, avatar)
        elif is_custom_group(target):
            gid = target[len(GROUP_PREFIX):]
            g = self.groups.get(gid)
            if not g:
                return
            lines = [
                n + (T("group_owner_tag") if n == g["owner"] else "") for n in g["members"]
            ]
            can_edit = (g["owner"] == self.my_name)
            dlg = GroupInfoDialog(
                g["name"], g.get("desc", ""), g.get("avatar", ""), lines, can_edit=can_edit,
                editable_name=True, can_leave=True,
                edit_denied_text=T("group_only_owner_edit"), color=group_color(gid), parent=self,
            )
            if dlg.exec():
                if dlg.leave_requested:
                    self.group_leave_requested.emit(gid)
                elif can_edit:
                    name, desc, avatar = dlg.values()
                    self.group_update_requested.emit(gid, name or g["name"], desc, avatar)

    def _on_send_clicked(self):
        text = self.message_edit.text().strip()
        if not text or self.current_target is None:
            return
        if self.editing_msg_id is not None:
            msg_id = self.editing_msg_id
            info = self.messages_by_id.get(msg_id)
            self.editing_msg_id = None
            self.message_edit.clear()
            self._update_compose_banner()
            if info is None or info["deleted"]:
                return
            self.edit_submit_requested.emit(msg_id, info["chat_key"], text)
            return
        if text.startswith("/") and not text.startswith("//"):
            replacement = self._handle_slash(text)
            self.message_edit.clear()
            if replacement is None:
                return
            text = replacement
        extra = {}
        if self.replying_to is not None:
            extra = {
                "reply_to": self.replying_to["msg_id"],
                "reply_from": self.replying_to["sender"],
                "reply_text": self.replying_to["text"],
            }
        self.replying_to = None
        self._update_compose_banner()
        extra["ttl"] = self.chat_ttl.get(self.current_target, 0)
        self.send_requested.emit(text, self.current_target, extra)
        self.message_edit.clear()

    def _on_text_changed(self):
        text = self.message_edit.text()
        if not text or self.current_target in (None, SAVED_MESSAGES_KEY):
            return
        now = time.time()
        if now - self._last_typing_sent > 2.0:
            self._last_typing_sent = now
            self.typing_requested.emit(self.current_target)

    # ----- reply / edit / delete / forward / pin -----

    def _update_compose_banner(self):
        if self.editing_msg_id is not None:
            self.compose_banner_label.setText(T("editing_label"))
            self.compose_banner.setVisible(True)
        elif self.replying_to is not None:
            self.compose_banner_label.setText(
                T("reply_preview_label").format(name=self.replying_to["sender"])
                + f" \u2014 {self.replying_to['text']}"
            )
            self.compose_banner.setVisible(True)
        else:
            self.compose_banner.setVisible(False)

    def _cancel_reply_edit(self):
        self.replying_to = None
        self.editing_msg_id = None
        self.message_edit.clear()
        self._update_compose_banner()

    def _start_reply(self, msg_id):
        info = self.messages_by_id.get(msg_id)
        if not info or info["deleted"]:
            return
        preview = info["bubble"].raw_text
        if len(preview) > 60:
            preview = preview[:60] + "\u2026"
        self.editing_msg_id = None
        self.replying_to = {"msg_id": msg_id, "sender": info["sender"], "text": preview}
        self._update_compose_banner()
        self.message_edit.setFocus()

    def _start_edit(self, msg_id):
        info = self.messages_by_id.get(msg_id)
        if not info or not info["is_own"] or info["deleted"]:
            return
        self.replying_to = None
        self.editing_msg_id = msg_id
        self.message_edit.setPlainText(info["bubble"].raw_text)
        cursor = self.message_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.message_edit.setTextCursor(cursor)
        self._update_compose_banner()
        self.message_edit.setFocus()

    def _request_delete(self, msg_id):
        info = self.messages_by_id.get(msg_id)
        if not info or not info["is_own"] or info["deleted"]:
            return
        self.delete_requested.emit(msg_id, info["chat_key"])

    def apply_edit_local(self, msg_id, new_text):
        info = self.messages_by_id.get(msg_id)
        if not info or info["deleted"]:
            return
        info["bubble"].mark_edited(new_text)
        key = info["chat_key"]
        if self.last_messages.get(key) is not None:
            self._update_row_preview(key)

    def apply_delete_local(self, msg_id):
        info = self.messages_by_id.get(msg_id)
        if not info or info["deleted"]:
            return
        info["deleted"] = True
        info["bubble"].mark_deleted()
        if any(p["msg_id"] == msg_id for p in self.pinned_by_chat.get(info["chat_key"], [])):
            self.apply_pin_local(info["chat_key"], msg_id, None, None, unpin=True)

    def _start_forward(self, msg_id):
        info = self.messages_by_id.get(msg_id)
        if not info or info["deleted"]:
            return
        menu = QMenu(self)
        actions = {}
        group_action = menu.addAction(T("group_title"))
        actions[group_action] = EVERYONE
        saved_action = menu.addAction(T("saved_messages_title"))
        actions[saved_action] = SAVED_MESSAGES_KEY
        for name in self.member_names:
            action = menu.addAction(name)
            actions[action] = name
        for gid, g in self.groups.items():
            action = menu.addAction("\U0001F465 " + g["name"])
            actions[action] = GROUP_PREFIX + gid
        chosen = menu.exec(QCursor.pos())
        target = actions.get(chosen)
        if target is None:
            return
        self.forward_to_requested.emit(info["sender"], info["bubble"].raw_text, target)

    def _request_pin(self, msg_id):
        info = self.messages_by_id.get(msg_id)
        if not info or info["deleted"]:
            return
        self.pin_toggle_requested.emit(msg_id, info["chat_key"])

    def apply_pin_local(self, chat_key, msg_id, sender, text, unpin=False):
        """Up to 10 pinned messages per chat. msg_id None clears them all;
        unpin=True removes just that one; otherwise it is added."""
        lst = self.pinned_by_chat.setdefault(chat_key, [])
        if msg_id is None:
            lst.clear()
        elif unpin:
            lst[:] = [p for p in lst if p["msg_id"] != msg_id]
        elif not any(p["msg_id"] == msg_id for p in lst):
            lst.append({"msg_id": msg_id, "sender": sender, "text": text})
            del lst[:-10]
        self._pin_index[chat_key] = len(lst) - 1
        if chat_key == self.current_target:
            self._refresh_pin_banner()

    # ----- emoji reactions -----

    def _request_react(self, msg_id, emoji):
        info = self.messages_by_id.get(msg_id)
        if not info or info["deleted"]:
            return
        reactions = self.reactions_by_msg.setdefault(msg_id, {})
        names = reactions.setdefault(emoji, set())
        if self.my_name in names:
            action = "remove"
            names.discard(self.my_name)
        else:
            action = "add"
            names.add(self.my_name)
        if not names:
            del reactions[emoji]
        self._render_reactions(msg_id)
        self.reaction_toggle_requested.emit(msg_id, info["chat_key"], emoji, action)

    def apply_reaction_local(self, from_name, msg_id, emoji, action):
        if msg_id not in self.messages_by_id:
            return  # a reaction on a message we haven't rendered (yet, or ever) - ignore
        reactions = self.reactions_by_msg.setdefault(msg_id, {})
        names = reactions.setdefault(emoji, set())
        if action == "add":
            names.add(from_name)
        else:
            names.discard(from_name)
        if not names:
            del reactions[emoji]
        self._render_reactions(msg_id)

    def _render_reactions(self, msg_id):
        info = self.messages_by_id.get(msg_id)
        if not info:
            return
        chips_layout = info["reactions_layout"]
        container = info["reactions_container"]
        while chips_layout.count():
            item = chips_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        reactions = self.reactions_by_msg.get(msg_id, {})
        if not reactions:
            container.setVisible(False)
            return
        for emoji, names in reactions.items():
            if not names:
                continue
            chip = QToolButton()
            chip.setObjectName("reactionChipMine" if self.my_name in names else "reactionChip")
            chip.setText(f"{emoji} {len(names)}" if len(names) > 1 else emoji)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setToolTip(", ".join(sorted(names)))
            chip.clicked.connect(lambda checked=False, m=msg_id, e=emoji: self._request_react(m, e))
            chips_layout.addWidget(chip)
        container.setVisible(True)

    def _refresh_pin_banner(self):
        lst = self.pinned_by_chat.get(self.current_target) or []
        if not lst:
            self.pin_banner.setVisible(False)
            return
        idx = min(max(self._pin_index.get(self.current_target, len(lst) - 1), 0), len(lst) - 1)
        pinned = lst[idx]
        preview = pinned["text"] or ""
        if len(preview) > 50:
            preview = preview[:50] + "\u2026"
        counter = f"{idx + 1}/{len(lst)}  " if len(lst) > 1 else ""
        self.pin_banner_label.setText(
            counter + (f"{pinned['sender']}: {preview}" if preview else T("pinned_label"))
        )
        self.pin_banner.setVisible(True)

    def _jump_to_pinned(self):
        lst = self.pinned_by_chat.get(self.current_target) or []
        if not lst:
            return
        idx = min(max(self._pin_index.get(self.current_target, len(lst) - 1), 0), len(lst) - 1)
        self._scroll_to_message(lst[idx]["msg_id"])
        self._pin_index[self.current_target] = (idx - 1) % len(lst)   # next click shows the previous pin
        self._refresh_pin_banner()

    def _on_unpin_clicked(self):
        lst = self.pinned_by_chat.get(self.current_target) or []
        if not lst or self.current_target is None:
            return
        idx = min(max(self._pin_index.get(self.current_target, len(lst) - 1), 0), len(lst) - 1)
        self.pin_toggle_requested.emit(lst[idx]["msg_id"], self.current_target)

    def _scroll_to_message(self, msg_id):
        info = self.messages_by_id.get(msg_id)
        if not info:
            return
        bubble = info["bubble"]
        area = self.chat_stack.currentWidget()
        if area is not None and hasattr(area, "ensureWidgetVisible"):
            area.ensureWidgetVisible(bubble, 40, 80)

    def set_room_role(self, is_host, host_name):
        self._room_is_host = is_host
        self._room_host_name = host_name
        self._update_room_title()

    def _update_room_title(self):
        role = T("role_host") if self._room_is_host else self._room_host_name
        self._room_title = f"{T('group_title')} \u2022 {role}"
        if self.current_target == EVERYONE:
            self.chat_title.setText(self._room_title)

    # ----- navigation between chats -----

    def _on_row_left_click(self, key, pos):
        if key in (EVERYONE, SAVED_MESSAGES_KEY) or is_custom_group(key):
            self._open_pinned(key)
            return
        self._show_member_menu(key, pos)

    def _on_row_right_click(self, key, pos):
        if key in (EVERYONE, SAVED_MESSAGES_KEY) or is_custom_group(key):
            self._open_pinned(key)
            return
        self.open_private(key)

    def _open_pinned(self, key):
        if key == EVERYONE:
            self.open_group()
        else:
            self.open_private(key)

    def _show_member_menu(self, name, pos):
        menu = QMenu(self)
        can_kick = self.is_host_flag or self.my_name in self.admins
        kick_action = menu.addAction(T("ctx_kick")) if can_kick else None
        admin_action = guest_action = None
        if self.is_host_flag:
            admin_action = menu.addAction(T("ctx_remove_admin") if name in self.admins else T("ctx_make_admin"))
            guest_action = menu.addAction(T("ctx_remove_guest") if name in self.guests else T("ctx_make_guest"))
        is_muted = name in self.muted_names
        mute_action = menu.addAction(T("ctx_unmute") if is_muted else T("ctx_mute"))
        chosen = menu.exec(pos)
        if chosen is None:
            return
        if kick_action is not None and chosen == kick_action:
            self.kick_requested.emit(name)
        elif admin_action is not None and chosen == admin_action:
            self.admin_toggle_requested.emit(name)
        elif guest_action is not None and chosen == guest_action:
            self.guest_toggle_requested.emit(name)
        elif chosen == mute_action:
            self._toggle_mute(name)

    def _toggle_mute(self, name):
        if name in self.muted_names:
            self.muted_names.discard(name)
        else:
            self.muted_names.add(name)

    def _leave_current_chat_search(self):
        self._exit_select_mode()
        self._purge_incognito(self.current_target)
        if self.chat_search_bar.isVisible():
            self.chat_search_bar.setVisible(False)
        self.chat_search_edit.blockSignals(True)
        self.chat_search_edit.clear()
        self.chat_search_edit.blockSignals(False)
        self.chat_search_matches = []
        self.chat_search_index = -1
        self.chat_search_status.setText("")

    def _mark_read(self, key):
        if self.unread_counts.get(key):
            self.unread_counts[key] = 0
            row = self.sidebar_rows.get(key)
            if row is not None:
                row.set_badge(0)

    def open_group(self):
        self._leave_current_chat_search()
        self._cancel_reply_edit()
        self._maybe_load_history(EVERYONE)
        self.compose_bar.setVisible(True)
        self.current_target = EVERYONE
        self.chat_stack.setCurrentWidget(self.group_scroll)
        self.back_btn.setVisible(False)
        self.chat_avatar.setVisible(True)
        self.chat_search_btn.setVisible(True)
        self.export_chat_btn.setVisible(True)
        self.security_code_btn.setVisible(False)
        self.group_info_btn.setVisible(True)
        self.ttl_btn.setVisible(True)
        self.chat_menu_btn.setVisible(True)
        self.chat_avatar.set_identity("", GROUP_AVATAR_COLOR)
        self.chat_avatar.set_image(pixmap_from_b64(self.main_group_info.get("avatar", "")))
        self.chat_title.setText(self._room_title)
        self._set_chat_desc(self.main_group_info.get("desc", ""))
        self._update_ttl_ui()
        self._apply_chat_bg(self.current_target)
        self._refresh_compose_visibility()
        self._highlight_selected()
        self._scroll_current_to_bottom()
        self._mark_read(EVERYONE)
        self._refresh_pin_banner()

    def open_private(self, name):
        self._leave_current_chat_search()
        self._cancel_reply_edit()
        self._maybe_load_history(name)
        self.compose_bar.setVisible(True)
        self._ensure_private_page(name)
        self.current_target = name
        self.chat_stack.setCurrentWidget(self.private_pages[name]["scroll"])
        self.back_btn.setVisible(True)
        self.chat_avatar.setVisible(True)
        self.chat_search_btn.setVisible(True)
        self.export_chat_btn.setVisible(True)
        self.ttl_btn.setVisible(True)
        self.chat_menu_btn.setVisible(True)
        self.group_info_btn.setVisible(is_custom_group(name))
        self._set_chat_desc("")
        if name == SAVED_MESSAGES_KEY:
            self.chat_avatar.set_identity("\U0001F516", "#6c8cff")
            self.chat_title.setText(T("saved_messages_title"))
            self.security_code_btn.setVisible(False)
        elif is_custom_group(name):
            self._show_group_header(name)
            self.security_code_btn.setVisible(False)
        else:
            self.chat_avatar.set_identity(name, avatar_color_for(name))
            self.chat_avatar.set_image(pixmap_from_b64(self.peer_avatars.get(name, "")))
            self.chat_title.setText(name)
            self._set_chat_desc(self.peer_bios.get(name, ""))
            self.seen_requested.emit(name)
            self.security_code_btn.setVisible(True)
        self._update_ttl_ui()
        self._apply_chat_bg(self.current_target)
        self._refresh_compose_visibility()
        self._highlight_selected()
        self._scroll_current_to_bottom()
        self.typing_until.pop(name, None)
        self._mark_read(name)
        self._refresh_pin_banner()

    # ----- link previews -----

    def _on_link_preview_toggled(self, checked):
        self.link_preview_enabled = checked
        set_setting("link_previews", checked)

    def _start_link_preview(self, wrapper, url, is_own):
        label = QLabel("")
        label.setObjectName("replyQuote")
        label.setWordWrap(True)
        label.setMaximumWidth(380)
        label.setVisible(False)
        wrapper.addWidget(
            label, alignment=Qt.AlignmentFlag.AlignRight if is_own else Qt.AlignmentFlag.AlignLeft
        )
        worker = LinkPreviewWorker(label, url)
        worker.ready.connect(self._on_link_preview_ready)
        self._link_workers.append(worker)
        threading.Thread(target=worker.run, daemon=True).start()

    def _on_link_preview_ready(self, label, text):
        try:
            label.setText(text)
            label.setVisible(True)
        except RuntimeError:
            pass  # the message was deleted meanwhile

    # ----- multi-select (batch forward / copy / delete) -----

    def _enter_select_mode(self, msg_id=None):
        if self.current_target is None:
            return
        self.select_mode = True
        self.selected_ids = set()
        for b in self.chat_bubbles.get(self.current_target, []):
            b.select_mode = True
        self.compose_bar.setVisible(False)
        self.select_bar.setVisible(True)
        if msg_id:
            self._toggle_select(msg_id)
        else:
            self._update_select_bar()

    def _exit_select_mode(self):
        if not self.select_mode:
            return
        self.select_mode = False
        for mid in list(self.selected_ids):
            info = self.messages_by_id.get(mid)
            if info:
                self._set_picked(info["bubble"], False)
        self.selected_ids = set()
        for lst in self.chat_bubbles.values():
            for b in lst:
                b.select_mode = False
        self.select_bar.setVisible(False)
        self.compose_bar.setVisible(self.current_target is not None and not self._is_readonly(self.current_target))

    @staticmethod
    def _set_picked(bubble, picked):
        try:
            bubble.setProperty("picked", picked)
            bubble.style().unpolish(bubble)
            bubble.style().polish(bubble)
        except RuntimeError:
            pass

    def _toggle_select(self, msg_id):
        info = self.messages_by_id.get(msg_id)
        if not info or info["deleted"]:
            return
        if msg_id in self.selected_ids:
            self.selected_ids.discard(msg_id)
            self._set_picked(info["bubble"], False)
        else:
            self.selected_ids.add(msg_id)
            self._set_picked(info["bubble"], True)
        self._update_select_bar()

    def _update_select_bar(self):
        n = len(self.selected_ids)
        self.select_count_lbl.setText(T("select_count").format(n=n))
        self.select_forward_btn.setEnabled(n > 0)
        self.select_copy_btn.setEnabled(n > 0)
        self.select_delete_btn.setEnabled(n > 0)

    def _selected_in_order(self):
        return [m for m in self.messages_by_id if m in self.selected_ids]

    def _pick_chat_target(self):
        menu = QMenu(self)
        actions = {}
        actions[menu.addAction(T("group_title"))] = EVERYONE
        actions[menu.addAction(T("saved_messages_title"))] = SAVED_MESSAGES_KEY
        for name in self.member_names:
            if name != self.my_name:
                actions[menu.addAction(name)] = name
        for gid, g in self.groups.items():
            actions[menu.addAction("\U0001F465 " + g["name"])] = GROUP_PREFIX + gid
        return actions.get(menu.exec(QCursor.pos()))

    def _forward_selected(self):
        ids = self._selected_in_order()
        if not ids:
            return
        target = self._pick_chat_target()
        if target is None:
            return
        for mid in ids:
            info = self.messages_by_id.get(mid)
            if info and not info["deleted"]:
                self.forward_to_requested.emit(info["sender"], info["bubble"].raw_text, target)
        self._exit_select_mode()

    def _copy_selected(self):
        lines = []
        for mid in self._selected_in_order():
            info = self.messages_by_id.get(mid)
            if info and not info["deleted"]:
                lines.append(f"{info['sender']}: {info['bubble'].raw_text}")
        QApplication.clipboard().setText("\n".join(lines))
        self._exit_select_mode()

    def _delete_selected(self):
        own = [m for m in self._selected_in_order()
               if self.messages_by_id[m]["is_own"] and not self.messages_by_id[m]["deleted"]]
        if not own:
            return
        if QMessageBox.question(self, T("select_delete"), T("select_delete_confirm")) \
                != QMessageBox.StandardButton.Yes:
            return
        for mid in own:
            self.delete_requested.emit(mid, self.messages_by_id[mid]["chat_key"])
        self._exit_select_mode()

    # ----- scheduled messages -----

    def _persist_scheduled(self):
        set_setting("scheduled", self.scheduled)

    def _attach_schedule(self):
        text = self.message_edit.text().strip()
        if not text or self.current_target is None:
            QMessageBox.information(self, T("schedule_title"), T("schedule_need_text"))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(T("schedule_title"))
        lay = QVBoxLayout(dlg)
        when = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        when.setCalendarPopup(True)
        when.setDisplayFormat("yyyy-MM-dd  HH:mm")
        lay.addWidget(when)
        ok_btn = QPushButton(T("schedule_ok"))
        ok_btn.setObjectName("primaryButton")
        ok_btn.clicked.connect(dlg.accept)
        lay.addWidget(ok_btn)
        if not dlg.exec():
            return
        at = float(when.dateTime().toSecsSinceEpoch())
        if at <= time.time():
            QMessageBox.information(self, T("schedule_title"), T("schedule_past"))
            return
        self.scheduled.append({
            "key": self.current_target, "text": text, "at": at,
            "ttl": self.chat_ttl.get(self.current_target, 0),
        })
        self._persist_scheduled()
        self.message_edit.clear()

    def _check_scheduled(self):
        self._refresh_compose_visibility()
        if not self.scheduled:
            return
        now = time.time()
        due = [x for x in self.scheduled if x["at"] <= now]
        if not due:
            return
        self.scheduled = [x for x in self.scheduled if x["at"] > now]
        self._persist_scheduled()
        for item in due:
            key = item["key"]
            valid = (key in (EVERYONE, SAVED_MESSAGES_KEY) or key in self.sidebar_rows
                     or (is_custom_group(key) and key[len(GROUP_PREFIX):] in self.groups))
            if valid:
                self.send_requested.emit(item["text"], key, {"ttl": item.get("ttl", 0)})

    def _menu_scheduled(self, menu, key):
        count = len([x for x in self.scheduled if x["key"] == key])
        if count:
            menu.addAction(f"{T('schedule_list')} ({count})").triggered.connect(
                lambda: self._show_scheduled_dialog(key)
            )

    def _show_scheduled_dialog(self, key):
        dlg = QDialog(self)
        dlg.setWindowTitle(T("schedule_list"))
        dlg.setMinimumWidth(380)
        lay = QVBoxLayout(dlg)
        lst = QListWidget()
        lst.setObjectName("discoverList")
        mine = [x for x in self.scheduled if x["key"] == key]
        for x in mine:
            when = QDateTime.fromSecsSinceEpoch(int(x["at"])).toString("yyyy-MM-dd HH:mm")
            lst.addItem(f"{when}  \u2014  {x['text'][:60]}")
        lay.addWidget(lst)
        rm = QPushButton(T("schedule_remove"))

        def remove():
            row = lst.currentRow()
            if row < 0:
                return
            self.scheduled.remove(mine[row])
            mine.pop(row)
            lst.takeItem(row)
            self._persist_scheduled()

        rm.clicked.connect(remove)
        lay.addWidget(rm)
        dlg.exec()

    # ----- media gallery / files list -----

    @staticmethod
    def _hash_status(content):
        declared = content.get("sha256", "")
        try:
            actual = hashlib.sha256(base64.b64decode(content.get("data", ""))).hexdigest()
        except Exception:
            actual = ""
        if declared:
            ok = (actual == declared)
            return ("\u2713 " if ok else "\u26A0 ") + "SHA-256 " + actual[:12], actual, ok
        return "SHA-256 " + actual[:12], actual, None

    def _menu_gallery(self, menu, key):
        menu.addAction(T("gallery_menu")).triggered.connect(lambda: self._open_gallery(False))

    def _open_gallery(self, all_chats):
        items = []
        for key, lst in self.chat_files.items():
            if all_chats or key == self.current_target:
                title = self._chat_title_for(key)
                for sender, content in lst:
                    items.append((title, sender, content))
        MediaGalleryDialog(items, self._save_file_content, self._play_voice, self).exec()

    def _is_readonly(self, key):
        if self.readonly_until.get(key, 0) > time.time():
            return True
        if not is_custom_group(key):
            return False
        g = self.groups.get(key[len(GROUP_PREFIX):], {})
        return bool(g.get("readonly")) and g.get("owner") != self.my_name

    # ----- display options -----

    def _on_list_lines_clicked(self):
        menu = QMenu(self)
        actions = {}
        for n in (1, 2, 3):
            actions[menu.addAction(("\u2713 " if n == CHAT_LIST_LINES[0] else "") + T("list_lines_opt").format(n=n))] = n
        chosen = menu.exec(QCursor.pos())
        if chosen in actions:
            CHAT_LIST_LINES[0] = actions[chosen]
            set_setting("list_lines", actions[chosen])
            self._rebuild_sidebar()

    def set_admins(self, names):
        self.admins = set(names)
        self._rebuild_sidebar()

    # ----- starred messages -----

    def _toggle_star(self, msg_id):
        info = self.messages_by_id.get(msg_id)
        if not info or info["deleted"]:
            return
        if msg_id in self.starred:
            del self.starred[msg_id]
        else:
            self.starred[msg_id] = {
                "id": msg_id, "key": info["chat_key"], "sender": info["sender"],
                "text": info["bubble"].raw_text, "ts": info.get("ts", ""),
            }
        set_setting("starred", list(self.starred.values())[-300:])

    def _show_starred(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(T("star_title"))
        dlg.resize(440, 420)
        lay = QVBoxLayout(dlg)
        lst = QListWidget()
        lst.setObjectName("searchResults")
        lst.setWordWrap(True)

        def fill():
            lst.clear()
            for entry in reversed(list(self.starred.values())):
                item = QListWidgetItem(
                    f"{self._chat_title_for(entry['key'])} \u00b7 {entry['sender']} \u00b7 {entry['ts']}\n"
                    f"{self._snippet(entry['text'], '')}"
                )
                item.setData(Qt.ItemDataRole.UserRole, entry)
                lst.addItem(item)
            if lst.count() == 0:
                empty = QListWidgetItem(T("star_none"))
                empty.setFlags(Qt.ItemFlag.NoItemFlags)
                lst.addItem(empty)

        def go(item):
            entry = item.data(Qt.ItemDataRole.UserRole)
            if not entry:
                return
            dlg.accept()
            fake = QListWidgetItem()
            if entry["id"] in self.messages_by_id:
                fake.setData(Qt.ItemDataRole.UserRole,
                             {"key": entry["key"], "msg_id": entry["id"], "needle": entry["text"][:20].lower()})
            else:
                fake.setData(Qt.ItemDataRole.UserRole, {"key": entry["key"], "msg_id": None, "needle": ""})
            self._on_search_result_clicked(fake)

        def unstar():
            item = lst.currentItem()
            entry = item.data(Qt.ItemDataRole.UserRole) if item else None
            if entry:
                self.starred.pop(entry["id"], None)
                set_setting("starred", list(self.starred.values())[-300:])
                fill()

        lst.itemClicked.connect(go)
        fill()
        lay.addWidget(lst)
        rm = QPushButton(T("star_remove"))
        rm.clicked.connect(unstar)
        lay.addWidget(rm)
        dlg.exec()

    # ----- who's online -----

    def _show_online_panel(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(T("online_title"))
        dlg.resize(380, 420)
        lay = QVBoxLayout(dlg)
        lst = QListWidget()
        lst.setObjectName("searchResults")
        lst.setWordWrap(True)
        dots = {"online": "\U0001F7E2", "busy": "\U0001F534", "away": "\U0001F7E0"}
        for name in sorted(self.member_names, key=str.lower):
            if name == self.my_name:
                status, ping = self.my_status, None
                label = f"{name} ({T('you_suffix')})"
            else:
                status, ping = self.peer_statuses.get(name, "online"), self.peer_pings.get(name)
                label = name
            role = T("role_host") if name == self.current_host_name else (
                T("role_admin") if name in self.admins else "")
            line = f"{dots.get(status, dots['online'])} {label}" + (" \u270B" if name in self.hands else "")
            if role:
                line += f"  [{role}]"
            if ping is not None:
                line += f"  {ping} ms"
            bio = self.my_bio if name == self.my_name else self.peer_bios.get(name, "")
            if bio:
                line += f"\n     {bio}"
            lst.addItem(QListWidgetItem(line))
        lay.addWidget(lst)
        dlg.exec()

    # ----- advanced search -----

    def _show_advanced_search(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(T("adv_title"))
        dlg.resize(540, 560)
        lay = QVBoxLayout(dlg)
        text_edit = QLineEdit()
        text_edit.setPlaceholderText(T("adv_text"))
        lay.addWidget(text_edit)
        row = QHBoxLayout()
        sender_box = QComboBox()
        sender_box.addItem(T("adv_sender") + ": " + T("adv_any"), "")
        for name in sorted({i["sender"] for i in self.messages_by_id.values()}, key=str.lower):
            sender_box.addItem(name, name)
        chat_box = QComboBox()
        chat_box.addItem(T("adv_chat") + ": " + T("adv_any"), "")
        for key in self.sidebar_rows:
            chat_box.addItem(self._chat_title_for(key), key)
        when_box = QComboBox()
        for label, span in (("adv_any", 0), ("adv_hour", 3600), ("adv_today", 86400), ("adv_week", 604800)):
            when_box.addItem(T("adv_when") + ": " + T(label), span)
        row.addWidget(sender_box)
        row.addWidget(chat_box)
        row.addWidget(when_box)
        lay.addLayout(row)
        files_check = QCheckBox(T("adv_files_only"))
        lay.addWidget(files_check)
        go_btn = QPushButton(T("adv_search"))
        go_btn.setObjectName("primaryButton")
        lay.addWidget(go_btn)
        results = QListWidget()
        results.setObjectName("searchResults")
        results.setWordWrap(True)
        lay.addWidget(results, stretch=1)

        def run():
            needle = text_edit.text().strip().lower()
            sender, chat, span = sender_box.currentData(), chat_box.currentData(), when_box.currentData()
            cutoff = time.time() - span if span else 0
            results.clear()
            shown = 0
            if files_check.isChecked():
                for key, lst in self.chat_files.items():
                    if chat and key != chat:
                        continue
                    for snd, content in reversed(lst):
                        if sender and snd != sender:
                            continue
                        if cutoff and content.get("_epoch", 0) < cutoff:
                            continue
                        if needle and needle not in content.get("filename", "").lower():
                            continue
                        item = QListWidgetItem(
                            f"\U0001F4CE {content.get('filename', '')}\n{self._chat_title_for(key)} \u00b7 {snd} \u00b7 {content.get('time', '')}"
                        )
                        item.setData(Qt.ItemDataRole.UserRole, {"file": content})
                        results.addItem(item)
                        shown += 1
            else:
                for mid, info in reversed(list(self.messages_by_id.items())):
                    if info["deleted"]:
                        continue
                    if sender and info["sender"] != sender:
                        continue
                    if chat and info["chat_key"] != chat:
                        continue
                    if cutoff and info.get("epoch", 0) < cutoff:
                        continue
                    raw = info["bubble"].raw_text
                    if needle and needle not in raw.lower():
                        continue
                    item = QListWidgetItem(
                        f"{self._chat_title_for(info['chat_key'])} \u00b7 {info['sender']} \u00b7 {info.get('ts', '')}\n"
                        f"{self._snippet(raw, needle)}"
                    )
                    item.setData(Qt.ItemDataRole.UserRole, {"key": info["chat_key"], "msg_id": mid, "needle": needle})
                    results.addItem(item)
                    shown += 1
                    if shown >= 200:
                        break
            if shown == 0:
                empty = QListWidgetItem(T("search_global_no_results"))
                empty.setFlags(Qt.ItemFlag.NoItemFlags)
                results.addItem(empty)

        def clicked(item):
            data = item.data(Qt.ItemDataRole.UserRole)
            if not data:
                return
            if "file" in data:
                self._save_file_content(data["file"].get("filename", "file"), data["file"].get("data", ""))
            else:
                dlg.accept()
                self._on_search_result_clicked(item)

        go_btn.clicked.connect(run)
        text_edit.returnPressed.connect(run)
        results.itemClicked.connect(clicked)
        dlg.exec()

    # ----- slash commands -----

    def _handle_slash(self, text):
        """Returns the text to actually send, or None when the command was
        handled locally (or was invalid)."""
        parts = text[1:].split(None, 1)
        cmd = parts[0].lower() if parts else ""
        arg = parts[1].strip() if len(parts) > 1 else ""
        me = self.my_name
        if cmd == "help":
            QMessageBox.information(self, T("slash_help_title"), T("slash_help"))
            return None
        if cmd == "me" and arg:
            return f"*{me} {arg}*"
        if cmd == "shrug":
            return (arg + " " if arg else "") + "\u00AF\\_(\u30C4)_/\u00AF"
        if cmd == "roll":
            n = int(arg) if arg.isdigit() and 2 <= int(arg) <= 1000 else 6
            return f"\U0001F3B2 {me}: {random.randint(1, n)} (1-{n})"
        if cmd == "flip":
            return "\U0001FA99 " + random.choice(["Heads", "Tails"])
        if cmd == "time":
            return "\U0001F552 " + time.strftime("%Y-%m-%d %H:%M")
        if cmd == "poll" and arg:
            pieces = [p.strip() for p in arg.split("|") if p.strip()]
            if len(pieces) >= 3 and self.current_target is not None:
                self.poll_create_requested.emit(self.current_target, pieces[0], pieces[1:9])
            else:
                QMessageBox.information(self, T("slash_help_title"), T("poll_err"))
            return None
        if cmd in ("focus", "lock", "present"):
            self.slash_command_requested.emit(cmd, arg)
            return None
        QMessageBox.information(self, T("slash_help_title"), T("slash_unknown"))
        return None

    # ----- tags, reply reminders -----

    TAG_IDS = ("important", "todo", "idea", "question")

    def _set_tag(self, msg_id):
        info = self.messages_by_id.get(msg_id)
        if not info or info["deleted"]:
            return
        menu = QMenu(self)
        actions = {menu.addAction(T("tag_" + tid)): tid for tid in self.TAG_IDS}
        if msg_id in self.tagged:
            actions[menu.addAction(T("tag_remove"))] = None
        chosen = menu.exec(QCursor.pos())
        if chosen not in actions:
            return
        tid = actions[chosen]
        label = info.get("tag_label")
        if tid is None:
            self.tagged.pop(msg_id, None)
            if label is not None:
                label.deleteLater()
                info["tag_label"] = None
        else:
            self.tagged[msg_id] = {
                "id": msg_id, "key": info["chat_key"], "sender": info["sender"],
                "text": info["bubble"].raw_text, "ts": info.get("ts", ""), "tag": tid,
            }
            if label is None:
                label = QLabel("")
                label.setObjectName("mutedLabel")
                info["wrapper"].addWidget(
                    label, alignment=Qt.AlignmentFlag.AlignRight if info["is_own"] else Qt.AlignmentFlag.AlignLeft
                )
                info["tag_label"] = label
            label.setText("\U0001F3F7 " + T("tag_" + tid))
        set_setting("tagged", list(self.tagged.values())[-500:])

    def _jump_to_entry(self, entry):
        fake = QListWidgetItem()
        if entry["id"] in self.messages_by_id:
            payload = {"key": entry["key"], "msg_id": entry["id"], "needle": entry["text"][:20].lower()}
        else:
            payload = {"key": entry["key"], "msg_id": None, "needle": ""}
        fake.setData(Qt.ItemDataRole.UserRole, payload)
        self._on_search_result_clicked(fake)

    def _show_tagged(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(T("tagged_title"))
        dlg.resize(440, 440)
        lay = QVBoxLayout(dlg)
        combo = QComboBox()
        combo.addItem(T("adv_any"), "")
        for tid in self.TAG_IDS:
            combo.addItem(T("tag_" + tid), tid)
        lay.addWidget(combo)
        lst = QListWidget()
        lst.setObjectName("searchResults")
        lst.setWordWrap(True)
        lay.addWidget(lst, stretch=1)

        def fill():
            lst.clear()
            want = combo.currentData()
            for entry in reversed(list(self.tagged.values())):
                if want and entry.get("tag") != want:
                    continue
                item = QListWidgetItem(
                    f"{T('tag_' + entry['tag'])}  \u00b7 {self._chat_title_for(entry['key'])} \u00b7 {entry['sender']}\n"
                    f"{self._snippet(entry['text'], '')}"
                )
                item.setData(Qt.ItemDataRole.UserRole, entry)
                lst.addItem(item)
            if lst.count() == 0:
                empty = QListWidgetItem(T("search_global_no_results"))
                empty.setFlags(Qt.ItemFlag.NoItemFlags)
                lst.addItem(empty)

        combo.currentIndexChanged.connect(fill)
        lst.itemClicked.connect(lambda item: item.data(Qt.ItemDataRole.UserRole) and (dlg.accept(), self._jump_to_entry(item.data(Qt.ItemDataRole.UserRole))))
        fill()
        dlg.exec()

    def _on_remind_requested(self, msg_id, minutes):
        info = self.messages_by_id.get(msg_id)
        if info and not info["deleted"]:
            self.reply_reminder_requested.emit(info["sender"], info["bubble"].raw_text, minutes)

    # ----- location card -----

    @staticmethod
    def _location_text(loc):
        parts = [str(loc.get(k)) for k in ("building", "floor", "room") if loc.get(k)]
        text = "\U0001F4CD " + " \u00b7 ".join(parts)
        if loc.get("note"):
            text += " \u2014 " + str(loc["note"])
        return text

    def _attach_location(self):
        if self.current_target is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(T("loc_title"))
        dlg.setMinimumWidth(340)
        lay = QVBoxLayout(dlg)
        edits = {}
        for key, label in (("building", "loc_building"), ("floor", "loc_floor"),
                           ("room", "loc_room"), ("note", "loc_note")):
            edit = QLineEdit()
            edit.setPlaceholderText(T(label))
            edit.setMaxLength(80)
            lay.addWidget(edit)
            edits[key] = edit
        ok = QPushButton(T("poll_create_btn"))
        ok.setObjectName("primaryButton")
        ok.clicked.connect(dlg.accept)
        lay.addWidget(ok)
        if dlg.exec():
            loc = {k: e.text().strip() for k, e in edits.items() if e.text().strip()}
            if loc:
                self.location_requested.emit(self.current_target, loc)

    def add_location_message(self, sender, content, is_own, chat_key):
        loc = content.get("location") or {}
        text = self._location_text({k: str(v)[:80] for k, v in loc.items() if k in ("building", "floor", "room", "note")})
        card = QFrame()
        card.setObjectName("fileCard")
        card.setMaximumWidth(340)
        lay = QHBoxLayout(card)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("background: transparent; font-weight: 600;")
        lay.addWidget(lbl, stretch=1)
        copy_btn = QPushButton(T("loc_copy"))
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(text))
        lay.addWidget(copy_btn)
        self._insert_card(chat_key, sender, content.get("time", ""), is_own, card, int(content.get("ttl", 0) or 0))
        self._touch_chat_preview(chat_key, text, is_own, sender)

    # ----- incognito, temporary read-only, PDF, stats, random chat, focus -----

    def _menu_privacy(self, menu, key):
        menu.addSeparator()
        inc = menu.addAction(T("incognito_toggle"))
        inc.setCheckable(True)
        inc.setChecked(bool(self._pref(key, "incognito", False)))
        inc.toggled.connect(lambda v: self._set_incognito(key, v))
        ro_menu = menu.addMenu(T("tempro_menu"))
        for mins in (15, 30, 60):
            ro_menu.addAction(f"{mins} min").triggered.connect(
                lambda checked=False, m=mins: self._set_temp_readonly(key, m)
            )
        if self.readonly_until.get(key, 0) > time.time():
            ro_menu.addAction(T("tempro_off")).triggered.connect(lambda: self._set_temp_readonly(key, 0))
        menu.addAction(T("pdf_export")).triggered.connect(lambda: self._export_pdf(key))
        if key not in (EVERYONE, SAVED_MESSAGES_KEY) and not is_custom_group(key):
            menu.addAction(T("person_note")).triggered.connect(lambda: self.person_note_requested.emit(key))
            menu.addAction(T("race_challenge")).triggered.connect(lambda: self.race_invite_requested.emit(key))

    def _set_incognito(self, key, on):
        self._set_pref(key, "incognito", on)
        self._refresh_compose_visibility()

    def _purge_incognito(self, key):
        for msg_id, container in self.incognito_ids.pop(key, []):
            self._expire_message(key, msg_id, container)

    def _set_temp_readonly(self, key, minutes):
        self.readonly_until[key] = time.time() + minutes * 60 if minutes else 0
        self._refresh_compose_visibility()

    def _refresh_compose_visibility(self):
        key = self.current_target
        allowed = key is not None and not self.select_mode and not self._is_readonly(key)
        self.compose_bar.setVisible(allowed)
        inc = bool(key is not None and self._pref(key, "incognito", False))
        if inc != self._incognito_view:
            self._incognito_view = inc
            self.incognito_view_changed.emit(inc)

    def _export_pdf(self, key):
        rows_src = [i for i in self.messages_by_id.values() if i["chat_key"] == key and not i["deleted"]]
        title = self._chat_title_for(key)
        if not rows_src:
            QMessageBox.information(self, T("pdf_export"), T("export_chat_empty"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, T("pdf_export"), f"{_safe_history_name(title)}.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            from PyQt6.QtPrintSupport import QPrinter
        except ImportError:
            QMessageBox.information(self, T("pdf_export"), "QtPrintSupport is not available.")
            return
        rows = []
        for info in rows_src:
            text = info["bubble"].raw_text
            rtl = bool(re.search(r"[\u0600-\u06FF]", text))
            body = html.escape(text).replace("\n", "<br>")
            rows.append(
                f'<tr><td align="{"right" if info["is_own"] else "left"}">'
                f'<table cellpadding="7" cellspacing="0"><tr><td bgcolor="{"#dbe7ff" if info["is_own"] else "#eeeeee"}" '
                f'dir="{"rtl" if rtl else "ltr"}"><b>{html.escape(info["sender"])}</b> '
                f'<font color="#888888">{html.escape(info.get("ts", ""))}</font><br>{body}</td></tr></table></td></tr>'
            )
        doc = QTextDocument()
        doc.setHtml(f"<h2>{html.escape(title)}</h2><table width='100%' cellspacing='6'>{''.join(rows)}</table>")
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        (getattr(doc, "print", None) or doc.print_)(printer)
        QMessageBox.information(self, T("pdf_export"), T("export_chat_done_body").format(path=path))

    def _show_stats(self):
        infos = [i for i in self.messages_by_id.values() if not i["deleted"]]
        if self.current_target is not None:
            scoped = [i for i in infos if i["chat_key"] == self.current_target]
            scope_title = self._chat_title_for(self.current_target)
            if scoped:
                infos = scoped
            else:
                scope_title = "\u2014"
        else:
            scope_title = T("adv_any")
        dlg = QDialog(self)
        dlg.setWindowTitle(T("stats_title") + " \u2014 " + scope_title)
        dlg.resize(460, 440)
        lay = QVBoxLayout(dlg)
        view = QTextBrowser()
        lay.addWidget(view)
        if not infos:
            view.setPlainText(T("search_global_no_results"))
            dlg.exec()
            return
        per_sender, hours, emoji_count, words = {}, {}, 0, 0
        emoji_re = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
        longest = max(infos, key=lambda i: len(i["bubble"].raw_text))
        for i in infos:
            text = i["bubble"].raw_text
            per_sender[i["sender"]] = per_sender.get(i["sender"], 0) + 1
            words += len(text.split())
            emoji_count += len(emoji_re.findall(text))
            if i.get("epoch"):
                h = time.localtime(i["epoch"]).tm_hour
                hours[h] = hours.get(h, 0) + 1
        top = max(per_sender.values())
        lines = [f"{len(infos)} messages \u2022 {words} words \u2022 {emoji_count} emoji", ""]
        for name, n in sorted(per_sender.items(), key=lambda kv: -kv[1]):
            bar = "\u2588" * max(1, int(20 * n / top))
            lines.append(f"{name:<16} {bar} {n}")
        if hours:
            busiest = max(hours, key=hours.get)
            lines += ["", f"Busiest hour: {busiest:02d}:00 ({hours[busiest]} messages)"]
        lines += ["", f"Longest message ({longest['sender']}): {longest['bubble'].raw_text[:120]}"]
        view.setPlainText("\n".join(lines))
        dlg.exec()

    def _random_chat(self):
        others = [n for n in self.member_names if n != self.my_name]
        if not others:
            QMessageBox.information(self, T("random_row"), T("group_no_one_online"))
            return
        name = random.choice(others)
        self.open_private(name)
        self.send_requested.emit("\U0001F44B", name, {"ttl": 0})

    def _on_focus_row_clicked(self):
        menu = QMenu(self)
        actions = {menu.addAction(T("focus_off")): 0}
        for mins in (15, 30, 60, 120):
            actions[menu.addAction(f"{mins} min")] = mins
        chosen = menu.exec(QCursor.pos())
        if chosen in actions:
            self.focus_requested.emit(actions[chosen])

    def set_focus_banner(self, until):
        if until > time.time():
            self.focus_banner.setText(T("focus_banner").format(t=time.strftime("%H:%M", time.localtime(until))))
            self.focus_banner.setVisible(True)
        else:
            self.focus_banner.setVisible(False)

    def set_presentation(self, on):
        self.sidebar_frame.setVisible(not on)
        self.menu_btn.setVisible(not on)

    # ----- live: push-to-talk, screen sharing, raised hands, shared player -----

    def _ptt_start(self):
        key = self.current_target
        if key is None or key == SAVED_MESSAGES_KEY or self._ptt is not None:
            return
        streamer = voice_utils.PttStreamer(self)
        err = streamer.start()
        if err:
            QMessageBox.information(self, T("voice_title"), T("ptt_err").format(error=err))
            return
        self._ptt, self._ptt_target = streamer, key
        streamer.chunk.connect(lambda pcm, k=key: self.ptt_chunk.emit(k, pcm))
        self.ptt_btn.setStyleSheet("color: #ff5555;")

    def _ptt_stop(self):
        streamer, self._ptt = self._ptt, None
        self.ptt_btn.setStyleSheet("")
        if streamer is not None:
            streamer.stop()

    def _menu_live(self, menu, key):
        if key == SAVED_MESSAGES_KEY:
            return
        sharing = key in self.sharing_keys
        menu.addAction(T("screen_stop") if sharing else T("screen_start")).triggered.connect(
            lambda: self.screen_share_toggled.emit(key, not sharing)
        )
        if key == EVERYONE:
            raised = self.my_name in self.hands
            menu.addAction(T("hand_lower") if raised else T("hand_raise")).triggered.connect(
                lambda: self.hand_toggle_requested.emit()
            )
            if self.is_host_flag or self.my_name in self.admins:
                menu.addAction(T("hands_clear")).triggered.connect(lambda: self.hands_clear_requested.emit())
        menu.addAction(T("media_menu")).triggered.connect(lambda: self.media_player_requested.emit(key))

    def set_hand(self, name, on):
        if on:
            self.hands.add(name)
        else:
            self.hands.discard(name)
        self._rebuild_sidebar()

    def set_guests(self, names):
        self.guests = set(names)
        self._rebuild_sidebar()

    # ----- time capsule -----

    def _attach_capsule(self):
        text = self.message_edit.text().strip()
        if not text or self.current_target is None:
            QMessageBox.information(self, T("capsule_title"), T("schedule_need_text"))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(T("capsule_title"))
        lay = QVBoxLayout(dlg)
        when = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        when.setCalendarPopup(True)
        when.setDisplayFormat("yyyy-MM-dd  HH:mm")
        lay.addWidget(when)
        ok = QPushButton(T("schedule_ok"))
        ok.setObjectName("primaryButton")
        ok.clicked.connect(dlg.accept)
        lay.addWidget(ok)
        if not dlg.exec():
            return
        at = float(when.dateTime().toSecsSinceEpoch())
        if at <= time.time():
            QMessageBox.information(self, T("capsule_title"), T("schedule_past"))
            return
        self.message_edit.clear()
        self.capsule_requested.emit(self.current_target, text, at)

    # ----- translate a message (online) -----

    def _translate_message(self, msg_id):
        info = self.messages_by_id.get(msg_id)
        if not info or info["deleted"]:
            return
        text = info["bubble"].raw_text
        if re.search(r"[\u0600-\u06FF]", text):
            src, tgt = "fa", "en"
        else:
            src, tgt = "en", "fa"
        label = info.get("trans_label")
        if label is None:
            label = QLabel("\U0001F310 ...")
            label.setObjectName("replyQuote")
            label.setWordWrap(True)
            label.setMaximumWidth(380)
            info["wrapper"].addWidget(
                label, alignment=Qt.AlignmentFlag.AlignRight if info["is_own"] else Qt.AlignmentFlag.AlignLeft
            )
            info["trans_label"] = label
        else:
            label.setText("\U0001F310 ...")
        worker = TranslateWorker(label, text, src, tgt)
        worker.ready.connect(self._on_link_preview_ready)
        self._link_workers.append(worker)
        threading.Thread(target=worker.run, daemon=True).start()

    # ----- shared sync folder -----

    def _menu_extras(self, menu, key):
        if key not in (EVERYONE, SAVED_MESSAGES_KEY) and not is_custom_group(key):
            menu.addAction(T("game_challenge")).triggered.connect(lambda: self.game_invite_requested.emit(key))
        if key != SAVED_MESSAGES_KEY:
            menu.addAction(T("clipboard_share")).triggered.connect(lambda: self.clipboard_share_requested.emit(key))
            menu.addAction(T("sync_menu")).triggered.connect(lambda: self._open_sync_dialog(key))

    def _persist_sync_folders(self):
        set_setting("sync_folders", {k: sf.folder for k, sf in self.sync_folders.items()
                                     if not is_custom_group(k)})

    def _emit_sync_files(self, key, files):
        for rel, data, sha in files:
            self.sync_file_requested.emit(key, rel, base64.b64encode(data).decode("ascii"), sha)

    def _sync_tick(self):
        for key, sf in list(self.sync_folders.items()):
            try:
                self._emit_sync_files(key, sf.changed())
            except Exception:
                continue

    def _open_sync_dialog(self, key):
        dlg = QDialog(self)
        dlg.setWindowTitle(T("sync_title") + " \u2014 " + self._chat_title_for(key))
        dlg.setMinimumWidth(420)
        lay = QVBoxLayout(dlg)
        note = QLabel(T("sync_note"))
        note.setWordWrap(True)
        note.setObjectName("mutedLabel")
        lay.addWidget(note)
        cur = QLabel("")
        cur.setWordWrap(True)
        lay.addWidget(cur)
        send_all = QPushButton(T("sync_send_all"))
        stop = QPushButton(T("sync_stop"))

        def refresh():
            sf = self.sync_folders.get(key)
            cur.setText(T("sync_current").format(path=sf.folder) if sf else T("sync_none"))
            send_all.setEnabled(sf is not None)
            stop.setEnabled(sf is not None)

        def choose():
            path = QFileDialog.getExistingDirectory(dlg, T("sync_choose"))
            if path:
                sf = SyncFolder(path)
                sf.prime()
                self.sync_folders[key] = sf
                self._persist_sync_folders()
                refresh()

        def push_all():
            sf = self.sync_folders.get(key)
            if sf:
                self._emit_sync_files(key, sf.changed(force_all=True))

        def stop_sync():
            self.sync_folders.pop(key, None)
            self._persist_sync_folders()
            refresh()

        choose_btn = QPushButton(T("sync_choose"))
        choose_btn.clicked.connect(choose)
        send_all.clicked.connect(push_all)
        stop.clicked.connect(stop_sync)
        for b in (choose_btn, send_all, stop):
            lay.addWidget(b)
        refresh()
        dlg.exec()

    def apply_remote_sync(self, key, sender, content):
        sf = self.sync_folders.get(key)
        if sf is None:
            return  # we never opted in to syncing for this chat
        try:
            data = base64.b64decode(content.get("data", ""))
            rel = str(content.get("rel", ""))
            if sf.write_incoming(rel, data, str(content.get("sha", ""))):
                self._touch_chat_preview(key, "\U0001F4C1 " + rel, False, sender)
        except Exception:
            pass

    # ----- mentions list -----

    def _show_mentions(self):
        needle = f"@{self.my_name}".lower()
        dlg = QDialog(self)
        dlg.setWindowTitle(T("mentions_title"))
        dlg.resize(420, 400)
        lay = QVBoxLayout(dlg)
        lst = QListWidget()
        lst.setObjectName("searchResults")
        lst.setWordWrap(True)
        for mid, info in reversed(list(self.messages_by_id.items())):
            if info["is_own"] or info["deleted"]:
                continue
            raw = info["bubble"].raw_text
            if needle not in raw.lower():
                continue
            item = QListWidgetItem(
                f"{self._chat_title_for(info['chat_key'])} \u00b7 {info['sender']} \u00b7 {info.get('ts', '')}\n"
                f"{self._snippet(raw, needle)}"
            )
            item.setData(Qt.ItemDataRole.UserRole, {"key": info["chat_key"], "msg_id": mid, "needle": needle})
            lst.addItem(item)
        if lst.count() == 0:
            empty = QListWidgetItem(T("mentions_none"))
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            lst.addItem(empty)
        lst.itemClicked.connect(lambda item: (dlg.accept(), self._on_search_result_clicked(item)))
        lay.addWidget(lst)
        dlg.exec()

    # ----- shared checklist / whiteboard -----

    def _menu_collab(self, menu, key):
        menu.addAction(T("collab_checklist")).triggered.connect(lambda: self._open_checklist(key))
        menu.addAction(T("collab_board")).triggered.connect(lambda: self._open_board(key))
        menu.addAction(T("enc_export_chat")).triggered.connect(lambda: self._export_encrypted(False))

    def _open_checklist(self, key):
        existing = self._collab_dialogs.get(("check", key))
        if existing is not None:
            existing.raise_()
            return
        items = self.checklists.setdefault(key, [])
        dlg = ChecklistDialog(
            f"{T('collab_checklist')} \u2014 {self._chat_title_for(key)}", items,
            lambda: self.checklist_changed.emit(key, list(self.checklists.get(key, []))),
            self.my_name,
            {"placeholder": T("collab_placeholder"), "add": T("collab_add"), "remove": T("collab_remove")},
            self,
        )
        self._collab_dialogs[("check", key)] = dlg
        dlg.finished.connect(lambda _r=0: self._collab_dialogs.pop(("check", key), None))
        dlg.show()

    def apply_remote_checklist(self, key, sender, items):
        clean = [
            {"id": str(i.get("id", ""))[:16], "text": str(i.get("text", ""))[:200],
             "done": bool(i.get("done")), "by": str(i.get("by", ""))[:40]}
            for i in items if isinstance(i, dict) and i.get("id")
        ]
        self.checklists.setdefault(key, [])[:] = clean
        dlg = self._collab_dialogs.get(("check", key))
        if dlg is not None:
            dlg.refresh()
        elif key in self.sidebar_rows:
            self._touch_chat_preview(key, "\U0001F5D2 " + T("collab_updated"), False, sender)

    def _open_board(self, key):
        existing = self._collab_dialogs.get(("board", key))
        if existing is not None:
            existing.raise_()
            return
        strokes = self.boards.setdefault(key, [])
        dlg = BoardDialog(
            f"{T('collab_board')} \u2014 {self._chat_title_for(key)}", strokes,
            lambda stroke: self.board_event.emit(key, {"op": "stroke", "stroke": stroke}),
            lambda: self.board_event.emit(key, {"op": "clear"}),
            lambda: self.board_event.emit(key, {"op": "full", "strokes": self.boards.get(key, [])[-300:]}),
            {"send_all": T("collab_send_all"), "clear": T("collab_clear")},
            self,
        )
        self._collab_dialogs[("board", key)] = dlg
        dlg.finished.connect(lambda _r=0: self._collab_dialogs.pop(("board", key), None))
        dlg.show()

    def apply_remote_board(self, key, content):
        strokes = self.boards.setdefault(key, [])
        op = content.get("op")

        def clean(st):
            pts = [[float(x), float(y)] for x, y in (st.get("p") or [])][:2000]
            return {"c": str(st.get("c", "#ffffff"))[:9], "w": int(st.get("w", 3)), "p": pts}

        try:
            if op == "stroke":
                strokes.append(clean(content.get("stroke") or {}))
            elif op == "clear":
                strokes.clear()
            elif op == "full":
                strokes[:] = [clean(st) for st in (content.get("strokes") or [])][:300]
        except (TypeError, ValueError):
            return
        dlg = self._collab_dialogs.get(("board", key))
        if dlg is not None:
            dlg.refresh()

    # ----- encrypted exports (password-protected, AES-256-GCM) -----

    def _collect_chat_lines(self, only_key):
        out = {}
        for mid, info in self.messages_by_id.items():
            if info["deleted"]:
                continue
            key = info["chat_key"]
            if only_key is not None and key != only_key:
                continue
            reactions = self.reactions_by_msg.get(mid, {})
            chips = "  ".join(f"{e}x{len(n)}" for e, n in reactions.items() if n)
            line = f"[{info.get('ts', '')}] {info['sender']}: {info['bubble'].raw_text}" + (f"  ({chips})" if chips else "")
            out.setdefault(self._chat_title_for(key), []).append(line)
        return out

    def _ask_new_password(self):
        pw, ok = QInputDialog.getText(self, T("enc_export_chat"), T("enc_password_new"), QLineEdit.EchoMode.Password)
        if not ok:
            return None
        pw2, ok2 = QInputDialog.getText(self, T("enc_export_chat"), T("enc_password_repeat"), QLineEdit.EchoMode.Password)
        if not ok2:
            return None
        if pw != pw2 or len(pw) < 4:
            QMessageBox.information(self, T("enc_export_chat"), T("enc_password_mismatch"))
            return None
        return pw

    def _export_encrypted(self, all_chats):
        only = None if all_chats else self.current_target
        data = self._collect_chat_lines(only)
        if not data:
            QMessageBox.information(self, T("enc_export_chat"), T("enc_nothing"))
            return
        pw = self._ask_new_password()
        if not pw:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, T("enc_export_chat"), "chat_export.lcenc", "Encrypted export (*.lcenc)"
        )
        if not path:
            return
        payload = json.dumps(
            {"app": "lan_chat", "exported": time.strftime("%Y-%m-%d %H:%M"), "chats": data},
            ensure_ascii=False,
        ).encode("utf-8")
        try:
            with open(path, "wb") as f:
                f.write(encrypt_with_password(payload, pw))
        except OSError as e:
            QMessageBox.information(self, T("enc_export_chat"), str(e))
            return
        QMessageBox.information(self, T("enc_export_chat"), T("enc_saved").format(path=path))

    def _open_encrypted_export(self):
        path, _ = QFileDialog.getOpenFileName(self, T("enc_open"), "", "Encrypted export (*.lcenc)")
        if not path:
            return
        pw, ok = QInputDialog.getText(self, T("enc_open"), T("enc_password_ask"), QLineEdit.EchoMode.Password)
        if not ok:
            return
        try:
            with open(path, "rb") as f:
                data = json.loads(decrypt_with_password(f.read(), pw).decode("utf-8"))
        except (ValueError, OSError):
            QMessageBox.information(self, T("enc_open"), T("enc_bad"))
            return
        text = [f"{data.get('exported', '')}", ""]
        for title, lines in (data.get("chats") or {}).items():
            text.append(f"=== {title} ===")
            text.extend(lines)
            text.append("")
        dlg = QDialog(self)
        dlg.setWindowTitle(T("enc_open"))
        dlg.resize(560, 480)
        lay = QVBoxLayout(dlg)
        view = QTextBrowser()
        view.setPlainText("\n".join(text))
        lay.addWidget(view)
        dlg.exec()

    # ----- per-chat preferences (background, notifications, sound) -----

    def _pref(self, key, name, default=None):
        return self.chat_prefs.get(key, {}).get(name, default)

    def _set_pref(self, key, name, value):
        self.chat_prefs.setdefault(key, {})[name] = value
        set_setting("chat_prefs", self.chat_prefs)

    def _apply_chat_bg(self, key):
        if key == EVERYONE:
            scroll = self.group_scroll
        elif key in self.private_pages:
            scroll = self.private_pages[key]["scroll"]
        else:
            return
        scroll.viewport().setObjectName("chatViewport")
        bg = self._pref(key, "bg", "")
        if not bg:
            scroll.setStyleSheet("")
        elif bg.startswith("img:"):
            path = bg[4:].replace("\\", "/").replace('"', "")
            scroll.setStyleSheet(
                f'QWidget#chatViewport {{ border-image: url("{path}") 0 0 0 0 stretch stretch; }}'
            )
        else:
            scroll.setStyleSheet(f"QWidget#chatViewport {{ background-color: {bg}; }}")

    def _set_chat_bg(self, key, value):
        self._set_pref(key, "bg", value)
        self._apply_chat_bg(key)

    def _pick_chat_bg_image(self, key):
        path, _ = QFileDialog.getOpenFileName(
            self, T("chat_bg_image"), "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self._set_chat_bg(key, "img:" + path)

    def _pick_chat_sound(self, key):
        path, _ = QFileDialog.getOpenFileName(self, T("chat_sound_custom"), "", "WAV (*.wav)")
        if path:
            self._set_pref(key, "sound_file", path)

    def _on_chat_menu_clicked(self):
        key = self.current_target
        if key is None:
            return
        menu = QMenu(self)
        bg_menu = menu.addMenu(T("chat_bg_menu"))
        bg_menu.addAction(T("chat_bg_default")).triggered.connect(lambda: self._set_chat_bg(key, ""))
        for _id, color, fa, en in BG_PRESETS:
            pm = QPixmap(14, 14)
            pm.fill(QColor(color))
            act = bg_menu.addAction(QIcon(pm), fa if CURRENT_LANG[0] == "fa" else en)
            act.triggered.connect(lambda checked=False, c=color: self._set_chat_bg(key, c))
        bg_menu.addAction(T("chat_bg_image")).triggered.connect(lambda: self._pick_chat_bg_image(key))

        notify = menu.addAction(T("chat_notify_toggle"))
        notify.setCheckable(True)
        notify.setChecked(self._pref(key, "notify", True))
        notify.toggled.connect(lambda v: self._set_pref(key, "notify", v))
        sound = menu.addAction(T("chat_sound_toggle"))
        sound.setCheckable(True)
        sound.setChecked(self._pref(key, "sound", True))
        sound.toggled.connect(lambda v: self._set_pref(key, "sound", v))
        menu.addAction(T("chat_sound_custom")).triggered.connect(lambda: self._pick_chat_sound(key))
        if self._pref(key, "sound_file", ""):
            menu.addAction(T("chat_sound_reset")).triggered.connect(
                lambda: self._set_pref(key, "sound_file", "")
            )
        for builder in self.chat_menu_builders:
            builder(menu, key)
        menu.exec(self.chat_menu_btn.mapToGlobal(QPoint(0, self.chat_menu_btn.height())))

    def _on_security_code_clicked(self):
        if self.current_target and self.current_target not in (EVERYONE, SAVED_MESSAGES_KEY) \
                and not is_custom_group(self.current_target):
            self.security_code_requested.emit(self.current_target)

    def _on_attach_clicked(self):
        if self.current_target is None:
            return
        menu = QMenu(self)
        actions = {}
        for str_key, callback in self.attach_menu_items:
            actions[menu.addAction(T(str_key))] = callback
        chosen = menu.exec(self.attach_btn.mapToGlobal(QPoint(0, -menu.sizeHint().height())))
        if chosen in actions:
            actions[chosen]()

    def _attach_file(self):
        path, _ = QFileDialog.getOpenFileName(self, T("attach_file_btn"), "")
        if path:
            self.file_send_requested.emit(path)

    def _attach_poll(self):
        dlg = PollDialog(self)
        if dlg.exec():
            question, options = dlg.values()
            self.poll_create_requested.emit(self.current_target, question, options)

    def _attach_yesno(self):
        question, ok = QInputDialog.getText(self, T("attach_menu_yesno"), T("poll_question_label"))
        if ok and question.strip():
            self.poll_create_requested.emit(
                self.current_target, question.strip(), [T("poll_yes"), T("poll_no")]
            )

    # ----- stickers / GIFs -----

    def _on_sticker_clicked(self):
        if self.current_target is None:
            return
        popup = QDialog(self, Qt.WindowType.Popup)
        grid = QGridLayout(popup)
        grid.setSpacing(2)
        for i, sticker in enumerate(STICKERS):
            btn = QToolButton()
            btn.setText(sticker)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("font-size: 20pt; border: none; background: transparent;")
            btn.clicked.connect(
                lambda checked=False, st=sticker: (popup.close(), self.sticker_requested.emit(self.current_target, st))
            )
            grid.addWidget(btn, i // 8, i % 8)
        gif_btn = QPushButton("GIF...")
        gif_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gif_btn.clicked.connect(lambda: (popup.close(), self._attach_gif_file()))
        grid.addWidget(gif_btn, (len(STICKERS) + 7) // 8, 0, 1, 8)
        popup.adjustSize()
        popup.move(self.sticker_btn.mapToGlobal(QPoint(0, -popup.sizeHint().height())))
        popup.show()
        self._sticker_popup = popup

    def _attach_gif_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "GIF", "", "GIF (*.gif)")
        if path:
            self.file_send_requested.emit(path)

    @staticmethod
    def _attach_gif(label, data_b64):
        """Show an animated GIF in `label`; returns False if it can't be decoded."""
        try:
            raw = QByteArray(base64.b64decode(data_b64))
            buf = QBuffer(raw)
            buf.open(QIODevice.OpenModeFlag.ReadOnly)
            movie = QMovie(buf, QByteArray(b"gif"))
            if not movie.isValid():
                return False
            movie.jumpToFrame(0)
            size = movie.currentPixmap().size()
            if size.isEmpty():
                return False
            size.scale(280, 280, Qt.AspectRatioMode.KeepAspectRatio)
            movie.setScaledSize(size)
            label.setMovie(movie)
            movie.start()
            # keep everything alive as long as the label lives
            label._movie, label._gif_buf, label._gif_raw = movie, buf, raw
            return True
        except Exception:
            return False

    # ----- voice messages -----

    def _on_mic_clicked(self):
        if self.current_target is None:
            return
        if self.recorder is None:
            rec = voice_utils.VoiceRecorder(self)
            err = rec.start()
            if err:
                QMessageBox.information(self, T("voice_title"), T("voice_err").format(error=err))
                return
            self.recorder = rec
            self._rec_target = self.current_target
            self.mic_btn.setStyleSheet("color: #ff5555;")
            self._rec_timer = QTimer(self)
            self._rec_timer.setInterval(250)
            self._rec_timer.timeout.connect(self._update_rec_button)
            self._rec_timer.start()
            self._update_rec_button()
        else:
            self._finish_recording(True)

    def _update_rec_button(self):
        if self.recorder is None:
            return
        secs = self.recorder.seconds()
        self.mic_btn.setText(f"\u23FA {int(secs)}s")
        if secs >= voice_utils.MAX_SECONDS:
            self._finish_recording(True)

    def _finish_recording(self, send):
        rec, self.recorder = self.recorder, None
        if self._rec_timer is not None:
            self._rec_timer.stop()
        self.mic_btn.setText("\U0001F3A4")
        self.mic_btn.setStyleSheet("")
        if rec is None:
            return
        data, secs = rec.stop()
        if send and data and secs >= 0.5 and self._rec_target is not None:
            self.voice_recorded.emit(self._rec_target, data, secs)

    def _play_voice(self, data_b64):
        try:
            ok = voice_utils.play_wav_bytes(base64.b64decode(data_b64))
        except Exception:
            ok = False
        if not ok:
            QMessageBox.information(self, T("voice_title"), T("voice_play_err"))

    # ----- generic card-like messages (polls, locations, ...) -----

    def _layout_scroll(self, chat_key):
        if chat_key == EVERYONE:
            return self.group_layout, self.group_scroll
        self._ensure_private_page(chat_key)
        page = self.private_pages[chat_key]
        return page["layout"], page["scroll"]

    def _touch_chat_preview(self, chat_key, preview, is_own, sender):
        if chat_key == EVERYONE or is_custom_group(chat_key):
            preview = f"{T('you_prefix') if is_own else sender}: {preview}"
        elif is_own:
            preview = f"{T('you_prefix')}: {preview}"
        self.last_messages[chat_key] = preview
        self.typing_until.pop(chat_key, None)
        if not is_own and chat_key != self.current_target:
            self.unread_counts[chat_key] = self.unread_counts.get(chat_key, 0) + 1
        self._update_row_preview(chat_key)
        row = self.sidebar_rows.get(chat_key)
        if row is not None:
            row.set_badge(self.unread_counts.get(chat_key, 0))

    def _insert_card(self, chat_key, sender, ts, is_own, card, ttl=0):
        layout, scroll = self._layout_scroll(chat_key)
        wrapper = QVBoxLayout()
        wrapper.setSpacing(2)
        header = QLabel(f"{sender} \u2022 {ts}" + (" \U0001F525" if ttl else ""))
        header.setObjectName("mutedLabel")
        header.setAlignment(Qt.AlignmentFlag.AlignRight if is_own else Qt.AlignmentFlag.AlignLeft)
        wrapper.addWidget(header)
        row = QHBoxLayout()
        row.setSpacing(0)
        if is_own:
            row.addStretch(1)
            row.addWidget(card)
        else:
            row.addWidget(card)
            row.addStretch(1)
        wrapper.addLayout(row)
        container = QWidget()
        container.setLayout(wrapper)
        layout.insertWidget(layout.count() - 1, container)
        if ttl:
            self._schedule_expiry(chat_key, None, int(ttl), container)
        if self.chat_stack.currentWidget() is scroll:
            bar = scroll.verticalScrollBar()
            QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))
        return container

    # ----- polls -----

    def add_poll_message(self, sender, content, is_own, chat_key):
        if not is_own and chat_key == sender and sender in self.muted_names:
            return
        poll = content.get("poll") or {}
        options = [str(o) for o in (poll.get("options") or [])][:8]
        question = str(poll.get("q") or content.get("text") or "")
        msg_id = content.get("msg_id") or uuid.uuid4().hex[:12]
        ts = content.get("time", "")

        card = QFrame()
        card.setObjectName("fileCard")
        card.setMaximumWidth(340)
        lay = QVBoxLayout(card)
        lay.setSpacing(4)
        q_lbl = QLabel("\U0001F4CA " + question)
        q_lbl.setWordWrap(True)
        q_lbl.setStyleSheet("font-weight: 700; background: transparent;")
        lay.addWidget(q_lbl)
        rows = []
        for i, opt in enumerate(options):
            btn = QPushButton(opt)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, m=msg_id, k=i: self._on_poll_option_clicked(m, k))
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            lay.addWidget(btn)
            lay.addWidget(bar)
            rows.append((btn, bar, opt))
        self.polls[msg_id] = {"question": question, "options": options, "chat_key": chat_key, "rows": rows}
        self._render_poll(msg_id)
        self._insert_card(chat_key, sender, ts, is_own, card, int(content.get("ttl", 0) or 0))
        self._touch_chat_preview(chat_key, "\U0001F4CA " + question, is_own, sender)

    def _render_poll(self, msg_id):
        info = self.polls.get(msg_id)
        if not info:
            return
        votes = self.poll_votes.get(msg_id, {})
        total = len(votes)
        counts = [0] * len(info["options"])
        for choice in votes.values():
            if 0 <= choice < len(counts):
                counts[choice] += 1
        mine = votes.get(self.my_name, -1)
        for i, (btn, bar, opt) in enumerate(info["rows"]):
            try:
                btn.setText(("\u2713 " if i == mine else "") + f"{opt}   \u2014 {counts[i]}")
                btn.setToolTip(", ".join(sorted(n for n, v in votes.items() if v == i)))
                bar.setValue(int(100 * counts[i] / total) if total else 0)
            except RuntimeError:
                return  # the poll card self-destructed

    def _on_poll_option_clicked(self, msg_id, idx):
        info = self.polls.get(msg_id)
        if not info:
            return
        votes = self.poll_votes.setdefault(msg_id, {})
        choice = -1 if votes.get(self.my_name, -1) == idx else idx
        if choice == -1:
            votes.pop(self.my_name, None)
        else:
            votes[self.my_name] = choice
        self._render_poll(msg_id)
        self.poll_vote_requested.emit(info["chat_key"], msg_id, choice)

    def apply_poll_vote(self, voter, msg_id, choice):
        if msg_id not in self.polls:
            return
        votes = self.poll_votes.setdefault(msg_id, {})
        if choice < 0:
            votes.pop(voter, None)
        else:
            votes[voter] = choice
        self._render_poll(msg_id)


    def _on_export_chat_clicked(self):
        if self.current_target is None:
            return
        chat_key = self.current_target
        if chat_key == EVERYONE:
            title = "Group"
        elif chat_key == SAVED_MESSAGES_KEY:
            title = "Saved Messages"
        elif is_custom_group(chat_key):
            title = self._chat_title_for(chat_key)
        else:
            title = chat_key

        lines = []
        for mid, info in self.messages_by_id.items():
            if info["chat_key"] != chat_key:
                continue
            sender = info["sender"]
            ts = info.get("ts", "")
            if info["deleted"]:
                text = T("export_chat_deleted_marker")
            else:
                text = info["bubble"].raw_text
            line = f"[{ts}] {sender}: {text}"
            reactions = self.reactions_by_msg.get(mid, {})
            chips = "  ".join(f"{emo}x{len(names)}" for emo, names in reactions.items() if names)
            if chips:
                line += f"  ({chips})"
            lines.append(line)

        if not lines:
            QMessageBox.information(self, T("export_chat_done_title"), T("export_chat_empty"))
            return

        default_name = f"{_safe_history_name(title)}_export.txt"
        path, _ = QFileDialog.getSaveFileName(self, T("export_chat_tooltip"), default_name, "Text files (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"{title}\n{'=' * len(title)}\n\n")
                f.write("\n".join(lines))
                f.write("\n")
        except Exception as e:
            QMessageBox.information(self, T("export_chat_done_title"), str(e))
            return
        QMessageBox.information(
            self, T("export_chat_done_title"), T("export_chat_done_body").format(path=path)
        )

    # ----- drag-and-drop file sending -----
    # Dropping one or more files anywhere on the chat screen attaches them
    # to whichever chat is currently open, exactly like using the 📎
    # button - just a faster way in.

    def dragEnterEvent(self, event):
        if self.current_target is not None and event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self.current_target is not None and event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if self.current_target is None or not event.mimeData().hasUrls():
            event.ignore()
            return
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self.file_send_requested.emit(path)
        event.acceptProposedAction()

    def mark_seen(self, peer):
        """Called when the other person has just told us (via a 'seen'
        packet) that they've viewed our messages in this private chat -
        flips our sent ticks to the double 'read' tick."""
        self.peer_seen[peer] = True
        for tick in list(self.own_tick_labels.get(peer, [])):
            try:
                tick.setText("\u2713\u2713")
                tick.setToolTip(T("read_tick_read"))
            except RuntimeError:
                pass  # its message already self-destructed

    def _show_empty_state(self):
        self._leave_current_chat_search()
        self._cancel_reply_edit()
        self.compose_bar.setVisible(False)
        self.current_target = None
        self.chat_stack.setCurrentWidget(self.empty_state)
        self.back_btn.setVisible(False)
        self.chat_avatar.setVisible(False)
        self.chat_search_btn.setVisible(False)
        self.export_chat_btn.setVisible(False)
        self.security_code_btn.setVisible(False)
        self.group_info_btn.setVisible(False)
        self.ttl_btn.setVisible(False)
        self.chat_menu_btn.setVisible(False)
        self._set_chat_desc("")
        self.chat_title.setText("")
        self._highlight_selected()
        self.pin_banner.setVisible(False)

    def reset_view(self):
        self._show_empty_state()

    def _highlight_selected(self):
        for key, row in self.sidebar_rows.items():
            row.set_selected(key == self.current_target)

    def _ensure_private_page(self, name):
        if name in self.private_pages:
            return
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)
        layout.addStretch(1)
        scroll.setWidget(container)
        self.chat_stack.addWidget(scroll)
        self.private_pages[name] = {"scroll": scroll, "container": container, "layout": layout}

    def _scroll_current_to_bottom(self):
        area = self.chat_stack.currentWidget()
        if area is None or not hasattr(area, "verticalScrollBar"):
            return
        bar = area.verticalScrollBar()
        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

    # ----- search inside the currently open chat's messages -----

    def _toggle_chat_search(self):
        showing = not self.chat_search_bar.isVisible()
        self.chat_search_bar.setVisible(showing)
        if showing:
            self.chat_search_edit.setFocus()
        else:
            self.chat_search_edit.clear()
            self._clear_chat_search_highlight()
            self.chat_search_matches = []
            self.chat_search_index = -1
            self.chat_search_status.setText("")

    def _clear_chat_search_highlight(self):
        for bubble in self.chat_bubbles.get(self.current_target, []):
            bubble.setProperty("searchHit", False)
            bubble.style().unpolish(bubble)
            bubble.style().polish(bubble)

    def _on_chat_search_changed(self, text):
        self._clear_chat_search_highlight()
        needle = text.strip().lower()
        self.chat_search_matches = []
        self.chat_search_index = -1
        if needle and self.current_target is not None:
            for bubble in self.chat_bubbles.get(self.current_target, []):
                if needle in bubble.text().lower():
                    self.chat_search_matches.append(bubble)
        if not needle:
            self.chat_search_status.setText("")
        elif not self.chat_search_matches:
            self.chat_search_status.setText(T("search_in_chat_no_match"))
        else:
            self.chat_search_index = len(self.chat_search_matches) - 1
            self._show_chat_search_match()

    def _step_chat_search(self, direction):
        if not self.chat_search_matches:
            return
        self.chat_search_index = (self.chat_search_index + direction) % len(self.chat_search_matches)
        self._show_chat_search_match()

    def _show_chat_search_match(self):
        self._clear_chat_search_highlight()
        bubble = self.chat_search_matches[self.chat_search_index]
        bubble.setProperty("searchHit", True)
        bubble.style().unpolish(bubble)
        bubble.style().polish(bubble)
        area = self.chat_stack.currentWidget()
        if area is not None and hasattr(area, "ensureWidgetVisible"):
            area.ensureWidgetVisible(bubble, 40, 60)
        self.chat_search_status.setText(T("search_in_chat_match").format(
            current=self.chat_search_index + 1, total=len(self.chat_search_matches)
        ))

    # ----- typing indicator -----

    def mark_typing(self, key, who=None):
        # who: for group chats, which member is typing; several people typing
        # at once are shown together ("Ann, Bob typing..." / "Ann +2").
        now = time.time()
        if who is None:
            self.typing_until[key] = (now + 3.0, None)
        else:
            typers = self.group_typers.setdefault(key, {})
            typers[who] = now + 3.0
            for name in [n for n, until in typers.items() if until <= now]:
                del typers[name]
            names = sorted(typers)
            if len(names) <= 2:
                label = ", ".join(names)
            else:
                label = f"{names[0]} +{len(names) - 1}"
            self.typing_until[key] = (now + 3.0, label)
        self._update_row_preview(key)

    def _sweep_typing(self):
        now = time.time()
        expired = [k for k, (until, _who) in self.typing_until.items() if until <= now]
        for k in expired:
            del self.typing_until[k]
            self._update_row_preview(k)

    def _update_row_preview(self, key):
        entry = self.typing_until.get(key)
        typing = bool(entry and entry[0] > time.time())
        text = ""
        if typing:
            who = entry[1]
            text = f"{who} {T('typing_now')}" if who else T("typing_now")
        row = self.sidebar_rows.get(key)
        if row is not None:
            if typing:
                row.set_subtitle(text, emphasize=True)
            else:
                row.set_subtitle(self.last_messages.get(key, ""))
        if key == self.current_target:
            if typing:
                self.chat_desc_lbl.setText(text)
                self.chat_desc_lbl.setVisible(True)
            else:
                self._set_chat_desc(self._base_desc)

    # ----- messages -----

    def _maybe_load_history(self, chat_key):
        """The first time a chat is opened in this run, if local history
        saving is on and there's a saved file for it, replay those older
        messages back onto the screen (and don't re-save them - that
        would duplicate them forever)."""
        if not self.save_history_enabled or not self.my_name:
            return
        if is_custom_group(chat_key):
            return  # groups only live for this session
        if chat_key in self._history_loaded_keys:
            return
        self._history_loaded_keys.add(chat_key)
        records = load_history(self.my_name, chat_key)
        if not records:
            return
        is_private_chat = (chat_key != EVERYONE)
        if is_private_chat:
            self._ensure_private_page(chat_key)
            layout = self.private_pages[chat_key]["layout"]
        else:
            layout = self.group_layout
        divider = QLabel(T("history_divider"))
        divider.setObjectName("mutedLabel")
        divider.setAlignment(Qt.AlignmentFlag.AlignCenter)
        divider.setWordWrap(True)
        layout.insertWidget(layout.count() - 1, divider)
        for rec in records:
            self.add_message(
                rec.get("sender", ""), rec.get("text", ""), rec.get("ts", ""),
                is_own=rec.get("is_own", False),
                is_private=rec.get("is_private", is_private_chat),
                theme=self.theme, peer=(chat_key if is_private_chat else None),
                msg_id=rec.get("msg_id"), from_history=True,
            )

    def add_system_message(self, text):
        row = QLabel(text)
        row.setObjectName("mutedLabel")
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.setWordWrap(True)
        self.group_layout.insertWidget(self.group_layout.count() - 1, row)
        self.bubbles.append((row, "system"))
        if self.chat_stack.currentWidget() is self.group_scroll:
            self._scroll_current_to_bottom()

    def add_message(self, sender, text, ts, is_own, is_private, theme, peer=None,
                     msg_id=None, reply_to=None, reply_from=None, reply_text=None,
                     forward_from=None, from_history=False, chat_key=None, ttl=0, sticker=False, capsule=0):
        if is_private and not is_own and peer in self.muted_names:
            return  # muted: this person's direct messages are dropped silently

        ttl = int(ttl or 0)
        if chat_key is None:
            chat_key = peer if is_private else EVERYONE
        if chat_key != EVERYONE:
            self._ensure_private_page(chat_key)
            layout = self.private_pages[chat_key]["layout"]
            scroll = self.private_pages[chat_key]["scroll"]
        else:
            layout = self.group_layout
            scroll = self.group_scroll
        preview_key = chat_key

        if not msg_id:
            msg_id = uuid.uuid4().hex[:12]

        wrapper = QVBoxLayout()
        wrapper.setSpacing(2)
        header = QLabel(f"{sender} \u2022 {ts}" + (" \U0001F525" if ttl else ""))
        header.setObjectName("mutedLabel")
        header.setAlignment(
            Qt.AlignmentFlag.AlignRight if is_own else Qt.AlignmentFlag.AlignLeft
        )
        wrapper.addWidget(header)

        if forward_from:
            fwd_lbl = QLabel(T("forwarded_prefix").format(name=forward_from))
            fwd_lbl.setObjectName("mutedLabel")
            fwd_lbl.setStyleSheet("font-style: italic; background: transparent;")
            wrapper.addWidget(fwd_lbl)

        if reply_text:
            quote_lbl = QLabel(f"\u21a9 {reply_from}: {reply_text}")
            quote_lbl.setObjectName("replyQuote")
            quote_lbl.setWordWrap(True)
            if reply_to and reply_to in self.messages_by_id:
                quote_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
                quote_lbl.mousePressEvent = (
                    lambda e, mid=reply_to: self._scroll_to_message(mid)
                )
            wrapper.addWidget(quote_lbl)

        if is_private:
            bg, fg = theme["private_bubble"], theme["private_text"]
            kind = "private"
        elif is_own:
            bg, fg = theme["own_bubble"], theme["own_text"]
            kind = "own"
        else:
            bg, fg = theme["other_bubble"], theme["other_text"]
            kind = "other"

        bubble = BubbleLabel(text, bg, fg, mention_names=self.member_names,
                              msg_id=msg_id, is_own=is_own, sticker=sticker)
        if capsule and capsule > time.time():
            bubble.set_capsule(capsule, text)
        bubble.translate_requested.connect(self._translate_message)
        bubble.tag_requested.connect(self._set_tag)
        bubble.remind_requested.connect(self._on_remind_requested)
        if self._pref(preview_key, "incognito", False) and not from_history:
            incognito_tag = True
        else:
            incognito_tag = False
        bubble.reply_requested.connect(self._start_reply)
        bubble.forward_requested.connect(self._start_forward)
        bubble.pin_requested.connect(self._request_pin)
        bubble.edit_requested.connect(self._start_edit)
        bubble.delete_requested.connect(self._request_delete)
        bubble.react_requested.connect(self._request_react)
        bubble.select_requested.connect(self._enter_select_mode)
        bubble.star_requested.connect(self._toggle_star)
        bubble.select_toggled.connect(self._toggle_select)
        bubble.select_mode = self.select_mode and preview_key == self.current_target
        row = QHBoxLayout()
        row.setSpacing(0)
        if is_own:
            row.addStretch(1)
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch(1)
        wrapper.addLayout(row)

        # Reaction chips (👍 2, etc.) render in their own small row right
        # under the bubble, hidden until the first reaction arrives.
        reactions_container = QWidget()
        reactions_layout = QHBoxLayout(reactions_container)
        reactions_layout.setContentsMargins(0, 0, 0, 0)
        reactions_layout.setSpacing(4)
        reactions_container.setVisible(False)
        reactions_row = QHBoxLayout()
        reactions_row.setSpacing(0)
        if is_own:
            reactions_row.addStretch(1)
            reactions_row.addWidget(reactions_container)
        else:
            reactions_row.addWidget(reactions_container)
            reactions_row.addStretch(1)
        wrapper.addLayout(reactions_row)

        if self.link_preview_enabled and not from_history and not ttl:
            url_match = URL_RE.search(text)
            if url_match:
                self._start_link_preview(wrapper, url_match.group(1), is_own)

        self.messages_by_id[msg_id] = {
            "bubble": bubble, "sender": sender, "is_own": is_own,
            "chat_key": preview_key, "deleted": False, "ts": ts, "epoch": time.time(), "wrapper": wrapper,
            "reactions_container": reactions_container,
            "reactions_layout": reactions_layout,
        }
        if msg_id in self.reactions_by_msg:
            self._render_reactions(msg_id)

        # Private messages we sent get a small sent/seen tick, the same
        # idea as WhatsApp's single vs. double check mark - updated later
        # when a "seen" packet comes back from the other person.
        if is_private and is_own and peer != SAVED_MESSAGES_KEY:
            self.peer_seen[peer] = False
            tick = QLabel("\u2713")
            tick.setObjectName("readTick")
            tick.setAlignment(Qt.AlignmentFlag.AlignRight)
            tick.setToolTip(T("read_tick_sent"))
            wrapper.addWidget(tick)
            self.own_tick_labels.setdefault(peer, []).append(tick)
            self.messages_by_id[msg_id]["tick"] = tick

        container = QWidget()
        container.setLayout(wrapper)
        layout.insertWidget(layout.count() - 1, container)
        self.bubbles.append((bubble, kind))
        self.chat_bubbles.setdefault(preview_key, []).append(bubble)
        self.messages_by_id[msg_id]["container"] = container
        self.last_message_id[preview_key] = msg_id
        if ttl and not from_history:
            self._schedule_expiry(preview_key, msg_id, ttl, container)
        if incognito_tag:
            self.incognito_ids.setdefault(preview_key, []).append((msg_id, container))

        if self.chat_stack.currentWidget() is scroll:
            bar = scroll.verticalScrollBar()
            QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

        # Optional local history: append this message to disk, unless it's
        # a message we just loaded FROM disk (that would duplicate it
        # forever on every future replay).
        if (self.save_history_enabled and not from_history and self.my_name
                and not ttl and not capsule and not is_custom_group(preview_key)
                and not self._pref(preview_key, "incognito", False)):
            append_history(self.my_name, preview_key, {
                "sender": sender, "text": text, "ts": ts, "is_own": is_own,
                "is_private": is_private, "msg_id": msg_id,
            })

        limit = 42 * max(1, min(3, CHAT_LIST_LINES[0]))
        preview_text = text if len(text) <= limit else text[:limit] + "\u2026"
        if preview_key == EVERYONE or is_custom_group(preview_key):
            who = T("you_prefix") if is_own else sender
            preview_text = f"{who}: {preview_text}"
        elif is_own:
            preview_text = f"{T('you_prefix')}: {preview_text}"
        self.last_messages[preview_key] = preview_text
        self.typing_until.pop(preview_key, None)

        if not is_own and preview_key != self.current_target:
            self.unread_counts[preview_key] = self.unread_counts.get(preview_key, 0) + 1
        self._update_row_preview(preview_key)
        row_widget = self.sidebar_rows.get(preview_key)
        if row_widget is not None:
            row_widget.set_badge(self.unread_counts.get(preview_key, 0))

        if is_private and not is_own and preview_key == self.current_target:
            # we're already looking at this chat as the message arrives -
            # tell the sender right away that we've seen it
            self.seen_requested.emit(peer)

    def add_file_message(self, sender, content, is_own, is_private, theme, peer=None, chat_key=None):
        """Shows a sent/received file or image as its own card in the
        chat - simpler than a text bubble: no reply/edit/pin/forward on
        these yet, just view (for images) and Save."""
        if is_private and not is_own and peer in self.muted_names:
            return

        if chat_key is None:
            chat_key = peer if is_private else EVERYONE
        if chat_key != EVERYONE:
            self._ensure_private_page(chat_key)
            layout = self.private_pages[chat_key]["layout"]
            scroll = self.private_pages[chat_key]["scroll"]
        else:
            layout = self.group_layout
            scroll = self.group_scroll
        preview_key = chat_key

        ts = content.get("time", "")
        filename = content.get("filename", "file")
        size = content.get("size", 0)
        data_b64 = content.get("data", "")
        kind = content.get("kind", "file")
        ttl = int(content.get("ttl", 0) or 0)
        hash_short, hash_full, hash_ok = self._hash_status(content)

        wrapper = QVBoxLayout()
        wrapper.setSpacing(2)
        header = QLabel(f"{sender} \u2022 {ts}" + (" \U0001F525" if ttl else ""))
        header.setObjectName("mutedLabel")
        header.setAlignment(
            Qt.AlignmentFlag.AlignRight if is_own else Qt.AlignmentFlag.AlignLeft
        )
        wrapper.addWidget(header)

        card = QFrame()
        card.setObjectName("fileCard")
        card.setMaximumWidth(300)

        if kind == "image":
            card_layout = QVBoxLayout(card)
            pixmap = pixmap_from_b64(data_b64)
            img_lbl = QLabel()
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            movie_ok = filename.lower().endswith(".gif") and self._attach_gif(img_lbl, data_b64)
            if pixmap is not None and not movie_ok:
                scaled = pixmap.scaled(
                    280, 280, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                img_lbl.setPixmap(scaled)
            card_layout.addWidget(img_lbl)
            name_row = QHBoxLayout()
            name_lbl = QLabel(filename)
            name_lbl.setObjectName("mutedLabel")
            name_lbl.setWordWrap(True)
            name_lbl.setToolTip(f"SHA-256: {hash_full}")
            name_row.addWidget(name_lbl, stretch=1)
            save_btn = QPushButton(T("file_save_btn"))
            save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            save_btn.clicked.connect(lambda: self._save_file_content(filename, data_b64))
            name_row.addWidget(save_btn)
            card_layout.addLayout(name_row)
        elif kind == "voice":
            card_layout = QHBoxLayout(card)
            play_btn = QPushButton("\u25B6")
            play_btn.setFixedWidth(40)
            play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            play_btn.clicked.connect(lambda checked=False, d=data_b64: self._play_voice(d))
            card_layout.addWidget(play_btn)
            dur = int(float(content.get("duration", 0) or 0))
            wave_lbl = QLabel(f"\U0001F3A4 {dur // 60}:{dur % 60:02d}   \u2581\u2583\u2585\u2587\u2585\u2583\u2581")
            wave_lbl.setStyleSheet("background: transparent;")
            wave_lbl.setToolTip(f"SHA-256: {hash_full}")
            card_layout.addWidget(wave_lbl, stretch=1)
            save_btn = QPushButton(T("file_save_btn"))
            save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            save_btn.clicked.connect(lambda: self._save_file_content(filename, data_b64))
            card_layout.addWidget(save_btn)
        else:
            card_layout = QHBoxLayout(card)
            icon_lbl = QLabel("\U0001F4C4")
            icon_lbl.setStyleSheet("font-size: 20pt; background: transparent;")
            card_layout.addWidget(icon_lbl)
            info_col = QVBoxLayout()
            info_col.setSpacing(1)
            name_lbl = QLabel(filename)
            name_lbl.setWordWrap(True)
            name_lbl.setStyleSheet("background: transparent;")
            size_lbl = QLabel(T("file_card_size").format(size=max(1, size // 1024)))
            size_lbl.setObjectName("mutedLabel")
            info_col.addWidget(name_lbl)
            info_col.addWidget(size_lbl)
            hash_lbl = QLabel(hash_short)
            hash_lbl.setObjectName("mutedLabel")
            hash_lbl.setToolTip(f"SHA-256: {hash_full}")
            if hash_ok is False:
                hash_lbl.setStyleSheet("color: #ff6b6b; background: transparent;")
            info_col.addWidget(hash_lbl)
            card_layout.addLayout(info_col, stretch=1)
            save_btn = QPushButton(T("file_save_btn"))
            save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            save_btn.clicked.connect(lambda: self._save_file_content(filename, data_b64))
            card_layout.addWidget(save_btn)

        row = QHBoxLayout()
        row.setSpacing(0)
        if is_own:
            row.addStretch(1)
            row.addWidget(card)
        else:
            row.addWidget(card)
            row.addStretch(1)
        wrapper.addLayout(row)

        container = QWidget()
        container.setLayout(wrapper)
        layout.insertWidget(layout.count() - 1, container)
        if ttl:
            self._schedule_expiry(preview_key, None, ttl, container)
        if self._pref(preview_key, "incognito", False):
            self.incognito_ids.setdefault(preview_key, []).append((None, container))

        if self.chat_stack.currentWidget() is scroll:
            bar = scroll.verticalScrollBar()
            QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

        content.setdefault("_epoch", time.time())
        self.chat_files.setdefault(preview_key, []).append((sender, content))
        preview_text = "\U0001F3A4 " + T("voice_title") if kind == "voice" else f"\U0001F4CE {filename}"
        if preview_key == EVERYONE or is_custom_group(preview_key):
            who = T("you_prefix") if is_own else sender
            preview_text = f"{who}: {preview_text}"
        elif is_own:
            preview_text = f"{T('you_prefix')}: {preview_text}"
        self.last_messages[preview_key] = preview_text
        self.typing_until.pop(preview_key, None)

        if not is_own and preview_key != self.current_target:
            self.unread_counts[preview_key] = self.unread_counts.get(preview_key, 0) + 1
        self._update_row_preview(preview_key)
        row_widget = self.sidebar_rows.get(preview_key)
        if row_widget is not None:
            row_widget.set_badge(self.unread_counts.get(preview_key, 0))

    def _save_file_content(self, filename, data_b64):
        path, _ = QFileDialog.getSaveFileName(self, T("file_save_dialog_title"), filename)
        if not path:
            return
        try:
            with open(path, "wb") as f:
                f.write(base64.b64decode(data_b64))
        except Exception:
            pass

    def apply_theme_to_history(self, theme):
        self.theme = theme  # remembered so history-replay can build correctly-colored bubbles
        for widget, kind in self.bubbles:
            if kind == "own":
                widget.set_colors(theme["own_bubble"], theme["own_text"])
            elif kind == "other":
                widget.set_colors(theme["other_bubble"], theme["other_text"])
            elif kind == "private":
                widget.set_colors(theme["private_bubble"], theme["private_text"])

    # ----- chat list (sidebar) -----

    def set_my_avatar(self, my_name, avatar_b64):
        """Stores the local user's own name/picture, to be shown later in
        the hamburger drawer's profile header (added in the next part)."""
        self.my_name = my_name
        self.my_avatar_pixmap = pixmap_from_b64(avatar_b64)

    def set_peer_ping(self, name, ms):
        self.peer_pings[name] = ms
        row = self.sidebar_rows.get(name)
        if row is not None:
            row.set_ping(ms)

    # ----- chat-list swipe actions (Pin / Mark read) -----

    def toggle_pin_chat(self, key):
        """Pin or unpin a chat from the list's swipe-reveal action. Group
        and Saved Messages are always pinned at the top already, so this
        only meaningfully reorders private member chats."""
        if key in self.pinned_chat_keys:
            self.pinned_chat_keys.discard(key)
        else:
            self.pinned_chat_keys.add(key)
        if self._last_update_members_args is not None:
            self.update_members(*self._last_update_members_args)

    def toggle_read_chat(self, key):
        """Flip a chat between read and unread from the swipe-reveal
        action, independent of whatever new messages actually arrive."""
        if self.unread_counts.get(key, 0) > 0:
            self.unread_counts[key] = 0
        else:
            self.unread_counts[key] = 1
        row = self.sidebar_rows.get(key)
        if row is not None:
            row.set_badge(self.unread_counts.get(key, 0))

    def update_members(self, names, my_name, host_name, is_host, theme, avatars=None, statuses=None, bios=None):
        avatars = avatars or {}
        statuses = statuses or {}
        bios = bios or {}
        self.peer_bios = bios
        self.peer_statuses = statuses
        self._last_update_members_args = (names, my_name, host_name, is_host, theme, avatars, statuses, bios)
        self.my_name = my_name
        self.member_names = names
        self.is_host_flag = is_host
        self.current_host_name = host_name
        self.peer_avatars = avatars
        if self.current_target and self.current_target not in (EVERYONE, SAVED_MESSAGES_KEY) \
                and self.current_target in avatars:
            self.chat_avatar.set_image(pixmap_from_b64(avatars.get(self.current_target, "")))
        while self.members_layout.count() > 1:
            item = self.members_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.sidebar_rows = {}

        group_row = ChatListRow(
            key=EVERYONE,
            avatar_text="",
            avatar_color=GROUP_AVATAR_COLOR,
            avatar_image=pixmap_from_b64(self.main_group_info.get("avatar", "")),
            title=T("group_title"),
            subtitle=self.last_messages.get(EVERYONE, f"{len(names)} {T('members_suffix')}"),
            clickable=True,
            show_status=False,
            role_badge=None,
            role_color=None,
            on_left_click=self._on_row_left_click,
            on_right_click=self._on_row_right_click,
            theme=theme,
            on_pin_toggle=self.toggle_pin_chat,
            on_read_toggle=self.toggle_read_chat,
        )
        self.members_layout.insertWidget(self.members_layout.count() - 1, group_row)
        self.sidebar_rows[EVERYONE] = group_row
        group_row.set_badge(self.unread_counts.get(EVERYONE, 0))

        saved_row = ChatListRow(
            key=SAVED_MESSAGES_KEY,
            avatar_text="\U0001F516",
            avatar_color="#6c8cff",
            title=T("saved_messages_title"),
            subtitle=self.last_messages.get(SAVED_MESSAGES_KEY, ""),
            clickable=True,
            show_status=False,
            role_badge=None,
            role_color=None,
            on_left_click=self._on_row_left_click,
            on_right_click=self._on_row_right_click,
            theme=theme,
            on_pin_toggle=self.toggle_pin_chat,
            on_read_toggle=self.toggle_read_chat,
        )
        self.members_layout.insertWidget(self.members_layout.count() - 1, saved_row)
        self.sidebar_rows[SAVED_MESSAGES_KEY] = saved_row
        saved_row.set_badge(self.unread_counts.get(SAVED_MESSAGES_KEY, 0))

        # User-created groups come right after Group / Saved Messages.
        for gid, g in sorted(self.groups.items(), key=lambda kv: kv[1]["name"].lower()):
            gkey = GROUP_PREFIX + gid
            grow = ChatListRow(
                key=gkey,
                avatar_text=g["name"],
                avatar_color=group_color(gid),
                avatar_image=pixmap_from_b64(g.get("avatar", "")),
                title=g["name"],
                subtitle=self.last_messages.get(gkey, f"{len(g['members'])} {T('members_suffix')}"),
                clickable=True,
                show_status=False,
                role_badge=None,
                role_color=None,
                on_left_click=self._on_row_left_click,
                on_right_click=self._on_row_right_click,
                theme=theme,
                on_pin_toggle=self.toggle_pin_chat,
                on_read_toggle=self.toggle_read_chat,
            )
            self.members_layout.insertWidget(self.members_layout.count() - 1, grow)
            self.sidebar_rows[gkey] = grow
            grow.set_badge(self.unread_counts.get(gkey, 0))
            if gkey in self.typing_until:
                self._update_row_preview(gkey)

        # Members are listed in their normal order, except that anyone the
        # user has pinned (via the chat-list swipe gesture) is moved to the
        # front of that list, right after Group / Saved Messages.
        others = [n for n in names if n != my_name]
        pinned_first = [n for n in others if n in self.pinned_chat_keys]
        rest = [n for n in others if n not in self.pinned_chat_keys]
        for name in pinned_first + rest:
            is_the_host = (name == host_name)
            role_badge = T("role_host") if is_the_host else (
                T("role_admin") if name in self.admins else (T("role_guest") if name in self.guests else T("role_member")))
            role_color = theme["accent"] if is_the_host else theme["muted_fg"]
            row = ChatListRow(
                key=name,
                avatar_text=name,
                avatar_color=avatar_color_for(name),
                title=((f"\U0001F4CC {name}" if name in self.pinned_chat_keys else name)
                       + (" \u270B" if name in self.hands else "")),
                subtitle=self.last_messages.get(name, ""),
                clickable=True,
                show_status=True,
                role_badge=role_badge,
                role_color=role_color,
                on_left_click=self._on_row_left_click,
                on_right_click=self._on_row_right_click,
                theme=theme,
                avatar_image=pixmap_from_b64(avatars.get(name, "")),
                status=statuses.get(name, "online"),
                on_pin_toggle=self.toggle_pin_chat,
                on_read_toggle=self.toggle_read_chat,
            )
            self.members_layout.insertWidget(self.members_layout.count() - 1, row)
            self.sidebar_rows[name] = row
            if bios.get(name):
                row.setToolTip(bios[name])
            row.set_badge(self.unread_counts.get(name, 0))
            row.set_ping(self.peer_pings.get(name))
            if name in self.typing_until:
                self._update_row_preview(name)

        if (self.current_target not in (None, EVERYONE, SAVED_MESSAGES_KEY)
                and not is_custom_group(self.current_target) and self.current_target not in names):
            # whoever we were privately chatting with left the room
            self.open_group()
        else:
            self._highlight_selected()

        if (self.current_target and self.current_target not in (EVERYONE, SAVED_MESSAGES_KEY)
                and not is_custom_group(self.current_target)):
            self._set_chat_desc(bios.get(self.current_target, ""))
        if self.search_edit.text():
            self._on_search_changed(self.search_edit.text())


# ---------- Main window ----------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Encrypted LAN Chat")
        self.resize(900, 620)

        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(APP_ICON_B64))
        self.setWindowIcon(QIcon(pixmap))

        self.current_theme = DEFAULT_THEME
        self.backend = ChatBackend()
        self._games_hub_window = None
        self._lang_test_window = None
        self._rates_window = None
        self._tools_hub_window = None
        self._tool_windows = {}        # "weather" / "calculator" / "converter" / "notes" -> window
        self.notes_store = NotesStore()  # notes + reminders (also polled while its window is closed)
        self._reminder_boxes = []
        self._known_names = set()
        self._locked = False
        self._lock_fails = 0
        self._last_activity = time.time()
        self._envelope_handlers = {
            "vote": self._h_vote, "checklist": self._h_checklist, "board": self._h_board,
            "game": self._h_game, "sync": self._h_sync, "ptt": self._h_ptt,
            "screen": self._h_screen, "ctl": self._h_ctl, "media": self._h_media,
        }
        self._online_games = {}
        self._screen_senders = {}
        self._screen_viewers = {}
        self._shared_players = {}
        self.contacts = ContactsStore()
        self._focus_until = 0.0
        self._presentation = False
        self._pres_prev_font = "medium"
        self._autoreply_sent = {}
        self._hand_up = False
        self._pending_invites = {}
        self.ping_history = {}

        self.stack = QStackedWidget()
        self.connect_page = ConnectPage()
        self.chat_page = ChatPage()
        self.stack.addWidget(self.connect_page)
        self.stack.addWidget(self.chat_page)
        self.setCentralWidget(self.stack)

        self._wire_backend()

        self.connect_page.connect_requested.connect(self._on_connect_requested)
        self.chat_page.send_requested.connect(self._on_send)
        self.chat_page.kick_requested.connect(self._on_kick_requested)
        self.chat_page.theme_change_requested.connect(self._on_user_theme_change)
        self.chat_page.theme_mode_change_requested.connect(self._on_theme_mode_change)
        self.chat_page.backup_requested.connect(self._on_backup_requested)
        self.chat_page.restore_requested.connect(self._on_restore_requested)
        self.chat_page.language_change_requested.connect(self.set_language)
        self.connect_page.language_change_requested.connect(self.set_language)
        self.chat_page.typing_requested.connect(self._on_typing_requested)
        self.chat_page.seen_requested.connect(self.backend.send_seen)
        self.chat_page.font_size_change_requested.connect(self.apply_font_size)

        self.theme_mode = get_setting("theme_mode", "manual")
        saved_theme = get_setting("theme", DEFAULT_THEME)
        self.apply_theme(saved_theme if saved_theme in THEMES else DEFAULT_THEME)
        self.chat_page.set_theme_mode_checked(self.theme_mode)
        self.apply_font_size("medium")

        self.tray_icon = QSystemTrayIcon(self.windowIcon(), self)
        self.tray_menu = QMenu()
        self.tray_show_action = self.tray_menu.addAction(T("tray_show"))
        self.tray_show_action.triggered.connect(self._restore_from_tray)
        self.tray_quit_action = self.tray_menu.addAction(T("tray_quit"))
        self.tray_quit_action.triggered.connect(self._quit_app)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.setVisible(True)
        self._tray_hint_shown = False

        # Keyboard shortcuts: Esc closes a private chat back to the group
        # view, Ctrl+F jumps to the in-chat search bar.
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self._on_escape_shortcut)
        QShortcut(QKeySequence("Ctrl+F"), self, self.chat_page._toggle_chat_search)

        # Reminders: checked on a timer owned by this window, so they still
        # fire while the app sits in the tray and the notes window is closed.
        self.notes_store.reminder_due.connect(self._on_reminder_due)
        self._reminder_timer = QTimer(self)
        self._reminder_timer.setInterval(15000)
        self._reminder_timer.timeout.connect(self.notes_store.check_due)
        self._reminder_timer.start()
        QTimer.singleShot(2000, self.notes_store.check_due)  # reminders that came due while the app was closed

        # App lock: cover + idle detection
        self.backend.my_bio = self.chat_page.my_bio
        self.lock_overlay = LockOverlay(self)
        self.lock_overlay.unlock_attempt.connect(self._try_unlock)
        self.lock_overlay.hide()
        self._activity_types = {
            QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove, QEvent.Type.Wheel,
        }
        QApplication.instance().installEventFilter(self)
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(10000)
        self._idle_timer.timeout.connect(self._check_idle)
        self._idle_timer.start()
        QShortcut(QKeySequence("Ctrl+L"), self, self.lock_now)
        QTimer.singleShot(0, self._lock_at_start)
        QShortcut(QKeySequence("F11"), self, self._toggle_presentation)
        self.backend.waiting_room = bool(get_setting("waiting_room", False))
        self._birthday_timer = QTimer(self)
        self._birthday_timer.setInterval(30 * 60 * 1000)
        self._birthday_timer.timeout.connect(self._check_birthdays)
        self._birthday_timer.start()
        QTimer.singleShot(4000, self._check_birthdays)

        # Automatic themes (follow Windows / time of day / occasions)
        self._auto_theme_timer = QTimer(self)
        self._auto_theme_timer.setInterval(60000)
        self._auto_theme_timer.timeout.connect(self._auto_theme_tick)
        self._auto_theme_timer.start()
        try:
            QApplication.styleHints().colorSchemeChanged.connect(lambda *_: self._auto_theme_tick())
        except Exception:
            pass
        QTimer.singleShot(500, self._auto_theme_tick)

    # ----- language -----

    def set_language(self, lang):
        if lang not in ("fa", "en"):
            return
        CURRENT_LANG[0] = lang
        self.chat_page.retranslate_ui()
        self.connect_page.retranslate_ui()
        self._refresh_members()
        if self._tools_hub_window is not None:
            self._tools_hub_window.retranslate()
        for win in self._tool_windows.values():
            if hasattr(win, "set_language"):
                win.set_language(lang)

    # ----- font size -----

    def apply_font_size(self, key):
        if key not in FONT_SIZES:
            return
        self.current_font_size = key
        QApplication.instance().setFont(QFont("Segoe UI", FONT_SIZES[key]))
        self.chat_page.set_font_size_checked(key)

    def _net_target(self, chat_key):
        """Map a chat key to what the backend wants: (recipient, group id).
        A user-created group becomes the list of its other members."""
        if is_custom_group(chat_key):
            gid = chat_key[len(GROUP_PREFIX):]
            g = self.chat_page.groups.get(gid)
            if not g:
                return [], gid
            me = self.backend.my_name
            return [m for m in g["members"] if m != me], gid
        return chat_key, None

    def _on_file_send_requested(self, path):
        recipient = self.chat_page.current_target
        if recipient is None:
            return
        ttl = self.chat_page.chat_ttl.get(recipient, 0)
        if recipient == SAVED_MESSAGES_KEY:
            network_target, gid = None, None
        else:
            network_target, gid = self._net_target(recipient)
        ts, msg_id, content = self.backend.send_file(path, network_target, ttl=ttl, group=gid)
        if not ts:
            return
        is_private = recipient != EVERYONE and gid is None
        peer = recipient if is_private else None
        self.chat_page.add_file_message(
            self.backend.my_name, content, is_own=True, is_private=is_private,
            peer=peer, theme=THEMES[self.current_theme], chat_key=recipient,
        )

    def _on_file_received(self, sender, content, is_private):
        gid = content.get("group")
        if gid and not is_private:
            if gid not in self.chat_page.groups:
                return
            chat_key, peer = GROUP_PREFIX + gid, None
        else:
            chat_key = sender if is_private else EVERYONE
            peer = sender if is_private else None
        if peer in self.chat_page.muted_names:
            return
        self.chat_page.add_file_message(
            sender, content, is_own=False, is_private=is_private,
            peer=peer, theme=THEMES[self.current_theme], chat_key=chat_key,
        )
        self._notify(chat_key, sender, f"\U0001F4CE {content.get('filename', '')}")

    def _on_security_code_requested(self, peer_name):
        with self.backend.peers_lock:
            info = self.backend.peers.get(peer_name)
        if not info:
            return
        my_pem = public_key_to_pem(self.backend.public_key)
        their_pem = public_key_to_pem(info["pubkey"])
        code = compute_safety_number(my_pem, their_pem)
        dlg = QDialog(self)
        dlg.setWindowTitle(T("security_code_title"))
        lay = QVBoxLayout(dlg)
        desc = QLabel(T("security_code_desc").format(name=peer_name))
        desc.setWordWrap(True)
        desc.setMinimumWidth(360)
        lay.addWidget(desc)
        code_lbl = QLabel(code)
        code_lbl.setStyleSheet("font-family: Consolas, monospace; font-size: 12pt; font-weight: 700;")
        code_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(code_lbl)
        matrix = None
        try:
            import qrcode
            qr = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(code)
            qr.make(fit=True)
            matrix = qr.get_matrix()
        except Exception:
            matrix = None
        if matrix:
            lay.addWidget(QRCodeWidget(matrix), alignment=Qt.AlignmentFlag.AlignCenter)
            hint = QLabel(T("qr_hint"))
        else:
            hint = QLabel(T("qr_missing"))
        hint.setObjectName("mutedLabel")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        dlg.exec()

    # ----- games / language test, also reachable while already in a chat -----

    def _on_games_requested(self):
        if self._games_hub_window is None:
            self._games_hub_window = GamesHubWindow()
        self._games_hub_window.show()
        self._games_hub_window.raise_()
        self._games_hub_window.activateWindow()

    def _on_language_test_requested(self):
        if self._lang_test_window is None:
            self._lang_test_window = LanguageTestWindow()
        self._lang_test_window.show()
        self._lang_test_window.raise_()
        self._lang_test_window.activateWindow()

    def _on_rates_requested(self):
        if self._rates_window is None:
            self._rates_window = RatesWindow()
        self._rates_window.show()
        self._rates_window.raise_()
        self._rates_window.activateWindow()

    def _show_tool(self, name, factory):
        win = self._tool_windows.get(name)
        if win is None:
            win = factory()
            self._tool_windows[name] = win
        if hasattr(win, "set_language"):
            win.set_language(CURRENT_LANG[0])
        win.show()
        win.raise_()
        win.activateWindow()

    def _on_tools_requested(self):
        if self._tools_hub_window is None:
            hub = ToolsHubWindow()
            hub.tool_requested.connect(self._open_tool)
            self._tools_hub_window = hub
        self._tools_hub_window.retranslate()
        self._tools_hub_window.show()
        self._tools_hub_window.raise_()
        self._tools_hub_window.activateWindow()

    def _open_tool(self, key):
        factories = {
            "weather": lambda: WeatherWindow(CURRENT_LANG[0]),
            "calculator": lambda: CalculatorWindow(CURRENT_LANG[0]),
            "converter": lambda: UnitConverterWindow(CURRENT_LANG[0]),
            "wol": lambda: WakeOnLanWindow(CURRENT_LANG[0]),
            "network": lambda: NetworkWindow(self._network_snapshot, CURRENT_LANG[0]),
        }
        if key in factories:
            self._show_tool(key, factories[key])

    def _on_notes_requested(self):
        self._show_tool("notes", lambda: NotesWindow(self.notes_store, CURRENT_LANG[0]))

    def _on_reminder_due(self, item):
        text = item.get("text", "")
        preview = text if len(text) <= 120 else text[:120] + "\u2026"
        QApplication.beep()
        self.tray_icon.showMessage(
            T("reminder_title"), preview, QSystemTrayIcon.MessageIcon.NoIcon, 8000
        )
        # A tray balloon vanishes after a few seconds, so also show a small
        # always-on-top box that stays until it's dismissed.
        box = QMessageBox(QMessageBox.Icon.Information, T("reminder_title"), text)
        box.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._reminder_boxes.append(box)
        box.finished.connect(
            lambda _result=0, b=box: self._reminder_boxes.remove(b) if b in self._reminder_boxes else None
        )
        box.show()

    # ----- profile picture (changeable any time, not just at Host/Join) -----

    def _on_avatar_change_requested(self):
        path, _ = QFileDialog.getOpenFileName(
            self, T("connect_btn_choose_picture"), "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        pixmap = pixmap.scaled(
            128, 128, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        buf = QByteArray()
        qbuf = QBuffer(buf)
        qbuf.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(qbuf, "PNG")
        b64 = base64.b64encode(bytes(buf)).decode("ascii")
        self.backend.send_avatar_update(b64)
        self.chat_page.set_my_avatar(self.backend.my_name, b64)
        self.chat_page.drawer_avatar.set_image(pixmap)

    # ----- theming -----

    def _on_user_theme_change(self, key):
        """The user picked a theme by hand: that switches to manual mode."""
        self.theme_mode = "manual"
        set_setting("theme_mode", "manual")
        set_setting("theme", key)
        self.chat_page.set_theme_mode_checked("manual")
        self.apply_theme(key)

    def _on_theme_mode_change(self, mode):
        self.theme_mode = mode
        set_setting("theme_mode", mode)
        self.chat_page.set_theme_mode_checked(mode)
        if mode == "manual":
            saved = get_setting("theme", DEFAULT_THEME)
            self.apply_theme(saved if saved in THEMES else DEFAULT_THEME)
        else:
            self._auto_theme_tick()

    def _auto_theme_tick(self):
        mode = getattr(self, "theme_mode", "manual")
        key = None
        if mode == "system":
            dark = system_prefers_dark()
            if dark is not None:
                key = "dark_modern" if dark else "light_clean"
        elif mode == "time":
            hour = time.localtime().tm_hour
            key = "dark_modern" if (hour >= 19 or hour < 7) else "light_clean"
        elif mode == "occasion":
            saved = get_setting("theme", DEFAULT_THEME)
            key = occasion_theme_for_today() or (saved if saved in THEMES else DEFAULT_THEME)
        if key and key != self.current_theme:
            self.apply_theme(key)

    # ----- settings backup / restore -----

    def _on_backup_requested(self):
        path, _ = QFileDialog.getSaveFileName(
            self, T("backup_export"), "lan_chat_backup.zip", "Zip (*.zip)"
        )
        if not path:
            return
        try:
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
                if os.path.isdir(APP_DATA_DIR):
                    for fn in os.listdir(APP_DATA_DIR):
                        full = os.path.join(APP_DATA_DIR, fn)
                        if fn.lower().endswith(".json") and os.path.isfile(full):
                            z.write(full, fn)
        except OSError as e:
            QMessageBox.information(self, T("backup_export"), str(e))
            return
        QMessageBox.information(self, T("backup_export"), T("backup_done").format(path=path))

    def _on_restore_requested(self):
        path, _ = QFileDialog.getOpenFileName(self, T("backup_restore"), "", "Zip (*.zip)")
        if not path:
            return
        try:
            with zipfile.ZipFile(path) as z:
                names = [n for n in z.namelist()
                         if n.lower().endswith(".json") and "/" not in n and "\\" not in n and not n.startswith(".")]
                payload = {}
                for n in names:
                    raw = z.read(n)
                    json.loads(raw.decode("utf-8"))  # must really be JSON
                    payload[n] = raw
        except Exception:
            payload = {}
        if not payload:
            QMessageBox.information(self, T("backup_restore"), T("backup_restore_bad"))
            return
        if QMessageBox.question(self, T("backup_restore"), T("backup_restore_confirm")) \
                != QMessageBox.StandardButton.Yes:
            return
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        for n, raw in payload.items():
            with open(os.path.join(APP_DATA_DIR, n), "wb") as f:
                f.write(raw)
        QMessageBox.information(self, T("backup_restore"), T("backup_restore_done"))

    # ----- notifications (honours each chat's own notification / sound settings) -----

    def _dnd_active(self):
        if self._presentation or time.time() < self._focus_until:
            return True
        cfg = get_setting("dnd", {}) or {}
        if not cfg.get("on"):
            return False

        def mins(text):
            try:
                h, m = text.split(":")
                return int(h) * 60 + int(m)
            except (ValueError, AttributeError):
                return 0

        now = time.localtime()
        cur = now.tm_hour * 60 + now.tm_min
        start, end = mins(cfg.get("from", "22:00")), mins(cfg.get("to", "07:00"))
        return (start <= cur < end) if start <= end else (cur >= start or cur < end)

    def _on_dnd_requested(self):
        cfg = get_setting("dnd", {}) or {}
        dlg = QDialog(self)
        dlg.setWindowTitle(T("dnd_title"))
        lay = QVBoxLayout(dlg)
        enable = QCheckBox(T("dnd_enable"))
        enable.setChecked(bool(cfg.get("on")))
        lay.addWidget(enable)
        row = QHBoxLayout()
        row.addWidget(QLabel(T("dnd_from")))
        t_from = QTimeEdit(QTime.fromString(cfg.get("from", "22:00"), "HH:mm"))
        row.addWidget(t_from)
        row.addWidget(QLabel(T("dnd_to")))
        t_to = QTimeEdit(QTime.fromString(cfg.get("to", "07:00"), "HH:mm"))
        row.addWidget(t_to)
        lay.addLayout(row)
        ok = QPushButton(T("schedule_ok"))
        ok.setObjectName("primaryButton")
        ok.clicked.connect(dlg.accept)
        lay.addWidget(ok)
        if dlg.exec():
            set_setting("dnd", {
                "on": enable.isChecked(),
                "from": t_from.time().toString("HH:mm"), "to": t_to.time().toString("HH:mm"),
            })

    def _notify(self, chat_key, title, body):
        if self._dnd_active():
            return
        if self._locked:
            title, body = "\U0001F512", T("lock_new_message")
        prefs = self.chat_page.chat_prefs.get(chat_key, {})
        if prefs.get("notify", True) is False:
            return
        if prefs.get("sound", True) is not False:
            if not voice_utils.play_sound_file(prefs.get("sound_file", "")):
                QApplication.beep()
        if not self.isActiveWindow():
            self.tray_icon.showMessage(title, body, QSystemTrayIcon.MessageIcon.NoIcon, 4000)

    def apply_theme(self, key):
        self.current_theme = key
        theme = THEMES[key]
        QApplication.instance().setStyleSheet(build_stylesheet(theme))
        self.chat_page.set_theme_checked(key)
        self.chat_page.apply_theme_to_history(theme)
        self._refresh_members()

    # ----- connect flow -----

    def _on_connect_requested(self, info):
        self.backend.my_name = info["name"]
        self.backend.my_avatar = info.get("avatar_b64", "")
        self.chat_page.set_my_avatar(self.backend.my_name, self.backend.my_avatar)
        self.backend.port = info["port"]
        self.connect_page.set_busy(True)
        self.connect_page.set_status(
            T("status_starting_host") if info["is_host"] else T("status_connecting")
        )

        if info["is_host"]:
            self.backend.is_host = True
            self.backend.room_password_hash = (
                hashlib.sha256(info["password"].encode("utf-8")).hexdigest()
                if info["password"] else ""
            )
            self.backend.max_members = info["max_members"]
            threading.Thread(
                target=self.backend.run_host, args=(info["port"],), daemon=True
            ).start()
        else:
            self.backend.join_password = info["password"]
            threading.Thread(
                target=self.backend.connect_to_host_safe,
                args=(info["ip"], info["port"], True, info["password"]),
                daemon=True,
            ).start()

    def _on_connect_failed(self, message):
        self.connect_page.set_busy(False)
        self.connect_page.set_status(message, is_error=True)

    # ----- signal wiring -----

    def _wire_backend(self):
        self.backend.status.connect(lambda msg: self.connect_page.set_status(msg))
        self.backend.switch_to_chat.connect(self._on_switch_to_chat)
        self.backend.message_received.connect(self._on_message_received)
        self.backend.system_message.connect(self.chat_page.add_system_message)
        self.backend.refresh_members.connect(self._refresh_members)
        self.backend.error.connect(self._on_error)
        self.backend.kicked.connect(self._on_kicked)
        self.backend.connect_failed.connect(self._on_connect_failed)
        self.backend.typing_received.connect(self._on_typing_received)
        self.backend.message_seen.connect(self.chat_page.mark_seen)
        self.backend.reconnect_status.connect(self._on_reconnect_status)
        self.backend.message_edited.connect(self.chat_page.apply_edit_local)
        self.backend.message_deleted.connect(self.chat_page.apply_delete_local)
        self.backend.pin_updated.connect(self._on_pin_updated)
        self.backend.message_reacted.connect(self.chat_page.apply_reaction_local)
        self.chat_page.edit_submit_requested.connect(self._on_edit_submit)
        self.chat_page.delete_requested.connect(self._on_delete_requested)
        self.chat_page.forward_to_requested.connect(self._on_forward_to_requested)
        self.chat_page.pin_toggle_requested.connect(self._on_pin_toggle)
        self.chat_page.reaction_toggle_requested.connect(self._on_reaction_toggle)
        self.chat_page.unpin_requested.connect(self._on_unpin_requested)
        self.chat_page.avatar_change_requested.connect(self._on_avatar_change_requested)
        self.chat_page.status_change_requested.connect(self.backend.send_status_update)
        self.backend.ping_updated.connect(self.chat_page.set_peer_ping)
        self.chat_page.file_send_requested.connect(self._on_file_send_requested)
        self.backend.file_received.connect(self._on_file_received)
        self.chat_page.security_code_requested.connect(self._on_security_code_requested)
        self.chat_page.games_requested.connect(self._on_games_requested)
        self.chat_page.language_test_requested.connect(self._on_language_test_requested)
        self.chat_page.rates_requested.connect(self._on_rates_requested)
        self.chat_page.slash_command_requested.connect(self._on_slash_command)
        self.chat_page.reply_reminder_requested.connect(self._on_reply_reminder)
        self.chat_page.location_requested.connect(self._on_location_requested)
        self.chat_page.race_invite_requested.connect(lambda peer: self._on_game_invite_requested(peer, "type"))
        self.chat_page.person_note_requested.connect(self._on_person_note_requested)
        self.chat_page.contacts_requested.connect(self._on_contacts_requested)
        self.chat_page.focus_requested.connect(self._on_focus_requested)
        self.chat_page.presentation_toggle_requested.connect(self._toggle_presentation)
        self.chat_page.waiting_room_toggled.connect(self._on_waiting_room_toggled)
        self.chat_page.autoreply_requested.connect(self._on_autoreply_requested)
        self.chat_page.incognito_view_changed.connect(self._on_incognito_view)
        self.backend.join_request.connect(self._on_join_request)
        self.chat_page.ptt_chunk.connect(self._on_ptt_chunk)
        self.chat_page.screen_share_toggled.connect(self._on_screen_share_toggled)
        self.chat_page.hand_toggle_requested.connect(self._on_hand_toggle)
        self.chat_page.hands_clear_requested.connect(self._on_hands_clear)
        self.chat_page.guest_toggle_requested.connect(self.backend.toggle_guest)
        self.backend.guests_updated.connect(self.chat_page.set_guests)
        self.chat_page.media_player_requested.connect(self._on_media_player_requested)
        self.backend.ping_updated.connect(self._on_ping_sample)
        self.chat_page.game_invite_requested.connect(self._on_game_invite_requested)
        self.chat_page.clipboard_share_requested.connect(self._on_clipboard_share_requested)
        self.chat_page.capsule_requested.connect(self._on_capsule_requested)
        self.chat_page.sync_file_requested.connect(self._on_sync_file_requested)
        self.backend.roles_updated.connect(self.chat_page.set_admins)
        self.chat_page.admin_toggle_requested.connect(self.backend.toggle_admin)
        self.chat_page.dnd_requested.connect(self._on_dnd_requested)
        self.chat_page.bio_change_requested.connect(self._on_bio_change)
        self.chat_page.checklist_changed.connect(self._on_checklist_changed)
        self.chat_page.board_event.connect(self._on_board_event)
        self.chat_page.security_pin_requested.connect(self._on_pin_requested)
        self.chat_page.security_autolock_requested.connect(self._on_autolock_requested)
        self.chat_page.security_lock_requested.connect(self.lock_now)
        self.backend.envelope_received.connect(self._on_envelope)
        self.chat_page.poll_create_requested.connect(self._on_poll_create_requested)
        self.chat_page.poll_vote_requested.connect(self._on_poll_vote_requested)
        self.chat_page.sticker_requested.connect(self._on_sticker_requested)
        self.chat_page.voice_recorded.connect(self._on_voice_recorded)
        self.chat_page.tools_requested.connect(self._on_tools_requested)
        self.chat_page.notes_requested.connect(self._on_notes_requested)
        self.backend.group_event.connect(self._on_group_event)
        self.backend.main_group_info_updated.connect(self._on_main_group_info_updated)
        self.chat_page.group_create_requested.connect(self._on_group_create_requested)
        self.chat_page.group_update_requested.connect(self._on_group_update_requested)
        self.chat_page.group_leave_requested.connect(self._on_group_leave_requested)
        self.chat_page.main_group_info_change_requested.connect(
            self._on_main_group_info_change_requested
        )

    def _on_switch_to_chat(self):
        self.chat_page.set_room_role(self.backend.is_host, self.backend.host_name)
        if self.backend.my_bio:
            self.backend.send_status_update(self.backend.my_status)
        self.chat_page.reset_view()
        self.stack.setCurrentWidget(self.chat_page)
        self._refresh_members()

    def _on_message_received(self, sender, content, is_private):
        peer = sender if is_private else None
        if peer in self.chat_page.muted_names:
            return
        gid = content.get("group")
        if gid and not is_private:
            group = self.chat_page.groups.get(gid)
            if group is None:
                return  # a group we were never told about
            if group.get("readonly") and sender != group["owner"]:
                return  # announcement channel: only the owner may post
            chat_key = GROUP_PREFIX + gid
        else:
            chat_key = peer if is_private else EVERYONE
        text = content.get("text", "")
        if content.get("poll"):
            self.chat_page.add_poll_message(sender, content, False, chat_key)
        elif content.get("location"):
            self.chat_page.add_location_message(sender, content, False, chat_key)
        else:
            self.chat_page.add_message(
                sender, text, content.get("time", ""), is_own=False, is_private=is_private,
                theme=THEMES[self.current_theme], peer=peer,
                msg_id=content.get("msg_id"),
                reply_to=content.get("reply_to"), reply_from=content.get("reply_from"),
                reply_text=content.get("reply_text"), forward_from=content.get("forward_from"),
                chat_key=chat_key, ttl=content.get("ttl", 0), sticker=bool(content.get("sticker")),
                capsule=self._safe_float(content.get("capsule")),
            )
        preview = text if len(text) <= 80 else text[:80] + "\u2026"
        self._notify(chat_key, sender, preview)
        if is_private:
            self._maybe_auto_reply(sender, text)

    def _on_typing_received(self, sender, is_private, group_id):
        if group_id:
            if group_id in self.chat_page.groups:
                self.chat_page.mark_typing(GROUP_PREFIX + group_id, who=sender)
        elif is_private:
            self.chat_page.mark_typing(sender)
        else:
            self.chat_page.mark_typing(EVERYONE, who=sender)

    def _on_typing_requested(self, target):
        recipient, gid = self._net_target(target)
        self.backend.send_typing(recipient, group_id=gid)

    def _on_send(self, text, recipient, extra):
        reply_to = extra.get("reply_to")
        reply_from = extra.get("reply_from")
        reply_text = extra.get("reply_text")
        ttl = int(extra.get("ttl", 0) or 0)
        if self.chat_page._is_readonly(recipient):
            return
        if recipient == SAVED_MESSAGES_KEY:
            # notes to self: never touches the network
            ts = time.strftime("%H:%M")
            msg_id = uuid.uuid4().hex[:12]
            self.chat_page.add_message(
                self.backend.my_name, text, ts,
                is_own=True, is_private=True, peer=SAVED_MESSAGES_KEY,
                theme=THEMES[self.current_theme], msg_id=msg_id,
                reply_to=reply_to, reply_from=reply_from, reply_text=reply_text, ttl=ttl,
            )
            return
        net_target, gid = self._net_target(recipient)
        ts, msg_id = self.backend.send_message(
            text, net_target, reply_to=reply_to, reply_from=reply_from, reply_text=reply_text,
            ttl=ttl, group=gid,
        )
        if ts:
            is_private = (recipient != EVERYONE and gid is None)
            peer = recipient if is_private else None
            self.chat_page.add_message(
                self.backend.my_name, text, ts,
                is_own=True, is_private=is_private, peer=peer,
                theme=THEMES[self.current_theme], msg_id=msg_id,
                reply_to=reply_to, reply_from=reply_from, reply_text=reply_text,
                chat_key=recipient, ttl=ttl,
            )

    def _on_edit_submit(self, msg_id, chat_key, new_text):
        if chat_key != SAVED_MESSAGES_KEY:
            self.backend.send_edit(msg_id, new_text, self._net_target(chat_key)[0])
        self.chat_page.apply_edit_local(msg_id, new_text)

    def _on_delete_requested(self, msg_id, chat_key):
        if chat_key != SAVED_MESSAGES_KEY:
            self.backend.send_delete(msg_id, self._net_target(chat_key)[0])
        self.chat_page.apply_delete_local(msg_id)

    def _on_forward_to_requested(self, orig_sender, text, target):
        if target == SAVED_MESSAGES_KEY:
            ts = time.strftime("%H:%M")
            msg_id = uuid.uuid4().hex[:12]
            self.chat_page.add_message(
                self.backend.my_name, text, ts, is_own=True, is_private=True,
                peer=SAVED_MESSAGES_KEY, theme=THEMES[self.current_theme],
                msg_id=msg_id, forward_from=orig_sender,
            )
            return
        net_target, gid = self._net_target(target)
        ts, msg_id = self.backend.send_message(text, net_target, forward_from=orig_sender, group=gid)
        if ts:
            is_private = (target != EVERYONE and gid is None)
            peer = target if is_private else None
            self.chat_page.add_message(
                self.backend.my_name, text, ts, is_own=True, is_private=is_private,
                peer=peer, theme=THEMES[self.current_theme],
                msg_id=msg_id, forward_from=orig_sender, chat_key=target,
            )

    def _on_kick_requested(self, name):
        if self.backend.is_host:
            self.backend.kick_peer(name)
        else:
            self.backend.request_kick(name)

    def _on_pin_toggle(self, msg_id, chat_key):
        pinned = {p["msg_id"]: p for p in self.chat_page.pinned_by_chat.get(chat_key, [])}
        already = msg_id in pinned
        info = self.chat_page.messages_by_id.get(msg_id)
        if info:
            sender, text = info["sender"], info["bubble"].raw_text
        elif already:
            sender, text = pinned[msg_id]["sender"], pinned[msg_id]["text"]
        else:
            return
        if chat_key != SAVED_MESSAGES_KEY:
            net_target, gid = self._net_target(chat_key)
            self.backend.send_pin(net_target, msg_id, sender, text, group=gid, unpin=already)
        self.chat_page.apply_pin_local(chat_key, msg_id, sender, text, unpin=already)

    def _on_pin_toggle_legacy(self, msg_id, chat_key):
        info = self.chat_page.messages_by_id.get(msg_id)
        if not info:
            return
        sender, text = info["sender"], info["bubble"].raw_text
        if chat_key != SAVED_MESSAGES_KEY:
            net_target, gid = self._net_target(chat_key)
            self.backend.send_pin(net_target, msg_id, sender, text, group=gid)
        self.chat_page.apply_pin_local(chat_key, msg_id, sender, text)

    def _on_reaction_toggle(self, msg_id, chat_key, emoji, action):
        # The local chip already updated instantly (ChatPage._request_react);
        # this just tells everyone else in that chat about it. Saved
        # Messages has no one else to tell.
        if chat_key != SAVED_MESSAGES_KEY:
            self.backend.send_reaction(self._net_target(chat_key)[0], msg_id, emoji, action)

    def _on_unpin_requested(self, chat_key):
        if chat_key != SAVED_MESSAGES_KEY:
            net_target, gid = self._net_target(chat_key)
            self.backend.send_pin(net_target, None, None, None, group=gid)
        self.chat_page.apply_pin_local(chat_key, None, None, None)

    def _on_pin_updated(self, is_private, from_name, content):
        gid = content.get("group")
        if gid and not is_private:
            chat_key = GROUP_PREFIX + gid
        else:
            chat_key = from_name if is_private else EVERYONE
        self.chat_page.apply_pin_local(
            chat_key, content.get("msg_id"), content.get("sender"), content.get("text"),
            unpin=bool(content.get("unpin")),
        )

    # ----- user-created groups -----

    def _group_others(self, group):
        me = self.backend.my_name
        return [m for m in group["members"] if m != me]

    def _on_group_create_requested(self, name, desc, avatar, members, readonly=False):
        me = self.backend.my_name
        gid = uuid.uuid4().hex[:10]
        group = {
            "id": gid, "name": name[:40], "desc": desc, "avatar": avatar, "owner": me,
            "members": [me] + [m for m in members if m != me], "readonly": bool(readonly),
        }
        self.chat_page.register_group(group)
        self.backend.send_group_event(self._group_others(group), {
            "action": "create", "gid": gid, "name": group["name"], "desc": desc,
            "avatar": avatar, "owner": me, "members": group["members"], "readonly": bool(readonly),
        })
        self.chat_page.open_private(GROUP_PREFIX + gid)

    def _on_group_update_requested(self, gid, name, desc, avatar):
        group = self.chat_page.groups.get(gid)
        if not group or group["owner"] != self.backend.my_name:
            return
        group["name"], group["desc"], group["avatar"] = name[:40], desc, avatar
        self.backend.send_group_event(self._group_others(group), {
            "action": "update", "gid": gid, "name": group["name"], "desc": desc, "avatar": avatar,
        })
        self.chat_page.group_changed(gid)

    def _on_group_leave_requested(self, gid):
        group = self.chat_page.groups.get(gid)
        if not group:
            return
        self.backend.send_group_event(self._group_others(group), {"action": "leave", "gid": gid})
        self.chat_page.remove_group(gid)

    def _on_group_event(self, sender, content):
        action = content.get("action")
        gid = content.get("gid")
        if not gid:
            return
        groups = self.chat_page.groups
        me = self.backend.my_name
        if action == "create":
            members = content.get("members") or []
            # Only the creator may announce a group, and only to its members.
            if gid in groups or sender != content.get("owner") or me not in members:
                return
            self.chat_page.register_group({
                "id": gid, "name": str(content.get("name") or "Group")[:40],
                "desc": str(content.get("desc") or ""), "avatar": content.get("avatar") or "",
                "owner": sender, "members": [str(m) for m in members],
                "readonly": bool(content.get("readonly")),
            })
        elif action == "update":
            group = groups.get(gid)
            if not group or sender != group["owner"]:
                return
            group["name"] = str(content.get("name") or group["name"])[:40]
            group["desc"] = str(content.get("desc") or "")
            group["avatar"] = content.get("avatar") or ""
            self.chat_page.group_changed(gid)
        elif action == "leave":
            group = groups.get(gid)
            if not group or sender not in group["members"]:
                return
            group["members"].remove(sender)
            if group["owner"] == sender and group["members"]:
                # every member picks the same new owner (first name alphabetically)
                group["owner"] = sorted(group["members"], key=str.lower)[0]
            self.chat_page.group_changed(gid)

    # ----- generic envelopes, polls, stickers, voice -----

    def _on_envelope(self, kind, sender, is_private, content):
        handler = self._envelope_handlers.get(kind)
        if handler:
            handler(sender, is_private, content)

    def _chat_key_for(self, sender, is_private, content):
        gid = content.get("group")
        if gid and not is_private:
            return GROUP_PREFIX + gid if gid in self.chat_page.groups else None
        return sender if is_private else EVERYONE

    def _h_vote(self, sender, is_private, content):
        self.chat_page.apply_poll_vote(sender, content.get("msg_id"), int(content.get("choice", -1)))

    def _send_rich(self, chat_key, text, extra):
        """Send a message carrying extra fields (poll, sticker, ...).
        Returns (ts, msg_id, ttl) or None if nothing was sent."""
        ttl = self.chat_page.chat_ttl.get(chat_key, 0)
        if chat_key == SAVED_MESSAGES_KEY:
            return time.strftime("%H:%M"), uuid.uuid4().hex[:12], ttl
        net_target, gid = self._net_target(chat_key)
        ts, msg_id = self.backend.send_message(text, net_target, ttl=ttl, group=gid, extra=extra)
        return (ts, msg_id, ttl) if ts else None

    def _on_poll_create_requested(self, chat_key, question, options):
        poll = {"q": question, "options": options}
        sent = self._send_rich(chat_key, question, {"poll": poll})
        if not sent:
            return
        ts, msg_id, ttl = sent
        self.chat_page.add_poll_message(
            self.backend.my_name,
            {"msg_id": msg_id, "poll": poll, "time": ts, "ttl": ttl, "text": question},
            True, chat_key,
        )

    def _on_poll_vote_requested(self, chat_key, msg_id, choice):
        if chat_key == SAVED_MESSAGES_KEY:
            return
        net_target, gid = self._net_target(chat_key)
        self.backend.send_envelope("vote", net_target, {"msg_id": msg_id, "choice": choice, "group": gid})

    def _on_sticker_requested(self, chat_key, sticker):
        sent = self._send_rich(chat_key, sticker, {"sticker": True})
        if not sent:
            return
        ts, msg_id, ttl = sent
        is_private = chat_key not in (EVERYONE,) and not is_custom_group(chat_key)
        self.chat_page.add_message(
            self.backend.my_name, sticker, ts, is_own=True, is_private=is_private,
            peer=chat_key if is_private else None, theme=THEMES[self.current_theme],
            msg_id=msg_id, chat_key=chat_key, ttl=ttl, sticker=True,
        )

    def _on_voice_recorded(self, chat_key, data, seconds):
        ttl = self.chat_page.chat_ttl.get(chat_key, 0)
        if chat_key == SAVED_MESSAGES_KEY:
            net_target, gid = None, None
        else:
            net_target, gid = self._net_target(chat_key)
        ts, msg_id, content = self.backend.send_file(
            time.strftime("voice_%H%M%S.wav"), net_target, ttl=ttl, group=gid,
            raw=data, kind="voice", extra={"duration": seconds},
        )
        if not ts:
            return
        is_private = chat_key != EVERYONE and gid is None
        self.chat_page.add_file_message(
            self.backend.my_name, content, is_own=True, is_private=is_private,
            peer=chat_key if is_private else None, theme=THEMES[self.current_theme],
            chat_key=chat_key,
        )

    # ----- status line, shared checklist / whiteboard -----

    def _on_bio_change(self, text):
        set_setting("bio", text)
        self.chat_page.my_bio = text
        self.backend.send_status_update(self.backend.my_status, bio=text)

    def _on_checklist_changed(self, key, items):
        if key == SAVED_MESSAGES_KEY:
            return
        net_target, gid = self._net_target(key)
        self.backend.send_envelope("checklist", net_target, {"items": items, "group": gid})

    def _on_board_event(self, key, content):
        if key == SAVED_MESSAGES_KEY:
            return
        net_target, gid = self._net_target(key)
        payload = dict(content)
        payload["group"] = gid
        self.backend.send_envelope("board", net_target, payload)

    def _h_checklist(self, sender, is_private, content):
        key = self._chat_key_for(sender, is_private, content)
        if key is not None:
            self.chat_page.apply_remote_checklist(key, sender, content.get("items") or [])

    def _h_board(self, sender, is_private, content):
        key = self._chat_key_for(sender, is_private, content)
        if key is not None:
            self.chat_page.apply_remote_board(key, content)

    # ----- app lock (PIN) and idle auto-lock -----

    def eventFilter(self, obj, event):
        if event.type() in self._activity_types:
            self._last_activity = time.time()
        return False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "lock_overlay", None) is not None:
            self.lock_overlay.setGeometry(0, 0, self.width(), self.height())

    def _has_pin(self):
        return bool(get_setting("pin_hash", ""))

    def _lock_at_start(self):
        if self._has_pin():
            self.lock_now()

    def lock_now(self):
        if not self._has_pin():
            QMessageBox.information(self, T("security_pin"), T("pin_need_first"))
            return
        self._locked = True
        self.chat_page._close_drawer()
        self.lock_overlay.retranslate()
        self.lock_overlay.setGeometry(0, 0, self.width(), self.height())
        self.lock_overlay.set_message("")
        self.lock_overlay.show()
        self.lock_overlay.raise_()
        self.stack.setEnabled(False)
        self.lock_overlay.entry.setFocus()

    def _try_unlock(self, pin):
        salt, stored = get_setting("pin_salt", ""), get_setting("pin_hash", "")
        if stored and salt and hash_pin(pin, salt) == stored:
            self._locked = False
            self._lock_fails = 0
            self._last_activity = time.time()
            self.lock_overlay.hide()
            self.stack.setEnabled(True)
            return
        self._lock_fails += 1
        self.lock_overlay.set_message(T("pin_wrong"))
        if self._lock_fails >= 3:
            wait = 5 * (self._lock_fails - 2)
            self.lock_overlay.set_message(T("lock_wait").format(n=wait))
            self.lock_overlay.set_busy(True)
            QTimer.singleShot(wait * 1000, lambda: self.lock_overlay.set_busy(False))

    def _check_idle(self):
        self._focus_tick()
        minutes = int(get_setting("auto_lock_min", 0) or 0)
        if minutes and not self._locked and self._has_pin():
            if time.time() - self._last_activity >= minutes * 60:
                self.lock_now()

    def _ask_pin(self, label):
        pin, ok = QInputDialog.getText(self, T("security_pin"), label, QLineEdit.EchoMode.Password)
        return pin if ok else None

    def _verify_current_pin(self):
        pin = self._ask_pin(T("pin_ask_current"))
        if pin is None:
            return False
        if hash_pin(pin, get_setting("pin_salt", "00")) == get_setting("pin_hash", ""):
            return True
        QMessageBox.information(self, T("security_pin"), T("pin_wrong"))
        return False

    def _set_new_pin(self):
        pin = self._ask_pin(T("pin_ask_new"))
        if pin is None:
            return
        again = self._ask_pin(T("pin_ask_repeat"))
        if again is None:
            return
        if pin != again or len(pin) < 4:
            QMessageBox.information(self, T("security_pin"), T("pin_mismatch"))
            return
        salt = os.urandom(16).hex()
        set_setting("pin_salt", salt)
        set_setting("pin_hash", hash_pin(pin, salt))

    def _on_pin_requested(self):
        menu = QMenu(self)
        if self._has_pin():
            change = menu.addAction(T("pin_change"))
            remove = menu.addAction(T("pin_remove"))
        else:
            change = menu.addAction(T("pin_set"))
            remove = None
        chosen = menu.exec(QCursor.pos())
        if chosen is None:
            return
        if self._has_pin() and not self._verify_current_pin():
            return
        if chosen == remove:
            settings = load_app_settings()
            for k in ("pin_hash", "pin_salt", "auto_lock_min"):
                settings.pop(k, None)
            save_app_settings(settings)
        else:
            self._set_new_pin()

    def _on_autolock_requested(self):
        if not self._has_pin():
            QMessageBox.information(self, T("security_autolock"), T("pin_need_first"))
            return
        current = int(get_setting("auto_lock_min", 0) or 0)
        menu = QMenu(self)
        actions = {}
        for minutes in (0, 1, 5, 15, 30):
            label = T("autolock_off") if minutes == 0 else T("autolock_min").format(n=minutes)
            actions[menu.addAction(("\u2713 " if minutes == current else "") + label)] = minutes
        chosen = menu.exec(QCursor.pos())
        if chosen in actions:
            set_setting("auto_lock_min", actions[chosen])

    # ----- network health, online games, clipboard, capsule, sync -----

    @staticmethod
    def _safe_float(value):
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _on_ping_sample(self, name, ms):
        self.ping_history.setdefault(name, deque(maxlen=300)).append((time.time(), ms))

    def _network_snapshot(self):
        me = self.backend.my_name
        host = me if self.backend.is_host else self.backend.host_name
        members = [{"name": me, "ip": self.backend.my_ip, "status": self.backend.my_status, "ping": None}]
        with self.backend.peers_lock:
            for name, info in self.backend.peers.items():
                members.append({
                    "name": name, "ip": info.get("ip", ""), "status": info.get("status", "online"),
                    "ping": self.backend.peer_ping.get(name),
                })
        return {"me": me, "host": host, "members": members,
                "history": {n: list(d) for n, d in self.ping_history.items()}}

    def _send_game(self, peer, content):
        self.backend.send_envelope("game", peer, content)

    def _on_game_invite_requested(self, peer, kind="ttt"):
        gid = uuid.uuid4().hex[:8]
        sentence = ""
        if kind == "type":
            sentence = random.choice(TYPING_SENTENCES["fa" if CURRENT_LANG[0] == "fa" else "en"])
        self._pending_invites[gid] = (peer, kind, sentence)
        self._send_game(peer, {"game": kind, "op": "invite", "id": gid, "sentence": sentence})
        self.chat_page._touch_chat_preview(peer, "\U0001F3AE " + T("game_invite_sent"), True, self.backend.my_name)

    def _register_game_window(self, gid, win):
        self._online_games[gid] = win
        win.destroyed.connect(lambda _=None, g=gid: self._online_games.pop(g, None))
        win.show()
        win.raise_()
        win.activateWindow()

    def _open_online_ttt(self, gid, opponent, symbol):
        self._register_game_window(gid, OnlineTTTWindow(
            gid, opponent, symbol, lambda c, p=opponent: self._send_game(p, c), CURRENT_LANG[0]))

    def _open_online_race(self, gid, opponent, sentence):
        self._register_game_window(gid, OnlineTypingWindow(
            gid, opponent, sentence, lambda c, p=opponent: self._send_game(p, c), CURRENT_LANG[0]))

    def _ask_game_invite(self, sender, gid, kind, sentence):
        text = T("race_invite_text" if kind == "type" else "game_invite_text").format(name=sender)
        if QMessageBox.question(self, T("game_challenge"), text) == QMessageBox.StandardButton.Yes:
            self._send_game(sender, {"game": kind, "op": "accept", "id": gid})
            if kind == "type":
                self._open_online_race(gid, sender, sentence)
            else:
                self._open_online_ttt(gid, sender, "O")
        else:
            self._send_game(sender, {"game": kind, "op": "decline", "id": gid})

    def _h_game(self, sender, is_private, content):
        kind = content.get("game")
        if not is_private or kind not in ("ttt", "type"):
            return
        op, gid = content.get("op"), str(content.get("id", ""))
        if op == "invite":
            sentence = str(content.get("sentence", ""))[:200]
            QTimer.singleShot(0, lambda: self._ask_game_invite(sender, gid, kind, sentence))
        elif op == "accept":
            pending = self._pending_invites.get(gid)
            if pending and pending[0] == sender:
                del self._pending_invites[gid]
                if pending[1] == "type":
                    self._open_online_race(gid, sender, pending[2])
                else:
                    self._open_online_ttt(gid, sender, "X")
        elif op == "decline":
            self._pending_invites.pop(gid, None)
        elif op in ("move", "reset", "leave", "done"):
            win = self._online_games.get(gid)
            if win is not None and win.opponent == sender:
                win.on_remote(content)

    def _send_raw_file(self, chat_key, filename, raw):
        ttl = self.chat_page.chat_ttl.get(chat_key, 0)
        if chat_key == SAVED_MESSAGES_KEY:
            net_target, gid = None, None
        else:
            net_target, gid = self._net_target(chat_key)
        ts, msg_id, content = self.backend.send_file(filename, net_target, ttl=ttl, group=gid, raw=raw)
        if not ts:
            return
        is_private = chat_key != EVERYONE and gid is None
        self.chat_page.add_file_message(
            self.backend.my_name, content, is_own=True, is_private=is_private,
            peer=chat_key if is_private else None, theme=THEMES[self.current_theme], chat_key=chat_key,
        )

    def _on_clipboard_share_requested(self, chat_key):
        clip = QApplication.clipboard()
        text = clip.text()
        if text:
            self._on_send("\U0001F4CB " + text[:4000], chat_key, {"ttl": self.chat_page.chat_ttl.get(chat_key, 0)})
            return
        image = clip.image()
        if not image.isNull():
            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            image.save(buf, "PNG")
            self._send_raw_file(chat_key, time.strftime("clipboard_%H%M%S.png"), bytes(ba))
            return
        QMessageBox.information(self, T("clipboard_share"), T("clipboard_empty"))

    def _on_capsule_requested(self, chat_key, text, epoch):
        sent = self._send_rich(chat_key, text, {"capsule": epoch})
        if not sent:
            return
        ts, msg_id, ttl = sent
        is_private = chat_key != EVERYONE and not is_custom_group(chat_key)
        self.chat_page.add_message(
            self.backend.my_name, text, ts, is_own=True, is_private=is_private,
            peer=chat_key if is_private else None, theme=THEMES[self.current_theme],
            msg_id=msg_id, chat_key=chat_key, ttl=ttl, capsule=epoch,
        )

    def _on_sync_file_requested(self, chat_key, rel, data_b64, sha):
        net_target, gid = self._net_target(chat_key)
        self.backend.send_envelope("sync", net_target, {"rel": rel, "data": data_b64, "sha": sha, "group": gid})

    def _h_sync(self, sender, is_private, content):
        key = self._chat_key_for(sender, is_private, content)
        if key is not None:
            self.chat_page.apply_remote_sync(key, sender, content)

    # ----- live features -----

    def _on_ptt_chunk(self, key, pcm):
        net_target, gid = self._net_target(key)
        self.backend.send_envelope("ptt", net_target, {"pcm": base64.b64encode(pcm).decode("ascii"), "group": gid})

    def _h_ptt(self, sender, is_private, content):
        if self._locked or self._dnd_active() or sender in self.chat_page.muted_names:
            return
        try:
            voice_utils.ptt_play(sender, base64.b64decode(content.get("pcm", "")))
        except Exception:
            pass

    def _on_screen_share_toggled(self, key, on):
        if on:
            net_target, _gid = self._net_target(key)
            count = len(net_target) if isinstance(net_target, list) else (
                len(self.backend.peers) if key == EVERYONE else 1)
            if QMessageBox.question(self, T("screen_start"), T("screen_confirm").format(n=count)) \
                    != QMessageBox.StandardButton.Yes:
                return
            sharer = ScreenSharer(self)
            sharer.frame.connect(lambda jpeg, k=key: self._send_screen_frame(k, jpeg))
            self._screen_senders[key] = sharer
            self.chat_page.sharing_keys.add(key)
            sharer.start()
            self.tray_icon.showMessage(T("screen_start"), T("screen_sharing_now"),
                                       QSystemTrayIcon.MessageIcon.NoIcon, 3000)
        else:
            sharer = self._screen_senders.pop(key, None)
            if sharer is not None:
                sharer.stop()
                sharer.deleteLater()
            self.chat_page.sharing_keys.discard(key)
            net_target, gid = self._net_target(key)
            self.backend.send_envelope("screen", net_target, {"op": "stop", "group": gid})

    def _send_screen_frame(self, key, jpeg):
        net_target, gid = self._net_target(key)
        self.backend.send_envelope(
            "screen", net_target,
            {"op": "frame", "frame": base64.b64encode(jpeg).decode("ascii"), "group": gid},
        )

    def _h_screen(self, sender, is_private, content):
        if self._locked:
            return
        op = content.get("op")
        win = self._screen_viewers.get(sender)
        if op == "frame":
            if win is None:
                win = ScreenViewerWindow(T("screen_viewer_title").format(name=sender))
                self._screen_viewers[sender] = win
                win.show()
                self.tray_icon.showMessage(sender, T("screen_viewer_title").format(name=sender),
                                           QSystemTrayIcon.MessageIcon.NoIcon, 3000)
            try:
                win.set_frame(base64.b64decode(content.get("frame", "")))
            except Exception:
                pass
        elif op == "stop" and win is not None:
            win.set_message(T("screen_stopped"))

    def _on_hand_toggle(self):
        self._hand_up = not self._hand_up
        self.backend.send_envelope("ctl", EVERYONE, {"op": "hand", "on": self._hand_up})
        self.chat_page.set_hand(self.backend.my_name, self._hand_up)

    def _on_hands_clear(self):
        self.backend.send_envelope("ctl", EVERYONE, {"op": "clear_hands"})
        self._hand_up = False
        self.chat_page.hands.clear()
        self.chat_page._rebuild_sidebar()

    def _h_ctl(self, sender, is_private, content):
        if is_private or content.get("group"):
            return
        op = content.get("op")
        if op == "hand":
            self.chat_page.set_hand(sender, bool(content.get("on")))
        elif op == "clear_hands":
            host = self.backend.my_name if self.backend.is_host else self.backend.host_name
            if sender == host or sender in self.backend.admins:
                self._hand_up = False
                self.chat_page.hands.clear()
                self.chat_page._rebuild_sidebar()

    def _send_media(self, key, content):
        net_target, gid = self._net_target(key)
        payload = dict(content)
        payload["group"] = gid
        self.backend.send_envelope("media", net_target, payload)

    def _get_shared_player(self, key):
        win = self._shared_players.get(key)
        if win is None:
            win = SharedPlayerWindow(lambda c, k=key: self._send_media(k, c), CURRENT_LANG[0])
            self._shared_players[key] = win
        win.set_language(CURRENT_LANG[0])
        return win

    def _on_media_player_requested(self, key):
        win = self._get_shared_player(key)
        win.show()
        win.raise_()
        win.activateWindow()

    def _h_media(self, sender, is_private, content):
        key = self._chat_key_for(sender, is_private, content)
        if key is None or self._locked:
            return
        if key not in self._shared_players and content.get("op") != "load":
            return
        win = self._get_shared_player(key)
        if content.get("op") == "load" and not win.isVisible():
            win.show()
        win.on_remote(content, sender)

    # ----- slash commands, reminders, locations, contacts -----

    def _on_slash_command(self, cmd, arg):
        if cmd == "lock":
            self.lock_now()
        elif cmd == "present":
            self._toggle_presentation()
        elif cmd == "focus":
            self._on_focus_requested(int(arg) if arg.isdigit() else 30)

    def _on_reply_reminder(self, sender, text, minutes):
        preview = text if len(text) <= 80 else text[:80] + "\u2026"
        self.notes_store.add(
            T("reply_reminder_text").format(name=sender, text=preview), time.time() + minutes * 60
        )

    def _on_location_requested(self, chat_key, loc):
        text = ChatPage._location_text(loc)
        sent = self._send_rich(chat_key, text, {"location": loc})
        if not sent:
            return
        ts, msg_id, ttl = sent
        self.chat_page.add_location_message(
            self.backend.my_name,
            {"msg_id": msg_id, "location": loc, "time": ts, "ttl": ttl, "text": text}, True, chat_key,
        )

    def _on_contacts_requested(self):
        self._show_tool("contacts", lambda: ContactsWindow(self.contacts, CURRENT_LANG[0]))

    def _on_person_note_requested(self, name):
        self._on_contacts_requested()
        self._tool_windows["contacts"].select(name)

    def _check_birthdays(self):
        today = time.strftime("%Y-%m-%d")
        notified = dict(get_setting("bday_notified", {}) or {})
        changed = False
        for name in self.contacts.birthdays_today():
            if notified.get(name) != today:
                notified[name] = today
                changed = True
                self.tray_icon.showMessage(
                    "\U0001F382", T("birthday_today").format(name=name), QSystemTrayIcon.MessageIcon.NoIcon, 8000
                )
        if changed:
            set_setting("bday_notified", notified)

    # ----- focus / presentation / waiting room / auto-reply / incognito -----

    def _on_focus_requested(self, minutes):
        self._focus_until = time.time() + minutes * 60 if minutes else 0.0
        self.chat_page.set_focus_banner(self._focus_until)

    def _focus_tick(self):
        if self._focus_until and time.time() >= self._focus_until:
            self._focus_until = 0.0
            self.chat_page.set_focus_banner(0)

    def _toggle_presentation(self):
        self._presentation = not self._presentation
        if self._presentation:
            self._pres_prev_font = getattr(self, "current_font_size", "medium")
            self.apply_font_size("large")
            self.chat_page.set_presentation(True)
            self.showFullScreen()
        else:
            self.apply_font_size(self._pres_prev_font)
            self.chat_page.set_presentation(False)
            self.showNormal()

    def _on_waiting_room_toggled(self, on):
        set_setting("waiting_room", on)
        self.backend.waiting_room = on

    def _on_join_request(self, name, token):
        allowed = QMessageBox.question(
            self, T("waiting_row"), T("join_request_text").format(name=name)
        ) == QMessageBox.StandardButton.Yes
        self.backend.resolve_join(token, allowed)

    def _on_autoreply_requested(self):
        cfg = get_setting("autoreply", {}) or {}
        dlg = QDialog(self)
        dlg.setWindowTitle(T("autoreply_row"))
        dlg.setMinimumWidth(420)
        lay = QVBoxLayout(dlg)
        enable = QCheckBox(T("autoreply_enable"))
        enable.setChecked(bool(cfg.get("on")))
        lay.addWidget(enable)
        text_edit = QLineEdit(cfg.get("text") or T("autoreply_default"))
        text_edit.setMaxLength(200)
        lay.addWidget(text_edit)
        ok = QPushButton(T("schedule_ok"))
        ok.setObjectName("primaryButton")
        ok.clicked.connect(dlg.accept)
        lay.addWidget(ok)
        if dlg.exec():
            set_setting("autoreply", {"on": enable.isChecked(), "text": text_edit.text().strip()})

    def _maybe_auto_reply(self, sender, text):
        cfg = get_setting("autoreply", {}) or {}
        if not cfg.get("on") or self.backend.my_status != "away" or text.startswith("\U0001F916"):
            return
        if time.time() - self._autoreply_sent.get(sender, 0) < 1800:
            return
        self._autoreply_sent[sender] = time.time()
        reply = "\U0001F916 " + (cfg.get("text") or T("autoreply_default"))
        QTimer.singleShot(600, lambda: self._on_send(reply, sender, {"ttl": 0}))

    def _on_incognito_view(self, on):
        """While an incognito chat is on screen, ask Windows to hide this
        window from screenshots / screen recording (Windows 10 2004+)."""
        try:
            import ctypes
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), 0x11 if on else 0x0)
        except Exception:
            pass

    def _on_main_group_info_change_requested(self, desc, avatar):
        self.backend.send_main_group_info(desc, avatar)
        self.chat_page.set_main_group_info(desc, avatar)

    def _on_main_group_info_updated(self, desc, avatar):
        self.chat_page.set_main_group_info(desc, avatar)

    def _on_reconnect_status(self, status):
        self.chat_page.set_reconnecting(status == "start")

    def _on_error(self, message):
        self.chat_page.add_system_message(f"\u26a0 {message}")
        self.chat_page.set_reconnecting(False)

    def _on_kicked(self):
        QMessageBox.information(
            self, T("kicked_dialog_title"), T("kicked_dialog_body")
        )
        self.close()

    def _refresh_members(self):
        with self.backend.peers_lock:
            names = list(self.backend.peers.keys())
            avatars = {n: info.get("avatar", "") for n, info in self.backend.peers.items()}
            statuses = {n: info.get("status", "online") for n, info in self.backend.peers.items()}
        all_names = [self.backend.my_name] + [n for n in names if n != self.backend.my_name]
        newcomers = set(all_names) - self._known_names - {self.backend.my_name}
        self._known_names = set(all_names)
        if newcomers and self.backend.my_bio and self.backend.running:
            self.backend.send_status_update(self.backend.my_status)  # lets them see my status line
        if newcomers and self._hand_up and self.backend.running:
            self.backend.send_envelope("ctl", EVERYONE, {"op": "hand", "on": True})
        host_name = self.backend.my_name if self.backend.is_host else self.backend.host_name
        self.chat_page.update_members(
            sorted(all_names, key=str.lower),
            my_name=self.backend.my_name,
            host_name=host_name,
            is_host=self.backend.is_host,
            theme=THEMES[self.current_theme],
            avatars=avatars,
            statuses=statuses,
            bios=dict(self.backend.peer_bios),
        )

    def _on_escape_shortcut(self):
        if self.chat_page.current_target not in (None, EVERYONE):
            self.chat_page.open_group()

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_app(self):
        self.backend.shutdown()
        self.tray_icon.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        # Minimize to the system tray instead of fully closing, so the
        # chat (and its connection) keeps running in the background.
        event.ignore()
        self.hide()
        if not self._tray_hint_shown:
            self._tray_hint_shown = True
            self.tray_icon.showMessage(
                T("tray_hint_title"), T("tray_hint_body"),
                QSystemTrayIcon.MessageIcon.Information, 3500,
            )


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # The main window only hides to the tray when closed, and reminders need
    # the app alive, so closing a tool/game window must never quit the app.
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
