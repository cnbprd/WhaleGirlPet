# -*- coding: utf-8 -*-
"""启动新版 exe 并连续抓帧，用来确认「鲸鱼娘加载中」真的出现过。"""
import os
import subprocess
import sys
import time

from PIL import ImageGrab

EXE = r"F:\WhaleGirlPet\dist\WhaleGirlPet.exe"
OUT = r"F:\WhaleGirlPet\assets\_matting"

proc = subprocess.Popen([EXE]) if len(sys.argv) < 2 else None
shots = []
for i in range(10):
    time.sleep(0.32)
    im = ImageGrab.grab()
    path = os.path.join(OUT, f"boot_{i}.png")
    im.save(path)
    shots.append(path)
    print("shot", i, im.size, flush=True)

print("pid", proc.pid)
