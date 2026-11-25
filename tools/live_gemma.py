# -*- coding: utf-8 -*-
"""验证引擎能不能加载 gemma4 架构（Gemma 4 E2B），以及加 --mmproj 前后差别。

用法：
  python tools/live_gemma.py            # 只测纯文本加载
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import local_llm  # noqa: E402

CFG = {
    "llm_port": local_llm.DEFAULT_PORT,
    "llm_ctx": 4096,
    "llm_model_file": "",
    "model_roles": {"brain": "qwen35-4b-Q4_K_M.gguf",
                    "tool": "deepseek-coder-6.7b-instruct.gguf",
                    "fast": "gemma4-e2b-it.gguf"},
    "ollama_host": local_llm.OLLAMA_HOST,
}


def main():
    m = local_llm.ServerManager(CFG)
    t = time.perf_counter()
    ok = m.ensure_role("fast")
    print(f"加载 gemma4 ok={ok} 耗时 {time.perf_counter() - t:.1f}s "
          f"active={os.path.basename(m.active_model)} note={m.fallback_note} "
          f"last_error={m.last_error}")
    if ok and m.is_running():
        t2 = time.perf_counter()
        okc, out = m.dispatch([{"role": "user", "content": "说一句话：你是什么模型？"}],
                              max_tokens=40, temperature=0.3)
        print(f"chat ok={okc} {time.perf_counter() - t2:.1f}s -> {str(out)[:80]!r}")
        # 顺手看服务端自报的模型信息（是否认出多模态）
        import json
        import urllib.request
        try:
            with urllib.request.urlopen(m.base_url() + "/v1/models", timeout=5) as r:
                print("models:", json.loads(r.read().decode("utf-8")))
        except Exception as e:  # noqa: BLE001
            print("models 查询失败:", e)
    m.stop()


if __name__ == "__main__":
    main()
