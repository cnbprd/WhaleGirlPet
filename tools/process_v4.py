# -*- coding: utf-8 -*-
"""第四轮素材后处理：下载 -> mediakit 抠图 -> 归一化。

清单：JK 制服、汉服（以成熟母版派生）、萝莉形态默认（第一轮旧立绘）。
"""
import json
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT = os.path.join(ROOT, "assets", "_matting")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from normalize import normalize  # noqa: E402

# key -> (目标路径, aka 短链, 原始下载名)
MANIFEST = {
    "jk":    (os.path.join("skins", "jk.png"),     "https://aka.doubaocdn.com/s/UjMbIaeb0Z", "v4-jk-raw"),
    "hanfu": (os.path.join("skins", "hanfu.png"),  "https://aka.doubaocdn.com/s/qW9l2gJmdL", "v4-hanfu-raw"),
    "loli":  (os.path.join("loli", "default.png"), "https://aka.doubaocdn.com/s/mwTI3hVjjk", "v4-loli-raw"),
}


def download(url: str, dst: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as r, open(dst, "wb") as f:
        f.write(r.read())


def matte(raw_url: str) -> str:
    proc = subprocess.run(
        ["mediakit-cli", "image", "remove-image-background",
         "--image-url", raw_url, "--scene", "general"],
        capture_output=True, text=True, encoding="utf-8", timeout=240)
    out = proc.stdout.strip()
    if not out:
        raise RuntimeError("matting empty: " + proc.stderr[:200])
    data = json.loads(out)
    if not data.get("success"):
        raise RuntimeError("matting failed: " + out[:200])
    return data["image_url"]


def main():
    os.makedirs(MAT, exist_ok=True)
    results = []
    for key, (rel, url, tag) in MANIFEST.items():
        dst = os.path.join(ROOT, "assets", rel)
        raw = os.path.join(MAT, tag + ".png")
        matted = os.path.join(MAT, tag + "-matted.png")
        try:
            if not (os.path.exists(raw) and os.path.getsize(raw) > 10000):
                download(url, raw)
            if not (os.path.exists(matted) and os.path.getsize(matted) > 10000):
                download(matte(url), matted)
            info = normalize(matted, dst)
            results.append((key, "ok", info))
            print(key, "ok", info, flush=True)
        except Exception as e:  # noqa: BLE001
            results.append((key, "FAIL", str(e)[:200]))
            print(key, "FAIL", e, flush=True)
    print("\n=== summary ===")
    for r in results:
        print(r)


if __name__ == "__main__":
    main()
