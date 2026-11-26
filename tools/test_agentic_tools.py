# -*- coding: utf-8 -*-
"""注册表懒加载：describe 不 import 业务模块，call 才加载。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import agentic_tools
from agentic_runtime import PermissionGate, ToolCall

reg = agentic_tools.build_registry()
assert {x["name"] for x in reg.describe()} == {"security_cards", "security_learning", "security_posture"}
assert "security_cards" not in sys.modules and "secscan" not in sys.modules
cards = reg.call(ToolCall("security_cards"), PermissionGate())
assert len(cards) >= 14 and "security_cards" in sys.modules
print("agentic_tools_ok", len(cards), "cards", "lazy_ok")
