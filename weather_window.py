"""Weather forecast window: search a city, see current conditions and a
5-day forecast. Uses the free, keyless Open-Meteo geocoding + forecast
APIs (needs an internet connection, separate from the LAN chat). The
last searched city is remembered in ~/.lan_chat_gui/tools.json."""

import json
import sys
import threading
import urllib.parse
import urllib.request
from datetime import datetime

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame,
)

from tools_common import TOOL_STYLE, load_json, save_json

REQUEST_TIMEOUT = 8

STR = {
    "title": {"fa": "آب‌وهوا", "en": "Weather"},
    "placeholder": {"fa": "نام شهر (مثلاً Tehran)", "en": "City name (e.g. London)"},
    "search": {"fa": "جستجو", "en": "Search"},
    "searching": {"fa": "در حال دریافت...", "en": "Loading..."},
    "hint": {"fa": "نام یک شهر رو بنویسید و جستجو بزنید.", "en": "Type a city name and press Search."},
    "not_found": {"fa": "شهری با این نام پیدا نشد.", "en": "No city found with that name."},
    "error": {"fa": "خطا در دریافت اطلاعات: {e}", "en": "Could not load weather: {e}"},
    "feels": {"fa": "احساس‌شده", "en": "Feels like"},
    "humidity": {"fa": "رطوبت", "en": "Humidity"},
    "wind": {"fa": "باد", "en": "Wind"},
    "forecast": {"fa": "پیش‌بینی ۵ روز آینده", "en": "5-day forecast"},
    "source": {"fa": "منبع: Open-Meteo", "en": "Source: Open-Meteo"},
    "today": {"fa": "امروز", "en": "Today"},
}

# WMO weather code -> (emoji, English, Persian)
WEATHER_CODES = {
    0: ("\u2600\ufe0f", "Clear sky", "آسمان صاف"),
    1: ("\U0001F324", "Mostly clear", "عمدتاً صاف"),
    2: ("\u26C5", "Partly cloudy", "نیمه‌ابری"),
    3: ("\u2601\ufe0f", "Overcast", "ابری"),
    45: ("\U0001F32B", "Fog", "مه"),
    48: ("\U0001F32B", "Freezing fog", "مه یخ‌زده"),
    51: ("\U0001F326", "Light drizzle", "نم‌نم باران"),
    53: ("\U0001F326", "Drizzle", "نم‌نم باران"),
    55: ("\U0001F326", "Heavy drizzle", "نم‌نم باران شدید"),
    56: ("\U0001F327", "Freezing drizzle", "نم‌نم یخ‌زده"),
    57: ("\U0001F327", "Freezing drizzle", "نم‌نم یخ‌زده"),
    61: ("\U0001F327", "Light rain", "باران ملایم"),
    63: ("\U0001F327", "Rain", "باران"),
    65: ("\U0001F327", "Heavy rain", "باران شدید"),
    66: ("\U0001F327", "Freezing rain", "باران یخ‌زده"),
    67: ("\U0001F327", "Freezing rain", "باران یخ‌زده"),
    71: ("\U0001F328", "Light snow", "برف ملایم"),
    73: ("\U0001F328", "Snow", "برف"),
    75: ("\u2744\ufe0f", "Heavy snow", "برف سنگین"),
    77: ("\U0001F328", "Snow grains", "دانه‌های برف"),
    80: ("\U0001F326", "Light showers", "رگبار ملایم"),
    81: ("\U0001F327", "Showers", "رگبار"),
    82: ("\u26C8", "Violent showers", "رگبار شدید"),
    85: ("\U0001F328", "Snow showers", "بارش برف"),
    86: ("\U0001F328", "Heavy snow showers", "بارش برف شدید"),
    95: ("\u26C8", "Thunderstorm", "رعد و برق"),
    96: ("\u26C8", "Thunderstorm with hail", "رعد و برق با تگرگ"),
    99: ("\u26C8", "Thunderstorm with heavy hail", "رعد و برق با تگرگ شدید"),
}

