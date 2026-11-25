# -*- coding: utf-8 -*-
"""重绘 PyInstaller 原生启动图（assets/ui/splash_native.png）。

v3.0.0 用户反馈：「启动画面深色背景是一整块纯色」。exe 冷启动时先显示的是
PyInstaller 的 Splash 图（不是 app/splash.py），所以这张静态图必须自己带层次：
多层径向渐变 + 顶部/底部压暗 + 人物背光 + 三圈涟漪 + 上浮气泡 + 脚下水波。

用法：python tools/make_splash_native.py
"""
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from paths import asset_path  # noqa: E402

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QApplication  # noqa: E402

W, H = 420, 620
OUT = os.path.join(ROOT, "assets", "ui", "splash_native.png")


def draw():
    pm = QPixmap(W, H)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)

    # 1) 垂直基底
    base = QLinearGradient(0, 0, 0, H)
    base.setColorAt(0.0, QColor(13, 33, 58))
    base.setColorAt(0.45, QColor(10, 25, 45))
    base.setColorAt(1.0, QColor(4, 12, 22))
    p.fillRect(QRectF(0, 0, W, H), base)

    # 2) 中央偏上的冷光（人物背后那团亮）
    halo = QRadialGradient(QPointF(W / 2, H * 0.40), W * 1.05)
    halo.setColorAt(0.0, QColor(96, 182, 240, 235))
    halo.setColorAt(0.26, QColor(56, 128, 190, 155))
    halo.setColorAt(0.58, QColor(28, 74, 120, 72))
    halo.setColorAt(1.0, QColor(14, 36, 60, 0))
    p.fillRect(QRectF(0, 0, W, H), halo)

    # 2.5) 一道斜向光柱（从右上打下来），把纯色感彻底破掉
    beam = QLinearGradient(QPointF(W * 0.78, -20), QPointF(W * 0.42, H * 0.92))
    beam.setColorAt(0.0, QColor(150, 216, 255, 0))
    beam.setColorAt(0.35, QColor(150, 216, 255, 62))
    beam.setColorAt(0.68, QColor(120, 190, 245, 30))
    beam.setColorAt(1.0, QColor(120, 190, 245, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(beam)
    p.drawPolygon([
        QPointF(W * 0.60, -30), QPointF(W * 0.92, -30),
        QPointF(W * 0.46, H + 30), QPointF(W * 0.18, H + 30),
    ])

    # 3) 左上冷蓝点光 + 右下暖紫点光，避免整块同色
    sp1 = QRadialGradient(QPointF(W * 0.10, H * 0.06), W * 0.62)
    sp1.setColorAt(0.0, QColor(110, 196, 240, 110))
    sp1.setColorAt(1.0, QColor(110, 196, 240, 0))
    p.fillRect(QRectF(0, 0, W, H), sp1)

    sp2 = QRadialGradient(QPointF(W * 0.92, H * 0.78), W * 0.72)
    sp2.setColorAt(0.0, QColor(96, 78, 150, 95))
    sp2.setColorAt(1.0, QColor(96, 78, 150, 0))
    p.fillRect(QRectF(0, 0, W, H), sp2)

    # 4) 顶部与底部压暗，收住画面
    top = QLinearGradient(0, 0, 0, H * 0.24)
    top.setColorAt(0.0, QColor(0, 0, 0, 155))
    top.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.fillRect(QRectF(0, 0, W, H * 0.24), top)

    bot = QLinearGradient(0, H * 0.58, 0, H)
    bot.setColorAt(0.0, QColor(0, 0, 0, 0))
    bot.setColorAt(1.0, QColor(0, 0, 0, 205))
    p.fillRect(QRectF(0, H * 0.58, W, H * 0.42), bot)

    # 5) 三圈错相位涟漪
    for i, (rx, ry, a) in enumerate(((150, 34, 92), (196, 44, 58), (246, 56, 34), (300, 68, 20))):
        pen = QPen(QColor(150, 218, 255, a))
        pen.setWidthF(1.6)
        p.setPen(pen)
        p.drawEllipse(QPointF(W / 2, H * 0.73), rx, ry)

    # 6) 上浮气泡（固定种子，每次生成一致）
    rnd = random.Random(20261125)
    for _ in range(28):
        x = rnd.uniform(14, W - 14)
        y = rnd.uniform(H * 0.08, H * 0.88)
        r = rnd.uniform(1.8, 6.2)
        alpha = int(rnd.uniform(30, 108))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(180, 232, 255, alpha))
        p.drawEllipse(QPointF(x, y), r, r)
        p.setBrush(QColor(255, 255, 255, min(200, alpha + 70)))
        p.drawEllipse(QPointF(x - r * 0.28, y - r * 0.28), r * 0.30, r * 0.30)

    # 7) 人物背光 + 立绘
    pet_pm = QPixmap(asset_path("skins/default.png"))
    if not pet_pm.isNull():
        pet = pet_pm.scaledToHeight(int(H * 0.70), Qt.SmoothTransformation)
        px = int(W / 2 - pet.width() / 2)
        py = int(H * 0.50 - pet.height() * 0.52)
        glow = QRadialGradient(QPointF(W / 2, H * 0.44), pet.width() * 0.82)
        glow.setColorAt(0.0, QColor(150, 220, 255, 120))
        glow.setColorAt(0.55, QColor(96, 168, 226, 62))
        glow.setColorAt(1.0, QColor(60, 120, 180, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(W / 2, H * 0.44), pet.width() * 0.82, pet.width() * 0.82)
        p.drawPixmap(px, py, pet)

    # 8) 脚下投影 + 水波
    sh = QRadialGradient(QPointF(W / 2, H * 0.72), 108)
    sh.setColorAt(0.0, QColor(0, 0, 0, 150))
    sh.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(sh)
    p.drawEllipse(QPointF(W / 2, H * 0.72), 108, 22)

    pen = QPen(QColor(120, 200, 250, 70))
    pen.setWidthF(1.2)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(W / 2, H * 0.72), 86, 15)

    p.end()
    return pm


def main():
    app = QApplication.instance() or QApplication([])
    pm = draw()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    ok = pm.save(OUT, "PNG")
    print(f"saved={ok} {OUT} {pm.width()}x{pm.height()} bytes={os.path.getsize(OUT)}")


if __name__ == "__main__":
    main()
