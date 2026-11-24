# -*- coding: utf-8 -*-
"""通用探测下载：python dl_any.py <url> <dest>"""
import os
import sys
import time
import urllib.request

URL = sys.argv[1]
DEST = sys.argv[2]
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
        if now - last > 3:
            print(f"  {pos/1048576:.0f}/{total/1048576:.0f} MB  "
                  f"{pos/(now-t0)/1048576:.1f} MB/s", flush=True)
            last = now
os.replace(part, DEST)
print("done:", DEST, round(os.path.getsize(DEST) / 1048576, 1), "MB",
      round(time.time() - t0, 1), "s")
