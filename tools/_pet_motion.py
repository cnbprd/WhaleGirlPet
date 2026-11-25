# -*- coding: utf-8 -*-
"""扫描整段录屏的帧差强度，输出「画面在动 / 静止」的时间线，用来定位剪辑点。

用法：python tools/_pet_motion.py <视频> [fs]
输出：assets/_matting/vidscan/motion.csv 与高变化区间清单
"""
import csv
import os
import subprocess
import sys

import imageio_ffmpeg
import numpy as np

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "_matting", "vidscan")
W, H = 160, 76


def main():
    src = sys.argv[1]
    fs = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    os.makedirs(OUT, exist_ok=True)
    cmd = [FF, "-hide_banner", "-loglevel", "error", "-i", src,
           "-vf", f"fps={fs},scale={W}:{H}", "-pix_fmt", "gray",
           "-f", "rawvideo", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            creationflags=0x08000000)
    frame_bytes = W * H
    rows, prev = [], None
    idx = 0
    while True:
        buf = proc.stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        cur = np.frombuffer(buf, dtype=np.uint8).reshape(H, W).astype(np.int16)
        if prev is not None:
            d = np.abs(cur - prev)
            rows.append((idx / fs, float(d.mean()),
                         float(d[:, int(W * 0.86):].mean())))  # 右侧桌宠区
        prev = cur
        idx += 1
    proc.stdout.close()
    proc.wait()
    print("总帧", idx, "diff 行", len(rows))
    if not rows:
        return

    with open(os.path.join(OUT, "motion.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t", "diff_all", "diff_pet"])
        w.writerows(rows)

    arr = np.array([[r[0], r[1], r[2]] for r in rows])
    q = np.percentile(arr[:, 1], [50, 75, 90, 99])
    print("diff_all 分位数 50/75/90/99 =", [round(x, 2) for x in q])

    thr = max(2.0, float(q[1]))
    moving = arr[:, 1] > thr
    # 合并连续段，间隔小于 3 秒的接上
    segs, start, last = [], None, None
    for t, m in zip(arr[:, 0], moving):
        if m:
            if start is None:
                start = t
            last = t
        elif start is not None and t - last > 3:
            segs.append((start, last))
            start = None
    if start is not None:
        segs.append((start, last))
    segs = [(s, e) for s, e in segs if e - s >= 2]
    print("高变化段数", len(segs), "阈值", round(thr, 2))
    for s, e in segs[:60]:
        print(f"  {int(s)//60:02d}:{int(s)%60:02d} → {int(e)//60:02d}:{int(e)%60:02d}"
              f"  ({e - s:.0f}s)")


if __name__ == "__main__":
    main()
