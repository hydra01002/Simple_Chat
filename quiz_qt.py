"""مسابقه سؤال و جواب - PyQt6   |   pip install PyQt6"""
import random
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

QUESTIONS = [
    ("پایتخت ایران کدام شهر است؟", "تهران", ["اصفهان", "شیراز", "تبریز"]),
    ("بزرگ‌ترین سیاره منظومه شمسی کدام است؟", "مشتری", ["زحل", "مریخ", "زمین"]),
    ("حاصل ۷ × ۸ چند است؟", "۵۶", ["۴۸", "۵۴", "۶۳"]),
    ("نام کدام زبان برنامه‌نویسی یادآور یک مار است؟", "پایتون", ["جاوا", "روبی", "سی"]),
    ("آب در سطح دریا در چند درجه سانتی‌گراد می‌جوشد؟", "۱۰۰", ["۹۰", "۸۰", "۱۲۰"]),
    ("سراینده شاهنامه کیست؟", "فردوسی", ["حافظ", "سعدی", "مولوی"]),
    ("زمین چند قاره دارد؟", "۷", ["۵", "۶", "۸"]),
    ("خروجی len('abc') در پایتون چیست؟", "۳", ["۲", "۴", "خطا"]),
    ("به کدام سیاره «سیاره سرخ» می‌گویند؟", "مریخ", ["زهره", "عطارد", "نپتون"]),
    ("بلندترین قله جهان کدام است؟", "اورست", ["دماوند", "کی‌۲", "مون‌بلان"]),
]


class Quiz(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مسابقه")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(480)
        self.setStyleSheet("QLabel#qtext { font-size: 16pt; font-weight: bold; } QLabel { font-size: 11pt; } QPushButton { font-size: 14pt; }")
        lay = QVBoxLayout(self)
        self.info = QLabel()
        self.info.setFont(QFont("Arial", 11))
        self.q = QLabel()
        self.q.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.q.setWordWrap(True)
        self.q.setObjectName("qtext")
        lay.addWidget(self.info)
        lay.addWidget(self.q)
        self.btns = []
        for i in range(4):
            b = QPushButton()
            b.setFont(QFont("Arial", 14))
            b.setMinimumHeight(44)
            b.clicked.connect(lambda _, i=i: self.answer(i))
            lay.addWidget(b)
            self.btns.append(b)
        self.next_btn = QPushButton("سؤال بعدی")
        self.next_btn.clicked.connect(self.next_q)
        lay.addWidget(self.next_btn)
        self.reset()

    def reset(self):
        self.order = random.sample(QUESTIONS, len(QUESTIONS))
        self.idx, self.score = -1, 0
        self.next_q()

    def next_q(self):
        self.idx += 1
        if self.idx >= len(self.order):
            self.q.setText(f"پایان! امتیاز شما: {self.score} از {len(self.order)}")
            self.info.setText("")
            for b in self.btns:
                b.hide()
            self.next_btn.setText("شروع دوباره")
            self.next_btn.clicked.disconnect()
            self.next_btn.clicked.connect(self.restart)
            return
        text, right, wrong = self.order[self.idx]
        opts = [right] + wrong
        random.shuffle(opts)
        self.right = right
        self.q.setText(text)
        self.info.setText(f"سؤال {self.idx + 1} از {len(self.order)}   |   امتیاز: {self.score}")
        for b, o in zip(self.btns, opts):
            b.setText(o)
            b.setEnabled(True)
            b.setStyleSheet("")
            b.show()
        self.next_btn.setEnabled(False)

    def restart(self):
        self.next_btn.clicked.disconnect()
        self.next_btn.clicked.connect(self.next_q)
        self.next_btn.setText("سؤال بعدی")
        self.reset()

    def answer(self, i):
        for b in self.btns:
            b.setEnabled(False)
            if b.text() == self.right:
                b.setStyleSheet("background:#3cb450;color:white;")
        if self.btns[i].text() == self.right:
            self.score += 1
        else:
            self.btns[i].setStyleSheet("background:#e64646;color:white;")
        self.next_btn.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Quiz()
    w.show()
    sys.exit(app.exec())
