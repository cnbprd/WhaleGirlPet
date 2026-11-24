# -*- coding: utf-8 -*-
"""对话气泡：独立顶层透明窗口，跟随桌宠、鼠标穿透。"""
import math

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class BubbleWindow(QWidget):
    def __init__(self, pet):
        super().__init__(None)
        self._pet = pet
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool
                            | Qt.WindowStaysOnTopHint
                            | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._text = ""
        self._max_w = 240
        self._below = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self._font = QFont("Microsoft YaHei", 10)
        self._font.setPixelSize(15)
        self.hide()

    def show_text(self, text: str, ms: int = 3000):
        self._text = text
        self._layout_bubble()
        self.show()
        self.update_position()
        self.raise_()
        self._timer.start(ms)

    def _layout_bubble(self):
        fm = QFontMetrics(self._font)
        lines = 0
        w = 0
        for seg in self._text.split("\n"):
            tw = fm.horizontalAdvance(seg)
            lines += max(1, math.ceil(tw / self._max_w))
            w = max(w, min(tw, self._max_w))
        text_w = w + 28
        text_h = lines * fm.height() + 22
        self.resize(text_w, text_h)

    def update_position(self):
        if not self.isVisible():
            return
        pet = self._pet
        pw, ph = pet.width(), pet.height()
        bw, bh = self.width(), self.height()
        scr = QGuiApplication.primaryScreen().availableGeometry()
        x = pet.x() + int(pw / 2) - int(bw / 2) + int(pw * 0.08)
        x = max(scr.left() + 4, min(x, scr.right() - bw - 4))
        above_y = pet.y() - bh - 6
        below_y = pet.y() + ph + 6
        if above_y >= scr.top():
            y, self._below = above_y, False
        elif below_y + bh <= scr.bottom():
            y, self._below = below_y, True
        else:
            y, self._below = above_y, False
        if y + bh > scr.bottom() and not self._below:
            if below_y + bh <= scr.bottom():
                y, self._below = below_y, True
        self.move(x, y)

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        rect = QRect(0, 8, w, h - 8) if self._below else QRect(0, 0, w, h - 8)
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        tail = QPainterPath()
        if self._below:
            tail.moveTo(w / 2 - 8, 8); tail.lineTo(w / 2, 0); tail.lineTo(w / 2 + 8, 8)
        else:
            tail.moveTo(w / 2 - 8, h - 8); tail.lineTo(w / 2, h); tail.lineTo(w / 2 + 8, h - 8)
        tail.closeSubpath()
        path = path.united(tail)
        p.setPen(QPen(QColor(210, 210, 215, 160), 1))
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawPath(path)
        p.setPen(QColor(40, 40, 45))
        p.setFont(self._font)
        p.drawText(rect.adjusted(14, 10, -14, -6), Qt.AlignCenter | Qt.TextWordWrap, self._text)
