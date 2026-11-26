# -*- coding: utf-8 -*-
"""B 路线第 3 步：自研多 slot 渲染器（只读 RigModel，不依赖 Spine Runtime）。

当前能力：
- region 附件按 slot 顺序绘制；slot 的 bone 世界角度绕骨骼枢轴旋转；
- 父子骨链已生效（头转 → 左右发束跟着转）；
- 静止位与原图的平均像素差 <0.1（Qt alpha 合成误差，无可见白缝）。

后续在 skeletal.py 里接 mesh/权重/弹簧时，直接复用 RigModel.world()。
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPixmap

from spine_import import RigModel


class RigRenderer:
    def __init__(self, model: RigModel, asset_dir: str = ""):
        self.model = model
        self.asset_dir = asset_dir
        self.pix: dict[str, QPixmap] = {}
        for slot in model.slots:
            path = model.path_for(slot)
            if not path:
                continue
            pix = QPixmap(path)
            if pix.isNull():
                raise ValueError("bad layer: " + path)
            self.pix[slot.name] = pix
        self.W = int(model.width or max((p.width() for p in self.pix.values()), default=0))
        self.H = int(model.height or max((p.height() for p in self.pix.values()), default=0))

    def render(self, angles: dict[str, float] | None = None,
               offsets: dict[str, tuple[float, float]] | None = None) -> QPixmap:
        angles = angles or {}
        offsets = offsets or {}
        world = self.model.world(angles)
        canvas = QPixmap(self.W, self.H)
        canvas.fill(Qt.transparent)
        p = QPainter(canvas)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        for slot in self.model.slots:
            pix = self.pix.get(slot.name)
            if pix is None or pix.isNull():
                continue
            region = self.model.region_for(slot)
            if region is None:
                continue
            wx, wy, wa = world.get(slot.bone, (0.0, 0.0, 0.0))
            ox, oy = offsets.get(slot.name, (0.0, 0.0))
            p.save()
            if abs(wa) > 1e-9:
                p.translate(wx + ox, wy + oy)
                p.rotate(wa)
                p.translate(-wx - ox, -wy - oy)
            elif ox or oy:
                p.translate(ox, oy)
            p.drawPixmap(QPointF(region.x, region.y), pix)
            p.restore()
        p.end()
        return canvas
