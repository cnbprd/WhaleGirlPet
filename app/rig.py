# -*- coding: utf-8 -*-
"""档 B：网格蒙皮骨骼（单张立绘，不拆图）。

为什么不是"切部件"：实测把立绘按矩形切开后，每块都带着相邻部位的像素，
一转关节就在膝盖/裙摆处断成两截（tools/proto_rig.py 的对比图）。改成
Live2D 同款思路——整张图铺一张顶点网格，按骨骼权重扭网格，皮是连续的，
关节表现为局部网格弯曲，没有断口。

骨骼（第一版只做腿，够撑起走路/小跑/屈膝）：
    hip_L/R → knee_L/R（大腿绕髋转，小腿再绕膝转，膝部有混合带）
枢轴用相对比例定义，换皮肤/萝莉形态/表情图都不用重新量。
"""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap, QPolygonF, QTransform

# 相对比例（以立绘自身宽高为 1），从 default.png 的坐标网格量得
PROFILE = {
    "center_x": 0.500,
    "split_x": 0.500,      # 左右腿分界
    "hip_y": 0.586,        # 髋（裙摆内侧）
    "knee_y": 0.773,       # 膝
    "hip_dx": 0.065,       # 髋相对中心的横向偏移
    "leg_top_y": 0.598,    # 裙摆下沿：此线以下才参与形变
    "knee_blend": 0.020,   # 膝部混合带宽（比例高）
    "grid": (8, 20),       # 网格列 × 行
    "grow": 0.18,          # 三角形向外扩张像素，消掉相邻块之间的缝
}


def _rot(pt, origin, deg):
    if not deg:
        return pt
    ox, oy = (origin.x(), origin.y()) if isinstance(origin, QPointF) else (origin[0], origin[1])
    rad = math.radians(deg)
    dx, dy = pt.x() - ox, pt.y() - oy
    return QPointF(ox + dx * math.cos(rad) - dy * math.sin(rad),
                   oy + dx * math.sin(rad) + dy * math.cos(rad))


def _affine_from_tri(s0, s1, s2, d0, d1, d2):
    """把源三角形映射到目标三角形的仿射矩阵；退化时返回 None。"""
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


