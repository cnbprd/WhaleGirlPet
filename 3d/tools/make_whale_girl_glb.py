#!/usr/bin/env python3
"""Generate a low-poly whale-girl v1 for the 3D desktop pet.

Design target: the existing JK skin -- blue gradient hair, white sailor top,
navy pleated skirt, white knee socks, black shoes, large whale tail.

The output deliberately stays inside the current C++ loader's limits:
one mesh, one skin, one material, one texture atlas, one animation.
"""

import json
import math
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "models" / "whale_girl.glb"
ATLAS = OUT.parent / "_whale_girl_atlas.png"

# ---------------------------------------------------------------- palette
def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


HAIR_DARK = rgb("#1b2b45")
HAIR_MID = rgb("#27577e")
HAIR_BLUE = rgb("#3f9fd0")
HAIR_LIGHT = rgb("#79d3e8")
SKIN = rgb("#f6c9a8")
SKIN_SHADOW = rgb("#e5ae8d")
SHIRT = rgb("#f4f1e9")
NAVY = rgb("#1d2a3d")
NAVY_LIGHT = rgb("#2a4059")
TEAL = rgb("#2e7180")
RED = rgb("#b53a46")
SOCK = rgb("#f7f5ef")
BLACK = rgb("#1c1b1d")
TAIL = rgb("#1d2d46")
TAIL_LIGHT = rgb("#345b78")
WHITE = (1.0, 1.0, 1.0)

# ---------------------------------------------------------------- texture atlas
# Three 512x256 face frames in a 2048x256 atlas (drawn at 512x512, then
# downsampled): open (neutral), blink, smile.  The last 512-wide slot stays
# pure white so vertex colors drive the body.  Face UVs only use the first
# 512 pixels.
W, H = 512, 512
img = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)

FACE = (246, 201, 168)
d.rectangle((0, 0, 511, 511), fill=FACE)

# Hair fringe across the top, with a few pointed strands.
d.polygon([(0, 0), (511, 0), (511, 58), (470, 78), (430, 62), (390, 84),
           (350, 66), (310, 88), (270, 66), (230, 90), (190, 68), (150, 84),
           (110, 64), (70, 80), (30, 62), (0, 78)], fill=(27, 43, 69))
