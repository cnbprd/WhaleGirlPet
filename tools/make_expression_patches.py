# -*- coding: utf-8 -*-
"""生成表情补丁（v3.0.25 第二阶段）。

思路：表情图整张换会把身体网格一起换掉，表现为“闪一下”。这里只把
每张表情图的眼/嘴/脸中心裁成带羽化 alpha 的补丁，贴到默认立绘同一张脸上；
运行时身体保持 idle，只叠脸补丁。

输出：
  assets/expressions/patches/<expr>.png       267×512，透明底，只含脸补丁
  assets/expressions/patches/<expr>@2x.png    534×1024
  assets/expressions/patches/mouth/<expr>.png 54×36 嘴部小块（口型缩放用）
  assets/expressions/patches/mouth/<expr>@2x.png
"""
import os
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "expressions", "patches")
MOUTH_OUT = os.path.join(OUT, "mouth")

# 每张表情里脸中心（眼/鼻区域）的坐标；由皮肤连通域 + 目检校准。
ANCHORS = {
    "angry":   (125, 100),
    "curious": (110, 95),
    "eat":     (102, 100),
    "happy":   (118, 100),
    "idle":    (105, 100),
    "pat":     (104, 100),
    "shy":     (104, 100),
    "sleepy":  (103, 100),
    "walk":    (105, 99),
}
# 这几个表情本来就是“姿势表情”：吃饭捧碗、睡觉蜷坐、好奇托腮、困倦捂嘴。
# 整张换身体才合理，不做脸部补丁。
POSE_EXPR = {"sleep", "eat", "curious", "sleepy"}

# 默认立绘（assets/skins/default.png，267×512）的脸中心
BASE_ANCHOR = (108, 100)
FACE_W, FACE_H = 96, 112
MOUTH_W, MOUTH_H = 54, 36
MOUTH_DY = 18          # 嘴中心相对脸中心的下移（脸中心约在鼻梁）


def ellipse_mask(size, inset_x, inset_y, blur):
    w, h = size
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.ellipse((inset_x, inset_y, w - inset_x, h - inset_y), fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur))


def main():
    os.makedirs(MOUTH_OUT, exist_ok=True)
    face_mask = ellipse_mask((FACE_W, FACE_H), 10, 8, 8)
    mouth_mask = ellipse_mask((MOUTH_W, MOUTH_H), 6, 4, 4)
    for expr, (cx, cy) in ANCHORS.items():
        src = Image.open(os.path.join(ROOT, "assets", "expressions", expr + ".png")).convert("RGBA")
        if expr in POSE_EXPR:
            for p in (os.path.join(OUT, expr + ".png"), os.path.join(OUT, expr + "@2x.png"),
                      os.path.join(MOUTH_OUT, expr + ".png"), os.path.join(MOUTH_OUT, expr + "@2x.png")):
                if os.path.exists(p):
                    os.remove(p)
            print("skip pose", expr)
            continue
        # 脸补丁：贴到默认立绘的同一张脸上
        face = src.crop((cx - FACE_W // 2, cy - FACE_H // 2,
                         cx + FACE_W // 2, cy + FACE_H // 2)).copy()
        face.putalpha(face_mask)
        canvas = Image.new("RGBA", (267, 512), (0, 0, 0, 0))
        canvas.alpha_composite(face, (BASE_ANCHOR[0] - FACE_W // 2,
                                      BASE_ANCHOR[1] - FACE_H // 2))
        canvas.save(os.path.join(OUT, expr + ".png"))
        canvas.resize((534, 1024), Image.LANCZOS).save(os.path.join(OUT, expr + "@2x.png"))

        # 嘴部小块：不带整张脸，只保留嘴+下巴，供口型纵向缩放
        mcy = cy + MOUTH_DY
        mouth = src.crop((cx - MOUTH_W // 2, mcy - MOUTH_H // 2,
                          cx + MOUTH_W // 2, mcy + MOUTH_H // 2)).copy()
        mouth.putalpha(mouth_mask)
        mouth.save(os.path.join(MOUTH_OUT, expr + ".png"))
        mouth.resize((MOUTH_W * 2, MOUTH_H * 2), Image.LANCZOS).save(
            os.path.join(MOUTH_OUT, expr + "@2x.png"))
        print("patch", expr, "face", face.size, "mouth", mouth.size)
    print("out", OUT)


if __name__ == "__main__":
    main()
