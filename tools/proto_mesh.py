# -*- coding: utf-8 -*-
"""档 B 原型 v2：不拆图，改用网格蒙皮（顶点按骨骼权重形变），验证「真屈膝」效果。"""
import math
import os
import sys
sys.path.insert(0, r"F:\WhaleGirlPet\app")
from PySide6.QtCore import QPointF, QRect, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QImage, QPainter,  # noqa: E402
                           QPainterPath, QPixmap, QPolygonF, QTransform)
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])
SRC = r"F:\WhaleGirlPet\assets\skins\default.png"
src = QPixmap(SRC)
W, H = src.width(), src.height()

# 骨骼枢轴（从坐标网格图上量得）
HIP_L, KNEE_L = (116.0, 300.0), (116.5, 396.0)
HIP_R, KNEE_R = (151.0, 300.0), (151.5, 396.0)
SPLIT_X = 133.5          # 双腿分界
LEG_TOP_Y = 306.0        # 裙摆下沿，此线以下才参与形变
KNEE_BLEND = 10.0        # 膝部混合带宽，避免硬折

GX, GY = 10, 26          # 网格分辨率（列×行）


def rot(pt, origin, deg):
    if not deg:
        return pt
    ox, oy = (origin.x(), origin.y()) if isinstance(origin, QPointF) else (origin[0], origin[1])
    rad = math.radians(deg)
    dx, dy = pt.x() - ox, pt.y() - oy
    return QPointF(ox + dx * math.cos(rad) - dy * math.sin(rad),
                   oy + dx * math.sin(rad) + dy * math.cos(rad))


def leg_point(pt, hip, knee, a_thigh, a_shin):
    """把一点按其所在高度/左右腿，施加髋与膝的旋转变换。"""
    if pt.y() < LEG_TOP_Y or a_thigh == 0 and a_shin == 0:
        return pt
    side_l = pt.x() < SPLIT_X
    hip_o, knee_o = (HIP_L, KNEE_L) if side_l else (HIP_R, KNEE_R)
    a1 = a_thigh if side_l else 0.0     # 原型只弯左腿（右腿留作对照）
    a2 = a_shin if side_l else 0.0
    if a1 == 0 and a2 == 0:
        return pt
    # 膝部混合：靠近膝线时，把腿段变换按距离做插值
    knee_now = rot(QPointF(*knee_o), hip_o, a1)
    knee_radius = KNEE_BLEND
    # 小腿点（y 在膝以下）
    p_mid = rot(QPointF(*knee_o), hip_o, a1)
    dist = pt.y() - knee_o[1]
    if dist <= -knee_radius:
        return rot(pt, hip_o, a1)                      # 纯大腿
    if dist >= knee_radius:
        q = rot(pt, QPointF(*knee_o), a2)              # 先绕原膝转
        return rot(q, hip_o, a1)                       # 再由大腿带着走
    # 混合带：在两条结果之间线形插值
    t = (dist + knee_radius) / (2 * knee_radius)
    a = rot(pt, hip_o, a1)
    b = rot(rot(pt, QPointF(*knee_o), a2), hip_o, a1)
    return QPointF(a.x() * (1 - t) + b.x() * t, a.y() * (1 - t) + b.y() * t)


def make_grid(a_thigh, a_shin):
    pts = []
    for j in range(GY + 1):
        row = []
        y = H * j / GY
        for i in range(GX + 1):
            x = W * i / GX
            row.append(leg_point(QPointF(x, y), HIP_L, KNEE_L, a_thigh, a_shin))
        pts.append(row)
    return pts


def affine_from_tri(s0, s1, s2, d0, d1, d2):
    """求把源三角形映射到目标三角形的仿射矩阵；退化时返回 None。

    解的是矩阵元素本身：
        m11*u + m21*v = p   （u,v 为源基向量，p 为目标基向量 x 分量）
        m12*u + m22*v = q   （同一组基，y 分量）
    """
    ux, uy = s1.x() - s0.x(), s1.y() - s0.y()
    vx, vy = s2.x() - s0.x(), s2.y() - s0.y()
    det = ux * vy - uy * vx
    if abs(det) < 1e-9:
        return None
    px, py = d1.x() - d0.x(), d1.y() - d0.y()
    qx, qy = d2.x() - d0.x(), d2.y() - d0.y()
    m11 = (px * vy - qx * uy) / det
    m21 = (ux * qx - vx * px) / det
    m12 = (py * vy - qy * uy) / det
    m22 = (ux * qy - vx * py) / det
    return QTransform(m11, m12, m21, m22,
                      d0.x() - m11 * s0.x() - m21 * s0.y(),
                      d0.y() - m12 * s0.x() - m22 * s0.y())


