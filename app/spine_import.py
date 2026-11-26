# -*- coding: utf-8 -*-
"""Spine 4.0 JSON 迁移层：只取数据，不引入 Spine Runtime。

本次是 B 路线的第 2→3 步：把「分层资产 + 骨骼树 + slot 顺序」写成
Spine 兼容 JSON，再由本项目自己的解析器读成 RigModel。后续 skeletal.py
的多部件渲染直接消费这个模型，不依赖 spine_json_lib / spine_asset。

支持：
- bones[]：name / parent / x / y / rotation / scaleX / scaleY
- slots[]：name / bone / attachment，数组顺序即 draw order
- skins[].attachments：region 附件（path / x / y / width / height）
- 先兼容 region；mesh 附件保留 raw，后续权重解码再用
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field


@dataclass
class Bone:
    name: str
    parent: str | None
    x: float
    y: float
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0


@dataclass
class Slot:
    name: str
    bone: str
    attachment: str
    order: int


@dataclass
class Region:
    path: str
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    kind: str = "region"
    raw: dict = field(default_factory=dict)


@dataclass
class RigModel:
    width: float
    height: float
    spine: str
    fmt: str
    base_dir: str
    bones: list[Bone]
    slots: list[Slot]
    attachments: dict[str, dict[str, Region]]

    def bone_map(self) -> dict[str, Bone]:
        return {b.name: b for b in self.bones}

    def region_for(self, slot: Slot) -> Region | None:
        by_slot = self.attachments.get(slot.name) or {}
        if slot.attachment in by_slot:
            return by_slot[slot.attachment]
        return next(iter(by_slot.values()), None)

    def path_for(self, slot: Slot) -> str:
        r = self.region_for(slot)
        if r is None:
            return ""
        return os.path.normpath(os.path.join(self.base_dir, r.path))

    def world(self, angles: dict[str, float] | None = None) -> dict[str, tuple[float, float, float]]:
        """返回 {骨名: (世界枢轴x, 世界枢轴y, 世界角度)}。

        角度单位是度；局部 x/y 相对父骨枢轴；root 的 x/y 是画布绝对坐标。
        """
        angles = angles or {}
        bm = self.bone_map()
        out: dict[str, tuple[float, float, float]] = {}
        visiting = set()

        def solve(name: str) -> tuple[float, float, float]:
            if name in out:
                return out[name]
            if name in visiting:
                raise ValueError("bone cycle: " + name)
            b = bm.get(name)
            if b is None:
                raise ValueError("missing bone: " + name)
            visiting.add(name)
            own = float(b.rotation) + float(angles.get(name, 0.0))
            if b.parent:
                px, py, pa = solve(b.parent)
                dx = math.cos(math.radians(pa)) * b.x - math.sin(math.radians(pa)) * b.y
                dy = math.sin(math.radians(pa)) * b.x + math.cos(math.radians(pa)) * b.y
                pos = (px + dx, py + dy, pa + own)
            else:
                pos = (float(b.x), float(b.y), own)
            visiting.discard(name)
            out[name] = pos
            return pos

        for b in self.bones:
            solve(b.name)
        return out


def load_rig(path: str) -> RigModel:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    sk = data.get("skeleton") or {}
    width = float(sk.get("width", data.get("width", 0)) or 0)
    height = float(sk.get("height", data.get("height", 0)) or 0)
    spine = str(data.get("spine", sk.get("spine", "4.0.0")))
    fmt = str(data.get("format", sk.get("format", "")))

    bones = []
    for raw in data.get("bones") or []:
        bones.append(Bone(
            name=str(raw.get("name", "")),
            parent=raw.get("parent"),
            x=float(raw.get("x", 0.0)),
            y=float(raw.get("y", 0.0)),
            rotation=float(raw.get("rotation", 0.0)),
            scale_x=float(raw.get("scaleX", raw.get("scale_x", 1.0))),
            scale_y=float(raw.get("scaleY", raw.get("scale_y", 1.0))),
        ))
    if not bones:
        raise ValueError("no bones")

    slots = []
    for i, raw in enumerate(data.get("slots") or []):
        name = str(raw.get("name", ""))
        if not name:
            raise ValueError("slot without name")
        slots.append(Slot(name=name, bone=str(raw.get("bone", "")),
                          attachment=str(raw.get("attachment", "")), order=i))

    skins = data.get("skins") or []
    if isinstance(skins, dict):
        skin = skins
    else:
        skin = skins[0] if skins else {}
    attachments_raw = skin.get("attachments") or {}
    attachments: dict[str, dict[str, Region]] = {}
    for slot_name, names in attachments_raw.items():
        if not isinstance(names, dict):
            continue
        by_name = {}
        for att_name, raw in names.items():
            if not isinstance(raw, dict):
                continue
            by_name[str(att_name)] = Region(
                path=str(raw.get("path", "")),
                x=float(raw.get("x", 0.0)),
                y=float(raw.get("y", 0.0)),
                width=float(raw.get("width", 0.0)),
                height=float(raw.get("height", 0.0)),
                kind=str(raw.get("type", "region")),
                raw=raw,
            )
        attachments[str(slot_name)] = by_name

    model = RigModel(width=width, height=height, spine=spine, fmt=fmt,
                     base_dir=os.path.dirname(os.path.abspath(path)),
                     bones=bones, slots=slots, attachments=attachments)
    # 提前跑一次，父骨缺失/环会在这里暴露
    model.world({})
    return model
