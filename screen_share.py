"""Simple screen sharing: a sender that grabs the primary screen about
once a second as a small JPEG, and a window that shows the latest frame."""

from PyQt6.QtCore import Qt, QTimer, QObject, QBuffer, QByteArray, QIODevice, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QPixmap
from PyQt6.QtWidgets import QMainWindow, QLabel

from tools_common import TOOL_STYLE


class ScreenSharer(QObject):
    frame = pyqtSignal(bytes)

    def __init__(self, parent=None, interval_ms=1000, width=960, quality=45):
        super().__init__(parent)
        self.width_px = width
        self.quality = quality
        self.timer = QTimer(self)
        self.timer.setInterval(interval_ms)
        self.timer.timeout.connect(self._grab)

    def start(self):
        self.timer.start()
        self._grab()

    def stop(self):
        self.timer.stop()

    def _grab(self):
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        pm = screen.grabWindow(0)
        if pm.isNull():
            return
        if pm.width() > self.width_px:
            pm = pm.scaledToWidth(self.width_px, Qt.TransformationMode.SmoothTransformation)
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pm.save(buf, "JPEG", self.quality)
        self.frame.emit(bytes(ba))


class ScreenViewerWindow(QMainWindow):
    def __init__(self, title):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(900, 560)
        self._pixmap = None
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self.label)
        self.setStyleSheet(TOOL_STYLE)

    def set_frame(self, jpeg_bytes):
        pm = QPixmap()
        if pm.loadFromData(jpeg_bytes):
            self._pixmap = pm
            self._rescale()

    def set_message(self, text):
        self._pixmap = None
        self.label.setPixmap(QPixmap())
        self.label.setText(text)

    def _rescale(self):
        if self._pixmap is not None:
            self.label.setPixmap(self._pixmap.scaled(
                self.label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()
