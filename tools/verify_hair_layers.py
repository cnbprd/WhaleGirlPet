# -*- coding: utf-8 -*-
"""发束 A 案验收：default 四层（裙摆/尾巴/左右发束）+ 4° 限幅 + 绘制顺序。

运行：.venv\\Scripts\\python.exe tools\\verify_hair_layers.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PIL import Image, ImageChops, ImageDraw, ImageFont  # noqa: E402
from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtGui import QImage, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import secondary as sm  # noqa: E402
from paths import asset_path  # noqa: E402

R = []


def ck(name, cond, extra=""):
    R.append((name, bool(cond)))
    print(("  ok   " if cond else "  FAIL ") + name + ("  " + str(extra) if extra else ""))


def rest_composition():
    src = Image.open(os.path.join(ROOT, "assets", "skins", "default.png")).convert("RGBA")
    base = Image.open(os.path.join(ROOT, "assets", "skins", "layers",
                                   "default_base.png")).convert("RGBA")
    rest = base.copy()
    for name in ("default_skirt.png", "default_tail.png",
                 "default_hair_l.png", "default_hair_r.png"):
        rest.alpha_composite(Image.open(os.path.join(ROOT, "assets", "skins", "layers",
                                                      name)).convert("RGBA"))
    diff = ImageChops.difference(rest, src)
    mean = sum(diff.convert("L").getdata()) / (src.width * src.height)
    ck("四层静止位重组原图", mean < 0.5, "mean_abs=%.4f bbox=%s" % (mean, diff.getbbox()))


def layer_checks():
    sec = sm.SecondaryMotion(1.0)
    ok = sec.set_skin("default", False)
    ck("default 四层加载", ok and set(sec.pix) == {"tail", "skirt", "hair_l", "hair_r"},
       list(sec.pix))
    ck("发束枢轴来自 layers.json",
       sec.specs["hair_l"].pivot == (0.14, 0.23)
       and sec.specs["hair_r"].pivot == (0.78, 0.23),
       (sec.specs["hair_l"].pivot, sec.specs["hair_r"].pivot))
    sec2 = sm.SecondaryMotion(1.0)
    ok2 = sec2.set_skin("default", True)
    ck("2x 发束层加载", ok2 and "hair_l" in sec2.pix
       and sec2.pix["hair_l"].width() == 534,
       sec2.pix["hair_l"].size() if "hair_l" in sec2.pix else None)
    own = sm.SecondaryMotion(1.0)
    own.set_skin("default", False)
    for _ in range(30):
        own.step(0.033, 80.0, 0.0, "idle", 0.0)
    vals = own.angles()
    ck("横向拖拽驱动发束", abs(vals["hair_l"]) > 0.5 and abs(vals["hair_r"]) > 0.5, vals)
    ck("发束角度不超 4°", all(abs(vals[k]) <= 4.0 for k in ("hair_l", "hair_r")), vals)
    ck("裙摆/尾巴仍在限幅内",
       all(abs(vals[k]) <= 15.0 for k in ("tail", "skirt")), vals)


def render(angle):
    orig = QPixmap(asset_path("skins/default.png"))
    w, h = orig.width(), orig.height()
    sec = sm.SecondaryMotion(1.0)
    sec.set_skin("default", False)
    for spring in sec.springs.values():
        spring.angle = float(angle)
        spring.vel = 0.0
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.translate(w // 2, h)
    p.drawPixmap(QRect(-w // 2, -h, w, h), orig)
    sec.paint(p, w, h)
    p.end()
    return img


def preview():
    app = QApplication.instance() or QApplication(sys.argv)
    frames = []
    for angle in (-4.0, 0.0, 4.0):
        im = render(angle)
        path = os.path.join(ROOT, "docs", "_hair_runtime_%+.0f.png" % angle)
        im.save(path)
        pil = Image.open(path).convert("RGBA").crop((0, 80, im.width(), 380))
        bg = Image.new("RGBA", pil.size, (244, 246, 250, 255))
        bg.alpha_composite(pil)
        frames.append(bg)
    cw, ch = frames[0].size
    pad = 12
    out = Image.new("RGB", (cw * 3 + pad * 4, ch + 44), (255, 255, 255))
    d = ImageDraw.Draw(out)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 14)
    except OSError:
        font = ImageFont.load_default()
    for i, (angle, fr) in enumerate(zip((-4, 0, 4), frames)):
        x = pad + i * (cw + pad)
        out.paste(fr.convert("RGB"), (x, 32))
        d.text((x, 10), "%+d deg" % angle, fill=(40, 55, 80), font=font)
    out.save(os.path.join(ROOT, "docs", "_hair_runtime_default.png"))
    print("preview", os.path.join(ROOT, "docs", "_hair_runtime_default.png"))


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    rest_composition()
    layer_checks()
    preview()
    print("\n===== %d/%d =====" % (sum(1 for _, ok in R if ok), len(R)))
    for name, ok in R:
        if not ok:
            print("FAIL:", name)


if __name__ == "__main__":
    main()
