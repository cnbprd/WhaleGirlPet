# -*- coding: utf-8 -*-
"""生成「关于与更新」页的两张素材：透明底 logo 与仓库下载二维码。

    .venv\\Scripts\\python.exe tools\\_make_about_assets.py
"""
import os

from PIL import Image, ImageDraw
import qrcode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(ROOT, "assets", "ui")
RELEASES = "https://github.com/cnbprd/WhaleGirlPet/releases"


def make_logo():
    """从多尺寸 ico 里取最大一帧，按最大透明边裁成正方形，输出 256 透明底 png。"""
    ico = Image.open(os.path.join(UI, "pet_flat.ico"))
    best = None
    for size in getattr(ico, "info", {}).get("sizes", []):
        try:
            ico.size = size
            frame = ico.convert("RGBA")
        except Exception:
            continue
        if best is None or frame.size[0] > best.size[0]:
            best = frame
    if best is None:
        best = ico.convert("RGBA")
    # 裁掉四周全透明，再补成正方形，避免头像偏下
    box = best.split()[-1].getbbox()
    if box:
        best = best.crop(box)
    side = max(best.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(best, ((side - best.size[0]) // 2, (side - best.size[1]) // 2), best)
    canvas.resize((256, 256), Image.LANCZOS).save(os.path.join(UI, "about_logo.png"))
    return canvas.size


def make_qr():
    """下载页二维码：白底、圆角、四边留白，深色与浅色主题下都放得住。"""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=10, border=2)
    qr.add_data(RELEASES)
    qr.make(fit=True)
    raw = qr.make_image(fill_color="#12161c", back_color="#ffffff").convert("RGB")
    size = raw.size[0]
    pad = 14
    canvas = Image.new("RGBA", (size + pad * 2, size + pad * 2), (255, 255, 255, 0))
    mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, canvas.size[0] - 1, canvas.size[1] - 1], radius=18, fill=255)
    plate = Image.new("RGBA", canvas.size, (255, 255, 255, 255))
    canvas.paste(plate, (0, 0), mask)
    canvas.paste(raw, (pad, pad))
    canvas.save(os.path.join(UI, "repo_qr.png"))
    return canvas.size


if __name__ == "__main__":
    print("logo:", make_logo(), "-> assets/ui/about_logo.png")
    print("qr:", make_qr(), "-> assets/ui/repo_qr.png")
