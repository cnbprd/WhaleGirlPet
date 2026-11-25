# -*- coding: utf-8 -*-
"""v3.0.17 真机实测：三档角色真的会把引擎换成对应模型吗，代价多少秒。

跑法：python tools/live_roles.py
会真的起 dafeiyu-server（占内存 2.5~4GB），测完自动停掉。
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
                    "fast": ""},
    "ollama_host": local_llm.OLLAMA_HOST,
}


def main():
    m = local_llm.ServerManager(CFG)
    print("引擎 exe:", local_llm.server_exe())
    print("exe 存在:", os.path.exists(local_llm.server_exe()))

    for role in ("brain", "tool", "brain"):
        t = time.perf_counter()
        ok = m.ensure_role(role)
        dt = time.perf_counter() - t
        print(f"[{role}] ok={ok} 耗时 {dt:.1f}s active={os.path.basename(m.active_model)} "
              f"note={m.fallback_note}")
        if ok and m.is_running():
            t2 = time.perf_counter()
            okc, out = m.dispatch([{"role": "user", "content": "只回复两个字：在的"}],
                                  max_tokens=12, temperature=0.2)
            print(f"      对话 ok={okc} 用时 {time.perf_counter() - t2:.1f}s "
                  f"→ {str(out)[:60]!r}")
    m.stop()
    time.sleep(1)
    print("已停止, 进程状态:", m.is_running())


if __name__ == "__main__":
    main()