WEEKDAYS_FA = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
WEEKDAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def describe(code, lang):
    emoji, en, fa = WEATHER_CODES.get(code, ("\U0001F321", "Unknown", "نامشخص"))
    return emoji, (fa if lang == "fa" else en)


def _fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


class WeatherWorker(QObject):
    ready = pyqtSignal(dict)
    failed = pyqtSignal(int, str)  # request token, error text ("" = city not found)

    def __init__(self, token, city, lang):
        super().__init__()
        self.token = token
        self.city = city
        self.lang = lang

    def run(self):
        try:
            geo = _fetch_json(
                "https://geocoding-api.open-meteo.com/v1/search?name="
                + urllib.parse.quote(self.city) + "&count=1&format=json&language=" + self.lang
            )
            results = geo.get("results") or []
            if not results:
                self.failed.emit(self.token, "")
                return
            place = results[0]
            forecast = _fetch_json(
                "https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
                "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
                "&daily=weather_code,temperature_2m_max,temperature_2m_min"
                "&timezone=auto&forecast_days=5" % (place["latitude"], place["longitude"])
            )
            self.ready.emit({
                "token": self.token,
                "place": place.get("name", self.city),
                "country": place.get("country", ""),
                "current": forecast["current"],
                "daily": forecast["daily"],
            })
        except Exception as e:
            self.failed.emit(self.token, str(e) or "error")


