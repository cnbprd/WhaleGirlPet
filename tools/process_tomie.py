# -*- coding: utf-8 -*-
"""富江脸素材后处理：备份原图 -> mediakit 抠图 -> 归一化写回。

清单覆盖 8 张：成熟 7 套皮肤 + 萝莉 1 套。
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT = os.path.join(ROOT, "assets", "_matting")
BACKUP = os.path.join(MAT, "tomie-old")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from normalize import normalize  # noqa: E402

# key -> (相对 assets 的落盘路径, 富江版 aka 短链)
MANIFEST = {
    "default":    ("skins/default.png",    "https://aka.doubaocdn.com/s/4etUgQzaTo"),
    "jk":         ("skins/jk.png",         "https://aka.doubaocdn.com/s/klmscsrBf9"),
    "hanfu":      ("skins/hanfu.png",      "https://aka.doubaocdn.com/s/NVy8nFIRa6"),
    "longmaid":   ("skins/longmaid.png",   "https://aka.doubaocdn.com/s/CRD5789Jwq"),
    "blackgown":  ("skins/blackgown.png",  "https://aka.doubaocdn.com/s/yrxL84ktEc"),
    "blackgreen": ("skins/blackgreen.png", "https://aka.doubaocdn.com/s/4h6cYSmuo0"),
    "blackred":   ("skins/blackred.png",   "https://aka.doubaocdn.com/s/If1H5eUBNf"),
    "loli":       ("loli/default.png",     "https://aka.doubaocdn.com/s/JO4JNM9xrs"),
}


def download(url: str, dst: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as r, open(dst, "wb") as f:
        f.write(r.read())


def matte(raw_url: str) -> str:
    proc = subprocess.run(
        ["mediakit-cli", "image", "remove-image-background",
         "--image-url", raw_url, "--scene", "general"],
        capture_output=True, text=True, encoding="utf-8", timeout=300)
    out = (proc.stdout or "").strip()
    if not out:
        raise RuntimeError("matting empty: " + (proc.stderr or "")[:200])
    data = json.loads(out)
    if not data.get("success"):
        raise RuntimeError("matting failed: " + out[:200])
    return data["image_url"]


def main():
    os.makedirs(BACKUP, exist_ok=True)
    results = []
    # 先备份所有将被覆盖的原图（只备份一次）
    for key, (rel, _url) in MANIFEST.items():
        src = os.path.join(ROOT, "assets", rel)
        dst = os.path.join(BACKUP, os.path.basename(rel))
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)

    for key, (rel, url) in MANIFEST.items():
        raw = os.path.join(MAT, f"tomie-{key}.png")
        matted = os.path.join(MAT, f"tomie-{key}-matted.png")
        dst = os.path.join(ROOT, "assets", rel)
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
