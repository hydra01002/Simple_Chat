"""A small unit converter (length, weight, temperature, volume, area,
speed, time, data size). Fully offline."""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QFrame,
)

from tools_common import TOOL_STYLE, normalize_number_text

STR = {
    "title": {"fa": "مبدل واحد", "en": "Unit converter"},
    "category": {"fa": "دسته", "en": "Category"},
    "value": {"fa": "مقدار", "en": "Value"},
    "from": {"fa": "از", "en": "From"},
    "to": {"fa": "به", "en": "To"},
    "all_units": {"fa": "همه‌ی واحدها", "en": "All units"},
    "invalid": {"fa": "یه عدد معتبر وارد کنید", "en": "Enter a valid number"},
}

# category -> (fa name, en name, [(symbol, en name, fa name, factor to the base unit)])
CATEGORIES = {
    "length": ("طول", "Length", [
        ("mm", "Millimeter", "میلی‌متر", 0.001), ("cm", "Centimeter", "سانتی‌متر", 0.01),
        ("m", "Meter", "متر", 1.0), ("km", "Kilometer", "کیلومتر", 1000.0),
        ("in", "Inch", "اینچ", 0.0254), ("ft", "Foot", "فوت", 0.3048),
        ("yd", "Yard", "یارد", 0.9144), ("mi", "Mile", "مایل", 1609.344),
    ]),
    "weight": ("وزن", "Weight", [
        ("mg", "Milligram", "میلی‌گرم", 1e-6), ("g", "Gram", "گرم", 0.001),
        ("kg", "Kilogram", "کیلوگرم", 1.0), ("t", "Tonne", "تن", 1000.0),
        ("oz", "Ounce", "اونس", 0.028349523125), ("lb", "Pound", "پوند", 0.45359237),
    ]),
    "temperature": ("دما", "Temperature", [
        ("°C", "Celsius", "سانتی‌گراد", None), ("°F", "Fahrenheit", "فارنهایت", None),
        ("K", "Kelvin", "کلوین", None),
    ]),
    "volume": ("حجم", "Volume", [
        ("mL", "Milliliter", "میلی‌لیتر", 0.001), ("L", "Liter", "لیتر", 1.0),
        ("m³", "Cubic meter", "متر مکعب", 1000.0),
        ("tsp", "Teaspoon (US)", "قاشق چای‌خوری", 0.00492892159375),
        ("tbsp", "Tablespoon (US)", "قاشق غذاخوری", 0.01478676478125),
        ("fl oz", "Fluid ounce (US)", "اونس مایع", 0.0295735295625),
        ("cup", "Cup (US)", "فنجان", 0.2365882365),
        ("gal", "Gallon (US)", "گالن", 3.785411784),
    ]),
    "area": ("مساحت", "Area", [
        ("cm²", "Square centimeter", "سانتی‌متر مربع", 1e-4), ("m²", "Square meter", "متر مربع", 1.0),
        ("ha", "Hectare", "هکتار", 10000.0), ("km²", "Square kilometer", "کیلومتر مربع", 1e6),
        ("ft²", "Square foot", "فوت مربع", 0.09290304), ("acre", "Acre", "اکر", 4046.8564224),
        ("mi²", "Square mile", "مایل مربع", 2589988.110336),
    ]),
    "speed": ("سرعت", "Speed", [
        ("m/s", "Meter/second", "متر بر ثانیه", 1.0), ("km/h", "Kilometer/hour", "کیلومتر بر ساعت", 1 / 3.6),
        ("mph", "Mile/hour", "مایل بر ساعت", 0.44704), ("kn", "Knot", "گره دریایی", 1852 / 3600),
    ]),
    "time": ("زمان", "Time", [
        ("s", "Second", "ثانیه", 1.0), ("min", "Minute", "دقیقه", 60.0), ("h", "Hour", "ساعت", 3600.0),
        ("day", "Day", "روز", 86400.0), ("week", "Week", "هفته", 604800.0),
    ]),
    "data": ("حجم داده", "Data size", [
        ("B", "Byte", "بایت", 1.0), ("KB", "Kilobyte", "کیلوبایت", 1024.0),
        ("MB", "Megabyte", "مگابایت", 1024.0 ** 2), ("GB", "Gigabyte", "گیگابایت", 1024.0 ** 3),
        ("TB", "Terabyte", "ترابایت", 1024.0 ** 4),
    ]),
}


