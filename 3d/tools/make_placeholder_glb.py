#!/usr/bin/env python3
"""Generate a low-poly, skinned glTF placeholder for the 3D desktop pet.

It is deliberately dependency-light: one mesh, one texture atlas, 13 joints,
one idle animation.  The result is a .glb that the C++ loader can consume
without any engine or VRM runtime.
"""

import json
import math
import struct
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "models" / "placeholder.glb"

# ---------------------------------------------------------------- texture atlas
img = Image.new("RGBA", (128, 128), (255, 255, 255, 255))
d = ImageDraw.Draw(img)

# Left half: face for the +Z side of the head.
d.rectangle((0, 0, 63, 127), fill=(255, 219, 202, 255))
d.rectangle((0, 0, 63, 20), fill=(242, 143, 166, 255))       # fringe
d.ellipse((13, 31, 25, 45), fill=(38, 28, 34, 255))          # left eye
d.ellipse((38, 31, 50, 45), fill=(38, 28, 34, 255))          # right eye
d.ellipse((17, 34, 21, 38), fill=(255, 255, 255, 255))       # highlights
d.ellipse((42, 34, 46, 38), fill=(255, 255, 255, 255))
d.arc((24, 48, 40, 62), 0, 180, fill=(176, 78, 98, 255))     # mouth
d.ellipse((7, 47, 16, 55), fill=(255, 166, 166, 255))        # blush
d.ellipse((47, 47, 56, 55), fill=(255, 166, 166, 255))

# Right half: neutral, slightly checkered base for vertex-color tinting.
d.rectangle((64, 0, 127, 127), fill=(242, 242, 242, 255))
for y in range(0, 128, 16):
    d.line((64, y, 127, y), fill=(226, 226, 226, 255))
for x in range(64, 128, 16):
    d.line((x, 0, x, 127), fill=(226, 226, 226, 255))

atlas_png = OUT.parent / "_placeholder_atlas.png"
OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(atlas_png)
atlas_bytes = atlas_png.read_bytes()

