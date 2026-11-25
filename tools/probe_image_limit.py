# -*- coding: utf-8 -*-
"""③ 图片上限实验：960px 到底是被 token 限制还是被请求体大小卡住。

做法：直接起引擎（不同 --image-* 参数），逐个尺寸往上打，找能过的最大尺寸。
用法：python tools/probe_image_limit.py
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MDIR = os.path.join(ROOT, "runtime", "models")
EXE = os.path.join(ROOT, "runtime", "dafeiyu", "dafeiyu-server.exe")
MODEL = os.path.join(MDIR, "gemma4-e2b-it.gguf")
MMPROJ = os.path.join(MDIR, "mmproj-gemma4-e2b-f16.gguf")
SRC = os.path.join(ROOT, "docs", "api_card_v315_on.png")
PORT = 11599


def jpeg_b64(side):
    from PySide6.QtGui import QImage
    from PySide6.QtCore import Qt
    img = QImage(SRC)
    img = img.scaled(side, side, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    out = os.path.join(ROOT, "build", f"lim_{side}.jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out, "JPG", 80)
    with open(out, "rb") as f:
        raw = f.read()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii"), len(raw), img.width(), img.height()


def wait_health(t=90):
    for _ in range(int(t * 2)):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
                if (json.loads(r.read().decode()) or {}).get("status") in ("ok", "no slot available"):
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def ask(url, text="这张图里有什么文字？逐字写出标题。"):
    body = {"model": "local", "stream": False, "max_tokens": 120, "temperature": 0.1,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": url}}]}]}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.loads(r.read().decode("utf-8"))
        msg = (d.get("choices") or [{}])[0].get("message", {})
        return True, time.perf_counter() - t0, (msg.get("content") or "")[:150]
    except urllib.error.HTTPError as e:
        return False, time.perf_counter() - t0, f"{e.code} " + (e.read() or b"")[:120].decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001
        return False, time.perf_counter() - t0, str(e)[:120]


def run_case(name, extra, sizes):
    print(f"\n=== {name}  extra={extra} ===")
    log = open(os.path.join(ROOT, "runtime", f"probe_{name}.log"), "ab")
    args = [EXE, "-m", MODEL, "-c", "4096", "-np", "1", "-rea", "off",
            "--port", str(PORT), "--host", "127.0.0.1",
            "--mmproj", MMPROJ, "-mmdev", "none"] + extra
    p = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT,
                         creationflags=0x08000000 if os.name == "nt" else 0)
    try:
        if not wait_health():
            print("  引擎没起来，跳过")
            return
        for side in sizes:
            url, raw, w, h = jpeg_b64(side)
            ok, dt, out = ask(url)
            print(f"  {side:>4}px ({w}x{h}, jpg {raw/1024:.0f}KB, url {len(url)/1024:.0f}KB): "
                  f"ok={ok} {dt:.1f}s -> {out!r}")
            time.sleep(0.3)
    finally:
        p.terminate()
        try:
            p.wait(timeout=8)
        except Exception:
            p.kill()
        log.close()
        time.sleep(1.0)


def main():
    sizes = [512, 640, 768, 960]
    run_case("default", [], sizes)
    run_case("mtok8k", ["--image-max-tokens", "8192"], [768, 960, 1280])
    run_case("mtokmax", ["--image-max-tokens", "16384", "--image-min-tokens", "256"], [960, 1280])


if __name__ == "__main__":
    main()