for x, y, w, h in [(34, 20, 16, 110), (78, 10, 20, 95), (126, 14, 14, 100),
                   (360, 10, 18, 100), (410, 18, 12, 92), (458, 8, 20, 105)]:
    d.polygon([(x, y), (x + w, y), (x + w // 2, y + h)], fill=(39, 87, 126))

# Brows.
d.line((92, 132, 195, 126), fill=(52, 43, 52), width=11)
d.line((317, 126, 420, 132), fill=(52, 43, 52), width=11)

# Eye whites / outline. Narrower, half-lidded eyes to match the JK face.
for cx in (154, 358):
    d.ellipse((cx - 62, 168, cx + 62, 252), fill=(255, 255, 255),
              outline=(42, 33, 43), width=8)
    # Iris: crimson, nearly filling the eye height.
    d.ellipse((cx - 42, 178, cx + 42, 246), fill=(155, 48, 66),
              outline=(63, 28, 40), width=5)
    d.ellipse((cx - 37, 182, cx + 37, 242), fill=(196, 73, 86))
    d.ellipse((cx - 21, 194, cx + 21, 240), fill=(92, 26, 42))
    d.ellipse((cx - 9, 202, cx + 9, 238), fill=(35, 16, 25))
    # Highlights.
    d.ellipse((cx - 29, 184, cx - 3, 208), fill=(255, 255, 255))
    d.ellipse((cx + 10, 218, cx + 24, 232), fill=(255, 232, 236))
    # Lower-iris warm reflection.
    d.arc((cx - 32, 214, cx + 32, 244), 18, 162, fill=(224, 130, 136), width=4)

# Upper lashes and eyelid line.
d.arc((84, 152, 224, 238), 195, 345, fill=(35, 28, 37), width=15)
d.arc((288, 152, 428, 238), 195, 345, fill=(35, 28, 37), width=15)
d.line((92, 176, 216, 176), fill=(58, 45, 56), width=8)
d.line((296, 176, 420, 176), fill=(58, 45, 56), width=8)
# Lower lash hint.
d.arc((116, 238, 192, 274), 20, 150, fill=(118, 63, 70), width=4)
d.arc((320, 238, 396, 274), 20, 150, fill=(118, 63, 70), width=4)

# Small nose and a calm half-smile.
d.arc((240, 292, 268, 318), 20, 160, fill=(211, 149, 126), width=4)
d.arc((208, 346, 304, 394), 15, 165, fill=(150, 66, 84), width=9)
d.line((258, 386, 286, 386), fill=(196, 150, 144), width=4)

# Blush.
blush = Image.new("RGBA", (W, H), (0, 0, 0, 0))
bd = ImageDraw.Draw(blush)
bd.ellipse((34, 300, 120, 354), fill=(245, 142, 148, 105))
bd.ellipse((392, 300, 478, 354), fill=(245, 142, 148, 105))
blush = blush.filter(ImageFilter.GaussianBlur(10))
img = Image.alpha_composite(img.convert("RGBA"), blush).convert("RGB")
d = ImageDraw.Draw(img)

# Subtle fringe highlights / the white headpiece hint at the top.
d.line((184, 54, 208, 118), fill=(121, 211, 232), width=5)
d.line((330, 48, 308, 114), fill=(121, 211, 232), width=5)

# ---------------------------------------------------------------- face frames
# The base face is the neutral open-eye frame.  Blink and smile are derived
# from it so hair fringe, skin tone and blush stay pixel-identical.
face_open = img.copy()

face_blink = img.copy()
bd = ImageDraw.Draw(face_blink)
for cx in (154, 358):
    # Cover the open eye with skin, then draw a closed lash curve.
    bd.ellipse((cx - 72, 150, cx + 72, 272), fill=FACE)
    bd.arc((cx - 62, 188, cx + 62, 238), 200, 340, fill=(35, 28, 37), width=10)
    bd.arc((cx - 52, 222, cx + 52, 254), 20, 160, fill=(118, 63, 70), width=4)
    bd.line((cx - 64, 204, cx - 76, 194), fill=(35, 28, 37), width=5)
    bd.line((cx + 64, 204, cx + 76, 194), fill=(35, 28, 37), width=5)

face_smile = img.copy()
sd = ImageDraw.Draw(face_smile)
# Happy closed eyes: cover the open eyes, then draw upward arcs.  This reads
# as a different expression at pet scale instead of only widening the mouth.
for cx in (154, 358):
    sd.ellipse((cx - 72, 150, cx + 72, 272), fill=FACE)
    sd.arc((cx - 54, 190, cx + 54, 236), 200, 340, fill=(35, 28, 37), width=11)
# Open crescent smile: a dark mouth with the skin ellipse trimming the top
# edge into a smile curve; no teeth, so it stays soft at pet scale.
sd.ellipse((186, 326, 326, 412), fill=FACE)
sd.ellipse((214, 346, 298, 398), fill=(112, 41, 58))
sd.ellipse((214, 334, 298, 378), fill=FACE)
sd.ellipse((234, 386, 278, 399), fill=(208, 108, 120))
sd.arc((204, 386, 308, 414), 20, 160, fill=(196, 150, 144), width=3)

ATLAS_IMG = Image.new("RGB", (2048, 256), (255, 255, 255))
# 512x256 per frame keeps the atlas at the same 2 MB as the old 1024x512
# texture while still giving the pet-scale face more than 2x texture density.
ATLAS_IMG.paste(face_open.resize((512, 256), Image.LANCZOS), (0, 0))
ATLAS_IMG.paste(face_blink.resize((512, 256), Image.LANCZOS), (512, 0))
ATLAS_IMG.paste(face_smile.resize((512, 256), Image.LANCZOS), (1024, 0))
ATLAS_IMG.save(ATLAS)
atlas_bytes = ATLAS.read_bytes()

# ---------------------------------------------------------------- skeleton
# (index, name, parent, world bind position)
JOINTS = [
    (0, "root", None, (0.0, 0.0, 0.0)),
    (1, "hips", 0, (0.0, 0.76, 0.0)),
    (2, "spine", 1, (0.0, 0.92, 0.0)),
    (3, "chest", 2, (0.0, 1.04, 0.0)),
    (4, "neck", 3, (0.0, 1.16, 0.0)),
    (5, "head", 4, (0.0, 1.28, 0.0)),
    (6, "shoulder.L", 3, (-0.18, 1.10, 0.0)),
    (7, "upper_arm.L", 6, (-0.20, 1.10, 0.0)),
    (8, "lower_arm.L", 7, (-0.26, 0.92, 0.0)),
    (9, "hand.L", 8, (-0.28, 0.78, 0.0)),
    (10, "shoulder.R", 3, (0.18, 1.10, 0.0)),
    (11, "upper_arm.R", 10, (0.20, 1.10, 0.0)),
    (12, "lower_arm.R", 11, (0.26, 0.92, 0.0)),
    (13, "hand.R", 12, (0.28, 0.78, 0.0)),
    (14, "thigh.L", 1, (-0.10, 0.74, 0.0)),
    (15, "shin.L", 14, (-0.10, 0.42, 0.0)),
    (16, "foot.L", 15, (-0.10, 0.12, 0.0)),
    (17, "thigh.R", 1, (0.10, 0.74, 0.0)),
    (18, "shin.R", 17, (0.10, 0.42, 0.0)),
    (19, "foot.R", 18, (0.10, 0.12, 0.0)),
    (20, "tail", 1, (0.06, 0.76, -0.14)),
    (21, "tail_tip", 20, (0.22, 0.48, -0.32)),
    (22, "hair_side.L", 5, (-0.17, 1.43, -0.04)),
    (23, "hair_side_end.L", 22, (-0.27, 1.14, -0.06)),
    (24, "hair_side.R", 5, (0.17, 1.43, -0.04)),
    (25, "hair_side_end.R", 24, (0.27, 1.14, -0.06)),
    (26, "hair_back", 5, (0.0, 1.42, -0.12)),
    (27, "hair_back_end", 26, (0.0, 1.02, -0.20)),
]
JOINT_COUNT = len(JOINTS)
MESH_NODE = JOINT_COUNT

verts = []
indices = []


def add_vertex(p, n, uv, color, joint):
    verts.append({
        "p": p, "n": n, "uv": uv,
        "c": (color[0], color[1], color[2], 1.0),
        "j": joint, "w": 1.0,
    })


def add_quad(ps, ns, uvs, color, joint):
    base = len(verts)
    for p, n, uv in zip(ps, ns, uvs):
        add_vertex(p, n, uv, color, joint)
    indices.extend([base, base + 1, base + 2, base, base + 2, base + 3])


def add_tri(ps, ns, uvs, color, joint):
    base = len(verts)
    for p, n, uv in zip(ps, ns, uvs):
        add_vertex(p, n, uv, color, joint)
    indices.extend([base, base + 1, base + 2])


def vadd(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def vsub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def vmul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def vlen(a): return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
def vnorm(a):
    l = vlen(a)
    return (a[0] / l, a[1] / l, a[2] / l) if l > 1e-9 else (0.0, 1.0, 0.0)
def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])

WHITE_UV = (0.875, 0.5)


def add_box(x0, x1, y0, y1, z0, z1, color, joint):
    xa, xb, ya, yb, za, zb = x0, x1, y0, y1, z0, z1
    faces = [
        ([(xa, yb, zb), (xa, ya, zb), (xb, ya, zb), (xb, yb, zb)], (0, 0, 1)),
        ([(xb, yb, za), (xb, ya, za), (xa, ya, za), (xa, yb, za)], (0, 0, -1)),
        ([(xb, yb, zb), (xb, ya, zb), (xb, ya, za), (xb, yb, za)], (1, 0, 0)),
        ([(xa, yb, za), (xa, ya, za), (xa, ya, zb), (xa, yb, zb)], (-1, 0, 0)),
        ([(xa, yb, za), (xb, yb, za), (xb, yb, zb), (xa, yb, zb)], (0, 1, 0)),
        ([(xa, ya, zb), (xb, ya, zb), (xb, ya, za), (xa, ya, za)], (0, -1, 0)),
    ]
    for ps, n in faces:
        add_quad(ps, [n, n, n, n], [WHITE_UV] * 4, color, joint)


def add_tube(p0, p1, r0, r1, sides, color, joint, cap=False, color_alt=None):
    axis = vnorm(vsub(p1, p0))
    ref = (0, 1, 0) if abs(axis[1]) < 0.9 else (0, 0, 1)
    u = vnorm(cross(ref, axis))
    v = cross(axis, u)
    ring0, ring1 = [], []
    for k in range(sides):
        a = 2.0 * math.pi * k / sides
        dirv = vadd(vmul(u, math.cos(a)), vmul(v, math.sin(a)))
        ring0.append((vadd(p0, vmul(dirv, r0)), dirv))
        ring1.append((vadd(p1, vmul(dirv, r1)), dirv))
    for k in range(sides):
        k2 = (k + 1) % sides
        p00, n00 = ring0[k]
        p01, n01 = ring1[k]
        p11, n11 = ring1[k2]
        p10, n10 = ring0[k2]
        col = color_alt if (color_alt is not None and k % 2) else color
        add_quad([p00, p01, p11, p10], [n00, n01, n11, n10], [WHITE_UV] * 4, col, joint)
    if cap:
        for k in range(sides):
            k2 = (k + 1) % sides
            add_tri([p0, ring0[k2][0], ring0[k][0]],
                    [vmul(axis, -1.0)] * 3, [WHITE_UV] * 3, color, joint)
            add_tri([p1, ring1[k][0], ring1[k2][0]],
                    [axis] * 3, [WHITE_UV] * 3, color, joint)


def add_ellipsoid(c, r, seg, rings, color, joint, theta_max=math.pi, uv=WHITE_UV):
    rows = []
    for i in range(rings + 1):
        theta = theta_max * i / rings
        row = []
        for j in range(seg):
            phi = 2.0 * math.pi * j / seg
            x = math.sin(theta) * math.cos(phi)
            y = math.cos(theta)
            z = math.sin(theta) * math.sin(phi)
            p = (c[0] + r[0] * x, c[1] + r[1] * y, c[2] + r[2] * z)
            n = vnorm((x / r[0], y / r[1], z / r[2]))
            row.append((p, n))
        rows.append(row)

    # Top cap.
    ptop = rows[0][0][0]
    ntop = rows[0][0][1]
    for j in range(seg):
        j2 = (j + 1) % seg
        add_tri([ptop, rows[1][j][0], rows[1][j2][0]],
                [ntop, rows[1][j][1], rows[1][j2][1]],
                [uv] * 3, color, joint)

    # Middle quads.
    for i in range(1, rings):
        for j in range(seg):
            j2 = (j + 1) % seg
            a, b = rows[i][j], rows[i][j2]
            cc, dd = rows[i + 1][j2], rows[i + 1][j]
            add_quad([a[0], b[0], cc[0], dd[0]],
                     [a[1], b[1], cc[1], dd[1]],
                     [uv] * 4, color, joint)

    # Bottom cap only for a full sphere.
    if theta_max >= math.pi - 1e-4:
        pbot = (c[0], c[1] - r[1], c[2])
        nbot = (0.0, -1.0, 0.0)
        last = rings - 1
        for j in range(seg):
            j2 = (j + 1) % seg
            add_tri([pbot, rows[last][j2][0], rows[last][j][0]],
                    [nbot, rows[last][j2][1], rows[last][j][1]],
                    [uv] * 3, color, joint)


def add_face_patch(c, r, halfx, halfy, grid, joint):
    # 512 px face inside a 2048 px atlas; frame 0 starts at x=4.
    u0, u1 = 0.002, 0.248
    v0, v1 = 0.002, 0.998
    for i in range(grid):
        for j in range(grid):
            ps, ns, uvs = [], [], []
            for ii, jj in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                fx = (-1.0 + 2.0 * jj / grid) * halfx
                fy = (1.0 - 2.0 * ii / grid) * halfy
                fx = max(-r[0] * 0.98, min(r[0] * 0.98, fx))
                fy = max(-r[1] * 0.98, min(r[1] * 0.98, fy))
                zz = math.sqrt(max(0.0, 1.0 - (fx / r[0]) ** 2 - (fy / r[1]) ** 2))
                p = (c[0] + fx, c[1] + fy, c[2] + r[2] * zz + 0.0035)
                n = vnorm((fx / (r[0] * r[0]), fy / (r[1] * r[1]),
                           r[2] * zz / (r[2] * r[2])))
                uv = (u0 + (u1 - u0) * jj / grid, v0 + (v1 - v0) * ii / grid)
                ps.append(p); ns.append(n); uvs.append(uv)
            add_quad(ps, ns, uvs, WHITE, joint)


def add_fin(poly_xz, y0, y1, color, joint, top_color=None):
    """A thin horizontal fin; poly_xz is a convex loop in the XZ plane."""
    top = top_color or color
    cx = sum(p[0] for p in poly_xz) / len(poly_xz)
    cz = sum(p[1] for p in poly_xz) / len(poly_xz)
    ctop = (cx, y1, cz)
    cbot = (cx, y0, cz)
    n = len(poly_xz)
    for i in range(n):
        a = poly_xz[i]; b = poly_xz[(i + 1) % n]
        # top fan (normal +Y)
        add_tri([ctop, (a[0], y1, a[1]), (b[0], y1, b[1])],
                [(0, 1, 0)] * 3, [WHITE_UV] * 3, top, joint)
        # bottom fan (normal -Y), reversed winding
        add_tri([cbot, (b[0], y0, b[1]), (a[0], y0, a[1])],
                [(0, -1, 0)] * 3, [WHITE_UV] * 3, color, joint)
        # side wall
        edge = vsub((b[0], 0, b[1]), (a[0], 0, a[1]))
        out = vnorm((edge[2], 0.0, -edge[0]))
        add_quad([(a[0], y0, a[1]), (b[0], y0, b[1]),
                  (b[0], y1, b[1]), (a[0], y1, a[1])],
                 [out] * 4, [WHITE_UV] * 4, color, joint)


def add_fin_xy(poly_xy, z0, z1, color, joint, front_color=None):
    """A thin vertical fin; poly_xy is a convex loop in the XY plane."""
    front = front_color or color
    cx = sum(p[0] for p in poly_xy) / len(poly_xy)
    cy = sum(p[1] for p in poly_xy) / len(poly_xy)
    cfront = (cx, cy, z1)
    cback = (cx, cy, z0)
    n = len(poly_xy)
    for i in range(n):
        a = poly_xy[i]; b = poly_xy[(i + 1) % n]
        add_tri([cfront, (a[0], a[1], z1), (b[0], b[1], z1)],
                [(0, 0, 1)] * 3, [WHITE_UV] * 3, front, joint)
        add_tri([cback, (b[0], b[1], z0), (a[0], a[1], z0)],
                [(0, 0, -1)] * 3, [WHITE_UV] * 3, color, joint)
        edge = vsub((b[0], b[1], 0), (a[0], a[1], 0))
        out = vnorm((edge[1], -edge[0], 0.0))
        add_quad([(a[0], a[1], z0), (b[0], b[1], z0),
                  (b[0], b[1], z1), (a[0], a[1], z1)],
                 [out] * 4, [WHITE_UV] * 4, color, joint)


def add_fluke(poly_xy, z0, z1, color, joint, front_color=None):
    """A thicker, potentially concave vertical fluke, fan-triangulated."""
    front = front_color or color
    cx = sum(p[0] for p in poly_xy) / len(poly_xy)
    cy = sum(p[1] for p in poly_xy) / len(poly_xy)
    n = len(poly_xy)
    for i in range(n):
        a = poly_xy[i]; b = poly_xy[(i + 1) % n]
        # front / back surfaces
        add_tri([(cx, cy, z1), (a[0], a[1], z1), (b[0], b[1], z1)],
                [(0, 0, 1)] * 3, [WHITE_UV] * 3, front, joint)
        add_tri([(cx, cy, z0), (b[0], b[1], z0), (a[0], a[1], z0)],
                [(0, 0, -1)] * 3, [WHITE_UV] * 3, color, joint)
        # side walls
        edge = vsub((b[0], b[1], 0), (a[0], a[1], 0))
        out = vnorm((edge[1], -edge[0], 0.0))
        add_quad([(a[0], a[1], z0), (b[0], b[1], z0),
                  (b[0], b[1], z1), (a[0], a[1], z1)],
                 [out] * 4, [WHITE_UV] * 4, color, joint)


# Head center / radii.
HEAD_C = (0.0, 1.36, 0.0)
HEAD_R = (0.185, 0.195, 0.175)

# ---------------------------------------------------------------- body
# Neck.
add_tube((0, 1.16, 0), (0, 1.27, 0), 0.052, 0.048, 8, SKIN, 4, cap=False)

# Head.
add_ellipsoid(HEAD_C, HEAD_R, 20, 12, SKIN, 5)

# Face decal patch, curved onto the front of the head.
add_face_patch(HEAD_C, HEAD_R, 0.147, 0.137, 8, 5)

# Hair: back mass, cap, side locks, twin side locks, and top bow.
add_ellipsoid((0.0, 1.27, -0.105), (0.215, 0.295, 0.095), 16, 10, HAIR_DARK, 5)
add_ellipsoid((0.0, 1.40, -0.015), (0.203, 0.205, 0.185), 16, 7, HAIR_DARK, 5,
              theta_max=1.85)

# Long back hair strands: dark roots -> blue tips.
BACK_STRANDS = [
    ((-0.13, 1.43, -0.12), (-0.16, 1.18, -0.18), (-0.20, 0.92, -0.16), -1),
    ((-0.05, 1.43, -0.14), (-0.06, 1.14, -0.20), (-0.08, 0.86, -0.17), -1),
    ((0.05, 1.43, -0.14), (0.06, 1.14, -0.20), (0.08, 0.86, -0.17), 1),
    ((0.13, 1.43, -0.12), (0.16, 1.18, -0.18), (0.20, 0.92, -0.16), 1),
    ((-0.09, 1.42, -0.08), (-0.12, 1.10, -0.14), (-0.15, 0.78, -0.12), -1),
    ((0.09, 1.42, -0.08), (0.12, 1.10, -0.14), (0.15, 0.78, -0.12), 1),
]
for a, b, c, side in BACK_STRANDS:
    add_tube(a, b, 0.050, 0.042, 6, HAIR_DARK, 26, cap=False)
    add_tube(b, c, 0.042, 0.016, 6, HAIR_BLUE if side < 0 else HAIR_LIGHT, 27, cap=False)

# Side locks framing the face.
for side, sx in ((-1, -1), (1, 1)):
    base = (0.198 * sx, 1.39, -0.095)
    mid = (0.258 * sx, 1.19, -0.120)
    tip = (0.300 * sx, 0.98, -0.100)
    joint = 22 if sx < 0 else 24
    end_joint = 23 if sx < 0 else 25
    add_tube(base, mid, 0.050, 0.042, 7, HAIR_DARK, joint, cap=False)
    add_tube(mid, tip, 0.042, 0.014, 7, HAIR_BLUE, end_joint, cap=False)

# Short front bangs as flat panels over the forehead.
add_quad([(-0.10, 1.545, 0.162), (-0.12, 1.425, 0.185),
          (0.10, 1.425, 0.185), (0.12, 1.545, 0.162)],
         [(0, 0.55, 1)] * 4, [WHITE_UV] * 4, HAIR_DARK, 5)
add_quad([(-0.175, 1.535, 0.105), (-0.175, 1.395, 0.135),
          (-0.035, 1.425, 0.178), (-0.020, 1.545, 0.150)],
         [(0, 0.55, 1)] * 4, [WHITE_UV] * 4, HAIR_MID, 5)
add_quad([(0.175, 1.535, 0.105), (0.175, 1.395, 0.135),
          (0.035, 1.425, 0.178), (0.020, 1.545, 0.150)],
         [(0, 0.55, 1)] * 4, [WHITE_UV] * 4, HAIR_MID, 5)

# White headband strip + blue top bow.
add_box(-0.165, 0.165, 1.505, 1.535, 0.075, 0.145, SHIRT, 5)
add_tri([(-0.165, 1.535, 0.145), (-0.10, 1.585, 0.09), (-0.045, 1.535, 0.145)],
        [(0, 0.5, 1)] * 3, [WHITE_UV] * 3, SHIRT, 5)
add_tri([(0.165, 1.535, 0.145), (0.10, 1.585, 0.09), (0.045, 1.535, 0.145)],
        [(0, 0.5, 1)] * 3, [WHITE_UV] * 3, SHIRT, 5)
add_tri([(-0.10, 1.545, -0.145), (0.0, 1.50, -0.19), (0.0, 1.57, -0.13)],
        [(0, 0, -1)] * 3, [WHITE_UV] * 3, HAIR_BLUE, 5)
add_tri([(0.10, 1.545, -0.145), (0.0, 1.50, -0.19), (0.0, 1.57, -0.13)],
        [(0, 0, -1)] * 3, [WHITE_UV] * 3, HAIR_LIGHT, 5)

# Torso: white sailor blouse.
add_tube((0, 0.79, 0), (0, 1.12, 0), 0.165, 0.190, 14, SHIRT, 2, cap=False)
# Waistband.
add_tube((0, 0.78, 0), (0, 0.815, 0), 0.175, 0.180, 16, NAVY, 1, cap=False)

# Sailor collar: navy ring + front V panels with white trim.
add_tube((0, 1.075, 0), (0, 1.115, 0), 0.195, 0.205, 18, NAVY, 3, cap=False)
add_tri([(0.0, 1.12, 0.192), (-0.19, 1.095, 0.150), (0.0, 1.005, 0.218)],
        [(0, 0, 1)] * 3, [WHITE_UV] * 3, NAVY, 3)
add_tri([(0.0, 1.12, 0.192), (0.19, 1.095, 0.150), (0.0, 1.005, 0.218)],
        [(0, 0, 1)] * 3, [WHITE_UV] * 3, NAVY, 3)
# White collar edging.
add_tri([(-0.185, 1.093, 0.153), (0.0, 1.116, 0.195), (-0.16, 1.075, 0.163)],
        [(0, 0, 1)] * 3, [WHITE_UV] * 3, SHIRT, 3)
add_tri([(0.185, 1.093, 0.153), (0.0, 1.116, 0.195), (0.16, 1.075, 0.163)],
        [(0, 0, 1)] * 3, [WHITE_UV] * 3, SHIRT, 3)

# Navy chest bow.
add_tri([(-0.045, 1.055, 0.224), (-0.13, 1.085, 0.205), (-0.12, 1.015, 0.214)],
        [(0, 0, 1)] * 3, [WHITE_UV] * 3, NAVY, 3)
add_tri([(0.045, 1.055, 0.224), (0.13, 1.085, 0.205), (0.12, 1.015, 0.214)],
        [(0, 0, 1)] * 3, [WHITE_UV] * 3, NAVY, 3)
add_box(-0.035, 0.035, 1.025, 1.075, 0.218, 0.242, NAVY_LIGHT, 3)

# Pleated skirt.
add_tube((0, 0.805, 0), (0, 0.625, 0), 0.185, 0.285, 18, NAVY, 1,
         cap=False, color_alt=NAVY_LIGHT)
# Skirt hem light edge.
add_tube((0, 0.625, 0), (0, 0.615, 0), 0.285, 0.292, 18, TEAL, 1, cap=False)

# Arms: short white sleeves, skin forearms, small hands.
for sx in (-1, 1):
    p0 = (0.195 * sx, 1.10, 0.0)
    p1 = (0.26 * sx, 0.965, 0.0)
    p2 = (0.278 * sx, 0.80, 0.0)
    hand = (0.286 * sx, 0.765, 0.015)
    upper_joint = 7 if sx < 0 else 11
    lower_joint = 8 if sx < 0 else 12
    hand_joint = 9 if sx < 0 else 13
    add_tube(p0, p1, 0.060, 0.050, 10, SHIRT, upper_joint, cap=False)
    add_tube(p1, p2, 0.042, 0.034, 10, SKIN, lower_joint, cap=False)
    add_ellipsoid(hand, (0.043, 0.052, 0.040), 8, 6, SKIN, hand_joint)

# Legs: skin thighs, white knee socks, black shoes.
for sx in (-1, 1):
    thigh_joint = 14 if sx < 0 else 17
    shin_joint = 15 if sx < 0 else 18
    foot_joint = 16 if sx < 0 else 19
    add_tube((0.10 * sx, 0.74, 0.0), (0.10 * sx, 0.42, 0.0),
             0.070, 0.055, 10, SKIN, thigh_joint, cap=False)
    add_tube((0.10 * sx, 0.43, 0.0), (0.10 * sx, 0.09, 0.0),
             0.057, 0.043, 10, SOCK, shin_joint, cap=False)
    # Sock band.
    add_tube((0.10 * sx, 0.43, 0.0), (0.10 * sx, 0.405, 0.0),
             0.058, 0.058, 10, SHIRT, shin_joint, cap=False)
    add_box(0.10 * sx - 0.055, 0.10 * sx + 0.055, 0.0, 0.085,
            -0.115, 0.075, BLACK, foot_joint)

# Whale tail: offset to the right, dark navy with a lighter inner fin.
add_tube((0.06, 0.78, -0.13), (0.24, 0.50, -0.31), 0.095, 0.045, 10,
         TAIL, 20, cap=False)
add_tube((0.24, 0.50, -0.31), (0.30, 0.43, -0.33), 0.045, 0.025, 8,
         TAIL, 21, cap=False)
# Fluke: one large whale-tail silhouette, readable from the front.
FLUKE = [
    (0.04, 0.43), (0.18, 0.52), (0.30, 0.45), (0.43, 0.52),
    (0.57, 0.43), (0.47, 0.34), (0.30, 0.29), (0.14, 0.34),
]
add_fluke(FLUKE, -0.35, -0.27, TAIL, 21, front_color=TAIL)
# A lighter inner patch, slightly in front, to catch the eye.
add_fluke([(0.14, 0.42), (0.26, 0.47), (0.29, 0.37), (0.20, 0.34)],
          -0.368, -0.36, TAIL_LIGHT, 21)
add_fluke([(0.31, 0.47), (0.45, 0.42), (0.41, 0.36), (0.30, 0.37)],
          -0.368, -0.36, TAIL_LIGHT, 21)

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
    channel(5, (0, 1, 0), 0.10),                    # head yaw
    channel(3, (1, 0, 0), 0.025),                   # chest breathe
    channel(7, (1, 0, 0), 0.11),                    # left upper arm
    channel(11, (1, 0, 0), -0.11),                  # right upper arm
    channel(8, (1, 0, 0), 0.05),                    # left forearm
    channel(12, (1, 0, 0), -0.05),                  # right forearm
    channel(14, (1, 0, 0), 0.045),                  # left thigh
    channel(17, (1, 0, 0), -0.045),                 # right thigh
    channel(22, (0, 1, 1), 0.10, 0.6),              # left side hair
    channel(24, (0, 1, 1), -0.10, 0.6),             # right side hair
    channel(23, (0, 1, 1), 0.13, 1.2),              # left hair tip
    channel(25, (0, 1, 1), -0.13, 1.2),             # right hair tip
    channel(20, (0, 1, 0), 0.16, 2.0),              # tail sway
    channel(21, (0, 1, 0), 0.12, 2.4),              # tail tip
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
    acc = {"bufferView": view, "componentType": component_type,
           "count": count, "type": type_}
    if minmax:
        acc["min"], acc["max"] = minmax
    accessors.append(acc)
    return len(accessors) - 1


positions = [c for v in verts for c in v["p"]]
normals = [c for v in verts for c in v["n"]]
uvs = [c for v in verts for c in v["uv"]]
colors = [c for v in verts for c in v["c"]]
joints, weights = [], []
for v in verts:
    joints.extend([v["j"], 0, 0, 0])
    weights.extend([v["w"], 0.0, 0.0, 0.0])

pos_min = [min(positions[i::3]) for i in range(3)]
pos_max = [max(positions[i::3]) for i in range(3)]

pos_acc = add_accessor(struct.pack("<%df" % len(positions), *positions),
                       5126, len(verts), "VEC3", 34962, (pos_min, pos_max))
nrm_acc = add_accessor(struct.pack("<%df" % len(normals), *normals),
                       5126, len(verts), "VEC3", 34962)
uv_acc = add_accessor(struct.pack("<%df" % len(uvs), *uvs),
                      5126, len(verts), "VEC2", 34962)
col_acc = add_accessor(struct.pack("<%df" % len(colors), *colors),
                       5126, len(verts), "VEC4", 34962)
jnt_acc = add_accessor(struct.pack("<%dB" % len(joints), *joints),
                       5121, len(verts), "VEC4", 34962)
wgt_acc = add_accessor(struct.pack("<%df" % len(weights), *weights),
                       5126, len(verts), "VEC4", 34962)
idx_acc = add_accessor(struct.pack("<%dH" % len(indices), *indices),
                       5123, len(indices), "SCALAR", 34963)

# Inverse bind matrices, pure translation bind pose.
ibms = []
for _, _, _, world in JOINTS:
    ibms.extend([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0,
                 -world[0], -world[1], -world[2], 1])
ibm_acc = add_accessor(struct.pack("<%df" % len(ibms), *ibms),
                       5126, JOINT_COUNT, "MAT4")

time_acc = add_accessor(struct.pack("<%df" % len(TIMES), *TIMES),
                        5126, len(TIMES), "SCALAR")

output_accessors = []
for _, quats in CHANNELS:
    vals = [c for q in quats for c in q]
    output_accessors.append(add_accessor(
        struct.pack("<%df" % len(vals), *vals), 5126, len(quats), "VEC4"))

# Embedded PNG atlas: image bufferView is a raw chunk, not an accessor.
image_view = add_view(atlas_bytes)

# ---------------------------------------------------------------- JSON
nodes = []
world_of = {}
for idx, name, parent, world in JOINTS:
    world_of[idx] = world
    local = world if parent is None else vsub(world, world_of[parent])
    node = {"name": name, "translation": list(local),
            "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]}
    nodes.append(node)
nodes.append({"name": "whale_girl_mesh", "mesh": 0, "skin": 0})
for idx, name, parent, world in JOINTS:
    if parent is not None:
        nodes[parent].setdefault("children", []).append(idx)

gltf = {
    "asset": {"version": "2.0", "generator": "WhaleGirl low-poly v1 generator"},
    "scene": 0,
    "scenes": [{"name": "Scene", "nodes": [0, MESH_NODE]}],
    "nodes": nodes,
    "meshes": [{
        "name": "WhaleGirlBody",
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
        "name": "WhaleGirlRig",
        "inverseBindMatrices": ibm_acc,
        "skeleton": 0,
        "joints": list(range(JOINT_COUNT)),
    }],
    "materials": [{
        "name": "WhaleGirlAtlas",
        "pbrMetallicRoughness": {
            "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
            "baseColorTexture": {"index": 0},
            "metallicFactor": 0.0,
            "roughnessFactor": 0.9,
        },
        "doubleSided": True,
    }],
    "textures": [{"sampler": 0, "source": 0}],
    "samplers": [{"magFilter": 9729, "minFilter": 9987,
                  "wrapS": 33071, "wrapT": 33071}],
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
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(glb)

print(f"Wrote {OUT} ({len(glb)} bytes)")
print(f"  vertices={len(verts)} indices={len(indices)} triangles={len(indices)//3}")
print(f"  joints={JOINT_COUNT} channels={len(CHANNELS)}")
print(f"  atlas {ATLAS} ({len(atlas_bytes)} bytes)")
