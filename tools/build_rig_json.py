# -*- coding: utf-8 -*-
"""B 路线第 2 步（本项目自写，不依赖 Stretchy）：由 layers.json 生成 Spine 兼容 rig JSON。

default 的骨骼树：
  root(髋) → spine(腰) → head(颈/头) → hair_l / hair_r
  root → tail
  root → skirt

输出：assets/skins/rig/default_rig.json
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYERS = os.path.join(ROOT, "assets", "skins", "layers")
OUT = os.path.join(ROOT, "assets", "skins", "rig")

W, H = 267.0, 512.0
PIVOTS = {
    "root": (0.500, 0.586),
    "spine": (0.500, 0.430),
    "head": (0.500, 0.240),
    "hair_l": (0.140, 0.230),
    "hair_r": (0.780, 0.230),
    "tail": (0.630, 0.550),
    "skirt": (0.500, 0.430),
}
PARENTS = {
    "root": None,
    "spine": "root",
    "head": "spine",
    "hair_l": "head",
    "hair_r": "head",
    "tail": "root",
    "skirt": "root",
}
SLOTS = (
    ("body", "root", "body"),
    ("hair_l", "hair_l", "hair_l"),
    ("hair_r", "hair_r", "hair_r"),
    ("tail", "tail", "tail"),
    ("skirt", "skirt", "skirt"),
)


def bone_json(name):
    x, y = PIVOTS[name][0] * W, PIVOTS[name][1] * H
    parent = PARENTS[name]
    if parent:
        px, py = PIVOTS[parent][0] * W, PIVOTS[parent][1] * H
        x, y = x - px, y - py
    return {
        "name": name,
        "parent": parent,
        "x": round(x, 3),
        "y": round(y, 3),
        "rotation": 0.0,
        "scaleX": 1.0,
        "scaleY": 1.0,
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    meta = json.load(open(os.path.join(LAYERS, "layers.json"), encoding="utf-8"))
    skin = meta["skins"]["default"]
    w, h = W, H
    attachments = {}
    for slot, _bone, key in SLOTS:
        file_key = "base" if key == "body" else key
        file_name = skin.get(file_key)
        if not file_name:
            raise SystemExit("missing layer: " + file_key)
        attachments[slot] = {
            key: {
                "type": "region",
                "path": "../layers/" + file_name,
                "x": 0.0,
                "y": 0.0,
                "width": w,
                "height": h,
            }
        }
    data = {
        "format": "whale-rig/1",
        "spine": "4.0.0",
        "skeleton": {"width": w, "height": h, "x": 0, "y": 0},
        "meta": {"generator": "tools/build_rig_json.py", "skin": "default",
                 "note": "Spine-compatible data only; rendered by app/rig_runtime.py"},
        "bones": [bone_json(n) for n in PARENTS],
        "slots": [
            {"name": slot, "bone": bone, "attachment": key, "z": i}
            for i, (slot, bone, key) in enumerate(SLOTS)
        ],
        "skins": [{"name": "default", "attachments": attachments}],
        "animations": {},
    }
    path = os.path.join(OUT, "default_rig.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("saved", path, "bones", len(data["bones"]), "slots", len(data["slots"]))


if __name__ == "__main__":
    main()
