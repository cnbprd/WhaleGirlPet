# -*- coding: utf-8 -*-
"""v3.0.17 三档角色分工的离线自检（不动真进程，只查解析与判定）。

1) role_model 能把 config 里的文件名解析成真实 gguf 路径
2) 内存闸的判断函数口径（需要 1.15 倍余量）
3) main._looks_like_code 的判定
4) ensure_role 在"目标缺失/未配置"时必须返回 True 且不动当前模型（不能把能用的停掉）
"""
import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

import local_llm  # noqa: E402

OK = 0
FAIL = 0


def check(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  PASS {name} {detail}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


class DummyMgr:
    """只借用 ServerManager 的方法，不真起进程。"""

    def __init__(self, cfg):
        self.config = cfg
        self.active_model = ""
        self.fallback_note = ""
        self._chat_lock = threading.Lock()
        self.spawned = []

    role_model = local_llm.ServerManager.role_model
    _mem_free_mb = local_llm.ServerManager._mem_free_mb
    ensure_role = local_llm.ServerManager.ensure_role

    # 起不来就当失败，但 ensure_role 只在需要换模型时才会走到这里
    def is_running(self):
        return False

    def stop(self):
        pass

    def _ensure_port(self):
        pass

    def _spawn_and_wait(self, exe, model):
        self.spawned.append(os.path.basename(model))
        return True

    def health(self):
        return True


def main():
    root = r"F:\WhaleGirlPet\runtime\models"
    cfg = {"llm_model_file": "", "model_roles": {
        "brain": "qwen35-4b-Q4_K_M.gguf",
        "tool": "deepseek-coder-6.7b-instruct.gguf",
        "fast": ""}}
    m = DummyMgr(cfg)

    print("[1] 角色 -> 模型文件解析")
    b = m.role_model("brain")
    check("brain 解析成 qwen35", os.path.basename(b) == "qwen35-4b-Q4_K_M.gguf", b)
    check("brain 文件存在", os.path.exists(b))
    t = m.role_model("tool")
    check("tool 解析成 deepseek-coder", os.path.basename(t) == "deepseek-coder-6.7b-instruct.gguf", t)
    check("fast 未配置返回空", m.role_model("fast") == "")
    check("未知角色返回空", m.role_model("wat") == "")

    print("[2] 体积累积：tool 比 brain 大多少")
    sb = os.path.getsize(b) / 1048576
    st = os.path.getsize(t) / 1048576
    check("tool > brain", st > sb, f"tool {st:.0f}MB vs brain {sb:.0f}MB，差 {st - sb:.0f}MB")

    print("[3] 没配置角色时不强制切换 / 配置指向不存在的文件也不切换")
    m2 = DummyMgr({"model_roles": {}})
    rb = m2.role_model("brain")
    check("空 roles 走默认 brain", os.path.basename(rb) == "qwen35-4b-Q4_K_M.gguf", rb)
    m2.active_model = rb
    check("已在该模型 -> True 不重启", m2.ensure_role("brain") is True)
    check("一次都没起进程", m2.spawned == [], str(m2.spawned))
    m3 = DummyMgr({"model_roles": {"brain": "no-such-model.gguf"}})
    check("文件不存在 -> True", m3.ensure_role("brain") is True)
    check("不存在时不起进程", m3.spawned == [], str(m3.spawned))

    print("[4] 已是目标模型时不该重启")
    m4 = DummyMgr(cfg)
    m4.active_model = b
    m4.is_running = lambda: True   # 已在跑
    check("同模型 -> True 不重启", m4.ensure_role("brain") is True)

    print("[4b] 角色真的变了（且内存够）才换模型")
    m6 = DummyMgr(cfg)
    m6.active_model = b
    m6._mem_free_mb = lambda: 12000
    check("brain -> tool 触发一次切换", m6.ensure_role("tool") is True
          and m6.spawned == ["deepseek-coder-6.7b-instruct.gguf"], str(m6.spawned))
    check("切换后 active_model 指向 tool", os.path.basename(m6.active_model) ==
          "deepseek-coder-6.7b-instruct.gguf", m6.active_model)

    print("[5] 内存闸：可用内存不足时不切")
    m5 = DummyMgr(cfg)
    m5._mem_free_mb = lambda: 1000      # 假装只剩 1GB
    m5.is_running = lambda: True
    check("内存不足 -> True 并记 note", m5.ensure_role("tool") is True and "内存不足" in m5.fallback_note,
          m5.fallback_note)

    print("[6] 代码意图识别")
    import main  # noqa: E402  只取判定函数，不建 GUI
    f = main.Controller._looks_like_code

    class _Stub:
        CODE_HINTS = main.Controller.CODE_HINTS

    s = _Stub()
    check("报错 -> 代码", f(s, "这段报错怎么解决") is True)
    check("普通闲聊 -> 非代码", f(s, "今天天气不错，陪我聊聊") is False)
    check("写脚本 -> 代码", f(s, "帮我写个脚本重命名文件") is True)
    check("正则 -> 代码", f(s, "这个正则匹配不到中文") is True)
    check("「异常」这种日常词不触发", f(s, "最近有点异常，睡不好") is False)

    print(f"\n=== {OK} passed, {FAIL} failed ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
