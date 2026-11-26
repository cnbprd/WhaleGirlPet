# -*- coding: utf-8 -*-
"""知识卡 → 规则回归：14 张卡必须都有规则，自动正反例与人工项都要可复现。

    python tools/test_security_rules.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import security_cards
import security_rules


def good_posture():
    return {
        "uac": {"ok": True, "enabled": True, "consent": 5, "secure_desktop": 1},
        "rdp": {"ok": True, "enabled": False},
        "smb1": {"ok": True, "disabled": True, "start": 4},
        "remote_registry": {"ok": True, "disabled": True, "start": 4},
        "guest": {"ok": True, "present": True, "enabled": False},
        "autoplay": {"ok": True, "disabled": True},
        "office_macros": {"ok": True, "unsafe": []},
        "office_protected_view": {"ok": True, "unsafe": []},
        "wsh": {"ok": True, "enabled": False, "disabled": True},
        "event_logs": {"ok": True, "security_readable": True,
                       "items": [{"name": "Security", "max_mb": 20, "mode": "Retain"}]},
    }


def bad_posture():
    p = good_posture()
    p["uac"] = {"ok": True, "enabled": False, "consent": 0, "secure_desktop": 0}
    p["rdp"] = {"ok": True, "enabled": True}
    p["smb1"] = {"ok": True, "disabled": False, "start": 2}
    p["guest"] = {"ok": True, "present": True, "enabled": True}
    p["autoplay"] = {"ok": True, "disabled": False}
    p["office_macros"] = {"ok": True, "unsafe": [{"app": "Excel", "version": "16.0"}]}
    p["office_protected_view"] = {
        "ok": True,
        "unsafe": [{"app": "Word", "version": "16.0",
                    "disabled": [("Internet 文件", "DisableInternetFilesInPV")]}],
    }
    p["wsh"] = {"ok": True, "enabled": True, "disabled": False}
    p["event_logs"] = {"ok": True, "security_readable": True,
                       "items": [{"name": "Security", "max_mb": 5, "mode": "Circular"}]}
    return p


cards = security_cards.all_cards()
rules = security_rules.catalog()
assert len(cards) == 14, f"expected 14 cards, got {len(cards)}"
assert len(rules) == len(cards), f"expected one rule per card, got {len(rules)}"
assert {r["card"] for r in rules} == {c["id"] for c in cards}
assert len({r["id"] for r in rules}) == len(rules), "duplicate rule id"
for r in rules:
    assert r["mode"] in ("auto", "manual"), r
    assert r["level"] in ("high", "warn", "info"), r
    assert r["why"] and r["signals"], r

good = security_rules.evaluate(good_posture())
assert good["summary"]["hit"] == 0, good["summary"]
assert good["summary"]["manual"] == 5, good["summary"]
assert not good["issues"], "good posture produced issues"

bad = security_rules.evaluate(
    bad_posture(),
    startup=[{"name": "evil", "cmd": r"C:\Users\x\AppData\Local\Temp\evil.exe", "system": False}],
    suspect=["njrat"],
)
assert bad["summary"]["hit"] == 9, bad["summary"]
assert bad["summary"]["hit_ids"] == [
    "KR-UAC-01", "KR-RDP-01", "KR-SMB1-01", "KR-GUEST-01",
    "KR-AUTOPLAY-01", "KR-OFFICE-01", "KR-WSH-01", "KR-LOGS-01", "KR-TROJAN-01",
], bad["summary"]["hit_ids"]
assert len(bad["issues"]) == 9
assert all(i.get("rule") and i.get("card") for i in bad["issues"])
assert any("上限仅 5 MB" in i["text"] for i in bad["issues"])

manual = {x["id"] for x in bad["results"] if x["status"] == "manual"}
assert manual == {"KR-ROOTKIT-01", "KR-INJECTION-01", "KR-KALI-01",
                  "KR-DDOS-01", "KR-PHISHING-01"}, manual
print("security_rules_ok", len(rules), "rules; bad hits", bad["summary"]["hit_ids"])
