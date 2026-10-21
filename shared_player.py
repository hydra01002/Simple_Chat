"""Shared audio player ("listen together"): one person picks a music file,
it is sent to the others (up to 50 MB), and play / pause / seek commands
from ANY participant are applied on everyone's player. Sync is approximate
(network delay), audio only (a video file plays its sound).
Uses QtMultimedia; if it's missing the window says so instead of crashing."""

import base64
import os
import re
import tempfile

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFileDialog,
)

from tools_common import TOOL_STYLE

try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    AVAILABLE = True
except Exception:  # pragma: no cover
    AVAILABLE = False

MAX_BYTES = 50 * 1024 * 1024

STR = {
    "title": {"fa": "پخش‌کننده‌ی مشترک", "en": "Shared player"},
    "open": {"fa": "انتخاب و ارسال فایل صوتی...", "en": "Pick & share an audio file..."},
    "nothing": {"fa": "فایلی بارگذاری نشده", "en": "Nothing loaded"},
    "no_mm": {"fa": "QtMultimedia در دسترس نیست.", "en": "QtMultimedia isn't available."},
    "too_big": {"fa": "فایل از ۵۰ مگابایت بزرگ‌تره.", "en": "That file is over 50 MB."},
    "shared_by": {"fa": "از طرف {name}", "en": "from {name}"},
    "note": {"fa": "هر کدوم از شرکت‌کننده‌ها می‌تونه پخش/مکث/جابه‌جایی رو برای همه کنترل کنه.", "en": "Anyone here can play / pause / seek for everyone."},
}


def _fmt(ms):
    s = max(0, int(ms // 1000))
    return f"{s // 60}:{s % 60:02d}"


class SharedPlayerWindow(QMainWindow):
    def __init__(self, send_cb, lang="en"):
        super().__init__()
        self.send_cb = send_cb
        self.lang = lang if lang in ("fa", "en") else "en"
        self.setMinimumSize(420, 240)
        self._tmp_path = None
        self._dragging = False

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)
        self.name_lbl = QLabel("")
        self.name_lbl.setStyleSheet("font-size: 12pt; font-weight: 700;")
        self.name_lbl.setWordWrap(True)
        root.addWidget(self.name_lbl)
        self.open_btn = QPushButton("")
        self.open_btn.clicked.connect(self._pick_file)
        root.addWidget(self.open_btn)

        row = QHBoxLayout()
        self.play_btn = QPushButton("\u25B6")
        self.play_btn.setObjectName("primary")
        self.play_btn.setFixedWidth(56)
        self.play_btn.clicked.connect(self._toggle)
        row.addWidget(self.play_btn)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.sliderPressed.connect(lambda: setattr(self, "_dragging", True))
        self.slider.sliderReleased.connect(self._seek_released)
        row.addWidget(self.slider, stretch=1)
        self.time_lbl = QLabel("0:00 / 0:00")
        row.addWidget(self.time_lbl)
        root.addLayout(row)
        self.note_lbl = QLabel("")
        self.note_lbl.setObjectName("muted")
        self.note_lbl.setWordWrap(True)
        root.addWidget(self.note_lbl)
        root.addStretch(1)

        self.player = None
        if AVAILABLE:
            self.audio = QAudioOutput()
            self.audio.setVolume(0.8)
            self.player = QMediaPlayer()
            self.player.setAudioOutput(self.audio)
            self.player.positionChanged.connect(self._on_position)
            self.player.durationChanged.connect(lambda d: self.slider.setRange(0, int(d)))
            self.player.playbackStateChanged.connect(self._on_state)
        self.setStyleSheet(TOOL_STYLE)
        self._retranslate()

    def _t(self, key, **kw):
        return STR[key][self.lang].format(**kw)

    def _retranslate(self):
        self.setWindowTitle("\U0001F3B5 " + self._t("title"))
        self.open_btn.setText(self._t("open"))
        self.note_lbl.setText(self._t("note") if AVAILABLE else self._t("no_mm"))
        if not self.name_lbl.text():
            self.name_lbl.setText(self._t("nothing"))

    def set_language(self, lang):
        self.lang = lang if lang in ("fa", "en") else "en"
        self._retranslate()

    # ----- local actions (also broadcast) -----

    def _pos(self):
        return int(self.player.position()) if self.player else 0

    def _pick_file(self):
        if not AVAILABLE:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, self._t("open"), "", "Audio (*.mp3 *.wav *.ogg *.flac *.m4a *.aac *.mp4 *.mkv)"
        )
        if not path:
            return
        if os.path.getsize(path) > MAX_BYTES:
            self.name_lbl.setText(self._t("too_big"))
            return
        with open(path, "rb") as f:
            raw = f.read()
        name = os.path.basename(path)
        self._load_bytes(name, raw, "")
        self.send_cb({"op": "load", "name": name, "data": base64.b64encode(raw).decode("ascii")})

    def _toggle(self):
        if not self.player:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.send_cb({"op": "pause", "pos": self._pos()})
        else:
            self.player.play()
            self.send_cb({"op": "play", "pos": self._pos()})

    def _seek_released(self):
        self._dragging = False
        if self.player:
            self.player.setPosition(self.slider.value())
            self.send_cb({"op": "seek", "pos": self.slider.value()})

    # ----- player callbacks -----

    def _on_position(self, pos):
        if not self._dragging:
            self.slider.setValue(int(pos))
        self.time_lbl.setText(f"{_fmt(pos)} / {_fmt(self.player.duration())}")

    def _on_state(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_btn.setText("\u23F8" if playing else "\u25B6")

    def _load_bytes(self, name, raw, sender):
        if not self.player:
            return
        safe = re.sub(r"[^\w.\- ]", "_", name)[:80] or "audio"
        if self._tmp_path and os.path.exists(self._tmp_path):
            try:
                self.player.stop()
                self.player.setSource(QUrl())
                os.remove(self._tmp_path)
            except OSError:
                pass
        fd, path = tempfile.mkstemp(suffix="_" + safe, prefix="lanchat_media_")
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        self._tmp_path = path
        self.player.setSource(QUrl.fromLocalFile(path))
        self.name_lbl.setText(name + (("  \u2014 " + self._t("shared_by", name=sender)) if sender else ""))

    # ----- remote commands -----

    def on_remote(self, content, sender=""):
        if not self.player:
            return
        op = content.get("op")
        try:
            pos = int(content.get("pos", 0))
        except (TypeError, ValueError):
            pos = 0
        if op == "load":
            try:
                raw = base64.b64decode(content.get("data", ""))
            except Exception:
                return
            if 0 < len(raw) <= MAX_BYTES:
                self._load_bytes(str(content.get("name", "audio")), raw, sender)
        elif op == "play":
            self.player.setPosition(pos)
            self.player.play()
        elif op == "pause":
            self.player.pause()
            self.player.setPosition(pos)
        elif op == "seek":
            self.player.setPosition(pos)

    def closeEvent(self, event):
        if self.player:
            self.player.stop()
        super().closeEvent(event)
