# -*- coding: utf-8 -*-
"""v3.3.x Agentic 薄层回归：懒加载、权限三态、有限步循环。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import agentic_runtime as ar

loads = {"read": 0, "write": 0, "danger": 0}


def _loader(key, result):
    def load():
        loads[key] += 1
        return lambda **kwargs: {"tool": key, "args": kwargs, "result": result}
    return load


reg = ar.ToolRegistry()
reg.register(ar.ToolSpec("read_tool", _loader("read", "r"), ar.READ, "只读"))
reg.register(ar.ToolSpec("write_tool", _loader("write", "w"), ar.WRITE, "写操作"))
reg.register(ar.ToolSpec("danger_tool", _loader("danger", "d"), ar.DANGEROUS, "危险"))
assert reg.describe() and loads == {"read": 0, "write": 0, "danger": 0}
assert reg.names() == ["danger_tool", "read_tool", "write_tool"]

gate = ar.PermissionGate()
assert reg.call(ar.ToolCall("read_tool", {"x": 1}), gate)["result"] == "r"
assert loads["read"] == 1
# 第二次仍命中缓存，不重复加载
reg.call(ar.ToolCall("read_tool", {"x": 2}), gate)
assert loads["read"] == 1

try:
    reg.call(ar.ToolCall("write_tool", {"y": 1}), gate)
    raise AssertionError("write without approval should fail")
except PermissionError as e:
    assert "approval" in str(e)
assert reg.call(ar.ToolCall("write_tool", {"y": 1}, approved=True), gate)["result"] == "w"
assert loads["write"] == 1
try:
    reg.call(ar.ToolCall("danger_tool", {}), gate)
    raise AssertionError("dangerous should fail")
except PermissionError as e:
    assert "dangerous" in str(e)

calls = [ar.ToolCall("read_tool", {"i": 1}), ar.ToolCall("read_tool", {"i": 2})]
loop = ar.AgentLoop(reg, gate, max_steps=2)
res = loop.run(lambda trace: calls.pop(0) if calls else None)
assert res.stopped == "max_steps" and res.steps == 2 and len(res.trace) == 2
res2 = loop.run(lambda trace: None)
assert res2.stopped == "no_more_tools" and res2.steps == 0

print("agentic_runtime_ok", "loads", loads, "steps", res.steps, "stop", res.stopped)
