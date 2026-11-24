# -*- coding: utf-8 -*-
"""生成安装向导用的美术资源（一次性脚本，产物进 installer/art）。

- whale.png   角色立绘（裁掉透明边，高 980，透明底），装到向导右侧
- bubble.png  白色圆角对话气泡（右侧带小尾巴，指向角色）
- small.png   右上角小图：只留角色、无圆形背景（透明底）
"""
import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = r"F:\WhaleGirlPet"
ART = os.path.join(ROOT, "installer", "art")
os.makedirs(ART, exist_ok=True)


def trim(im: Image.Image) -> Image.Image:
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def make_whale():
    src = Image.open(os.path.join(ROOT, "assets", "skins", "default.png")).convert("RGBA")
    src = trim(src)
    h = 980
    w = int(src.width * h / src.height)
    src.resize((w, h), Image.LANCZOS).save(os.path.join(ART, "whale.png"))
    print("whale.png", w, h)


def make_small():
    src = Image.open(os.path.join(ROOT, "assets", "ui", "qwhale.png")).convert("RGBA")
    src = trim(src)
    side = 400
    inner = 380
    w = int(src.width * inner / src.height)
    r = src.resize((w, inner), Image.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(r, ((side - w) // 2, (side - inner) // 2), r)
    canvas.save(os.path.join(ART, "small.png"))
    print("small.png", side, side)


def make_bubble():
    W, H = 640, 400
    radius = 44
    body = (18, 16, W - 104, H - 30)          # 右侧留 86px 给尾巴
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # 阴影
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    ds.rounded_rectangle(body, radius=radius, fill=(28, 56, 96, 46))
    ds.polygon([(body[2] - 10, 196), (W - 26, 248), (body[2] - 10, 300)],
               fill=(28, 56, 96, 46))
    sh = sh.filter(ImageFilter.GaussianBlur(16))
    base = Image.alpha_composite(base, sh)

    # 主体
    d = ImageDraw.Draw(base)
    d.rounded_rectangle(body, radius=radius, fill=(255, 255, 255, 248))
    d.polygon([(body[2] - 14, 198), (W - 30, 248), (body[2] - 14, 298)],
              fill=(255, 255, 255, 248))

    # 淡边
    d.rounded_rectangle(body, radius=radius, outline=(186, 211, 236, 255), width=2)
    d.line([(W - 30, 248), (body[2] - 14, 298)], fill=(186, 211, 236, 255), width=2)
    d.line([(W - 30 - 1, 248), (body[2] - 14, 198)], fill=(186, 211, 236, 255), width=2)

    base.save(os.path.join(ART, "bubble.png"))
    print("bubble.png", W, H)


make_whale()
make_small()
make_bubble()
