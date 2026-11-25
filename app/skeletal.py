# -*- coding: utf-8 -*-
"""游戏引擎式 2D 骨骼动画（骨架 + 蒙皮 + 动画剪辑 + 播放器）。

结构参考（设计借鉴，代码自写，未复制任何项目源码）：
  - Godot Engine 4.x 的 2D 骨骼系统：Skeleton2D 骨架树 + Bone2D（骨骼落在"起点"）
    + Polygon2D 顶点权重蒙皮。https://docs.godotengine.org/ (MIT)
  - Inochi2D：开源 2D rigging（Live2D 替代），BSD 2-Clause，仅作参数驱动思路参考。
    https://inochi2d.com
  - Spine Runtime 未使用：其许可要求分发时用户自行持有 Spine Editor 授权，不适合本项目。

引擎四件套：
  Skeleton  骨骼树（每根骨：父骨、图像坐标枢轴）
  Skin      顶点 + 每顶点绑定的骨骼权重（线性混合蒙皮 LBS）
  Clip      某根骨的角度关键帧轨道，复用 anim_engine 的缓动
  Player    时间轴播放、循环回卷、事件点

渲染：顶点经 LBS 变换后，按网格逐三角形仿射贴图（与 rig.py 同一套画法）。
"""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap, QPolygonF

import anim_engine as anim
from rig import _affine_from_tri

# 骨骼定义（图像相对坐标，取自 267×512 立绘的坐标网格）
BONES = {
    "root":   {"parent": None,    "pivot": (0.500, 0.586)},
    "spine":  {"parent": "root",  "pivot": (0.500, 0.586)},
    "head":   {"parent": "spine", "pivot": (0.500, 0.240)},
    "thigh_l": {"parent": "root", "pivot": (0.435, 0.586)},
    "shin_l":  {"parent": "thigh_l", "pivot": (0.435, 0.773)},
    "foot_l":  {"parent": "shin_l", "pivot": (0.435, 0.918)},
    "thigh_r": {"parent": "root", "pivot": (0.565, 0.586)},
    "shin_r":  {"parent": "thigh_r", "pivot": (0.565, 0.773)},
    "foot_r":  {"parent": "shin_r", "pivot": (0.565, 0.918)},
}

# 蒙皮分区（相对高度）
LEG_TOP = 0.598      # 裙摆下沿：以下才归腿骨
KNEE_Y = 0.773
ANKLE_Y = 0.918
SPLIT_X = 0.500      # 左右腿分界
KNEE_BLEND = 0.030   # 膝部权重过渡带（比例高）
ANKLE_BLEND = 0.022  # 踝部过渡带（小腿 → 脚）
HEAD_Y = 0.215       # 头/颈分界
HEAD_BLEND = 0.055

GRID = (8, 20)


def _rot(pt, pivot, deg):
    if not deg:
        return pt
    px, py = (pivot.x(), pivot.y()) if isinstance(pivot, QPointF) else (pivot[0], pivot[1])
    rad = math.radians(deg)
    dx, dy = pt.x() - px, pt.y() - py
    return QPointF(px + dx * math.cos(rad) - dy * math.sin(rad),
                   py + dx * math.sin(rad) + dy * math.cos(rad))


class Skeleton:
    """骨骼树：算一次姿态，得到每根骨的世界枢轴与世界角度。"""

    def __init__(self, w, h, bones=None):
        self.W, self.H = w, h
        self.defs = bones or BONES
        self.rest = {n: (d["pivot"][0] * w, d["pivot"][1] * h) for n, d in self.defs.items()}

    def solve(self, angles: dict) -> dict:
        """返回 {骨名: (世界枢轴, 世界角度)}；角度是相对父骨的局部角度（度）。"""
        out = {}
        for name, d in self.defs.items():
            p = d["parent"]
            if p is None:
                out[name] = (self.rest[name], float(angles.get(name, 0.0)))
                continue
            pp, pa = out[p]
            out[name] = (_rot(QPointF(*self.rest[name]), pp, pa),
                         pa + float(angles.get(name, 0.0)))
        return out


