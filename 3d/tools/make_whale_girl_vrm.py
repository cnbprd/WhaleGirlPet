#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add a minimal VRM 1.0 humanoid + spring-bone declaration to the WhaleGirl
GLB. This keeps the existing mesh/skin/animation and makes the same file
loadable as a .vrm by the C++ runtime, which reads VRMC_springBone.

This is intentionally a small, auditable VRM subset: humanoid node mapping and
spring groups only. MToon materials, expressions and look-at are not declared.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "models" / "whale_girl.glb"
DST = ROOT / "assets" / "models" / "whale_girl.vrm"

HUMAN_BONES = {
    "hips": 1,
    "spine": 2,
    "chest": 3,
    "neck": 4,
    "head": 5,
    "leftShoulder": 6,
    "leftUpperArm": 7,
    "leftLowerArm": 8,
    "leftHand": 9,
    "rightShoulder": 10,
    "rightUpperArm": 11,
    "rightLowerArm": 12,
    "rightHand": 13,
    "leftUpperLeg": 14,
    "leftLowerLeg": 15,
    "leftFoot": 16,
    "rightUpperLeg": 17,
    "rightLowerLeg": 18,
    "rightFoot": 19,
}

SPRINGS = [
    # name, joints, stiffness, gravityPower, dragForce
    ("hair_side.L", [22, 23], 0.85, 0.12, 0.45),
    ("hair_side.R", [24, 25], 0.85, 0.12, 0.45),
    ("hair_back", [26, 27], 0.75, 0.10, 0.50),
    ("tail", [20, 21], 0.55, 0.00, 0.35),
]


def split_glb(data: bytes):
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2 or length != len(data):
        raise ValueError("not a GLB 2.0 file")
    chunks = []
    off = 12
    while off < length:
        clen, ctype = struct.unpack_from("<II", data, off)
        payload = data[off + 8 : off + 8 + clen]
        chunks.append((ctype, payload))
        off += 8 + clen
    json_chunk = next(p for ctype, p in chunks if ctype == 0x4E4F534A)
    bin_chunks = [p for ctype, p in chunks if ctype == 0x004E4942]
    return json.loads(json_chunk.decode("utf-8")), (bin_chunks[0] if bin_chunks else b"")


def build_vrm(gltf: dict, bin_data: bytes) -> bytes:
    gltf.setdefault("extensionsUsed", [])
    for ext in ("VRMC_vrm", "VRMC_springBone"):
        if ext not in gltf["extensionsUsed"]:
            gltf["extensionsUsed"].append(ext)

    exts = gltf.setdefault("extensions", {})
    exts["VRMC_vrm"] = {
        "specVersion": "1.0",
        "meta": {
            "name": "WhaleGirl",
            "version": "1.0",
            "authors": ["cnbprd"],
            "licenseUrl": "https://github.com/cnbprd/WhaleGirlPet/blob/main/LICENSE",
        },
        "humanoid": {
            "humanBones": {name: {"node": node} for name, node in HUMAN_BONES.items()}
        },
    }
    exts["VRMC_springBone"] = {
        "specVersion": "1.0",
        "colliders": [],
        "springs": [
            {
                "name": name,
                "joints": joints,
                "stiffness": stiffness,
                "gravityPower": gravity,
                "gravityDir": {"x": 0.0, "y": -1.0, "z": 0.0},
                "dragForce": drag,
                "hitRadius": 0.02,
            }
            for name, joints, stiffness, gravity, drag in SPRINGS
        ],
    }

    json_bytes = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    json_pad = (-len(json_bytes)) % 4
    json_bytes += b" " * json_pad
    bin_pad = (-len(bin_data)) % 4
    bin_bytes = bin_data + b"\x00" * bin_pad

    chunks = [(0x4E4F534A, json_bytes)]
    if bin_data:
        chunks.append((0x004E4942, bin_bytes))
    total = 12 + sum(8 + len(p) for _, p in chunks)
    out = bytearray(struct.pack("<III", 0x46546C67, 2, total))
    for ctype, payload in chunks:
        out += struct.pack("<II", len(payload), ctype)
        out += payload
    return bytes(out)


def main() -> int:
    if not SRC.exists():
        print("missing", SRC)
        return 1
    gltf, bin_data = split_glb(SRC.read_bytes())
    vrm = build_vrm(gltf, bin_data)
    DST.write_bytes(vrm)
    print(f"wrote {DST} ({len(vrm)} bytes)")
    print("springs:", ", ".join(s[0] for s in SPRINGS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
