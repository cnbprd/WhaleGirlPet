# -*- coding: utf-8 -*-
"""安全管家新能力自测：EICAR 两层自证 + SHA256 黑白名单 → 命中/跳过/缓存失效。
全部在临时 data_dir 里跑，不碰用户真实名单。用真机 venv 跑：
    python tools/test_guard_hash.py
"""
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import guard_core as g  # noqa: E402

P = 0
F = 0


def ck(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print(f"  ok   {name} {extra}")
    else:
        F += 1
        print(f"  FAIL {name} {extra}")


def main():
    tmp = tempfile.mkdtemp(prefix="whale_guard_test_")
    data = os.path.join(tmp, "data")
    os.makedirs(data, exist_ok=True)
    try:
        rules = g.load_rules(data)
        ck("内置规则含 AV-EICAR", any(r["id"] == "AV-EICAR" for r in rules), f"共 {len(rules)} 条")

        print("[1] EICAR 两层自证")
        st = g.eicar_selftest(data, rules)
        ck("规则层认出标准串", st["rule_match"], "")
        ck("端到端已检出（自身命中或系统拦截）",
           st["eicar_hits"] > 0 or st["blocked"] == "system",
           f"hits={st['eicar_hits']} blocked={st['blocked'] or 'no'} score={st['eicar_score']}")
        ck("无害对照零命中", st["clean_hits"] == 0)
        ck("自测整体 ok", st["ok"], f"{st}")
        ck("耗时 < 3s", st["ms"] < 3000, f"{st['ms']} ms")

        print("[2] 哈希名单目录初始化")
        paths = g.ensure_hash_dirs(data)
        ck("black.txt 已建", os.path.isfile(paths["black"]))
        ck("white.txt 已建", os.path.isfile(paths["white"]))
        idem = g.ensure_hash_dirs(data)
        ck("重复调用幂等", os.path.isfile(idem["black"]))

        print("[3] 黑名单命中")
        sample = os.path.join(tmp, "sample.exe")
        with open(sample, "wb") as f:
            f.write(b"MZ" + b"\0" * 62 + b"not-a-real-pe")
        sha = g.sha256_of(sample)
        ck("SHA256 长度 64", len(sha) == 64, sha[:12] + "…")
        with open(paths["black"], "a", encoding="utf-8") as f:
            f.write(f"{sha}  # 测试样本\n")
        t = time.time() + 1.5
        os.utime(paths["black"], (t, t))
        hits = g.scan_file(sample, rules, data_dir=data)
        ck("黑名单命中", any(h.get("rule") == "HASH-BLACK" for h in hits),
           str([h.get("rule") for h in hits]))
        ck("黑名单 45 分", g.score_of(hits) >= 45, f"score={g.score_of(hits)}")
        ck("备注被带出", any("测试样本" in (h.get("why") or "") for h in hits))

        print("[4] 白名单优先")
        with open(paths["white"], "a", encoding="utf-8") as f:
            f.write(f"{sha}  # 已知安全\n")
        os.utime(paths["white"], (t + 1, t + 1))
        hits2 = g.scan_file(sample, rules, data_dir=data)
        ck("白名单优先 → 零命中", hits2 == [], str(hits2))
        ck("hash_verdict 判 white", g.hash_verdict(sample, data).get("kind") == "white")

        print("[5] 名单缓存失效")
        with open(paths["white"], "w", encoding="utf-8") as f:
            f.write("# 清空\n")
        os.utime(paths["white"], (t + 2, t + 2))
        hits3 = g.scan_file(sample, rules, data_dir=data)
        ck("白名单清空后恢复黑名单判定", any(h.get("rule") == "HASH-BLACK" for h in hits3))

        print("[6] 性能")
        big = os.path.join(tmp, "big.bin")
        with open(big, "wb") as f:
            f.write(b"\0" * (8 * 1024 * 1024))
        t0 = time.perf_counter()
        sha_big = g.sha256_of(big)
        dt = (time.perf_counter() - t0) * 1000
        ck("8MB 流式哈希正确", len(sha_big) == 64, f"{dt:.1f} ms")
        t0 = time.perf_counter()
        for _ in range(20):
            g.scan_file(big, rules, data_dir=data)
        dt = (time.perf_counter() - t0) * 1000
        ck("20 次扫描 < 2s", dt < 2000, f"{dt:.0f} ms")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{P} passed, {F} failed")
    return 1 if F else 0


if __name__ == "__main__":
    sys.exit(main())
