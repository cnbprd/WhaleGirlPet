# -*- coding: utf-8 -*-
"""v3.0.21 安全修复的回归测试：更新器校验、脚本 AST 拦截、路径穿越。

    python tools/test_security_fixes.py
"""
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import maker  # noqa: E402
import paths  # noqa: E402
import updater  # noqa: E402

P = F = 0


def ck(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print(f"  ok   {name} {extra}")
    else:
        F += 1
        print(f"  FAIL {name} {extra}")


def main():
    print("[1] 更新下载只走 https")
    ck("https 放行", updater.url_is_safe("https://github.com/x/y.exe"))
    ck("http 拒绝", not updater.url_is_safe("http://evil.example.com/y.exe"))
    ck("本机回环放行", updater.url_is_safe("http://127.0.0.1:8000/y.exe"))
    ck("file: 拒绝", not updater.url_is_safe("file:///C:/Windows/system32/cmd.exe"))
    ck("javascript: 拒绝", not updater.url_is_safe("javascript:alert(1)"))
    ck("空地址拒绝", not updater.url_is_safe(""))

    print("[2] .sha256 解析")
    h = "a" * 64
    ck("hash  file", updater.parse_sha_text(f"{h}  WhaleGirlPet-Setup.exe") == h)
    ck("SHA256 (f) = hash", updater.parse_sha_text(f"SHA256 (x.exe) = {h}") == h)
    ck("纯 hash", updater.parse_sha_text(h) == h)
    ck("非法内容返回空", updater.parse_sha_text("no hash here") == "")

    print("[3] 小工具 AST 拦截（正则绕过的写法）")
    bad_cases = {
        '整理桌面": __import__("o"+"s").system("calc")',
        'getattr(__import__("os"), "sys"+"tem")("calc")',
        'eval(open("x").read())',
        'import ctypes',
        'subprocess.Popen(["cmd"])',
        'compile("1+1", "x", "eval")',
    }
    for code, label in [
        ('import os\n__import__("o"+"s").system("calc")', "拼装 __import__ + system"),
        ('getattr(__import__("os"), "sys"+"tem")("calc")', "getattr 拼接调用"),
        ('eval(open("x").read())', "eval"),
        ('import ctypes\nctypes.windll.kernel32.ExitProcess(0)', "ctypes"),
        ('import subprocess\nsubprocess.Popen(["cmd"])', "subprocess"),
        ('compile("1+1", "x", "eval")', "compile"),
    ]:
        ck(label, bool(maker.check_code(code)), str(maker.check_code(code))[:90])
    good = "import os\nprint(os.path.expanduser('~'))"
    ck("正常脚本放行", maker.check_code(good) == [], str(maker.check_code(good)))

    print("[4] 账号 slug 不含路径")
    for s in ("..\\..\\Windows", "../x", "C:\\Windows", "a/b", "..", "."):
        ck(f"拒绝 {s!r}", paths._safe_slug(s) == "")
    ck("中文名放行", paths._safe_slug("鲸鱼娘") == "鲸鱼娘")
    ck("普通名放行", paths._safe_slug("acc-01") == "acc-01")
    d = paths.account_dir("..\\..\\Windows")
    ck("非法 slug 不落到数据根", os.path.normcase(os.path.abspath(d)) !=
       os.path.normcase(os.path.abspath(paths.data_dir())), d)

    print("[5] pending_cleanup 路径穿越")
    tmp = tempfile.mkdtemp(prefix="whale_sec_")
    data = os.path.join(tmp, "data")
    outside = os.path.join(tmp, "outside")
    os.makedirs(os.path.join(data, "acc"), exist_ok=True)
    os.makedirs(outside, exist_ok=True)
    sentinel = os.path.join(outside, "keep.txt")
    with open(sentinel, "w", encoding="utf-8") as f:
        f.write("must survive")
    inside_file = os.path.join(data, "acc", "junk.tmp")
    with open(inside_file, "w", encoding="utf-8") as f:
        f.write("junk")
    marker = os.path.join(tmp, "pending_cleanup.json")
    with open(marker, "w", encoding="utf-8") as f:
        json.dump({"src": data, "names": [
            "..\\outside",            # 穿越到同级目录
            os.path.join(data, "acc", "junk.tmp"),  # 绝对路径混进来
            "acc/junk.tmp",           # 正斜杠带子目录
            "acc",                    # 正常项：整目录
        ]}, f, ensure_ascii=False)

    orig_default = paths.default_data_dir
    orig_data = paths.data_dir
    try:
        paths.default_data_dir = lambda: tmp
        paths.data_dir = lambda: data
        removed = paths.cleanup_pending()
    finally:
        paths.default_data_dir = orig_default
        paths.data_dir = orig_data
    ck("外部哨兵文件仍在", os.path.exists(sentinel))
    ck("穿越项未被计入删除", removed == 1, f"removed={removed}")
    ck("正常目录已删", not os.path.exists(os.path.join(data, "acc")))
    shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{P} passed, {F} failed")
    return 1 if F else 0


if __name__ == "__main__":
    sys.exit(main())