# ---------------------------------------------------------------- skeleton
# Index, name, parent, local translation (relative to parent), world bind pos.
JOINTS = [
    (0, "root", None, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
    (1, "hips", 0, (0.0, 0.95, 0.0), (0.0, 0.95, 0.0)),
    (2, "spine", 1, (0.0, 0.30, 0.0), (0.0, 1.25, 0.0)),
    (3, "head", 2, (0.0, 0.40, 0.0), (0.0, 1.65, 0.0)),
    (4, "upper_arm.L", 2, (-0.32, 0.17, 0.0), (-0.32, 1.42, 0.0)),
    (5, "lower_arm.L", 4, (0.0, -0.30, 0.0), (-0.32, 1.12, 0.0)),
    (6, "upper_arm.R", 2, (0.32, 0.17, 0.0), (0.32, 1.42, 0.0)),
    (7, "lower_arm.R", 6, (0.0, -0.30, 0.0), (0.32, 1.12, 0.0)),
    (8, "thigh.L", 1, (-0.12, -0.05, 0.0), (-0.12, 0.90, 0.0)),
    (9, "shin.L", 8, (0.0, -0.42, 0.0), (-0.12, 0.48, 0.0)),
    (10, "thigh.R", 1, (0.12, -0.05, 0.0), (0.12, 0.90, 0.0)),
    (11, "shin.R", 10, (0.0, -0.42, 0.0), (0.12, 0.48, 0.0)),
    (12, "tail", 1, (0.0, -0.15, -0.16), (0.0, 0.80, -0.16)),
]
JOINT_COUNT = len(JOINTS)
MESH_NODE = JOINT_COUNT  # 13

verts = []
indices = []


def add_box(name, x0, x1, y0, y1, z0, z1, color, joint, face_front=False):
    """Append one box as 6 quads; returns nothing."""
    xa, xb = x0, x1
    ya, yb = y0, y1
    za, zb = z0, z1

    faces = [
        # +Z front: top-left, bottom-left, bottom-right, top-right
        ([(xa, yb, zb), (xa, ya, zb), (xb, ya, zb), (xb, yb, zb)], (0, 0, 1), face_front),
        # -Z back
        ([(xb, yb, za), (xb, ya, za), (xa, ya, za), (xa, yb, za)], (0, 0, -1), False),
        # +X
        ([(xb, yb, zb), (xb, ya, zb), (xb, ya, za), (xb, yb, za)], (1, 0, 0), False),
        # -X
        ([(xa, yb, za), (xa, ya, za), (xa, ya, zb), (xa, yb, zb)], (-1, 0, 0), False),
        # +Y
        ([(xa, yb, za), (xb, yb, za), (xb, yb, zb), (xa, yb, zb)], (0, 1, 0), False),
        # -Y
        ([(xa, ya, zb), (xb, ya, zb), (xb, ya, za), (xa, ya, za)], (0, -1, 0), False),
    ]

    for corners, normal, textured in faces:
        base = len(verts)
        if textured:
            uvs = [(0.0, 0.0), (0.0, 1.0), (0.5, 1.0), (0.5, 0.0)]
        else:
            uvs = [(0.5, 0.0), (0.5, 1.0), (1.0, 1.0), (1.0, 0.0)]
        for p, uv in zip(corners, uvs):
            verts.append({
                "p": p,
                "n": normal,
                "uv": uv,
                "c": (color[0], color[1], color[2], 1.0),
                "j": joint,
                "w": 1.0,
            })
        indices.extend([base, base + 1, base + 2, base, base + 2, base + 3])


TEAL = (0.30, 0.72, 0.78)
DARK_TEAL = (0.16, 0.40, 0.46)
SKIN = (1.0, 0.82, 0.72)
PINK = (0.92, 0.44, 0.56)

add_box("torso", -0.26, 0.26, 0.98, 1.48, -0.16, 0.16, TEAL, 2)
add_box("pelvis", -0.22, 0.22, 0.78, 1.00, -0.15, 0.15, DARK_TEAL, 1)
add_box("head", -0.18, 0.18, 1.58, 1.94, -0.18, 0.18, SKIN, 3, face_front=True)
add_box("hair_top", -0.20, 0.20, 1.88, 2.04, -0.18, 0.18, PINK, 3)
add_box("hair_back", -0.22, 0.22, 1.62, 2.02, -0.24, -0.10, PINK, 3)

add_box("upper_arm.L", -0.38, -0.26, 1.14, 1.44, -0.08, 0.08, TEAL, 4)
add_box("lower_arm.L", -0.36, -0.28, 0.84, 1.14, -0.07, 0.07, SKIN, 5)
add_box("upper_arm.R", 0.26, 0.38, 1.14, 1.44, -0.08, 0.08, TEAL, 6)
add_box("lower_arm.R", 0.28, 0.36, 0.84, 1.14, -0.07, 0.07, SKIN, 7)

add_box("thigh.L", -0.18, -0.06, 0.50, 0.92, -0.10, 0.10, DARK_TEAL, 8)
add_box("shin.L", -0.16, -0.08, 0.04, 0.50, -0.09, 0.09, TEAL, 9)
add_box("foot.L", -0.17, -0.07, 0.0, 0.08, -0.18, 0.10, DARK_TEAL, 9)
add_box("thigh.R", 0.06, 0.18, 0.50, 0.92, -0.10, 0.10, DARK_TEAL, 10)
add_box("shin.R", 0.08, 0.16, 0.04, 0.50, -0.09, 0.09, TEAL, 11)
add_box("foot.R", 0.07, 0.17, 0.0, 0.08, -0.18, 0.10, DARK_TEAL, 11)

add_box("tail", -0.14, 0.14, 0.70, 0.92, -0.42, -0.16, PINK, 12)
add_box("tail_fin.L", -0.30, -0.10, 0.68, 0.84, -0.52, -0.30, PINK, 12)
add_box("tail_fin.R", 0.10, 0.30, 0.68, 0.84, -0.52, -0.30, PINK, 12)

# ---------------------------------------------------------------- animation
TIMES = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]


