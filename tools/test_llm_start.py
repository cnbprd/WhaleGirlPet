# -*- coding: utf-8 -*-
"""验证：新扫描逻辑找到的模型，能不能被引擎真正加载起来。

用一个 833MB 的小模型跑，独立端口 8099，跑完立刻 stop，不动用户正在用的实例。
"""
import sys
import time

sys.path.insert(0, r"F:\WhaleGirlPet\app")
import local_llm  # noqa: E402

MODEL = r"F:\WhaleGirlPet\runtime\models\_probe\deepseek-coder-1.3b-Q4_K_M.gguf"
cfg = {"llm_model_file": MODEL, "llm_port": 8099, "llm_ctx": 2048, "llm_backend": "dafeiyu_cpp"}

print("available =", local_llm.available(cfg), flush=True)
print("model     =", local_llm.resolve_model(MODEL, cfg), flush=True)

m = local_llm.ServerManager(cfg)
print("backend =", m.backend, flush=True)
t = time.time()
ok = m.start()
print(f"start -> {ok}  ({time.time()-t:.1f}s)  错误={m.last_error!r}", flush=True)
if ok:
    print("health =", m.health(), flush=True)
    try:
        rep = m.chat([{"role": "user", "content": "说一句话：你好"}], max_tokens=24)
        print("chat  =", repr(rep)[:200], flush=True)
    except Exception as e:  # noqa: BLE001
        print("chat ERR", repr(e), flush=True)
m.stop()
print("已 stop", flush=True)
