# -*- coding: utf-8 -*-
"""v3.3.x Agentic 薄层：按需加载工具、权限门、有限步循环编排。

刻意不引入 LangChain/AutoGen 之类重型框架：
- 工具只在第一次被调用时加载，注册表里只存元数据；
- 权限门只做 allow / needs_approval / deny 三态，写操作要显式授权；
- 循环只负责“下一步 → 权限门 → 调用 → 记录”，不接管模型和提示词。

这个模块是给后续聊天工具调用接的骨架，不改变现有 `skills.py` 的 mock 行为。
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

READ = "read"
WRITE = "write"
DANGEROUS = "dangerous"
_PERMISSIONS = {READ, WRITE, DANGEROUS}


@dataclass(frozen=True)
class ToolSpec:
    """工具元数据。loader 必须是“调用时才执行”的零参函数。"""
    name: str
    loader: Callable[[], Callable[..., Any]]
    permission: str = READ
    description: str = ""
    validator: Optional[Callable[[dict], str]] = None

    def __post_init__(self):
        if self.permission not in _PERMISSIONS:
            raise ValueError(f"unknown permission: {self.permission}")


@dataclass
class ToolCall:
    name: str
    args: dict = field(default_factory=dict)
    purpose: str = ""
    approved: bool = False


@dataclass
class Decision:
    allowed: bool
    reason: str
    needs_approval: bool = False


@dataclass
class LoopResult:
    stopped: str
    steps: int
    trace: list


class PermissionGate:
    """最小权限门：读直接放行；写要显式授权；危险动作一律拒绝。"""

    def __init__(self, grants: Optional[set] = None):
        self.grants = set(grants or ())

    def grant(self, name: str):
        self.grants.add(name)

    def revoke(self, name: str):
        self.grants.discard(name)

    def check(self, spec: ToolSpec, args: dict, approved: bool = False) -> Decision:
        if spec.validator:
            why = spec.validator(args or {})
            if why:
                return Decision(False, f"validator:{why}")
        if spec.permission == READ:
            return Decision(True, "read")
        if spec.permission == WRITE:
            if approved or spec.name in self.grants:
                return Decision(True, "write-approved")
            return Decision(False, "write-needs-approval", needs_approval=True)
        return Decision(False, "dangerous-denied")


class ToolRegistry:
    """只存元数据；`load()` 第一次调用时才执行 loader 并缓存 handler。"""

    def __init__(self):
        self._specs = {}
        self._handlers = {}

    def register(self, spec: ToolSpec):
        if not spec.name:
            raise ValueError("empty tool name")
        if spec.name in self._specs:
            raise ValueError(f"duplicate tool: {spec.name}")
        self._specs[spec.name] = spec

    def names(self) -> list:
        return sorted(self._specs)

    def describe(self) -> list:
        """给模型看的工具清单；不触发任何 import。"""
        return [{"name": s.name, "permission": s.permission,
                 "description": s.description}
                for s in self._specs.values()]

    def load(self, name: str) -> Callable[..., Any]:
        if name in self._handlers:
            return self._handlers[name]
        spec = self._specs.get(name)
        if spec is None:
            raise KeyError(f"unknown tool: {name}")
        handler = spec.loader()
        if not callable(handler):
            raise TypeError(f"loader for {name} did not return callable")
        self._handlers[name] = handler
        return handler

    def call(self, call: ToolCall, gate: PermissionGate) -> Any:
        spec = self._specs.get(call.name)
        if spec is None:
            raise KeyError(f"unknown tool: {call.name}")
        decision = gate.check(spec, call.args or {}, approved=call.approved)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        handler = self.load(call.name)
        return handler(**(call.args or {}))


class AgentLoop:
    """有限步编排器。

    `next_call(trace)` 返回 ToolCall 或 None；None/步数用尽/权限拒绝时停。
    模型、提示词、记忆都不在这里，换模型不需要改这个类。
    """

    def __init__(self, registry: ToolRegistry, gate: PermissionGate,
                 max_steps: int = 6):
        self.registry = registry
        self.gate = gate
        self.max_steps = max(1, int(max_steps))

    def run(self, next_call: Callable[[list], Optional[ToolCall]]) -> LoopResult:
        trace = []
        for i in range(self.max_steps):
            call = next_call(trace)
            if call is None:
                return LoopResult("no_more_tools", len(trace), trace)
            try:
                result = self.registry.call(call, self.gate)
                trace.append({"step": i + 1, "name": call.name,
                              "purpose": call.purpose, "ok": True,
                              "result": result})
            except PermissionError as e:
                trace.append({"step": i + 1, "name": call.name,
                              "purpose": call.purpose, "ok": False,
                              "reason": str(e)})
                return LoopResult("permission_denied", len(trace), trace)
            except Exception as e:  # noqa: BLE001
                trace.append({"step": i + 1, "name": call.name,
                              "purpose": call.purpose, "ok": False,
                              "reason": f"{type(e).__name__}: {str(e)[:120]}"})
                return LoopResult("tool_error", len(trace), trace)
        return LoopResult("max_steps", len(trace), trace)
