# -*- coding: utf-8 -*-
"""批量后处理：下载 aka 短链原图 -> mediakit 抠图 -> 下载抠图结果 -> 归一化落盘。

用法: python tools/process_assets.py
清单写在 MANIFEST 中；跳过已存在且校验通过的目标文件。
"""
import json
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT_DIR = os.path.join(ROOT, "assets", "_matting")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from normalize import normalize  # noqa: E402

# key -> (类别目录, aka 短链)
MANIFEST = {
    # 表情
    "happy":    ("expressions", "https://aka.doubaocdn.com/s/wOcIsl0SHv"),
    "eat":      ("expressions", "https://aka.doubaocdn.com/s/d2mNzmCCyP"),
    "walk":     ("expressions", "https://aka.doubaocdn.com/s/NRVUCwPF0V"),
    "sleep":    ("expressions", "https://aka.doubaocdn.com/s/rBQ1aPHYC5"),
    "sleepy":   ("expressions", "https://aka.doubaocdn.com/s/Y2rcUWY7ZU"),
    "shy":      ("expressions", "https://aka.doubaocdn.com/s/PjUPPhe2Zn"),
    "angry":    ("expressions", "https://aka.doubaocdn.com/s/5DNAI2kUbe"),
    "curious":  ("expressions", "https://aka.doubaocdn.com/s/QNDUIXkSqd"),
    "pat":      ("expressions", "https://aka.doubaocdn.com/s/yG94GwbmjL"),
    # 动作
    "wave":     ("actions", "https://aka.doubaocdn.com/s/UeukriQcQp"),
    "dance":    ("actions", "https://aka.doubaocdn.com/s/ja73JYCvtD"),
    "type":     ("actions", "https://aka.doubaocdn.com/s/LF39QfNjma"),
    "balloon":  ("actions", "https://aka.doubaocdn.com/s/mbwbVoLxTX"),
    "fireworks":("actions", "https://aka.doubaocdn.com/s/ITvIjFJbOX"),
    "lion":     ("actions", "https://aka.doubaocdn.com/s/7ob6pCmklk"),
    "change":   ("actions", "https://aka.doubaocdn.com/s/SjqQCQ9qJ7"),
    # 换装
    "longmaid": ("skins", "https://aka.doubaocdn.com/s/SGnvHuuOqr"),
    "blackgown":("skins", "https://aka.doubaocdn.com/s/IH4i3fnZTH"),
    "blackgreen":("skins", "https://aka.doubaocdn.com/s/g8zgjTAq82"),
    "blackred": ("skins", "https://aka.doubaocdn.com/s/DBc9Up8HvA"),
}


def download(url: str, dst: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dst, "wb") as f:
        f.write(r.read())


def matte(raw: str) -> str:
    proc = subprocess.run(
        ["mediakit-cli", "image", "remove-image-background",
         "--image-url", raw, "--scene", "general"],
        capture_output=True, text=True, encoding="utf-8", timeout=180)
    out = proc.stdout.strip()
    if not out:
        raise RuntimeError(f"matting empty: {proc.stderr[:200]}")
    data = json.loads(out)
    if not data.get("success"):
        raise RuntimeError(f"matting failed: {out[:200]}")
    return data["image_url"]


def main():
    os.makedirs(MAT_DIR, exist_ok=True)
    report = []
    for key, (cat, url) in MANIFEST.items():
        dst = os.path.join(ROOT, "assets", cat, f"{key}.png")
        if os.path.exists(dst) and os.path.getsize(dst) > 10000:
            report.append((key, "skip", os.path.getsize(dst)))
            continue
        raw = os.path.join(MAT_DIR, f"v3-{key}-raw.png")
        matted = os.path.join(MAT_DIR, f"v3-{key}-matted.png")
        try:
            if not os.path.exists(raw):
                download(url, raw)
            if not os.path.exists(matted):
                murl = matte(raw)
                download(murl, matted)
            info = normalize(matted, dst)
            report.append((key, "ok", info["size"], info["corner_alpha"]))
            print(key, "ok", info, flush=True)
        except Exception as e:  # noqa: BLE001
            report.append((key, "FAIL", str(e)[:160]))
            print(key, "FAIL", e, flush=True)
    fails = [r for r in report if r[1] == "FAIL"]
    print("\n=== summary ===")
    for r in report:
        print(r)
    print(f"\nfailed: {len(fails)}")


if __name__ == "__main__":
    main()
