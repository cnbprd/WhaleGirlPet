# -*- coding: utf-8 -*-
"""启动画面「鲸鱼娘加载中」（v2.9.5）

背景：以前启动时桌宠窗口一构造就 show()，接着各组件陆续初始化、6 秒后还可能弹
「发现新版本」对话框，用户看到的是"一闪一闪 + 一堆弹窗"。

这里把启动过程收成一屏：
  main() 先 show 本窗口 → Controller 在后台初始化（期间只改这里的一行小字）→
  初始化完调 controller.show_pet() 一次性露出桌宠 → 本窗口淡出。

窗口本身是无边框透明浮层，画一张圆角卡片：上面鲸鱼娘立绘轻微上下浮动，
中间「鲸鱼娘加载中」+ 三个呼吸的点，下面一行步骤文字和细进度条。
"""
import math
import time

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import (QColor, QFont, QLinearGradient, QPainter, QPainterPath,
                           QPen, QPixmap)
from PySide6.QtWidgets import QApplication, QWidget

from paths import APP_VERSION, asset_path

W, H = 460, 322
CARD = QRectF(8, 8, W - 16, H - 16)
ART_H = 186          # 立绘高度
TXT_TOP = 214        # 文案基线区域起点
BAR_W = 300
MIN_SHOW = 2.0       # 最短驻留（秒）：初始化再快也要让「加载中」看完一轮，避免一闪而过


class LoadingSplash(QWidget):
    """无边框加载浮层：立绘浮动 + 呼吸点 + 假进度条。"""

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(W, H)
        self.setWindowTitle("鲸鱼娘加载中")

        self._t0 = time.time()
        self._step = "正在叫醒鲸鱼娘…"
        self._progress = 0.02
        self._target = 0.02
        self._done = False
        self._fade = 1.0
        self._closing = False
        self._finish_at = 0.0
        self._art = QPixmap(asset_path("skins/default.png"))
        if self._art.isNull():
            self._art = QPixmap(asset_path("ui/qwhale.png"))
        self._font_ok = True

        self._tm = QTimer(self)
        self._tm.setInterval(28)
        self._tm.timeout.connect(self._tick)
        self._tm.start()
        self._center()

    # ---------------- 外部调用 ----------------
    def set_step(self, text: str):
        """改底部的步骤文字（构造过程中分阶段调用）。"""
        self._step = text
        self.update()

    def finish(self):
        """初始化完毕：进度补满 → 至少看满 MIN_SHOW 秒 → 淡出关闭。"""
        self._done = True
        self._target = 1.0
        self._finish_at = max(self._t0 + MIN_SHOW, time.time())

    # ---------------- 内部 ----------------
    def _center(self):
        scr = QApplication.primaryScreen().availableGeometry()
        self.move(scr.center().x() - W // 2, scr.center().y() - H // 2)

    def _tick(self):
        el = max(0.0, time.time() - self._t0)
        self._progress += (self._target - self._progress) * 0.10
        if not self._done:
            # 前 1.2 秒动画先行，之后按时间缓慢爬升，最多到 0.94（完成后由 finish 补齐）
            self._target = min(0.94, 0.02 + el / 3.2)
        elif time.time() >= self._finish_at:
            # 到最短驻留时间后才开始淡出，避免"闪一下就没"
            self._fade -= 0.07
            if self._fade <= 0.0 and not self._closing:
                self._closing = True
                self._tm.stop()
                self.close()
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setOpacity(max(0.0, min(1.0, self._fade)))
        el = max(0.0, time.time() - self._t0)

        # ---- 卡片 ----
        card = QPainterPath()
        card.addRoundedRect(CARD, 18, 18)
        grad = QLinearGradient(CARD.topLeft(), CARD.bottomLeft())
        grad.setColorAt(0.0, QColor(250, 253, 255))
        grad.setColorAt(1.0, QColor(232, 241, 251))
        p.fillPath(card, grad)
        p.setPen(QPen(QColor(176, 205, 235), 1.2))
        p.drawPath(card)

        # ---- 立绘（轻微上下浮动）----
        bob = math.sin(el * 2.0) * 4.0
        if not self._art.isNull():
            src_w, src_h = self._art.width(), self._art.height()
            scale = ART_H / float(src_h or 1)
            aw = int(src_w * scale)
            ah = ART_H
            ax = int((W - aw) / 2)
            ay = int(26 + bob + (ART_H - ah))
            p.drawPixmap(ax, ay, aw, ah, self._art)

        # ---- 标题：鲸鱼娘加载中 + 呼吸三点 ----
        f = QFont("Microsoft YaHei", 15)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(34, 52, 77))
        title = "鲸鱼娘加载中"
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(title)
        dots_w = 26
        tx = int((W - tw - dots_w) / 2)
        p.drawText(tx, TXT_TOP + 18, title)
        for i in range(3):
            phase = (el * 2.4 - i * 0.45) % 1.6
            a = 90 + int(140 * max(0.0, 1.0 - abs(phase - 0.4) * 2.0))
            p.setBrush(QColor(70, 120, 200, a))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(tx + tw + 6 + i * 8, TXT_TOP + 12, 5, 5))

        # ---- 步骤文字 ----
        f2 = QFont("Microsoft YaHei", 9)
        p.setFont(f2)
        p.setPen(QColor(96, 118, 142))
        fm2 = p.fontMetrics()
        sw = fm2.horizontalAdvance(self._step)
        p.drawText(int((W - sw) / 2), TXT_TOP + 44, self._step)

        # ---- 细进度条 ----
        bar_x = (W - BAR_W) / 2
        bar_y = TXT_TOP + 58
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(203, 218, 235))
        p.drawRoundedRect(QRectF(bar_x, bar_y, BAR_W, 5), 2.5, 2.5)
        w = max(6.0, BAR_W * max(0.0, min(1.0, self._progress)))
        g2 = QLinearGradient(bar_x, 0, bar_x + w, 0)
        g2.setColorAt(0.0, QColor(96, 156, 226))
        g2.setColorAt(1.0, QColor(140, 196, 246))
        p.setBrush(g2)
        p.drawRoundedRect(QRectF(bar_x, bar_y, w, 5), 2.5, 2.5)

        # ---- 版本号（右下角，小字）----
        f3 = QFont("Microsoft YaHei", 8)
        p.setFont(f3)
        p.setPen(QColor(150, 168, 188))
        p.drawText(int(CARD.right() - 8 - p.fontMetrics().horizontalAdvance("v" + APP_VERSION)),
                   int(CARD.bottom() - 8), "v" + APP_VERSION)
        p.end()
