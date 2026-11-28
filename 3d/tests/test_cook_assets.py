#!/usr/bin/env python3
"""Negative fixtures for 3d/tools/cook_assets.py.

Each fixture mutates a temporary copy; the real VRM/manifest/atlas is never
modified. Run locally or in a job that has Pillow installed.
"""
from __future__ import annotations

import copy
import json
import shutil
import struct
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
import cook_assets as cook  # noqa: E402

from PIL import Image  # noqa: E402

JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


def read_glb_chunks(path: Path) -> tuple[dict, bytes, list[tuple[int, bytes]]]:
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67 and version == 2 and length == len(data)
    chunks = []
    offset = 12
    while offset < len(data):
        size, kind = struct.unpack_from("<II", data, offset)
        payload = data[offset + 8:offset + 8 + size]
        chunks.append((kind, payload))
        offset += 8 + size
    gltf = json.loads(next(payload for kind, payload in chunks if kind == JSON_CHUNK))
    bin_payload = next((payload for kind, payload in chunks if kind == BIN_CHUNK), b"")
    return gltf, bin_payload, chunks


def write_glb(path: Path, gltf: dict, bin_payload: bytes) -> None:
    json_bytes = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    binary = bin_payload + b"\0" * ((4 - len(bin_payload) % 4) % 4)
    total = 12 + 8 + len(json_bytes) + (8 + len(binary) if binary else 0)
    with path.open("wb") as stream:
        stream.write(struct.pack("<III", 0x46546C67, 2, total))
        stream.write(struct.pack("<II", len(json_bytes), JSON_CHUNK))
        stream.write(json_bytes)
        if binary:
            stream.write(struct.pack("<II", len(binary), BIN_CHUNK))
            stream.write(binary)


def card_errors(manifest: dict, atlas: Path, tmp: Path) -> list[str]:
    path = tmp / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []
    cook.validate_cards(path, atlas, errors, warnings)
    return errors


def model_errors(model: Path, mutate) -> list[str]:
    gltf, binary, _ = read_glb_chunks(cook.MODEL)
    mutate(gltf)
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "bad.vrm"
        write_glb(target, gltf, binary)
        errors: list[str] = []
        warnings: list[str] = []
        cook.validate_model(target, errors, warnings)
        return errors


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp = Path(temp_dir)
        manifest = json.loads(cook.MANIFEST.read_text(encoding="utf-8"))
        atlas = cook.ATLAS
        if card_errors(manifest, atlas, tmp):
            failures.append("baseline manifest should pass")

        bad_rect = copy.deepcopy(manifest)
        bad_rect["cards"][0]["rect"] = [2000, 0, 10, 10]
        if not card_errors(bad_rect, atlas, tmp):
            failures.append("bad rect should fail")

        duplicate = copy.deepcopy(manifest)
        duplicate["cards"][1]["id"] = duplicate["cards"][0]["id"]
        if not card_errors(duplicate, atlas, tmp):
            failures.append("duplicate id should fail")

        missing = copy.deepcopy(manifest)
        missing["cards"][0]["source"] = "assets/expressions/not_here.png"
        if not card_errors(missing, atlas, tmp):
            failures.append("missing source should fail")

        bad_slot = copy.deepcopy(manifest)
        bad_slot["cards"][0]["slot"] = [0, 0, 80, 80]
        if not card_errors(bad_slot, atlas, tmp):
            failures.append("bad slot should fail")

        bad_atlas = tmp / "bad-atlas.png"
        Image.new("RGBA", (512, 256), (0, 0, 0, 0)).save(bad_atlas)
        if not card_errors(manifest, bad_atlas, tmp):
            failures.append("bad atlas size should fail")

        if model_errors(cook.MODEL, lambda gltf: gltf["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]["hips"].update(node=999)):
            pass
        else:
            failures.append("bad humanoid node should fail")

        def bad_accessor(gltf: dict) -> None:
            gltf["accessors"][0]["count"] = 0

        if not model_errors(cook.MODEL, bad_accessor):
            failures.append("bad accessor count should fail")

        def bad_spring(gltf: dict) -> None:
            gltf["extensions"]["VRMC_springBone"]["springs"][0]["joints"][0] = 999

        if not model_errors(cook.MODEL, bad_spring):
            failures.append("bad spring joint should fail")

    if failures:
        for failure in failures:
            print("FAIL", failure)
        return 1
    print("PASS baseline manifest")
    print("PASS bad rect rejected")
    print("PASS duplicate id rejected")
    print("PASS missing source rejected")
    print("PASS bad slot rejected")
    print("PASS bad atlas size rejected")
    print("PASS bad humanoid node rejected")
    print("PASS bad accessor rejected")
    print("PASS bad spring joint rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