def vertex_weights(x: float, y: float, w: float, h: float) -> list:
    """这个顶点受哪些骨影响、权重多少（线性混合蒙皮）。"""
    if y >= LEG_TOP * h:
        side = "l" if x < SPLIT_X * w else "r"
        knee = KNEE_Y * h
        blend = max(1.0, KNEE_BLEND * h)
        u = min(1.0, max(0.0, (y - (knee - blend)) / (2 * blend)))
        shin_w = u
        # 踝以下交给脚骨，脚不会被小腿带着整只翻过去
        ankle = ANKLE_Y * h
        ab = max(1.0, ANKLE_BLEND * h)
        v = min(1.0, max(0.0, (y - (ankle - ab)) / (2 * ab)))
        if v <= 0.0:
            return [(f"thigh_{side}", 1.0 - shin_w), (f"shin_{side}", shin_w)]
        return [(f"thigh_{side}", (1.0 - shin_w) * (1.0 - v)),
                (f"shin_{side}", shin_w * (1.0 - v)),
                (f"foot_{side}", v)]
    if y <= HEAD_Y * h - HEAD_BLEND * h:
        return [("head", 1.0)]
    if y <= HEAD_Y * h + HEAD_BLEND * h:
        blend = max(1.0, 2 * HEAD_BLEND * h)
        u = (y - (HEAD_Y * h - HEAD_BLEND * h)) / blend
        return [("head", 1.0 - u), ("spine", u)]
    return [("spine", 1.0)]


class Skin:
    """整图网格 + 顶点权重。顶点变形 = Σ 权重 × 对应骨的世界变换。"""

    def __init__(self, w, h, grid=GRID):
        gx, gy = grid
        self.W, self.H = w, h
        self.gx, self.gy = gx, gy
        self.verts = []      # [[(x, y, [(bone, w)])]]
        for j in range(gy + 1):
            row = []
            for i in range(gx + 1):
                x, y = w * i / gx, h * j / gy
                row.append((x, y, vertex_weights(x, y, w, h)))
            self.verts.append(row)

    def deform(self, world: dict) -> list:
        rows = []
        for j in range(self.gy + 1):
            row = []
            for i in range(self.gx + 1):
                x, y, ws = self.verts[j][i]
                if len(ws) == 1 and abs(world[ws[0][0]][1]) < 1e-6:
                    row.append(QPointF(x, y))        # 单骨且没转，省掉计算
                    continue
                ax = ay = 0.0
                for bone, wgt in ws:
                    pivot, ang = world[bone]
                    q = _rot(QPointF(x, y), pivot, ang)
                    ax += q.x() * wgt
                    ay += q.y() * wgt
                # 吸附：位移小于 0.8px 就当作没动，否则全身处处重绘会出一层细横纹
                if abs(ax - x) + abs(ay - y) < 0.8:
                    row.append(QPointF(x, y))
                else:
                    row.append(QPointF(ax, ay))
            rows.append(row)
        return rows


class Clip:
    """一段骨骼动画：骨名 → 角度关键帧轨道。"""

    def __init__(self, name, duration, tracks, loop=True, events=()):
        self.name = name
        self.duration = float(duration)
        self.tracks = {k: anim.Track(v) for k, v in tracks.items()}
        self.loop = loop
        self.events = list(events)

    def pose(self, t: float) -> dict:
        t = max(0.0, min(t, self.duration))
        d = {k: tr.value(t) for k, tr in self.tracks.items()}
        # 脚部自动补偿：让鞋大致保持水平，不跟着小腿整只翻过去；限幅 ±25°
        for side in ("l", "r"):
            fk = f"foot_{side}"
            if fk not in self.tracks:
                comp = -0.6 * (d.get(f"thigh_{side}", 0.0) + d.get(f"shin_{side}", 0.0))
                d[fk] = max(-25.0, min(25.0, comp))
        return d

    def done(self, t: float) -> bool:
        return (not self.loop) and t >= self.duration - 1e-6


def _kf(*pairs):
    """(时间占比, 角度, 缓动) 序列 → 关键帧列表（时间按占比给，播放时乘时长）。"""
    out = []
    for p in pairs:
        t, v = p[0], p[1]
        e = p[2] if len(p) > 2 else "sine"
        out.append((t, v, e))
    return out


