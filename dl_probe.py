# -*- coding: utf-8 -*-
"""下载 Gemma 4 E2B 官方 QAT q4_0 GGUF 用于选型实测（临时目录，测完可删）。"""
import os
import sys
import time
import urllib.request

URL = ("https://hf-mirror.com/google/gemma-4-E2B-it-qat-q4_0-gguf/"
       "resolve/main/gemma-4-E2B_q4_0-it.gguf")
DEST = r"C:\Users\yangmengke\Doubao\chats\2026-11-23\new-chat\whale-girl-pet\runtime\models\_probe\gemma4-e2b-q4_0.gguf"

os.makedirs(os.path.dirname(DEST), exist_ok=True)
part = DEST + ".part"
pos = os.path.getsize(part) if os.path.exists(part) else 0
headers = {"User-Agent": "WhaleGirlPet-probe"}
if pos:
    headers["Range"] = f"bytes={pos}-"
req = urllib.request.Request(URL, headers=headers)
t0 = time.time()
last = t0
with urllib.request.urlopen(req, timeout=60) as r, open(part, "ab" if pos else "wb") as f:
    total = int(r.headers.get("Content-Length") or 0) + pos
    while True:
        buf = r.read(1 << 20)
        if not buf:
            break
        f.write(buf)
        pos += len(buf)
        now = time.time()
        if now - last > 2:
            sp = pos / (now - t0) / 1048576
            print(f"  {pos/1048576:.0f}/{total/1048576:.0f} MB  {sp:.1f} MB/s", flush=True)
            last = now
os.replace(part, DEST)
print("done:", DEST, round(os.path.getsize(DEST) / 1048576, 1), "MB",
      round((time.time() - t0), 1), "s")
