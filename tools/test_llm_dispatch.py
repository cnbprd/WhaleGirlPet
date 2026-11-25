# -*- coding: utf-8 -*-
"""v3.0.9 调配机制实测：端口自适应 / 模型自动降级 / 请求串行 / 进程死后自愈。"""
import os
import socket
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import local_llm  # noqa: E402

GOOD = r"F:\WhaleGirlPetApp\models\qwen3.5-4b.gguf"
BAD = os.path.join(ROOT, "tools", "_bad.gguf")


def make_bad():
    with open(BAD, "wb") as f:
        f.write(b"this is not a gguf\n" * 100)


def hold(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", port))
    s.listen(2)
    return s


def main():
    make_bad()
    print("可用模型存在：", os.path.exists(GOOD), round(os.path.getsize(GOOD) / 1048576, 1), "MB")
    blocker = hold(8099)
    print("已占住 8099，模拟端口冲突")

    cfg = {"llm_port": 8099, "llm_ctx": 2048, "llm_backend": "dafeiyu_cpp",
           "llm_model_file": BAD}
    m = local_llm.ServerManager(cfg)
    t0 = time.time()
    ok = m.start()
    print(f"[1] 坏模型+端口占用 -> start={ok} 耗时 {time.time()-t0:.1f}s "
          f"port={m.port} auto={m.port_auto} model={os.path.basename(m.active_model or '')}")
    print("   降级说明：", m.fallback_note)
    if not ok:
        print("   失败原因：", m.last_error)
        return

    # [2] 串行：两个线程同时请求
    res = []

    def ask(tag, q):
        a = time.time()
        o, r = m.dispatch([{"role": "user", "content": q}], 32, 0.2, timeout=180)
        res.append((tag, o, r[:24], round(time.time() - a, 1)))

    th1 = threading.Thread(target=ask, args=("A", "只回答两个字：你好"))
    th2 = threading.Thread(target=ask, args=("B", "只回答两个字：再见"))
    t0 = time.time()
    th1.start(); th2.start()
    th1.join(); th2.join()
    print(f"[2] 两路并发总耗时 {time.time()-t0:.1f}s 结果={res}")

    # [3] 进程被 kill 后自愈
    pid = m.proc.pid if m.proc else None
    m.proc.kill()
    time.sleep(0.5)
    print("[3] 已 kill 引擎进程", pid, "running=", m.is_running(), "health=", m.health())
    t0 = time.time()
    o, r = m.dispatch([{"role": "user", "content": "只回答两个字：重启"}], 32, 0.2, timeout=180)
    print(f"   自愈后 ok={o} 回复={r[:20]!r} 耗时 {time.time()-t0:.1f}s running={m.is_running()}"
          f" model={os.path.basename(m.active_model or '')} err={m.last_error[:80]}")

    # [4] 状态
    st = m.status()
    print("[4] status:", {k: st[k] for k in ("backend", "model", "running", "port", "port_auto", "busy")})
    m.stop()
    blocker.close()
    try:
        os.remove(BAD)
    except OSError:
        pass
    print("清理完成")


if __name__ == "__main__":
    main()
