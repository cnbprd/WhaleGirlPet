# -*- coding: utf-8 -*-
"""事实抽取单测：该记的要记，不该记的（提问/假设/说对方）别记。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from memory import extract_facts  # noqa: E402

SHOULD = [
    ("我叫杨梦柯", [("用户名", "杨梦柯")]),
    ("以后叫我柯柯吧", [("用户名", "柯柯")]),
    ("我今年35岁", [("年龄", "35")]),
    ("我住在郑州中原区", [("所在地", "郑州中原区")]),
    ("我在前置仓上班", [("职业", "前置仓")]),
    ("我最爱吃白米饭", [("喜好", "白米饭")]),
    ("我每天早上六点起", [("习惯", "早上六点起")]),
    ("我明天要交房租", [("计划", "交房租")]),
    ("我下个月要搬家", [("计划", "搬家")]),
    ("我养了一只橘猫", [("宠物", "一只橘猫")]),
]

SHOULD_NOT = [
    "你喜欢吃什么？",
    "我能问个事吗",
    "如果我有钱你会跟我走吗",
    "你会不会觉得我很烦",
    "我想知道明天天气",
]

bad = 0
for text, want in SHOULD:
    got = extract_facts(text)
    ok = got == want
    print(("[ok]  " if ok else "[BAD] ") + f"{text} → {got}")
    if not ok:
        print("    want:", want)
        bad += 1

print("\n--- 不该记的 ---")
for text in SHOULD_NOT:
    got = extract_facts(text)
    ok = got == []
    print(("[ok]  " if ok else "[BAD] ") + f"{text} → {got}")
    if not ok:
        bad += 1

print(f"\n{len(SHOULD)+len(SHOULD_NOT)-bad}/{len(SHOULD)+len(SHOULD_NOT)} 通过")
sys.exit(1 if bad else 0)
