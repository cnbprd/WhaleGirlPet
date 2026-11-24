# -*- coding: utf-8 -*-
"""全屏判定边界测试。

说明：本机被一个置顶窗口长期占用前台焦点（SetForegroundWindow 抢不过来），
无法在测试里真实制造"全屏前台"，所以这里测三件事：
  1. 覆盖率比较函数 _covers 的边界（这是判定核心）
  2. 本机真实前台窗口（最大化窗口）必须判 False —— 就是当初误判的那种情况
  3. 传入自身 hwnd 必须判 False
    .venv/Scripts/python.exe test_v29_fs.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

import awareness

FAIL = []


def check(name, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(name)


print("[比较函数边界]")
check("刚好全屏 1920x1080", awareness._covers(1920, 1080, 1920, 1080) is True)
check("最大化含任务栏 1920x1032 不算", awareness._covers(1920, 1032, 1920, 1080) is False)
check("GetWindowRect 含阴影 1936x1048 不算", awareness._covers(1936, 1048, 1920, 1080) is False)
check("99.5% 边界下 1918x1078 算", awareness._covers(1918, 1078, 1920, 1080) is True)
check("1911x1075 算", awareness._covers(1911, 1075, 1920, 1080) is True)
check("1910x1074 差一点点不算", awareness._covers(1910, 1074, 1920, 1080) is False)
check("1911x1074 高度不够不算", awareness._covers(1911, 1074, 1920, 1080) is False)
check("零尺寸不算", awareness._covers(0, 0, 1920, 1080) is False)
check("窗口比屏幕大也算（超出边界）", awareness._covers(2000, 1200, 1920, 1080) is True)

print("[真实前台窗口]")
fg = awareness.foreground_fullscreen(0)
print("    当前前台判全屏:", fg, "（本机前台是最大化窗口，期望 False）")
check("最大化前台不误判", fg is False)
check("排除自身 hwnd", awareness.foreground_fullscreen(123456) in (True, False))

print("[电源]")
ps = awareness.power_status()
print("   ", ps)
check("电源读取不抛异常", isinstance(ps, dict) and "on_battery" in ps)

print()
print("失败项:", FAIL) if FAIL else print("全部通过")
sys.exit(1 if FAIL else 0)
