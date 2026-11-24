# -*- coding: utf-8 -*-
"""本机硬件适配（v2.9.7 第 10~12 条）。

- 安装/首次启动：按显存 + 内存挑"最搭"的本地模型（而不是固定 qwen3-4b）；
- 每次启动比对硬件指纹：换了显卡/内存/CPU 就提醒，并给出新的搭配；
- 用户同意后自动切换推荐模型（已下载就直接用，没下载就提示下载）。
"""
import json

import hwinfo
import models_catalog

FIELDS = ("gpu", "vram_gb", "ram_gb", "threads")
LABELS = {"gpu": "显卡", "vram_gb": "显存(GB)", "ram_gb": "内存(GB)", "threads": "CPU 线程"}


def fingerprint() -> dict:
    h = hwinfo.snapshot()
    return {k: h.get(k) for k in FIELDS}


def best() -> tuple:
    """返回 (catalog 项, 理由)。"""
    return hwinfo.recommend(models_catalog.CATALOG)


def describe(fp: dict) -> str:
    gpu = fp.get("gpu") or "无独显"
    return f"{gpu}｜显存 {fp.get('vram_gb') or 0}GB｜内存 {fp.get('ram_gb') or 0}GB｜{fp.get('threads')} 线程"


def diff(old: dict, new: dict) -> list:
    """返回变化描述列表；空列表表示硬件没变。"""
    if not isinstance(old, dict) or not old:
        return []
    out = []
    for k in FIELDS:
        a, b = old.get(k), new.get(k)
        if k in ("vram_gb", "ram_gb"):
            if a is None or b is None:
                continue
            if abs(float(a) - float(b)) >= 0.5:
                out.append(f"{LABELS[k]}：{a} → {b}")
        elif k == "threads":
            if a and b and int(a) != int(b):
                out.append(f"{LABELS[k]}：{a} → {b}")
        elif (a or "") != (b or ""):
            out.append(f"{LABELS[k]}：{a or '无'} → {b or '无'}")
    return out


def check_and_update(config: dict) -> dict:
    """比对并写回指纹。返回 {changed: [...], old, new, model, why}。"""
    new = fingerprint()
    old = config.get("hw_profile") or {}
    changes = diff(old, new)
    config["hw_profile"] = new
    item, why = best()
    return {
        "changed": changes,
        "first_time": not bool(old),
        "old": old,
        "new": new,
        "model": item,
        "why": why,
    }
