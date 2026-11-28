#!/usr/bin/env python3
"""Stage 3 asset cook: validate the model/card inputs and write content.json.

The cook is deliberately read-mostly:
- validates the VRM/GLB structure the renderer relies on;
- validates the 2D atlas against the manifest and source PNGs;
- copies only the runtime assets into build/content;
- writes a deterministic content.json with source and cooked hashes.

It does not replace the runtime loader or claim a custom content.bin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"Pillow is required for the atlas check: {exc}")

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "3d/assets/models/whale_girl.vrm"
MANIFEST = ROOT / "assets/2d_bridge/manifest.json"
ATLAS = ROOT / "assets/2d_bridge/atlas.png"
DEFAULT_OUT = ROOT / "build/content"
DEFAULT_REPORT = ROOT / "docs/asset-cook-report.json"
SCHEMA = "whale3d-content-v1"
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
SLOT = 160
EXPECTED_IDS = {
    "expression/idle", "expression/happy", "expression/eat", "expression/walk",
    "expression/sleep", "expression/sleepy", "expression/shy", "expression/angry",
    "expression/curious", "expression/pat",
    "action/wave", "action/dance", "action/type", "action/balloon",
    "action/fireworks", "action/lion", "action/change",
}
EXPECTED_BONES = {
    "hips", "spine", "chest", "neck", "head",
    "leftShoulder", "leftUpperArm", "leftLowerArm", "leftHand",
    "rightShoulder", "rightUpperArm", "rightLowerArm", "rightHand",
    "leftUpperLeg", "leftLowerLeg", "leftFoot",
    "rightUpperLeg", "rightLowerLeg", "rightFoot",
}
EXPECTED_SPRINGS = 4


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def label_path(path: Path) -> str:
    try:
        return rel(path)
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_glb(path: Path, errors: list[str]) -> tuple[dict, int]:
    data = path.read_bytes()
    if len(data) < 20:
        errors.append(f"model too small: {len(data)} bytes")
        return {}, 0
    magic, version, declared = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67:
        errors.append(f"bad glb magic: {magic:#x}")
    if version != 2:
        errors.append(f"bad glb version: {version}")
    if declared != len(data):
        errors.append(f"glb length {declared} != file {len(data)}")
    chunks: list[tuple[int, bytes]] = []
    offset = 12
    while offset < len(data):
        if offset + 8 > len(data):
            errors.append("truncated glb chunk header")
            break
        length, kind = struct.unpack_from("<II", data, offset)
        payload = data[offset + 8:offset + 8 + length]
        if len(payload) != length:
            errors.append("truncated glb chunk payload")
            break
        chunks.append((kind, payload))
        offset += 8 + length
    if offset != len(data):
        errors.append(f"glb chunk end {offset} != file {len(data)}")
    json_chunks = [payload for kind, payload in chunks if kind == JSON_CHUNK]
    bin_chunks = [payload for kind, payload in chunks if kind == BIN_CHUNK]
    if not json_chunks:
        errors.append("glb JSON chunk missing")
        return {}, len(bin_chunks[0]) if bin_chunks else 0
    try:
        gltf = json.loads(json_chunks[0].decode("utf-8"))
    except Exception as exc:
        errors.append(f"glb JSON decode failed: {exc}")
        return {}, len(bin_chunks[0]) if bin_chunks else 0
    return gltf, len(bin_chunks[0]) if bin_chunks else 0


def validate_accessor(gltf: dict, index: int, context: str, errors: list[str]) -> None:
    accessors = gltf.get("accessors", [])
    if not isinstance(index, int) or not (0 <= index < len(accessors)):
        errors.append(f"{context}: accessor {index!r} out of range")
        return
    accessor = accessors[index]
    if not isinstance(accessor, dict) or not isinstance(accessor.get("count"), int):
        errors.append(f"{context}: accessor {index} missing count")
        return
    if accessor["count"] <= 0:
        errors.append(f"{context}: accessor {index} count <= 0")
    view = accessor.get("bufferView")
    views = gltf.get("bufferViews", [])
    if isinstance(view, int) and not (0 <= view < len(views)):
        errors.append(f"{context}: bufferView {view} out of range")


def validate_model(path: Path, errors: list[str], warnings: list[str]) -> dict:
    gltf, bin_length = load_glb(path, errors)
    if not gltf:
        return {}
    nodes = gltf.get("nodes", [])
    meshes = gltf.get("meshes", [])
    skins = gltf.get("skins", [])
    animations = gltf.get("animations", [])
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes missing")
        nodes = []
    if not isinstance(meshes, list) or not meshes:
        errors.append("meshes missing")
    else:
        primitives = meshes[0].get("primitives", []) if isinstance(meshes[0], dict) else []
        if not primitives:
            errors.append("mesh primitives missing")
        for primitive_index, primitive in enumerate(primitives):
            attrs = primitive.get("attributes", {})
            for name in ("POSITION", "NORMAL", "TEXCOORD_0", "JOINTS_0", "WEIGHTS_0"):
                if name not in attrs:
                    errors.append(f"mesh primitive {primitive_index}: missing {name}")
                else:
                    validate_accessor(gltf, attrs[name], f"primitive {primitive_index} {name}", errors)
            if "indices" in primitive:
                validate_accessor(gltf, primitive["indices"],
                                  f"primitive {primitive_index} indices", errors)
            material = primitive.get("material")
            materials = gltf.get("materials", [])
            if not isinstance(material, int) or not (0 <= material < len(materials)):
                errors.append(f"mesh primitive {primitive_index}: material {material!r} out of range")
    materials = gltf.get("materials", [])
    if not isinstance(materials, list) or not materials:
        errors.append("materials missing")
        materials = []
    textures = gltf.get("textures", [])
    images = gltf.get("images", [])
    if not isinstance(textures, list) or not textures:
        errors.append("textures missing")
        textures = []
    if not isinstance(images, list) or not images:
        errors.append("images missing")
        images = []
    for material_index, material in enumerate(materials):
        if not isinstance(material, dict):
            errors.append(f"material {material_index}: not an object")
            continue
        pbr = material.get("pbrMetallicRoughness", {})
        texture_info = pbr.get("baseColorTexture") if isinstance(pbr, dict) else None
        if texture_info is None:
            warnings.append(f"material {material_index}: no baseColorTexture")
            continue
        texture_index = texture_info.get("index") if isinstance(texture_info, dict) else None
        if not isinstance(texture_index, int) or not (0 <= texture_index < len(textures)):
            errors.append(f"material {material_index}: texture index {texture_index!r} out of range")
    for texture_index, texture in enumerate(textures):
        source = texture.get("source") if isinstance(texture, dict) else None
        if not isinstance(source, int) or not (0 <= source < len(images)):
            errors.append(f"texture {texture_index}: image source {source!r} out of range")
    if not isinstance(skins, list) or not skins:
        errors.append("skins missing")
    else:
        joints = skins[0].get("joints", []) if isinstance(skins[0], dict) else []
        if len(joints) < len(EXPECTED_BONES):
            errors.append(f"skin joints {len(joints)} < {len(EXPECTED_BONES)}")
        for joint in joints:
            if not isinstance(joint, int) or not (0 <= joint < len(nodes)):
                errors.append(f"skin joint {joint!r} out of range")
    if not isinstance(animations, list) or not animations:
        errors.append("animations missing")
    else:
        for animation_index, animation in enumerate(animations):
            channels = animation.get("channels", []) if isinstance(animation, dict) else []
            if not channels:
                errors.append(f"animation {animation_index}: channels missing")
            for channel_index, channel in enumerate(channels):
                sampler_index = channel.get("sampler") if isinstance(channel, dict) else None
                samplers = animation.get("samplers", [])
                if not isinstance(sampler_index, int) or not (0 <= sampler_index < len(samplers)):
                    errors.append(f"animation {animation_index} channel {channel_index}: bad sampler")
                    continue
                sampler = samplers[sampler_index]
                validate_accessor(gltf, sampler.get("input"),
                                  f"animation {animation_index} sampler input", errors)
                validate_accessor(gltf, sampler.get("output"),
                                  f"animation {animation_index} sampler output", errors)

    humanoid = {}
    extensions = gltf.get("extensions", {})
    if isinstance(extensions, dict):
        humanoid = extensions.get("VRMC_vrm", {}).get("humanoid", {}).get("humanBones", {})
    if not isinstance(humanoid, dict) or not humanoid:
        errors.append("VRMC_vrm humanoid bones missing")
        humanoid = {}
    missing_bones = sorted(EXPECTED_BONES - set(humanoid))
    if missing_bones:
        errors.append(f"missing humanoid bones: {missing_bones}")
    for name, entry in humanoid.items():
        node = entry.get("node") if isinstance(entry, dict) else None
        if not isinstance(node, int) or not (0 <= node < len(nodes)):
            errors.append(f"humanoid {name}: node {node!r} out of range")

    springs = []
    springs_ext = extensions.get("VRMC_springBone", {}) if isinstance(extensions, dict) else {}
    if isinstance(springs_ext, dict):
        springs = springs_ext.get("springs", [])
    if not isinstance(springs, list) or len(springs) != EXPECTED_SPRINGS:
        errors.append(f"spring chains {len(springs) if isinstance(springs, list) else '?'} != {EXPECTED_SPRINGS}")
    else:
        for spring in springs:
            chain = spring.get("joints", []) if isinstance(spring, dict) else []
            if len(chain) < 2:
                errors.append(f"spring {spring.get('name')!r}: fewer than 2 joints")
            for joint in chain:
                if not isinstance(joint, int) or not (0 <= joint < len(nodes)):
                    errors.append(f"spring {spring.get('name')!r}: joint {joint!r} out of range")

    buffers = gltf.get("buffers", [])
    if isinstance(buffers, list) and buffers:
        declared_bin = buffers[0].get("byteLength") if isinstance(buffers[0], dict) else None
        if isinstance(declared_bin, int) and declared_bin > bin_length:
            errors.append(f"buffer byteLength {declared_bin} > BIN chunk {bin_length}")
    elif bin_length:
        warnings.append("buffer declaration missing despite BIN chunk")

    return {
        "glb_version": 2,
        "bytes": path.stat().st_size,
        "nodes": len(nodes),
        "meshes": len(meshes),
        "materials": len(materials),
        "textures": len(textures),
        "images": len(images),
        "skin_joints": len(skins[0].get("joints", [])) if isinstance(skins, list) and skins else 0,
        "humanoid_bones": len(humanoid),
        "springs": len(springs),
        "animations": [
            {"name": item.get("name"), "channels": len(item.get("channels", []))}
            for item in animations if isinstance(item, dict)
        ],
    }


def validate_cards(manifest_path: Path, atlas_path: Path,
                   errors: list[str], warnings: list[str]) -> dict:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"manifest read failed: {exc}")
        return {}
    atlas = Image.open(atlas_path).convert("RGBA")
    sheet_size = list(atlas.size)
    if sheet_size != [1024, 512]:
        errors.append(f"atlas size {sheet_size} != [1024, 512]")
    if manifest.get("version") != 1:
        errors.append(f"manifest version {manifest.get('version')!r} != 1")
    if manifest.get("sheet_size") != sheet_size:
        errors.append(f"manifest sheet_size {manifest.get('sheet_size')} != {sheet_size}")
    if manifest.get("slot_size") != SLOT:
        errors.append(f"slot_size {manifest.get('slot_size')} != {SLOT}")
    cards = manifest.get("cards", [])
    if not isinstance(cards, list):
        errors.append("cards missing")
        cards = []
    ids: list[str] = []
    rows = []
    for index, entry in enumerate(cards):
        prefix = f"cards[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix}: not an object")
            continue
        cid = entry.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append(f"{prefix}: missing id")
            cid = ""
        ids.append(cid)
        source = entry.get("source")
        rect = entry.get("rect")
        slot = entry.get("slot")
        if not isinstance(source, str) or not source:
            errors.append(f"{prefix}: missing source")
            source = ""
        elif not (ROOT / source).exists():
            errors.append(f"{prefix}: source missing {source}")
        if not (isinstance(rect, list) and len(rect) == 4
                and all(isinstance(value, int) for value in rect)):
            errors.append(f"{prefix}: rect must be four integers")
            rect = None
        if not (isinstance(slot, list) and len(slot) == 4
                and all(isinstance(value, int) for value in slot)):
            errors.append(f"{prefix}: slot must be four integers")
            slot = None
        if rect:
            x, y, w, h = rect
            if w <= 0 or h <= 0:
                errors.append(f"{prefix}: rect width/height must be positive")
            if x < 0 or y < 0 or x + w > sheet_size[0] or y + h > sheet_size[1]:
                errors.append(f"{prefix}: rect outside atlas {rect}")
            crop = atlas.crop((x, y, x + w, y + h))
            if crop.getchannel("A").getbbox() is None:
                errors.append(f"{prefix}: atlas card is fully transparent")
            if source and (ROOT / source).exists():
                source_image = Image.open(ROOT / source).convert("RGBA")
                bbox = source_image.getchannel("A").getbbox()
                if bbox is None:
                    errors.append(f"{prefix}: source card is fully transparent")
                else:
                    trimmed = source_image.crop(bbox).resize((w, h), Image.Resampling.LANCZOS)
                    alpha_bytes = (crop.getchannel("A").tobytes(),
                                   trimmed.getchannel("A").tobytes())
                    if len(alpha_bytes[0]) != len(alpha_bytes[1]):
                        errors.append(f"{prefix}: atlas/source alpha size mismatch")
                    else:
                        mae = sum(abs(a - b) for a, b in zip(*alpha_bytes)) / max(1, len(alpha_bytes[0]))
                        if mae > 4.0:
                            errors.append(f"{prefix}: atlas/source alpha MAE {mae:.3f} > 4.0")
        if slot:
            sx, sy, sw, sh = slot
            if sw != SLOT or sh != SLOT:
                errors.append(f"{prefix}: slot size {sw}x{sh} != {SLOT}")
            if sx < 0 or sy < 0 or sx + sw > sheet_size[0] or sy + sh > sheet_size[1]:
                errors.append(f"{prefix}: slot outside atlas {slot}")
            if rect and not (sx <= rect[0] and sy <= rect[1]
                             and rect[0] + rect[2] <= sx + sw
                             and rect[1] + rect[3] <= sy + sh):
                errors.append(f"{prefix}: rect outside its slot")
        rows.append({
            "id": cid,
            "group": entry.get("group"),
            "name": entry.get("name"),
            "source": source,
            "rect": rect,
            "slot": slot,
        })
    duplicate_ids = sorted({value for value in ids if ids.count(value) > 1 and value})
    if duplicate_ids:
        errors.append(f"duplicate ids: {duplicate_ids}")
    missing = sorted(EXPECTED_IDS - set(ids))
    extra = sorted(set(ids) - EXPECTED_IDS)
    if missing:
        errors.append(f"missing expected ids: {missing}")
    if extra:
        errors.append(f"unexpected ids: {extra}")
    if len(cards) != len(EXPECTED_IDS):
        errors.append(f"card count {len(cards)} != {len(EXPECTED_IDS)}")
    if len(ids) != len(set(ids)):
        warnings.append("ids are not unique")
    return {
        "manifest": label_path(manifest_path),
        "atlas": label_path(atlas_path),
        "sheet_size": sheet_size,
        "slot_size": SLOT,
        "count": len(cards),
        "ids": sorted(ids),
        "rows": rows,
    }


def copy_runtime_asset(source: Path, out_dir: Path) -> dict:
    target = out_dir / source.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return {
        "path": rel(target),
        "bytes": target.stat().st_size,
        "sha256": sha256(target),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=MODEL)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--atlas", type=Path, default=ATLAS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    model = args.model.resolve()
    manifest = args.manifest.resolve()
    atlas = args.atlas.resolve()
    out_dir = args.out.resolve()
    report_path = args.report.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for path, label in ((model, "model"), (manifest, "manifest"), (atlas, "atlas")):
        if not path.exists():
            errors.append(f"{label} missing: {path}")

    model_info = validate_model(model, errors, warnings) if model.exists() else {}
    card_info = validate_cards(manifest, atlas, errors, warnings) if manifest.exists() and atlas.exists() else {}

    sources = []
    if not errors:
        for path in [model, manifest, atlas] + [
            ROOT / row["source"] for row in card_info.get("rows", []) if row.get("source")
        ]:
            if path.exists():
                sources.append({
                    "path": rel(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                })

    cooked = []
    if not errors:
        out_dir.mkdir(parents=True, exist_ok=True)
        for path in (model, manifest, atlas):
            cooked.append(copy_runtime_asset(path, out_dir))
        content = {
            "schema": SCHEMA,
            "model": {
                "source": rel(model),
                "sha256": sha256(model),
                **model_info,
            },
            "cards": {
                "manifest": rel(manifest),
                "manifest_sha256": sha256(manifest),
                "atlas": rel(atlas),
                "atlas_sha256": sha256(atlas),
                "sheet_size": card_info["sheet_size"],
                "slot_size": card_info["slot_size"],
                "count": card_info["count"],
                "ids": card_info["ids"],
                "rows": card_info["rows"],
            },
            "sources": sources,
            "cooked": {
                "dir": rel(out_dir),
                "files": cooked,
            },
        }
        content_path = out_dir / "content.json"
        content_path.write_text(
            json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    report = {
        "schema": "whale3d-cook-report-v1",
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "model": model_info,
        "cards": {
            "count": card_info.get("count"),
            "ids": card_info.get("ids", []),
            "sheet_size": card_info.get("sheet_size"),
            "slot_size": card_info.get("slot_size"),
        },
        "sources": sources,
        "cooked": cooked,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"model={'ok' if model_info else 'fail'} cards={card_info.get('count', 0)} "
          f"errors={len(errors)} warnings={len(warnings)} ok={not errors}")
    for error in errors:
        print("ERROR:", error)
    for warning in warnings:
        print("WARN:", warning)
    print(f"report={report_path}")
    if not errors:
        print(f"content={out_dir / 'content.json'}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
