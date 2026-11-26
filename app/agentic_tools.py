# -*- coding: utf-8 -*-
"""把工程里已有的只读能力注册成 Agentic 工具；模块本身不 import 重实现。

注册表只存 name/描述/权限/loader，真正调用时才执行 loader。
写操作和危险操作不要在这里注册；需要时由上层显式加 grant。
"""
from agentic_runtime import READ, ToolRegistry, ToolSpec


def _load_posture():
    import secscan
    return secscan.security_posture


def _load_cards():
    import security_cards
    return security_cards.all_cards


def _load_learning():
    import security_learning
    return security_learning.scan_library


def build_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(ToolSpec("security_posture", _load_posture, READ,
                          "只读检查 UAC/远程面/Guest/自动播放/Office/日志"))
    reg.register(ToolSpec("security_cards", _load_cards, READ,
                          "返回防守侧安全知识卡"))
    reg.register(ToolSpec("security_learning", _load_learning, READ,
                          "扫描本地安全资料目录并返回路线索引"))
    return reg