# 动作库（时间用占比，Clip 构造时换算成秒）
CLIP_DEFS = {
    "walk": dict(loop=True, dur=0.78, tracks={
        "thigh_l": _kf((0.0, 10), (0.5, -10), (1.0, 10)),
        "shin_l":  _kf((0.0, 0), (0.25, 22, "out"), (0.5, 0, "in"), (1.0, 0)),
        "thigh_r": _kf((0.0, -10), (0.5, 10), (1.0, -10)),
        "shin_r":  _kf((0.0, 0), (0.75, 22, "out"), (1.0, 0, "in")),
        "spine":   _kf((0.0, 2.8), (0.5, -2.8), (1.0, 2.8)),
        "head":    _kf((0.0, -1.8), (0.5, 1.8), (1.0, -1.8)),
    }),
    "run": dict(loop=True, dur=0.52, tracks={
        "thigh_l": _kf((0.0, 18), (0.5, -18), (1.0, 18)),
        "shin_l":  _kf((0.0, 4), (0.25, 40, "out"), (0.5, 6, "in"), (1.0, 4)),
        "thigh_r": _kf((0.0, -18), (0.5, 18), (1.0, -18)),
        "shin_r":  _kf((0.0, 4), (0.75, 40, "out"), (1.0, 4, "in")),
        "spine":   _kf((0.0, 6), (1.0, 6)),          # 前倾跑
        "head":    _kf((0.0, -4), (1.0, -4)),
    }),
    "hop": dict(loop=False, dur=2.04, events=((1.0, "land"),), tracks={
        # 蓄力下沉 → 起跳伸腿 → 滞空 → 落地缓冲
        "thigh_l": _kf((0.0, 0), (0.16, 24, "out"), (0.34, -16), (0.55, -6), (0.72, 22, "out"), (1.0, 0)),
        "shin_l":  _kf((0.0, 0), (0.16, 44, "out"), (0.34, 6), (0.72, 40, "out"), (1.0, 0)),
        "thigh_r": _kf((0.0, 0), (0.16, 22, "out"), (0.34, -14), (0.55, -4), (0.72, 20, "out"), (1.0, 0)),
        "shin_r":  _kf((0.0, 0), (0.16, 42, "out"), (0.34, 4), (0.72, 38, "out"), (1.0, 0)),
        "spine":   _kf((0.0, 0), (0.16, 5, "out"), (0.34, -4), (0.72, 4), (1.0, 0)),
        "head":    _kf((0.0, 0), (0.16, 4, "out"), (0.34, -3), (0.72, 3), (1.0, 0)),
    }),
    "tumble": dict(loop=False, dur=2.2, events=((1.35, "land"), (1.9, "recover")), tracks={
        "thigh_l": _kf((0.0, 0), (0.4, 26), (0.6, 8), (1.0, 0)),
        "shin_l":  _kf((0.0, 0), (0.4, 46), (0.6, 12), (1.0, 0)),
        "thigh_r": _kf((0.0, 0), (0.4, 10), (0.6, 2), (1.0, 0)),
        "shin_r":  _kf((0.0, 0), (0.4, 30), (0.6, 6), (1.0, 0)),
        "spine":   _kf((0.0, 0), (0.4, 12), (0.62, -8, "out"), (0.8, 2), (1.0, 0)),
        "head":    _kf((0.0, 0), (0.4, -8), (0.62, 6, "out"), (1.0, 0)),
    }),
    "breath": dict(loop=True, dur=3.6, tracks={
        "spine": _kf((0.0, 0), (0.5, 3.0), (1.0, 0)),
        "head":  _kf((0.0, 0), (0.5, -1.8), (1.0, 0)),
    }),
}


def _build_clip(name: str) -> Clip:
    d = CLIP_DEFS[name]
    dur = d["dur"]
    tracks = {}
    for bone, kfs in d["tracks"].items():
        tracks[bone] = [(t * dur, v, e) for (t, v, e) in kfs]
    events = [(t, n) for (t, n) in d.get("events", ())]
    return Clip(name, dur, tracks, loop=d["loop"], events=events)


CLIPS = {n: _build_clip(n) for n in CLIP_DEFS}


