# -*- coding: utf-8 -*-
"""启动画面「鲸鱼娘加载中」· v2.9.6 重做版

用户反馈（2026-11-25）：不要背景卡片、不要进度条，只要人物；要像 Windows 开机动画那样
有动感。于是改成：
  · 完全透明背景，画面里只有鲸鱼娘本人；
  · 三张动作帧轮播（站着 → 挥手 → 跳舞），每 1.6 秒换一次，切换带一次小跳；
  · 一直保持轻微呼吸浮动 + 左右小幅走动；
  · 脚下五个小点绕圈追逐（开机动画那种感觉），代替进度条；
  · 下方只留一行「鲸鱼娘加载中」+ 三个呼吸点，没有版本号、没有步骤文字。
"""
import math
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QApplication, QWidget

from paths import asset_path

W, H = 360, 500
ART_H = 370                 # 人物高度
FOOT_Y = 380                # 脚底线（v2.9.6 上移 22，给脚下点环和文字腾间距）
FRAME_SWITCH = 1.6          # 每张动作帧停留秒数
MIN_SHOW = 2.0              # 最短驻留，避免一闪而过

FRAMES = ["skins/default.png", "actions/wave.png", "actions/dance.png"]


class LoadingSplash(QWidget):
    """透明浮层：只有人物在动，没有卡片/进度条。"""

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(W, H)
        self.setWindowTitle("鲸鱼娘加载中")

        self._t0 = time.time()
        self._done = False
        self._fade = 1.0
        self._closing = False
        self._finish_at = 0.0
        self._step = ""
        self._frame_i = 0
        self._frame_t = 0.0

        self._pixs = []
        for rel in FRAMES:
            pm = QPixmap(asset_path(rel))
            if not pm.isNull():
                self._pixs.append(pm)
        if not self._pixs:
            self._pixs = [QPixmap(asset_path("ui/qwhale.png"))]

        self._tm = QTimer(self)
        self._tm.setInterval(28)
        self._tm.timeout.connect(self._tick)
        self._tm.start()
        self._center()

    # ---------------- 外部 ----------------
    def set_step(self, text: str):
        # 用户要求画面干净，步骤文字不再绘制；保留接口避免调用方报错
        self._step = text

    def finish(self):
        self._done = True
        self._finish_at = max(self._t0 + MIN_SHOW, time.time())

    # ---------------- 内部 ----------------
    def _center(self):
        scr = QApplication.primaryScreen().availableGeometry()
        self.move(scr.center().x() - W // 2, scr.center().y() - H // 2)

    def _tick(self):
        el = time.time() - self._t0
        if el - self._frame_t >= FRAME_SWITCH:
            self._frame_i = (self._frame_i + 1) % len(self._pixs)
            self._frame_t = el
        if self._done and time.time() >= self._finish_at:
            self._fade -= 0.07
            if self._fade <= 0.0 and not self._closing:
                self._closing = True
                self._tm.stop()
                self.close()
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setOpacity(max(0.0, min(1.0, self._fade)))
        el = time.time() - self._t0

        # ---- 人物：呼吸浮动 + 小幅走动 + 换帧小跳 ----
        bob = math.sin(el * 2.2) * 5.0
        sway = math.sin(el * 1.1) * 7.0
        since = el - self._frame_t
        hop = -7.0 * math.sin(max(0.0, min(1.0, since / 0.35)) * math.pi)

        pm = self._pixs[self._frame_i % len(self._pixs)]
        if not pm.isNull():
            scale = ART_H / float(pm.height() or 1)
            aw = int(pm.width() * scale)
            ah = ART_H
            ax = int(W / 2 - aw / 2 + sway)
            ay = int(FOOT_Y - ah + bob + hop)
            p.drawPixmap(ax, ay, aw, ah, pm)

        # ---- 脚下旋转点环（替代进度条，Windows 开机那种）----
        cx, cy, r = W / 2.0, FOOT_Y + 22.0, 26.0
        p.setPen(Qt.NoPen)
        for i in range(5):
            ang = el * 3.0 + i * (2 * math.pi / 5)
            x = cx + math.cos(ang) * r
            y = cy + math.sin(ang) * r * 0.42      # 压扁成椭圆，像地平线上的跑道
            a = int(60 + 170 * (1.0 - i / 5.0))
            p.setBrush(QColor(96, 156, 226, a))
            d = 7 - i * 0.6
            p.drawEllipse(QRectF(x - d / 2, y - d / 2, d, d))

        # ---- 文字（唯一保留的文案）----
        f = QFont("Microsoft YaHei", 12)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(34, 52, 77, 235))
        title = "鲸鱼娘加载中"
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(title)
        dots_w = 24
        tx = int((W - tw - dots_w) / 2)
        ty = FOOT_Y + 80
        p.drawText(tx, ty, title)
        for i in range(3):
            phase = (el * 2.4 - i * 0.45) % 1.6
            a = 90 + int(140 * max(0.0, 1.0 - abs(phase - 0.4) * 2.0))
            p.setBrush(QColor(70, 120, 200, a))
            p.drawEllipse(QRectF(tx + tw + 6 + i * 8, ty - 12, 5, 5))
        p.end()
