# -*- coding: utf-8 -*-
"""检查素材模式、尺寸与四角背景，输出报告。"""
import os
import glob
from PIL import Image

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

def main():
    for f in sorted(glob.glob(os.path.join(BASE, "**", "*.png"), recursive=True)):
        if os.sep + "_raw" + os.sep in f or os.sep + "_matting" + os.sep in f:
            continue
        im = Image.open(f)
        corners = [im.getpixel(p) for p in [
            (2, 2), (im.width - 3, 2), (2, im.height - 3), (im.width - 3, im.height - 3)]]
        print(os.path.relpath(f, BASE), im.mode, im.size, "corner:", corners)

if __name__ == "__main__":
    main()
