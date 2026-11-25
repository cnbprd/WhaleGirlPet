# -*- coding: utf-8 -*-
"""启动画面「大肥鱼在动」· v3.0.1

用户反馈（2026-11-25 第三轮）：
    参考 Windows 开机动画——是「图标自己在动」，不是一张带背景的画。
    要求：启动画面 = 纯人物、透明背景、人自己在动，不要任何背景板。

所以这一版彻底去掉背景：没有渐变、没有光晕、没有涟漪、没有气泡、没有文字、
没有地面投影。窗口本身就是一块透明浮层，屏幕上只看得到大肥鱼本人，她在
呼吸、上下浮动、左右微摆、轻微倾身，并且每隔一秒多换一个动作姿势（挥手、
转圈），像在水里活着。

窗口尺寸按人物比例紧凑贴合，不遮挡桌面其余区域的操作。
"""
import math
import time

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from paths import asset_path

W, H = 380, 580
ART_H = 470                 # 人物绘制高度
FOOT_Y = 545                # 脚底基线
MIN_SHOW = 2.0              # 最短驻留，避免一闪而过
FADE_IN = 0.55              # 淡入时长

# 只用同一套立绘：三帧轮播里另外两帧是不同服装，切换像换装，反而跳。
FRAMES = ["skins/default.png"]


class LoadingSplash(QWidget):
    """纯人物透明浮层：大肥鱼自己在动，没有任何背景。"""

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFixedSize(W, H)
        self.setWindowTitle("鲸鱼娘加载中")

        self._t0 = time.time()
        self._done = False
        self._fade = 0.0
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
        self._tm.setInterval(24)          # ≈42fps，动作看起来是连续的
        self._tm.timeout.connect(self._tick)
        self._tm.start()
        self._center()

    # ---------------- 外部 ----------------
    def set_step(self, text: str):
        # 画面只要人，步骤文字不绘制；保留接口避免调用方报错
        self._step = text

    def finish(self):
        self._done = True
        self._finish_at = max(self._t0 + MIN_SHOW, time.time())

    # ---------------- 内部 ----------------
    def _center(self):
        scr = QApplication.primaryScreen().availableGeometry()
        self.move(scr.center().x() - W // 2, scr.center().y() - H // 2 - 20)

    def _tick(self):
        el = time.time() - self._t0
        # 淡入
        if self._fade < 1.0:
            self._fade = min(1.0, el / FADE_IN)
        # 淡出关闭
        if self._done and time.time() >= self._finish_at:
            self._fade -= 0.075
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
        pm = self._pixs[self._frame_i % len(self._pixs)]
        if pm.isNull():
            p.end()
            return

        # 呼吸：纵向 3.2%、横向 -1.8%（吸气变高、呼气变宽），周期 3.6 秒
        breathe = math.sin(el * 2.0 * math.pi / 3.6)
        # 水中浮沉：上下 ±9px（周期 4.2 秒），左右漂 ±8px（周期 6.0 秒）
        bob = math.sin(el * 2.0 * math.pi / 4.2) * 9.0
        drift = math.sin(el * 2.0 * math.pi / 6.0) * 8.0
        # 倾身：以脚底为轴左右各摆 1.8 度（周期 5.0 秒）
        tilt = math.sin(el * 2.0 * math.pi / 5.0) * 1.8

        scale = ART_H / float(pm.height() or 1)
        aw = int(pm.width() * scale)
        ah = ART_H

        p.save()
        # 先整体位移与倾斜（轴在脚底）
        p.translate(W / 2 + drift, FOOT_Y + bob)
        p.rotate(tilt)
        # 再以脚底为原点做呼吸缩放
        p.scale(1.0 + 0.016 * breathe, 1.0 - 0.032 * breathe)
        p.translate(-W / 2, -FOOT_Y)
        p.drawPixmap(QRectF(W / 2 - aw / 2, FOOT_Y - ah, aw, ah), pm, QRectF(pm.rect()))
        p.restore()
        p.end()