def _to_celsius(value, sym):
    if sym == "°F":
        return (value - 32) * 5 / 9
    if sym == "K":
        return value - 273.15
    return value


def _from_celsius(c, sym):
    if sym == "°F":
        return c * 9 / 5 + 32
    if sym == "K":
        return c + 273.15
    return c


def convert(category, value, from_sym, to_sym):
    units = {u[0]: u for u in CATEGORIES[category][2]}
    if category == "temperature":
        return _from_celsius(_to_celsius(value, from_sym), to_sym)
    return value * units[from_sym][3] / units[to_sym][3]


def fmt(value):
    if value == 0:
        return "0"
    if abs(value) >= 1e12 or abs(value) < 1e-6:
        return f"{value:.6e}"
    return f"{value:,.8g}" if abs(value) < 1e6 else f"{value:,.4f}".rstrip("0").rstrip(".")


class UnitConverterWindow(QMainWindow):
    def __init__(self, lang="en"):
        super().__init__()
        self.lang = lang if lang in ("fa", "en") else "en"
        self.setMinimumSize(420, 480)
        self.resize(460, 540)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(8)

        self.category_lbl = QLabel("")
        self.category_lbl.setObjectName("muted")
        root.addWidget(self.category_lbl)
        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        root.addWidget(self.category_combo)

        self.value_lbl = QLabel("")
        self.value_lbl.setObjectName("muted")
        root.addWidget(self.value_lbl)
        self.value_edit = QLineEdit("1")
        self.value_edit.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.value_edit.setStyleSheet("font-size: 15pt;")
        self.value_edit.textChanged.connect(self._recalculate)
        root.addWidget(self.value_edit)

        row = QHBoxLayout()
        row.setSpacing(8)
        col_from = QVBoxLayout()
        self.from_lbl = QLabel("")
        self.from_lbl.setObjectName("muted")
        col_from.addWidget(self.from_lbl)
        self.from_combo = QComboBox()
        self.from_combo.currentIndexChanged.connect(self._recalculate)
        col_from.addWidget(self.from_combo)
        row.addLayout(col_from, stretch=1)

        self.swap_btn = QPushButton("\u21C4")
        self.swap_btn.setFixedWidth(46)
        self.swap_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.swap_btn.clicked.connect(self._swap)
        row.addWidget(self.swap_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        col_to = QVBoxLayout()
        self.to_lbl = QLabel("")
        self.to_lbl.setObjectName("muted")
        col_to.addWidget(self.to_lbl)
        self.to_combo = QComboBox()
        self.to_combo.currentIndexChanged.connect(self._recalculate)
        col_to.addWidget(self.to_combo)
        row.addLayout(col_to, stretch=1)
        root.addLayout(row)

        self.result_lbl = QLabel("")
        self.result_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_lbl.setStyleSheet("font-size: 20pt; font-weight: 800; color: #55f7ff; padding: 12px 0;")
        self.result_lbl.setWordWrap(True)
        root.addWidget(self.result_lbl)

        self.all_title_lbl = QLabel("")
        self.all_title_lbl.setObjectName("muted")
        root.addWidget(self.all_title_lbl)
        card = QFrame()
        card.setObjectName("card")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(14, 10, 14, 10)
        self.all_lbl = QLabel("")
        self.all_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.all_lbl.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        card_lay.addWidget(self.all_lbl)
        root.addWidget(card)
        root.addStretch(1)

        self.setStyleSheet(TOOL_STYLE)
        self._populate_categories()
        self._retranslate()

    def _t(self, key):
        return STR[key][self.lang]

    def _unit_label(self, unit):
        sym, en, fa, _ = unit
        return f"{fa if self.lang == 'fa' else en} ({sym})"

    def _populate_categories(self):
        self.category_combo.blockSignals(True)
        current = self.category_combo.currentData()
        self.category_combo.clear()
        for key, (fa, en, _units) in CATEGORIES.items():
            self.category_combo.addItem(fa if self.lang == "fa" else en, key)
        idx = max(0, self.category_combo.findData(current)) if current else 0
        self.category_combo.setCurrentIndex(idx)
        self.category_combo.blockSignals(False)
        self._populate_units(keep_selection=False)

    def _populate_units(self, keep_selection=True):
        key = self.category_combo.currentData()
        units = CATEGORIES[key][2]
        prev_from, prev_to = self.from_combo.currentData(), self.to_combo.currentData()
        for combo in (self.from_combo, self.to_combo):
            combo.blockSignals(True)
            combo.clear()
            for u in units:
                combo.addItem(self._unit_label(u), u[0])
        f_idx = self.from_combo.findData(prev_from) if keep_selection else -1
        t_idx = self.to_combo.findData(prev_to) if keep_selection else -1
        self.from_combo.setCurrentIndex(f_idx if f_idx >= 0 else 0)
        self.to_combo.setCurrentIndex(t_idx if t_idx >= 0 else (1 if len(units) > 1 else 0))
        self.from_combo.blockSignals(False)
        self.to_combo.blockSignals(False)
        self._recalculate()

    def _retranslate(self):
        self.setWindowTitle("\U0001F4D0 " + self._t("title"))
        self.category_lbl.setText(self._t("category"))
        self.value_lbl.setText(self._t("value"))
        self.from_lbl.setText(self._t("from"))
        self.to_lbl.setText(self._t("to"))
        self.all_title_lbl.setText(self._t("all_units"))

    def set_language(self, lang):
        self.lang = lang if lang in ("fa", "en") else "en"
        self._retranslate()
        self._populate_categories()

    def _on_category_changed(self):
        self._populate_units(keep_selection=False)

    def _swap(self):
        f, t = self.from_combo.currentIndex(), self.to_combo.currentIndex()
        self.from_combo.blockSignals(True)
        self.to_combo.blockSignals(True)
        self.from_combo.setCurrentIndex(t)
        self.to_combo.setCurrentIndex(f)
        self.from_combo.blockSignals(False)
        self.to_combo.blockSignals(False)
        self._recalculate()

    def _recalculate(self):
        key = self.category_combo.currentData()
        if key is None:
            return
        try:
            value = float(normalize_number_text(self.value_edit.text()))
        except ValueError:
            self.result_lbl.setStyleSheet("font-size: 11pt; color: #ff6b6b; padding: 12px 0;")
            self.result_lbl.setText(self._t("invalid"))
            self.all_lbl.setText("")
            return
        from_sym, to_sym = self.from_combo.currentData(), self.to_combo.currentData()
        if from_sym is None or to_sym is None:
            return
        self.result_lbl.setStyleSheet("font-size: 20pt; font-weight: 800; color: #55f7ff; padding: 12px 0;")
        self.result_lbl.setText(f"{fmt(convert(key, value, from_sym, to_sym))} {to_sym}")
        lines = []
        for u in CATEGORIES[key][2]:
            lines.append(
                f"<span style='color:#8798b6'>{self._unit_label(u)}</span>"
                f" &nbsp; <b>{fmt(convert(key, value, from_sym, u[0]))}</b>"
            )
        self.all_lbl.setText("<br>".join(lines))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = UnitConverterWindow()
    win.show()
    sys.exit(app.exec())