def quat_axis(axis, angle):
    s = math.sin(angle * 0.5)
    return [axis[0] * s, axis[1] * s, axis[2] * s, math.cos(angle * 0.5)]


def channel(node, axis, amp, phase=0.0, freq=1.0):
    out = []
    for t in TIMES:
        angle = amp * math.sin(2.0 * math.pi * freq * t / 4.0 + phase)
        out.append(quat_axis(axis, angle))
    return node, out


CHANNELS = [
    channel(3, (0, 1, 0), 0.12),                    # head yaw
    channel(2, (1, 0, 0), 0.04),                    # spine breathe
    channel(4, (1, 0, 0), 0.28),                    # left arm swing
    channel(6, (1, 0, 0), -0.28),                   # right arm swing
    channel(8, (1, 0, 0), 0.12),                    # left leg
    channel(10, (1, 0, 0), -0.12),                  # right leg
    channel(12, (0, 1, 0), 0.22, math.pi / 2.0),    # tail sway
]

# ---------------------------------------------------------------- GLB packing
bin_data = bytearray()
buffer_views = []
accessors = []


def align4():
    while len(bin_data) % 4:
        bin_data.append(0)


def add_view(data, target=None):
    align4()
    offset = len(bin_data)
    bin_data.extend(data)
    view = {"buffer": 0, "byteOffset": offset, "byteLength": len(data)}
    if target is not None:
        view["target"] = target
    buffer_views.append(view)
    return len(buffer_views) - 1


def add_accessor(data, component_type, count, type_, target=None, minmax=None):
    view = add_view(data, target)
    acc = {
        "bufferView": view,
        "componentType": component_type,
        "count": count,
        "type": type_,
    }
    if minmax:
        acc["min"], acc["max"] = minmax
    accessors.append(acc)
    return len(accessors) - 1


# Vertex attributes.
positions = [c for v in verts for c in v["p"]]
normals = [c for v in verts for c in v["n"]]
uvs = [c for v in verts for c in v["uv"]]
colors = [c for v in verts for c in v["c"]]
joints = []
weights = []
for v in verts:
    joints.extend([v["j"], 0, 0, 0])
    weights.extend([v["w"], 0.0, 0.0, 0.0])

pos_min = [min(positions[i::3]) for i in range(3)]
pos_max = [max(positions[i::3]) for i in range(3)]

pos_acc = add_accessor(
    struct.pack("<%df" % len(positions), *positions), 5126, len(verts), "VEC3",
    34962, (pos_min, pos_max))
nrm_acc = add_accessor(
    struct.pack("<%df" % len(normals), *normals), 5126, len(verts), "VEC3", 34962)
uv_acc = add_accessor(
    struct.pack("<%df" % len(uvs), *uvs), 5126, len(verts), "VEC2", 34962)
col_acc = add_accessor(
    struct.pack("<%df" % len(colors), *colors), 5126, len(verts), "VEC4", 34962)
jnt_acc = add_accessor(
    struct.pack("<%dB" % len(joints), *joints), 5121, len(verts), "VEC4", 34962)
wgt_acc = add_accessor(
    struct.pack("<%df" % len(weights), *weights), 5126, len(verts), "VEC4", 34962)
idx_acc = add_accessor(
    struct.pack("<%dH" % len(indices), *indices), 5123, len(indices), "SCALAR", 34963)

# Inverse bind matrices. Bones are pure translations in bind pose.
ibms = []
for _, _, _, _, world in JOINTS:
    ibms.extend([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -world[0], -world[1], -world[2], 1])
