"""Voice-message helpers: record from the default microphone into WAV bytes
and play WAV bytes back. Uses PyQt6.QtMultimedia, which ships with the
normal `pip install PyQt6` wheels; if it (or a microphone) is missing,
AVAILABLE is False / start() returns an error string instead of crashing."""

import io
import os
import tempfile
import time
import wave

from PyQt6.QtCore import QObject, QUrl, pyqtSignal

try:
    from PyQt6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices, QSoundEffect
    AVAILABLE = True
except Exception:  # pragma: no cover - depends on the user's install
    AVAILABLE = False

MAX_SECONDS = 300


class VoiceRecorder(QObject):
    """start() -> None on success or an error string. stop() -> (wav_bytes, seconds)."""

    tick = pyqtSignal(float)  # seconds recorded so far

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source = None
        self._io = None
        self._buf = bytearray()
        self._fmt_info = None
        self._started = 0.0

    def start(self):
        if not AVAILABLE:
            return "QtMultimedia is not available"
        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            return "No microphone found"
        fmt = QAudioFormat()
        fmt.setSampleRate(16000)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(fmt):
            fmt = device.preferredFormat()
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            if not device.isFormatSupported(fmt):
                return "The microphone doesn't support 16-bit audio"
        self._fmt_info = (fmt.channelCount(), fmt.sampleRate())
        self._buf = bytearray()
        self._source = QAudioSource(device, fmt)
        self._io = self._source.start()
        if self._io is None:
            return "Could not start recording"
        self._io.readyRead.connect(self._on_ready)
        self._started = time.time()
        return None

    def _on_ready(self):
        if self._io is None:
            return
        self._buf += bytes(self._io.readAll())
        elapsed = time.time() - self._started
        self.tick.emit(elapsed)

    def seconds(self):
        return time.time() - self._started if self._source is not None else 0.0

    def stop(self):
        if self._source is None:
            return b"", 0.0
        try:
            self._on_ready()
            self._source.stop()
        except Exception:
            pass
        channels, rate = self._fmt_info
        pcm = bytes(self._buf)
        self._source = None
        self._io = None
        out = io.BytesIO()
        with wave.open(out, "wb") as w:
            w.setnchannels(channels)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm)
        seconds = len(pcm) / float(max(1, channels * 2 * rate))
        return out.getvalue(), seconds


_player = {"effect": None, "path": None}


def stop_playback():
    eff = _player.get("effect")
    if eff is not None:
        try:
            eff.stop()
        except Exception:
            pass


def play_wav_bytes(data):
    """Play WAV bytes (stops whatever voice message was playing). Returns
    False if playback isn't possible."""
    if not AVAILABLE or not data:
        return False
    stop_playback()
    try:
        old = _player.get("path")
        if old and os.path.exists(old):
            os.remove(old)
    except OSError:
        pass
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="lanchat_voice_")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    eff = QSoundEffect()
    eff.setSource(QUrl.fromLocalFile(path))
    eff.setVolume(1.0)
    eff.play()
    _player["effect"] = eff
    _player["path"] = path
    return True


_sound_cache = {}


def play_sound_file(path):
    """Play a WAV file (a per-chat notification sound). Returns False when
    there's nothing to play or playback isn't possible, so the caller can
    fall back to the normal system beep."""
    if not AVAILABLE or not path or not os.path.isfile(path):
        return False
    try:
        eff = _sound_cache.get(path)
        if eff is None:
            eff = QSoundEffect()
            eff.setSource(QUrl.fromLocalFile(path))
            eff.setVolume(0.8)
            _sound_cache[path] = eff
        eff.play()
        return True
    except Exception:
        return False


# ---------- push-to-talk (live voice, experimental) ----------

PTT_RATE = 16000
PTT_CHUNK_BYTES = 3200   # 100 ms of 16 kHz mono 16-bit audio


class PttStreamer(QObject):
    """While running, emits chunk(bytes) with ~100 ms of raw PCM each."""
    chunk = pyqtSignal(bytes)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source = None
        self._io = None
        self._buf = bytearray()

    def start(self):
        if not AVAILABLE:
            return "QtMultimedia is not available"
        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            return "No microphone found"
        fmt = QAudioFormat()
        fmt.setSampleRate(PTT_RATE)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(fmt):
            return "The microphone doesn't support 16 kHz mono audio"
        self._source = QAudioSource(device, fmt)
        self._io = self._source.start()
        if self._io is None:
            return "Could not start the microphone"
        self._io.readyRead.connect(self._on_ready)
        return None

    def _on_ready(self):
        if self._io is None:
            return
        self._buf += bytes(self._io.readAll())
        while len(self._buf) >= PTT_CHUNK_BYTES:
            self.chunk.emit(bytes(self._buf[:PTT_CHUNK_BYTES]))
            del self._buf[:PTT_CHUNK_BYTES]

    def stop(self):
        if self._source is None:
            return
        try:
            self._on_ready()
            if len(self._buf) >= 2:
                self.chunk.emit(bytes(self._buf[: len(self._buf) - len(self._buf) % 2]))
            self._source.stop()
        except Exception:
            pass
        self._source = None
        self._io = None
        self._buf = bytearray()


_ptt_sinks = {}


def ptt_play(sender, pcm):
    """Play a received PTT chunk from `sender` (one output stream per sender)."""
    if not AVAILABLE or not pcm:
        return
    try:
        from PyQt6.QtMultimedia import QAudioSink
        entry = _ptt_sinks.get(sender)
        if entry is None:
            device = QMediaDevices.defaultAudioOutput()
            fmt = QAudioFormat()
            fmt.setSampleRate(PTT_RATE)
            fmt.setChannelCount(1)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            sink = QAudioSink(device, fmt)
            io_dev = sink.start()
            entry = (sink, io_dev)
            _ptt_sinks[sender] = entry
        entry[1].write(pcm[: len(pcm) - len(pcm) % 2])
    except Exception:
        pass
