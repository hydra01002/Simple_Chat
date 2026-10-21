"""Wake-on-LAN: send a "magic packet" to switch on a computer on the local
network (the target needs WoL enabled in its BIOS / network adapter).
Saved devices live in ~/.lan_chat_gui/tools.json."""

import re
import socket
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
)

from tools_common import TOOL_STYLE, load_json, save_json

STR = {
    "title": {"fa": "بیدارکردن از راه دور (Wake-on-LAN)", "en": "Wake-on-LAN"},
    "name": {"fa": "نام دستگاه", "en": "Device name"},
    "mac": {"fa": "آدرس MAC (مثلاً AA:BB:CC:DD:EE:FF)", "en": "MAC address (e.g. AA:BB:CC:DD:EE:FF)"},
    "save": {"fa": "ذخیره", "en": "Save"},
    "wake": {"fa": "بیدار کن", "en": "Wake up"},
    "remove": {"fa": "حذف", "en": "Remove"},
    "bad_mac": {"fa": "آدرس MAC معتبر نیست (۱۲ رقم هگزا).", "en": "That isn't a valid MAC (12 hex digits)."},
    "sent": {"fa": "بسته‌ی بیدارباش برای {name} فرستاده شد.", "en": "Magic packet sent to {name}."},
    "fail": {"fa": "ارسال نشد: {e}", "en": "Could not send: {e}"},
    "hint": {"fa": "دستگاه باید در همین شبکه و WoL روش فعال باشه.", "en": "The device must be on this network with WoL enabled."},
}


def parse_mac(text):
    digits = re.sub(r"[^0-9a-fA-F]", "", text or "")
    if len(digits) != 12:
        return None
    return bytes.fromhex(digits)


def send_magic_packet(mac_bytes):
    packet = b"\xff" * 6 + mac_bytes * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for port in (9, 7):
            sock.sendto(packet, ("255.255.255.255", port))


class WakeOnLanWindow(QMainWindow):
    def __init__(self, lang="en"):
        super().__init__()
        self.lang = lang if lang in ("fa", "en") else "en"
        self.setMinimumSize(440, 420)
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(8)

        self.name_edit = QLineEdit()
        root.addWidget(self.name_edit)
        self.mac_edit = QLineEdit()
        root.addWidget(self.mac_edit)
        self.save_btn = QPushButton("")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self._save)
        root.addWidget(self.save_btn)

        self.list = QListWidget()
        root.addWidget(self.list, stretch=1)
        row = QHBoxLayout()
        self.wake_btn = QPushButton("")
        self.wake_btn.setObjectName("primary")
        self.wake_btn.clicked.connect(self._wake)
        row.addWidget(self.wake_btn)
        self.remove_btn = QPushButton("")
        self.remove_btn.setObjectName("danger")
        self.remove_btn.clicked.connect(self._remove)
        row.addWidget(self.remove_btn)
        root.addLayout(row)

        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("muted")
        self.status_lbl.setWordWrap(True)
        root.addWidget(self.status_lbl)

        self.setStyleSheet(TOOL_STYLE)
        data = load_json("tools.json", {})
        self.devices = list(data.get("wol_devices", [])) if isinstance(data, dict) else []
        self._retranslate()
        self._fill()

    def _t(self, key, **kw):
        return STR[key][self.lang].format(**kw)

    def _retranslate(self):
        self.setWindowTitle("\u23FB " + self._t("title"))
        self.name_edit.setPlaceholderText(self._t("name"))
        self.mac_edit.setPlaceholderText(self._t("mac"))
        self.save_btn.setText(self._t("save"))
        self.wake_btn.setText(self._t("wake"))
        self.remove_btn.setText(self._t("remove"))
        if not self.status_lbl.text():
            self.status_lbl.setText(self._t("hint"))

    def set_language(self, lang):
        self.lang = lang if lang in ("fa", "en") else "en"
        self._retranslate()

    def _persist(self):
        data = load_json("tools.json", {})
        if not isinstance(data, dict):
            data = {}
        data["wol_devices"] = self.devices
        save_json("tools.json", data)

    def _fill(self):
        self.list.clear()
        for d in self.devices:
            item = QListWidgetItem(f"{d['name']}   ({d['mac']})")
            self.list.addItem(item)

    def _save(self):
        mac = parse_mac(self.mac_edit.text())
        if mac is None:
            self.status_lbl.setStyleSheet("color: #ff6b6b;")
            self.status_lbl.setText(self._t("bad_mac"))
            return
        pretty = ":".join(f"{b:02X}" for b in mac)
        name = self.name_edit.text().strip() or pretty
        self.devices.append({"name": name, "mac": pretty})
        self._persist()
        self.name_edit.clear()
        self.mac_edit.clear()
        self.status_lbl.setStyleSheet("")
        self.status_lbl.setText(self._t("hint"))
        self._fill()

    def _wake(self):
        row = self.list.currentRow()
        if row < 0:
            return
        dev = self.devices[row]
        try:
            send_magic_packet(parse_mac(dev["mac"]))
            self.status_lbl.setStyleSheet("")
            self.status_lbl.setText(self._t("sent", name=dev["name"]))
        except OSError as e:
            self.status_lbl.setStyleSheet("color: #ff6b6b;")
            self.status_lbl.setText(self._t("fail", e=e))

    def _remove(self):
        row = self.list.currentRow()
        if row >= 0:
            self.devices.pop(row)
            self._persist()
            self._fill()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = WakeOnLanWindow()
    win.show()
    sys.exit(app.exec())
