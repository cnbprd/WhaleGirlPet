# -*- coding: utf-8 -*-
"""v3.0.14 聊天输出清洗单测：6 类「乱」各来一条，看清洗后是否只剩人话。

跑法（PowerShell）：
  $env:QT_QPA_PLATFORM="offscreen"; $env:PYTHONPATH="F:/WhaleGirlPet/app"
  & "F:/WhaleGirlPet/.venv/Scripts/python.exe" tools/test_polish.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import main as app_main  # noqa: E402


def POLISH(s):
    """没起 Controller 实例也能测：这个函数不碰 self，直接手绑一个 None 进去。"""
    return app_main.Controller._polish_reply(None, s)

CASES = [
    ("markdown 粗体", "**好的！** 主人今天想聊什么呀？", "好的！ 主人今天想聊什么呀？"),
    ("代码块", "我可以写：\n```json\n{\"a\":1}\n```\n就这样。", "我可以写： 就这样。"),
    ("列表/标题", "回答：\n## 方案\n- 第一点\n- 第二点\n", "回答： 方案 第一点 第二点"),
    ("整句复读", "我在呢。我在呢。我在呢。你想聊什么？", "我在呢。你想聊什么？"),
    ("链接", "主人，我在 [这里](https://example.com/a) 等你", "主人，我在 这里 等你"),
    ("空行+残标点", "好呀\n\n\n\n那我陪你，", "好呀 那我陪你。"),
]


def main() -> int:
    bad = 0
    for name, src, want in CASES:
        got = POLISH(src)
        ok = got == want
        print(("[ok]  " if ok else "[BAD] ") + name)
        print("    in : " + repr(src))
        print("    out: " + repr(got))
        if not ok:
            print("    want: " + repr(want))
            bad += 1
    print("\n%d/%d 通过" % (len(CASES) - bad, len(CASES)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