def draw_tri(p, src_pts, dst_pts, src_rect):
    t = affine_from_tri(*src_pts, *dst_pts)
    if t is None:
        return
    # 源三角形围质心外扩 0.5px，消掉相邻三角形之间的抗锯齿缝。
    # 注意：clip 先在源坐标建好，再在 setTransform 之后设置，让 clip 跟着 t 映射；
    # 反过来（先 clip 后 transform）裁剪会被二次变换，结果就是碎块。
    cx = sum(pt.x() for pt in src_pts) / 3.0
    cy = sum(pt.y() for pt in src_pts) / 3.0
    grown = []
    for pt in src_pts:
        gx, gy = pt.x() - cx, pt.y() - cy
        ln = math.hypot(gx, gy) or 1.0
        grown.append(QPointF(pt.x() + gx / ln * 0.5, pt.y() + gy / ln * 0.5))
    path = QPainterPath()
    path.addPolygon(QPolygonF(grown))
    p.save()
    p.setTransform(t)
    p.setClipPath(path)
    p.drawPixmap(src_rect, src, src_rect)
    p.restore()


def render(a_thigh=0.0, a_shin=0.0) -> QImage:
    grid = make_grid(a_thigh, a_shin)
    canvas = QPixmap(W, H)
    canvas.fill(Qt.transparent)
    p = QPainter(canvas)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.setRenderHint(QPainter.Antialiasing)
    for j in range(GY):
        y0, y1 = H * j / GY, H * (j + 1) / GY
        for i in range(GX):
            x0, x1 = W * i / GX, W * (i + 1) / GX
            s00, s10 = QPointF(x0, y0), QPointF(x1, y0)
            s01, s11 = QPointF(x0, y1), QPointF(x1, y1)
            d00, d10 = grid[j][i], grid[j][i + 1]
            d01, d11 = grid[j + 1][i], grid[j + 1][i + 1]
            rect = QRectF(x0, y0, x1 - x0, y1 - y0)
            if (d00 == s00 and d10 == s10 and d01 == s01 and d11 == s11):
                p.drawPixmap(rect, src, rect)     # 完全没动，整块直贴
                continue
            draw_tri(p, (s00, s10, s11), (d00, d10, d11), rect)
            draw_tri(p, (s00, s11, s01), (d00, d11, d01), rect)
    p.end()
    return canvas.toImage()


CASES = [
    ("立正", 0, 0),
    ("小腿 20°", 0, 20),
    ("小腿 38°", 0, 38),
    ("大腿 15° 小腿 30°", 15, 30),
    ("深屈 25°/55°", 25, 55),
]
SC = 1.55
BW, BH = int(W * SC) + 10, int(H * SC) + 26
img = QImage(BW * len(CASES), BH, QImage.Format_ARGB32)
img.fill(QColor(250, 249, 246))
p = QPainter(img)
p.setRenderHint(QPainter.SmoothPixmapTransform)
for f in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf"):
    if os.path.exists(f):
        QFontDatabase.addApplicationFont(f)
        break
fnt = QFont()
fnt.setPointSize(11)
p.setFont(fnt)
for i, (label, a1, a2) in enumerate(CASES):
    frame = render(a1, a2)
    x0 = i * BW
    p.drawImage(QRect(x0 + 5, 24, int(W * SC), int(H * SC)), frame)
    p.setPen(QColor(70, 70, 80))
    p.drawText(QRect(x0 + 6, 3, BW - 8, 18), Qt.AlignLeft, label)
    if i:
        p.setPen(QColor(220, 220, 224))
        p.drawLine(x0, 0, x0, BH - 1)
p.end()
out = r"F:\WhaleGirlPet\docs\rig_proto_mesh.png"
img.save(out)
print("网格蒙皮原型:", out, os.path.getsize(out), "bytes", "| cells", GX * GY)