class Rig:
    """一张立绘 + 一副腿部骨骼。frame() 返回当前姿态的整张图。"""

    def __init__(self, pix: QPixmap, profile: dict | None = None):
        self.prof = dict(PROFILE, **(profile or {}))
        self.set_pix(pix)

    # ---------- 素材 ----------
    def set_pix(self, pix: QPixmap):
        self.pix = pix
        self.W, self.H = pix.width(), pix.height()
        prof = self.prof
        self.gx, self.gy = prof["grid"]
        cx = prof["center_x"] * self.W
        self._hip_l = (cx - prof["hip_dx"] * self.W, prof["hip_y"] * self.H)
        self._hip_r = (cx + prof["hip_dx"] * self.W, prof["hip_y"] * self.H)
        self._knee_l = (cx - prof["hip_dx"] * self.W * 0.95, prof["knee_y"] * self.H)
        self._knee_r = (cx + prof["hip_dx"] * self.W * 0.95, prof["knee_y"] * self.H)
        self._split_x = prof["split_x"] * self.W
        self._leg_top = prof["leg_top_y"] * self.H
        self._knee_blend = prof["knee_blend"] * self.H
        # 预切源网格几何：每格两个三角形的源点 + 源矩形
        self._cells = []
        for j in range(self.gy):
            y0, y1 = self.H * j / self.gy, self.H * (j + 1) / self.gy
            for i in range(self.gx):
                x0, x1 = self.W * i / self.gx, self.W * (i + 1) / self.gx
                s00, s10 = QPointF(x0, y0), QPointF(x1, y0)
                s01, s11 = QPointF(x0, y1), QPointF(x1, y1)
                rect = QRectF(x0, y0, x1 - x0, y1 - y0)
                self._cells.append((j, i, s00, s10, s01, s11, rect))
        self._cache_key = None
        self._cache = None

    # ---------- 形变 ----------
    def _leg_point(self, pt, side_l, a_thigh, a_shin):
        prof = self.prof
        if pt.y() < self._leg_top or (a_thigh == 0.0 and a_shin == 0.0):
            return pt
        hip = self._hip_l if side_l else self._hip_r
        knee = self._knee_l if side_l else self._knee_r
        if a_thigh == 0.0 and a_shin == 0.0:
            return pt
        dist = pt.y() - knee[1]
        blend = max(1.0, self._knee_blend)
        if dist <= -blend:
            return _rot(pt, hip, a_thigh)
        if dist >= blend:
            return _rot(_rot(pt, QPointF(*knee), a_shin), hip, a_thigh)
        t = (dist + blend) / (2 * blend)
        a = _rot(pt, hip, a_thigh)
        b = _rot(_rot(pt, QPointF(*knee), a_shin), hip, a_thigh)
        return QPointF(a.x() * (1 - t) + b.x() * t, a.y() * (1 - t) + b.y() * t)

    def _grid(self, tl, sl, tr, sr):
        rows = []
        for j in range(self.gy + 1):
            y = self.H * j / self.gy
            row = []
            for i in range(self.gx + 1):
                x = self.W * i / self.gx
                pt = QPointF(x, y)
                if pt.y() >= self._leg_top:
                    left = x < self._split_x
                    pt = self._leg_point(pt, left, tl if left else tr, sl if left else sr)
                row.append(pt)
            rows.append(row)
        return rows

    # ---------- 出帧 ----------
    def frame(self, thigh_l=0.0, shin_l=0.0, thigh_r=0.0, shin_r=0.0) -> QPixmap:
        key = (round(thigh_l, 2), round(shin_l, 2), round(thigh_r, 2), round(shin_r, 2))
        if key == self._cache_key and self._cache is not None:
            return self._cache
        gw = self._grid(*key)
        canvas = QPixmap(self.W, self.H)
        canvas.fill(Qt.transparent)
        p = QPainter(canvas)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setRenderHint(QPainter.Antialiasing)
        grow = self.prof["grow"]
        for (j, i, s00, s10, s01, s11, rect) in self._cells:
            d00, d10 = gw[j][i], gw[j][i + 1]
            d01, d11 = gw[j + 1][i], gw[j + 1][i + 1]
            if (d00 == s00 and d10 == s10 and d01 == s01 and d11 == s11):
                p.drawPixmap(rect, self.pix, rect)   # 没动，整块直贴
                continue
            for src_pts, dst_pts in (((s00, s10, s11), (d00, d10, d11)),
                                     ((s00, s11, s01), (d00, d11, d01))):
                t = _affine_from_tri(*src_pts, *dst_pts)
                if t is None:
                    continue
                # clip 用源坐标建、在 setTransform 之后设置，让裁剪跟着矩阵走
                cx = sum(q.x() for q in src_pts) / 3.0
                cy = sum(q.y() for q in src_pts) / 3.0
                grown = []
                for q in src_pts:
                    gx, gy = q.x() - cx, q.y() - cy
                    ln = math.hypot(gx, gy) or 1.0
                    grown.append(QPointF(q.x() + gx / ln * grow, q.y() + gy / ln * grow))
                path = QPainterPath()
                path.addPolygon(QPolygonF(grown))
                p.save()
                p.setTransform(t)
                p.setClipPath(path)
                p.drawPixmap(rect, self.pix, rect)
                p.restore()
        p.end()
        self._cache_key = key
        self._cache = canvas
        return canvas

    # ---------- 步态角度 ----------
    @staticmethod
    def walk_angles(phase: float, amp_thigh=9.0, amp_shin=20.0):
        """一个完整步幅的腿角度：phase 0..2π。返回 (thigh_l, shin_l, thigh_r, shin_r)。"""
        tl = -amp_thigh * math.sin(phase)
        tr = -amp_thigh * math.sin(phase + math.pi)
        # 膝只向后弯（不能反折），抬腿相位置大
        sl = amp_shin * max(0.0, math.sin(phase + 0.9))
        sr = amp_shin * max(0.0, math.sin(phase + math.pi + 0.9))
        return tl, sl, tr, sr
