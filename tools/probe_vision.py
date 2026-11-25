# -*- coding: utf-8 -*-
"""定位 400：同一个图，换几种 image_url 写法与尺寸，看服务端认哪一种。

用法：python tools/probe_vision.py
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import local_llm  # noqa: E402

CFG = {
    "llm_port": local_llm.DEFAULT_PORT, "llm_ctx": 4096, "llm_model_file": "",
    "llm_mmproj": "",
    "model_roles": {"brain": "qwen35-4b-Q4_K_M.gguf", "tool": "", "fast": "gemma4-e2b-it.gguf"},
    "ollama_host": local_llm.OLLAMA_HOST,
}
SRC = os.path.join(ROOT, "docs", "skeletal_v313.png")


def jpeg_b64(src, side, q=80):
    from PySide6.QtGui import QImage
    from PySide6.QtCore import Qt
    img = QImage(src)
    if side:
        img = img.scaled(side, side, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    out = os.path.join(ROOT, "build", f"probe_{side}.jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out, "JPG", q)
    with open(out, "rb") as f:
        raw = f.read()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii"), len(raw)


def post(base, body):
    req = urllib.request.Request(base + "/v1/chat/completions",
                                 data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read().decode("utf-8"))
        msg = (d.get("choices") or [{}])[0].get("message", {})
        return True, (msg.get("content") or msg.get("reasoning_content") or "")[:160]
    except urllib.error.HTTPError as e:
        return False, f"{e.code} " + (e.read() or b"")[:200].decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def main():
    m = local_llm.ServerManager(CFG)
    if not m.ensure_role("fast"):
        print("加载失败:", m.last_error)
        return
    base = m.base_url()
    url_1024, n1 = jpeg_b64(SRC, 1024)
    url_512, n2 = jpeg_b64(SRC, 512)
    url_320, n3 = jpeg_b64(SRC, 320)
    print(f"图体积: 1024→{n1/1024:.0f}KB  512→{n2/1024:.0f}KB  320→{n3/1024:.0f}KB")

    cases = [
        ("A 1024 对象url", {"type": "image_url", "image_url": {"url": url_1024}}),
        ("B 512 对象url", {"type": "image_url", "image_url": {"url": url_512}}),
        ("C 512 字符串url", {"type": "image_url", "image_url": url_512}),
        ("D 320 对象url", {"type": "image_url", "image_url": {"url": url_320}}),
    ]
    for name, part in cases:
        body = {"model": "local", "stream": False, "max_tokens": 120, "temperature": 0.2,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": "这张图里是什么？一句话。"}, part]}]}
        t = time.perf_counter()
        ok, out = post(base, body)
        print(f"{name}: ok={ok} {time.perf_counter() - t:.1f}s -> {out}")
        time.sleep(0.5)
    m.stop()


if __name__ == "__main__":
    main()
