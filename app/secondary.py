# -*- coding: utf-8 -*-
"""v3.0.26 第三阶段：裙摆 / 尾巴的 alpha 分层 + Verlet spring。

本阶段起 default 追加左右外侧发束（4° 整图叠加，不挖底图）。
设计口径：
- 资产层由 `tools/make_secondary_layers.py` 生成；运行时只读，不再抠图。
- 裙摆用「上端固定在腰、越往下摆幅越大」的剪切形变，不绕腰硬转，
  否则裙腰会离开身体，露出后面的头发/背景。
- 尾巴绕根部做小幅旋转，根部窄，旋转不会把整块腰线撕开。
- 弹簧是半隐式欧拉 + 子步长；30fps 和 60fps 下行为一致，不会因为掉帧炸开。
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass

from PySide6.QtCore import QRect
from PySide6.QtGui import QPainter, QPixmap, QTransform

from paths import asset_path


@dataclass
class LayerSpec:
    part: str
    pivot: tuple[float, float]
    mode: str          # "shear" 或 "rotate"
    max_deg: float
    stiffness: float
    damping: float
    gain: float


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class AngularSpring:
    """一维角弹簧：target 为期望偏角（度），drive 为外力角加速度。"""

    def __init__(self, stiffness: float, damping: float, max_deg: float):
        self.k = float(stiffness)
        self.d = float(damping)
        self.max_deg = float(max_deg)
        self.angle = 0.0
        self.vel = 0.0

    def step(self, dt: float, target: float, drive: float = 0.0):
        dt = _clamp(float(dt), 0.0, 0.08)
        # 大 dt 拆子步，避免 20fps 时弹簧越界
        n = max(1, int(math.ceil(dt / 0.016)))
        h = dt / n
        for _ in range(n):
            acc = -self.k * (self.angle - target) - self.d * self.vel + drive
            self.vel += acc * h
            self.angle += self.vel * h
            if self.angle > self.max_deg:
                self.angle = self.max_deg
                self.vel = min(0.0, self.vel)
            elif self.angle < -self.max_deg:
                self.angle = -self.max_deg
                self.vel = max(0.0, self.vel)


class SecondaryMotion:
    """按皮肤加载裙摆/尾巴层，并给绘制端提供当前摆角。"""

    def __init__(self, scale: float = 1.0):
        self.scale = float(scale)
        self.skin = ""
        self.two = False
        self.enabled = False
        self.meta = {}
        self.pix = {}
        self.springs = {}
        self.specs = {}
        self.t = 0.0

    def set_skin(self, skin_key: str, two: bool = False):
        self.skin = skin_key
        self.two = bool(two)
        self.meta = {}
        self.pix = {}
        self.springs = {}
        self.specs = {}
        self.enabled = False
        meta_path = asset_path(os.path.join("skins", "layers", "layers.json"))
        if not os.path.exists(meta_path):
            return False
        try:
            with open(meta_path, encoding="utf-8") as f:
                root = json.load(f)
            self.meta = (root.get("skins") or {}).get(skin_key) or {}
        except (OSError, ValueError):
            return False
        if not self.meta:
            return False

        specs = (
            LayerSpec("tail", tuple(self.meta.get("tail_pivot", (0.7, 0.55))),
                      "rotate", 12.0, 24.0, 8.0, 1.0),
            LayerSpec("skirt", tuple(self.meta.get("skirt_pivot", (0.5, 0.43))),
                      "shear", 7.0, 32.0, 10.0, 1.0),
        )
        # A 案：default 追加左右外侧发束，整图底叠加，最大 4°，不挖底图
        if self.meta.get("hair_l") and self.meta.get("hair_r"):
            specs += (
                LayerSpec("hair_l", tuple(self.meta.get("hair_l_pivot", (0.14, 0.23))),
                          "rotate", 4.0, 34.0, 10.0, 1.35),
                LayerSpec("hair_r", tuple(self.meta.get("hair_r_pivot", (0.78, 0.23))),
                          "rotate", 4.0, 34.0, 10.0, 1.35),
            )
        for spec in specs:
            name = self.meta.get(spec.part, "")
            if self.two:
                name = self.meta.get(spec.part + "_2x", "") or name
            rel = os.path.join("skins", "layers", name)
            if not rel or not os.path.exists(asset_path(rel)):
                continue
            self.pix[spec.part] = QPixmap(asset_path(rel))
            self.springs[spec.part] = AngularSpring(spec.stiffness, spec.damping, spec.max_deg)
            self.specs[spec.part] = spec
        self.enabled = bool(self.pix)
        return self.enabled

    def step(self, dt: float, dx: float, dy: float, state: str, state_t: float):
        if not self.enabled:
            return
        self.t += max(0.0, float(dt))
        # 世界坐标位移按 1x 立绘归一化；dx 是每帧像素，不是速度
        vx = float(dx) / max(0.35, self.scale)
        vy = float(dy) / max(0.35, self.scale)
        breathe = math.sin(self.t * 1.1) * 0.7
        amp = 1.0
        if state in ("run", "brawl", "tumble", "hop"):
            amp = 1.7
        elif state in ("walk", "trot", "crab"):
            amp = 1.25
        elif state in ("dance", "wave", "lion"):
            amp = 1.45
        elif state == "sleep":
            amp = 0.18
        # 惯性方向：向右走时裙摆向左滞后，dx 为正 → 目标偏角为正（剪切向左）
        tail_target = (vx * 2.2 + breathe * 1.5 * amp) * amp
        skirt_target = (vx * 1.45 + breathe * 0.5 * amp) * amp
        # 上浮/下落给一个小的前后惯性；dy 是窗口位移，落地时才会明显
        tail_target += -vy * 0.8
        skirt_target += -vy * 0.35
        tail = self.springs.get("tail")
        skirt = self.springs.get("skirt")
        if tail is not None:
            tail.step(dt, _clamp(tail_target, -10.0, 10.0))
        if skirt is not None:
            skirt.step(dt, _clamp(skirt_target, -6.0, 6.0))
        # 发束跟裙摆同向滞后，但限幅更小；发根不离开头皮
        hair_target = (vx * 1.7 + breathe * 0.9 * amp) * amp
        hair_target += -vy * 0.45
        for name in ("hair_l", "hair_r"):
            spring = self.springs.get(name)
            if spring is not None:
                spring.step(dt, _clamp(hair_target, -4.0, 4.0))

    def angles(self) -> dict:
        return {k: round(v.angle, 2) for k, v in self.springs.items()}

    def paint(self, p: QPainter, pw: int, ph: int):
        """按顺序画：发束（最里）→ 尾巴（在后面）→ 裙摆（压住尾巴根）。

        底图保留完整立绘，层只覆盖可动区域；静止时层与原图像素重合，
        动起来时不会在裙腰/尾巴根留下透明洞，只是边缘会保留一点原位布料。
        """
        if not self.enabled:
            return
        self._paint_one(p, pw, ph, "hair_l")
        self._paint_one(p, pw, ph, "hair_r")
        self._paint_one(p, pw, ph, "tail")
        self._paint_one(p, pw, ph, "skirt")

    def _paint_one(self, p: QPainter, pw: int, ph: int, part: str):
        pix = self.pix.get(part)
        spring = self.springs.get(part)
        spec = self.specs.get(part)
        if pix is None or pix.isNull() or spring is None or spec is None:
            return
        ox = -(pw // 2)
        oy = -ph
        px = ox + spec.pivot[0] * pw
        py = oy + spec.pivot[1] * ph
        p.save()
        if spec.mode == "shear":
            # x' = x + tan(angle) * (y - pivot_y)：腰线不动，裙摆下沿摆
            shear = math.tan(math.radians(spring.angle)) * 0.72
            p.translate(px, py)
            p.setTransform(QTransform(1.0, 0.0, shear, 1.0, 0.0, 0.0), True)
            p.translate(-px, -py)
        else:
            p.translate(px, py)
            p.rotate(spring.angle)
            p.translate(-px, -py)
        p.drawPixmap(QRect(ox, oy, pw, ph), pix)
        p.restore()