class WeatherWindow(QMainWindow):
    def __init__(self, lang="en"):
        super().__init__()
        self.lang = lang if lang in ("fa", "en") else "en"
        self.setMinimumSize(520, 520)
        self.resize(560, 560)
        self._token = 0
        self._worker = None
        self._data = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 18, 20, 14)
        root.setSpacing(10)

        search_row = QHBoxLayout()
        self.city_edit = QLineEdit()
        self.city_edit.returnPressed.connect(self._search)
        search_row.addWidget(self.city_edit, stretch=1)
        self.search_btn = QPushButton("")
        self.search_btn.setObjectName("primary")
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.clicked.connect(self._search)
        search_row.addWidget(self.search_btn)
        root.addLayout(search_row)

        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("muted")
        self.status_lbl.setWordWrap(True)
        root.addWidget(self.status_lbl)

        self.current_card = QFrame()
        self.current_card.setObjectName("card")
        cc = QVBoxLayout(self.current_card)
        cc.setContentsMargins(18, 14, 18, 14)
        cc.setSpacing(4)
        self.place_lbl = QLabel("")
        self.place_lbl.setStyleSheet("font-size: 13pt; font-weight: 700;")
        cc.addWidget(self.place_lbl)
        big = QHBoxLayout()
        self.icon_lbl = QLabel("")
        self.icon_lbl.setStyleSheet("font-size: 44pt;")
        big.addWidget(self.icon_lbl)
        temp_col = QVBoxLayout()
        temp_col.setSpacing(0)
        self.temp_lbl = QLabel("")
        self.temp_lbl.setStyleSheet("font-size: 30pt; font-weight: 800; color: #55f7ff;")
        temp_col.addWidget(self.temp_lbl)
        self.desc_lbl = QLabel("")
        self.desc_lbl.setObjectName("muted")
        temp_col.addWidget(self.desc_lbl)
        big.addLayout(temp_col)
        big.addStretch(1)
        cc.addLayout(big)
        self.details_lbl = QLabel("")
        self.details_lbl.setObjectName("muted")
        self.details_lbl.setWordWrap(True)
        cc.addWidget(self.details_lbl)
        self.current_card.setVisible(False)
        root.addWidget(self.current_card)

        self.forecast_title = QLabel("")
        self.forecast_title.setObjectName("muted")
        self.forecast_title.setVisible(False)
        root.addWidget(self.forecast_title)
        self.forecast_row = QHBoxLayout()
        self.forecast_row.setSpacing(8)
        root.addLayout(self.forecast_row)

        root.addStretch(1)
        self.source_lbl = QLabel("")
        self.source_lbl.setObjectName("muted")
        root.addWidget(self.source_lbl)

        self.setStyleSheet(TOOL_STYLE)
        self._retranslate()

        saved = load_json("tools.json", {}).get("weather_city", "")
        if isinstance(saved, str) and saved:
            self.city_edit.setText(saved)
            self._search()

    def _t(self, key):
        return STR[key][self.lang]

    def _retranslate(self):
        self.setWindowTitle("\U0001F324 " + self._t("title"))
        self.city_edit.setPlaceholderText(self._t("placeholder"))
        self.search_btn.setText(self._t("search"))
        self.source_lbl.setText(self._t("source"))
        self.forecast_title.setText(self._t("forecast"))
        if self._data is not None:
            self._render(self._data)
        elif not self.status_lbl.text():
            self.status_lbl.setText(self._t("hint"))

    def set_language(self, lang):
        self.lang = lang if lang in ("fa", "en") else "en"
        self._retranslate()

    def _set_status(self, text, error=False):
        self.status_lbl.setObjectName("error" if error else "muted")
        self.status_lbl.style().unpolish(self.status_lbl)
        self.status_lbl.style().polish(self.status_lbl)
        self.status_lbl.setText(text)

    def _search(self):
        city = self.city_edit.text().strip()
        if not city:
            self._set_status(self._t("hint"))
            return
        self._token += 1
        self.search_btn.setEnabled(False)
        self._set_status(self._t("searching"))
        worker = WeatherWorker(self._token, city, self.lang)
        worker.ready.connect(self._on_ready)
        worker.failed.connect(self._on_failed)
        self._worker = worker  # keep alive while the thread runs
        threading.Thread(target=worker.run, daemon=True).start()

    def _on_failed(self, token, error):
        if token != self._token:
            return  # an older search finished late - ignore it
        self.search_btn.setEnabled(True)
        if error == "":
            self._set_status(self._t("not_found"), error=True)
        else:
            self._set_status(self._t("error").format(e=error), error=True)

    def _on_ready(self, data):
        if data.get("token") != self._token:
            return
        self.search_btn.setEnabled(True)
        self._data = data
        self._set_status("")
        settings = load_json("tools.json", {})
        if not isinstance(settings, dict):
            settings = {}
        settings["weather_city"] = self.city_edit.text().strip()
        save_json("tools.json", settings)
        self._render(data)

    def _render(self, data):
        cur, daily = data["current"], data["daily"]
        emoji, desc = describe(cur.get("weather_code"), self.lang)
        place = data["place"] + (f", {data['country']}" if data.get("country") else "")
        self.place_lbl.setText(place)
        self.icon_lbl.setText(emoji)
        self.temp_lbl.setText(f"{cur['temperature_2m']:.0f}°C")
        self.desc_lbl.setText(desc)
        self.details_lbl.setText(
            f"{self._t('feels')}: {cur['apparent_temperature']:.0f}°C   •   "
            f"{self._t('humidity')}: {cur['relative_humidity_2m']:.0f}%   •   "
            f"{self._t('wind')}: {cur['wind_speed_10m']:.0f} km/h"
        )
        self.current_card.setVisible(True)
        self.forecast_title.setVisible(True)

        while self.forecast_row.count():
            item = self.forecast_row.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for i, day in enumerate(daily["time"]):
            card = QFrame()
            card.setObjectName("card")
            lay = QVBoxLayout(card)
            lay.setContentsMargins(6, 10, 6, 10)
            lay.setSpacing(2)
            try:
                wd = datetime.strptime(day, "%Y-%m-%d").weekday()
                name = (WEEKDAYS_FA if self.lang == "fa" else WEEKDAYS_EN)[wd]
            except ValueError:
                name = day
            if i == 0:
                name = self._t("today")
            for text, style in (
                (name, "font-size: 9pt; color: #8798b6;"),
                (describe(daily["weather_code"][i], self.lang)[0], "font-size: 20pt;"),
                (f"{daily['temperature_2m_max'][i]:.0f}°", "font-weight: 700;"),
                (f"{daily['temperature_2m_min'][i]:.0f}°", "color: #8798b6;"),
            ):
                lbl = QLabel(text)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet(style)
                lay.addWidget(lbl)
            self.forecast_row.addWidget(card)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = WeatherWindow()
    win.show()
    sys.exit(app.exec())