class Player:
    def __init__(self):
        self.clip = None
        self.t = 0.0
        self.playing = False
        self._events = []
        self._fired = set()

    def play(self, name):
        clip = CLIPS.get(name) if isinstance(name, str) else name
        if clip is None:
            return
        self.clip = clip
        self.t = 0.0
        self.playing = True
        self._events = []
        self._fired = set()

    def stop(self):
        self.clip = None
        self.playing = False
        self.t = 0.0
        self._events = []
        self._fired = set()

    def step(self, dt: float) -> dict:
        if not self.playing or self.clip is None:
            return {}
        self.t += dt
        if self.clip.loop:
            nt = self.t % self.clip.duration
            if nt < self.t:
                self._fired = set()
            self.t = nt
        else:
            self.t = min(self.t, self.clip.duration)
        for (et, name) in self.clip.events:
            if et <= self.t and (et, name) not in self._fired:
                self._fired.add((et, name))
                self._events.append((et, name))
        return self.clip.pose(self.t)

    def pop_events(self) -> list:
        out = self._events
        self._events = []
        return out

    def done(self) -> bool:
        return bool(self.clip) and self.clip.done(self.t)


class SkeletalSprite:
    """把一张立绘 + 骨架 + 蒙皮 + 动作库拼成"能出帧"的东西。"""

    def __init__(self, pix: QPixmap):
        self.pix = pix
        self.W, self.H = pix.width(), pix.height()
        self.skeleton = Skeleton(self.W, self.H)
        self.skin = Skin(self.W, self.H, GRID)
        self.player = Player()
        self._cells = []
        for j in range(self.skin.gy):
            y0, y1 = self.H * j / self.skin.gy, self.H * (j + 1) / self.skin.gy
            for i in range(self.skin.gx):
                x0, x1 = self.W * i / self.skin.gx, self.W * (i + 1) / self.skin.gx
                s00, s10 = QPointF(x0, y0), QPointF(x1, y0)
                s01, s11 = QPointF(x0, y1), QPointF(x1, y1)
                self._cells.append((j, i, s00, s10, s01, s11, QRectF(x0, y0, x1 - x0, y1 - y0)))
        self._cache_key = None
        self._cache = None

    def render(self, angles: dict) -> QPixmap:
        key = tuple(sorted((k, round(v, 2)) for k, v in angles.items() if abs(v) > 1e-6))
        if key == self._cache_key and self._cache is not None:
            return self._cache
        world = self.skeleton.solve(angles)
        gw = self.skin.deform(world)
        canvas = QPixmap(self.W, self.H)
        canvas.fill(Qt.transparent)
        p = QPainter(canvas)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        # 网格逐三角形绘制时若开抗锯齿，三角形外扩重叠处的半透明边缘会叠出一层细横纹；
        # 这里关掉 AA，靠 0.18px 外扩消缝，代价是极边缘有轻微锯齿。
        p.setRenderHint(QPainter.Antialiasing, False)
        for (j, i, s00, s10, s01, s11, rect) in self._cells:
            d00, d10 = gw[j][i], gw[j][i + 1]
            d01, d11 = gw[j + 1][i], gw[j + 1][i + 1]
            if d00 == s00 and d10 == s10 and d01 == s01 and d11 == s11:
                p.drawPixmap(rect, self.pix, rect)
                continue
            for sp, dp in (((s00, s10, s11), (d00, d10, d11)),
                           ((s00, s11, s01), (d00, d11, d01))):
                t = _affine_from_tri(*sp, *dp)
                if t is None:
                    continue
                cx = sum(q.x() for q in sp) / 3.0
                cy = sum(q.y() for q in sp) / 3.0
                grown = []
                for q in sp:
                    gx, gy = q.x() - cx, q.y() - cy
                    ln = math.hypot(gx, gy) or 1.0
                    grown.append(QPointF(q.x() + gx / ln * 0.18, q.y() + gy / ln * 0.18))
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

    # 便捷：直接播某个动作的某一时刻
    def frame_at(self, clip_name: str, t: float) -> QPixmap:
        clip = CLIPS[clip_name]
        return self.render(clip.pose(t))


