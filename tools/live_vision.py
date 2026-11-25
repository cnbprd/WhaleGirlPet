# -*- coding: utf-8 -*-
"""v3.0.18 真机实测：Gemma 4 E2B + mmproj 到底能不能看图。

用法：python tools/live_vision.py [图片路径]
"""
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import local_llm  # noqa: E402
import vision  # noqa: E402

CFG = {
    "llm_port": local_llm.DEFAULT_PORT,
    "llm_ctx": 4096,
    "llm_model_file": "",
    "llm_mmproj": "",
    "model_roles": {"brain": "qwen35-4b-Q4_K_M.gguf",
                    "tool": "deepseek-coder-6.7b-instruct.gguf",
                    "fast": "gemma4-e2b-it.gguf"},
    "ollama_host": local_llm.OLLAMA_HOST,
}


def modes(m):
    try:
        with urllib.request.urlopen(m.base_url() + "/v1/models", timeout=8) as r:
            d = json.loads(r.read().decode("utf-8"))
        for item in d.get("data", []):
            arch = item.get("architecture") or {}
            return arch.get("input_modalities"), arch.get("output_modalities")
    except Exception as e:  # noqa: BLE001
        return f"查询失败:{e}", None
    return None, None


def main():
    img = sys.argv[1] if len(sys.argv) > 1 else ""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    m = local_llm.ServerManager(CFG)
    fast = m.role_model("fast")
    print("fast 模型:", os.path.basename(fast) if fast else "(未配置)")
    print("匹配到的 mmproj:", os.path.basename(m.mmproj_for(fast)) or "(无)")

    t = time.perf_counter()
    ok = m.ensure_role("fast")
    print(f"加载 ok={ok} {time.perf_counter() - t:.1f}s active={os.path.basename(m.active_model)} "
          f"err={m.last_error}")
    if not ok:
        m.stop()
        return

    print("input/output modalities:", modes(m))

    if not img:
        # 没给图就截一张当前屏幕
        img = vision.capture_screen()
        print("自动截图:", img)
    if img and os.path.exists(img):
        print("图片大小: %.2f MB" % (os.path.getsize(img) / 1048576))
        msgs = [vision.vision_message("这张图里是什么？用一句话说重点。", img)]
        body_len = len(vision.to_data_url(img))
        print("data url 长度:", body_len)

        t1 = time.perf_counter()
        ok1, out1 = m.dispatch([{"role": "user", "content": "只说两个字：在的"}],
                               max_tokens=16, temperature=0.2)
        print(f"1) dispatch 纯文本 ok={ok1} {time.perf_counter() - t1:.1f}s -> {str(out1)[:60]!r}")

        t2 = time.perf_counter()
        ok2, out2 = m.chat(msgs, max_tokens=120, temperature=0.2)
        print(f"2) chat 带图     ok={ok2} {time.perf_counter() - t2:.1f}s -> {str(out2)[:60]!r}")

        t3 = time.perf_counter()
        ok3, out3 = m.dispatch(msgs, max_tokens=120, temperature=0.2)
        print(f"3) dispatch 带图 ok={ok3} {time.perf_counter() - t3:.1f}s -> {str(out3)[:80]!r}")

        # 4) 同一张图压到 512，看是不是尺寸/体积阈值
        import base64
        from PySide6.QtGui import QImage
        from PySide6.QtCore import Qt
        q = QImage(img).scaled(512, 512, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        tmp = os.path.join(os.environ.get("TEMP", "."), "probe512.jpg")
        q.save(tmp, "JPG", 80)
        with open(tmp, "rb") as f:
            u = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("ascii")
        print("512 data url 长度:", len(u))
        m512 = [{"role": "user", "content": [
            {"type": "text", "text": "这张图里是什么？一句话。"},
            {"type": "image_url", "image_url": {"url": u}}]}]
        t4 = time.perf_counter()
        ok4, out4 = m.chat(m512, max_tokens=120, temperature=0.2)
        print(f"4) chat 512px   ok={ok4} {time.perf_counter() - t4:.1f}s -> {str(out4)[:80]!r}")

        # 5) 396px（更小）
        q5 = QImage(img).scaled(396, 396, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        q5.save(tmp, "JPG", 78)
        with open(tmp, "rb") as f:
            u5 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("ascii")
        m5 = [{"role": "user", "content": [
            {"type": "text", "text": "这张图里是什么？一句话。"},
            {"type": "image_url", "image_url": {"url": u5}}]}]
        t5 = time.perf_counter()
        ok5, out5 = m.chat(m5, max_tokens=120, temperature=0.2)
        print(f"5) chat 396px   ok={ok5} {time.perf_counter() - t5:.1f}s -> {str(out5)[:80]!r}")
    else:
        print("没有可用图片，跳过看图。")
    m.stop()


if __name__ == "__main__":
    main()
