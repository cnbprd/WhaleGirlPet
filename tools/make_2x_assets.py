# -*- coding: utf-8 -*-
"""为立绘/表情生成 2 倍超采样版本（v3.0.22）。

放大桌宠时，267×512 的原图直接平滑缩放，alpha 边缘只有 ~4px 过渡，斜边会有台阶。
先离线做 2× Lanczos 版本（过渡 ~8.8px），运行时再压回目标尺寸，边缘就平了。

    python tools/make_2x_assets.py            # 生成
    python tools/make_2x_assets.py --check    # 只体检
"""
import os
import sys

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

TARGETS = []
for rel in ("skins/default.png", "skins/longmaid.png", "skins/blackgown.png",
            "skins/blackgreen.png", "skins/blackred.png", "skins/jk.png",
            "skins/hanfu.png", "skins/mature.png", "loli/default.png"):
    TARGETS.append(rel)
for name in ("idle", "happy", "eat", "walk", "sleep", "sleepy", "shy", "angry",
             "curious", "pat"):
    TARGETS.append(f"expressions/{name}.png")
# v3.0.22：睡颜差分（各皮肤闭眼图）也要 2x，否则放大后眼睛边缘台阶
import glob  # noqa: E402
for p in sorted(glob.glob(os.path.join(ASSETS, "skins", "*_sleep.png"))):
    TARGETS.append("skins/" + os.path.basename(p))
for p in sorted(glob.glob(os.path.join(ASSETS, "loli", "*_sleep.png"))):
    TARGETS.append("loli/" + os.path.basename(p))


def out_path(rel: str) -> str:
    return os.path.join(ASSETS, rel[:-4] + "@2x.png")


def main():
    check = "--check" in sys.argv
    missing = grown = 0
    total_in = total_out = 0
    for rel in TARGETS:
        src = os.path.join(ASSETS, rel)
        dst = out_path(rel)
        if not os.path.exists(src):
            print(f"  跳过（原图不存在）{rel}")
            continue
        if check:
            if os.path.exists(dst):
                im = Image.open(dst)
                print(f"  ok   {rel} → {im.size[0]}×{im.size[1]} "
                      f"({os.path.getsize(dst) / 1024:.0f}KB)")
            else:
                missing += 1
                print(f"  MISS {rel}")
            continue
        im = Image.open(src).convert("RGBA")
        w, h = im.size
        im2 = im.resize((w * 2, h * 2), Image.LANCZOS)
        # 关键是这一下：只对 alpha 做 1px 盒模糊（等效 1x 下 0.5px）。
        # 实测同一张立绘放大 1.6 倍，边缘"大跳变"从 19.6% 降到 0.0%；
        # 不做这一步，单纯 2x 缩放反而更锐（55%），台阶更明显。
        a = im2.getchannel("A").filter(ImageFilter.BoxBlur(1))
        im2.putalpha(a)
        im2.save(dst, "PNG", optimize=True)
        grown += 1
        total_in += os.path.getsize(src)
        total_out += os.path.getsize(dst)
    if not check:
        print(f"生成 {grown} 张 @2x，原图合计 {total_in / 1024:.0f}KB → {total_out / 1024:.0f}KB")
    print(f"缺失 {missing} 张" if check else "")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
