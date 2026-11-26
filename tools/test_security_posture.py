# -*- coding: utf-8 -*-
"""只读安全姿态检查的最小回归；不依赖 GUI，不改注册表。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import secscan

p = secscan.security_posture()
for key in ("uac", "rdp", "smb1", "remote_registry"):
    assert key in p, f"missing {key}"
assert "ok" in p["uac"] and "enabled" in p["uac"]
assert "ok" in p["rdp"] and "enabled" in p["rdp"]
assert "ok" in p["smb1"] and "disabled" in p["smb1"]
assert "ok" in p["remote_registry"] and "disabled" in p["remote_registry"]
print("security_posture_ok", {k: p[k].get("ok") for k in p})