ibm_acc = add_accessor(
    struct.pack("<%df" % len(ibms), *ibms), 5126, JOINT_COUNT, "MAT4")

# Animation input shared by every channel.
time_acc = add_accessor(
    struct.pack("<%df" % len(TIMES), *TIMES), 5126, len(TIMES), "SCALAR")

output_accessors = []
for _, quats in CHANNELS:
    vals = [c for q in quats for c in q]
    output_accessors.append(add_accessor(
        struct.pack("<%df" % len(vals), *vals), 5126, len(quats), "VEC4"))

# Embedded PNG atlas.
img_acc = add_accessor(atlas_bytes, 0, 0, "", None)
# Images are not accessors in glTF; keep the bufferView, drop the bogus accessor.
image_view = len(buffer_views) - 1
accessors.pop()

# ---------------------------------------------------------------- JSON
nodes = []
for idx, name, parent, trans, world in JOINTS:
    node = {"name": name, "translation": list(trans), "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]}
    nodes.append(node)
# Mesh node, identity.
nodes.append({"name": "placeholder_mesh", "mesh": 0, "skin": 0})
# Parent/children wiring.
for idx, name, parent, trans, world in JOINTS:
    if parent is not None:
        nodes[parent].setdefault("children", []).append(idx)

gltf = {
    "asset": {"version": "2.0", "generator": "WhaleGirl placeholder generator"},
    "scene": 0,
    "scenes": [{"name": "Scene", "nodes": [0, MESH_NODE]}],
    "nodes": nodes,
    "meshes": [{
        "name": "PlaceholderBody",
        "primitives": [{
            "attributes": {
                "POSITION": pos_acc,
                "NORMAL": nrm_acc,
                "TEXCOORD_0": uv_acc,
                "COLOR_0": col_acc,
                "JOINTS_0": jnt_acc,
                "WEIGHTS_0": wgt_acc,
            },
            "indices": idx_acc,
            "material": 0,
            "mode": 4,
        }],
    }],
    "skins": [{
        "name": "Rig",
        "inverseBindMatrices": ibm_acc,
        "skeleton": 0,
        "joints": list(range(JOINT_COUNT)),
    }],
    "materials": [{
        "name": "PlaceholderAtlas",
        "pbrMetallicRoughness": {
            "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
            "baseColorTexture": {"index": 0},
            "metallicFactor": 0.0,
            "roughnessFactor": 0.85,
        },
        "doubleSided": True,
    }],
    "textures": [{"sampler": 0, "source": 0}],
    "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}],
    "images": [{"name": "atlas", "bufferView": image_view, "mimeType": "image/png"}],
    "animations": [{
        "name": "Idle",
        "samplers": [{"input": time_acc, "output": out, "interpolation": "LINEAR"}
                    for out in output_accessors],
        "channels": [{"sampler": i, "target": {"node": node, "path": "rotation"}}
                     for i, (node, _) in enumerate(CHANNELS)],
    }],
    "accessors": accessors,
    "bufferViews": buffer_views,
    "buffers": [{"byteLength": 0}],
}

# Final buffer length with padding.
align4()
gltf["buffers"][0]["byteLength"] = len(bin_data)

json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
while len(json_bytes) % 4:
    json_bytes += b" "
bin_bytes = bytes(bin_data)
while len(bin_bytes) % 4:
    bin_bytes += b"\x00"

total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
glb = bytearray()
glb += struct.pack("<III", 0x46546C67, 2, total)
glb += struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
glb += struct.pack("<II", len(bin_bytes), 0x004E4942) + bin_bytes
OUT.write_bytes(glb)

print(f"Wrote {OUT} ({len(glb)} bytes)")
print(f"  vertices={len(verts)} indices={len(indices)} triangles={len(indices)//3}")
print(f"  joints={JOINT_COUNT} animations={len(CHANNELS)}")
