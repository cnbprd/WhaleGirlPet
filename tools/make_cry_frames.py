"""生成卸载界面的两帧哭泣立绘（在 whale.png 上叠加眼泪，帧间眼泪下落）。"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = Image.open(os.path.join(ROOT, "installer", "art", "whale.png")).convert("RGBA")
W, H = src.size

# 眼睛大致位置（468x980 立绘）：左眼 (181,148)，右眼 (252,148)
EYES = [(181, 150), (252, 150)]
TEAR = (150, 205, 245, 235)


def frame(drop: int) -> Image.Image:
    img = src.copy()
    d = ImageDraw.Draw(img, "RGBA")
    for i, (ex, ey) in enumerate(EYES):
        # 眼下泪痕（细长）
        d.line([(ex, ey + 10), (ex - 2 + i * 3, ey + 44)], fill=(170, 220, 250, 150), width=3)
        # 挂在脸颊的泪珠
        d.ellipse([ex - 6, ey + 40, ex + 6, ey + 56], fill=TEAR)
        # 下落中的泪滴：两帧错开
        yy = ey + 74 + (drop if i == 0 else 18 - drop)
        d.ellipse([ex - 5, yy, ex + 5, yy + 14], fill=(175, 225, 252, 220))
        yy2 = yy + 30
        d.ellipse([ex - 3, yy2, ex + 3, yy2 + 8], fill=(175, 225, 252, 160))
    # 鼻尖一点红（哭意）
    d.ellipse([212, 196, 222, 205], fill=(240, 150, 160, 110))
    return img


for n, drop in ((1, 0), (2, 16)):
    out = os.path.join(ROOT, "installer", "art", f"whale_cry{n}.png")
    frame(drop).save(out)
    print("saved", out)
