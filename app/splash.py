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
MAX_LIFE_MS = 15000         # v3.0.6：兜底存活上限，超过就无条件收掉

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
        self._tm.setTimerType(Qt.PreciseTimer)   # v3.0.22：默认 CoarseTimer 会被拉到 31ms，实测 32fps
        self._tm.setInterval(24)          # ≈42fps，动作看起来是连续的
        self._tm.timeout.connect(self._tick)
        self._tm.start()
        self._center()
        # v3.0.6：不管调用方有没有按时 finish、哪怕它自己抛异常，最多活 15 秒
        QTimer.singleShot(MAX_LIFE_MS, self._hard_close)

    # ---------------- 外部 ----------------
    def set_step(self, text: str):
        # 画面只要人，步骤文字不绘制；保留接口避免调用方报错
        self._step = text

    def finish(self):
        self._done = True
        self._finish_at = max(self._t0 + MIN_SHOW, time.time())

    def _hide_now(self):
        """直接调 Win32 隐藏窗口。

        v3.0.6 实测：程序首次启动时主线程可能被初始化卡住上百毫秒到几秒，
        Qt 的 close()/hide() 只是投递消息，主线程不空转就不会真正隐藏，
        屏幕上于是留着一个"卡住的大肥鱼"。ShowWindow(SW_HIDE) 直接走系统调用，
        不依赖事件循环，立刻从屏幕上消失。
        """
        try:
            hwnd = int(self.winId())
            if hwnd:
                import ctypes
                ctypes.windll.user32.ShowWindow(hwnd, 0)   # SW_HIDE
        except Exception:  # noqa: BLE001
            pass
        try:
            self.hide()
        except Exception:  # noqa: BLE001
            pass

    def _hard_close(self):
        """无条件收尾：先系统级隐藏，再 close，最后销毁。"""
        if self._closing:
            return
        self._closing = True
        try:
            self._tm.stop()
        except Exception:  # noqa: BLE001
            pass
        self._hide_now()
        try:
            self.close()
        except Exception:  # noqa: BLE001
            pass

    # ---------------- 内部 ----------------
    def _center(self):
        scr = QApplication.primaryScreen().availableGeometry()
        self.move(scr.center().x() - W // 2, scr.center().y() - H // 2 - 20)

    def _tick(self):
        el = time.time() - self._t0
        # 淡入：只在还没收到 finish() 时做。
        # v3.0.6 修的 bug：原来这里不看 _done，每帧都把 _fade 重置回 1.0，
        # 而淡出每帧只减 0.075，两个方向互相抵消，_fade 永远卡在 0.925，
        # 关闭分支永远进不去 —— 表现就是屏幕上一直留着一个不动的大肥鱼。
        if self._fade < 1.0 and not self._done:
            self._fade = min(1.0, el / FADE_IN)
        # 淡出关闭
        if self._done and time.time() >= self._finish_at:
            self._fade -= 0.075
            if self._fade <= 0.0 and not self._closing:
                self._hard_close()
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
