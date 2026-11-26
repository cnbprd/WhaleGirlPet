# -*- coding: utf-8 -*-
"""安全管家知识规则（v3.2 security rules）

把 `security_cards.py` 的 14 张防守知识卡映射成可执行规则：
- 能自动读系统状态的，进 `evaluate()` 生成 issue；
- 必须看日志/流量/应用侧证据的（Rootkit/注入/Kali/DDoS/钓鱼），标成 `manual`，
  不伪造“已检查”，只在报告里保留人工核对项。

所有规则只读、只报不改；不提供攻击步骤、工具参数或 payload。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

import security_cards

CARD_BY_ID = {c["id"]: c for c in security_cards.CARDS}


def _posture(facts: dict) -> dict:
    return facts.get("posture") or {}


def _uac(facts: dict) -> dict:
    return _posture(facts).get("uac") or {}


def _rdp(facts: dict) -> dict:
    return _posture(facts).get("rdp") or {}


def _smb1(facts: dict) -> dict:
    return _posture(facts).get("smb1") or {}


def _guest(facts: dict) -> dict:
    return _posture(facts).get("guest") or {}


def _autoplay(facts: dict) -> dict:
    return _posture(facts).get("autoplay") or {}


def _office(facts: dict) -> dict:
    return _posture(facts).get("office_macros") or {}


def _office_pv(facts: dict) -> dict:
    return _posture(facts).get("office_protected_view") or {}


def _wsh(facts: dict) -> dict:
    return _posture(facts).get("wsh") or {}


def _logs(facts: dict) -> dict:
    return _posture(facts).get("event_logs") or {}


def _startup_flag(facts: dict) -> list:
    """只看用户级启动项里的高可疑落点，避免把正常 AppData 启动项全报。

    知识卡原文包含“临时/下载/公共目录”等信号；这里先做最保守的一层，
    误报优先于漏报控制，不把仅位于 Roaming 的正常软件启动项当木马。
    """
    flagged = []
    for it in facts.get("startup") or []:
        if not isinstance(it, dict) or it.get("system"):
            continue
        cmd = str(it.get("cmd") or "").replace("/", "\\")
        low = cmd.lower()
        name = str(it.get("name") or "").strip() or cmd[:60]
        if any(h in low for h in ("\\temp\\", "\\tmp\\", "\\downloads\\",
                                  "\\public\\", "\\desktop\\")):
            flagged.append(name)
        elif re.search(r"(?i)[a-f0-9]{8,}\.(exe|dll|scr|cmd|bat|ps1)$", cmd):
            flagged.append(name)
    return flagged


def _check_uac(facts: dict) -> Optional[dict]:
    uac = _uac(facts)
    if not uac.get("ok"):
        return None
    bad = []
    if uac.get("enabled") is False:
        bad.append("EnableLUA=0，UAC 已关闭")
    if uac.get("consent") == 0:
        bad.append("ConsentPromptBehaviorAdmin=0，提权不提示")
    if uac.get("secure_desktop") == 0:
        bad.append("PromptOnSecureDesktop=0，安全桌面确认被关闭")
    if not bad:
        return None
    level = "high" if (uac.get("enabled") is False or uac.get("consent") == 0) else "warn"
    return {"level": level, "detail": "；".join(bad)}


def _check_rdp(facts: dict) -> Optional[dict]:
    rdp = _rdp(facts)
    if not rdp.get("ok") or not rdp.get("enabled"):
        return None
    return {"level": "warn", "detail": "3389 登录入口已开启；不用时关闭，必须用时走 VPN/白名单"}


def _check_smb1(facts: dict) -> Optional[dict]:
    smb1 = _smb1(facts)
    if not smb1.get("ok") or smb1.get("disabled"):
        return None
    return {"level": "high", "detail": "mrxsmb10 未禁用；旧式共享协议容易被蠕虫横向利用"}


def _check_guest(facts: dict) -> Optional[dict]:
    guest = _guest(facts)
    if not guest.get("ok") or not guest.get("present") or not guest.get("enabled"):
        return None
    return {"level": "warn", "detail": "Guest 处于启用状态；建议禁用，别让它成为无口令入口"}


def _check_autoplay(facts: dict) -> Optional[dict]:
    auto = _autoplay(facts)
    if not auto.get("ok") or auto.get("disabled"):
        return None
    return {"level": "warn", "detail": "DisableAutoplay 未设 1，且策略没屏蔽可移动盘；U 盘插入后可能自动处理内容"}


def _check_office(facts: dict) -> Optional[dict]:
    macro = _office(facts)
    pv = _office_pv(facts)
    parts = []
    if macro.get("ok"):
        for a in macro.get("unsafe") or []:
            parts.append(f"{a.get('app')} {a.get('version')} 宏=启用所有宏")
    if pv.get("ok"):
        for a in pv.get("unsafe") or []:
            labels = "/".join(str(x[0]) for x in (a.get("disabled") or []))
            parts.append(f"{a.get('app')} {a.get('version')} 受保护视图关闭（{labels}）")
    if not parts:
        return None
    return {"level": "high", "detail": "；".join(parts) + "；正常文档不需要无提示执行宏"}


def _check_wsh(facts: dict) -> Optional[dict]:
    wsh = _wsh(facts)
    if not wsh.get("ok") or not wsh.get("enabled"):
        return None
    return {"level": "warn", "detail": "wscript.exe 仍可用且策略未显式禁用；来源不明的 .vbs/.js/.wsf 不要双击"}


def _check_logs(facts: dict) -> Optional[dict]:
    logs = _logs(facts)
    if not logs.get("ok"):
        return None
    sec = next((x for x in (logs.get("items") or [])
                if isinstance(x, dict) and x.get("name") == "Security"), None)
    if not sec:
        return None
    max_mb = sec.get("max_mb")
    mode = str(sec.get("mode") or "")
    parts = []
    level = "warn"
    if isinstance(max_mb, (int, float)) and max_mb > 0:
        if max_mb < 10:
            level = "high"
            parts.append(f"上限仅 {max_mb:g} MB，很快被覆盖")
        elif max_mb < 20:
            parts.append(f"上限 {max_mb:g} MB，偏小")
    if "circular" in mode.lower():
        parts.append("LogMode=Circular，满了覆盖旧记录")
    if max_mb == 0:
        parts.append("上限读数为 0，无法判断真实保留量")
    if not parts:
        return None
    return {"level": level, "detail": "；".join(parts) + "；建议至少 20 MB 或集中收集"}


def _check_trojan(facts: dict) -> Optional[dict]:
    proc_hits = [str(x) for x in (facts.get("suspect") or []) if x]
    start_hits = _startup_flag(facts)
    if not proc_hits and not start_hits:
        return None
    parts = []
    if proc_hits:
        parts.append("进程名命中：" + "、".join(proc_hits[:4]))
    if start_hits:
        parts.append("用户级启动项落在高可疑目录/无意义文件名：" + "、".join(start_hits[:4]))
    return {"level": "warn", "detail": "；".join(parts) + "；需人工确认，可能是误报"}


@dataclass(frozen=True)
class Rule:
    id: str
    card: str
    title: str
    level: str
    weight: int
    why: str
    mode: str = "auto"
    check: Optional[Callable[[dict], Optional[dict]]] = None


RULES = [
    Rule("KR-UAC-01", "uac", "UAC 被关闭或被设为不提示提权",
         "high", 30, "UAC 是系统最后一道提权确认；它被削弱后，普通程序更容易直接改系统。",
         check=_check_uac),
    Rule("KR-RDP-01", "rdp", "远程桌面 RDP 已开启",
         "warn", 8, "RDP 暴露在登录入口上，弱口令/暴力尝试会直接落在这里。",
         check=_check_rdp),
    Rule("KR-SMB1-01", "smb1", "SMBv1 旧协议仍开着",
         "high", 30, "SMBv1 缺少现代保护，历史上被蠕虫类恶意代码大量横向利用。",
         check=_check_smb1),
    Rule("KR-GUEST-01", "guest", "Guest 来宾账户处于启用状态",
         "warn", 8, "来宾账户缺少强口令约束，容易变成被忽视的入口。",
         check=_check_guest),
    Rule("KR-AUTOPLAY-01", "autoplay", "自动播放未显式关闭",
         "warn", 8, "移动介质里的内容可能在用户点击前就被系统处理。",
         check=_check_autoplay),
    Rule("KR-OFFICE-01", "office", "Office 宏或受保护视图被削弱",
         "high", 30, "“启用所有宏”等于把文档变成可执行入口；关闭受保护视图会让外部文档更早进入可编辑状态。",
         check=_check_office),
    Rule("KR-WSH-01", "wsh", "Windows Script Host 仍可用",
         "warn", 8, "WSH 默认可用；不需要脚本的机器，关掉它比事后查脚本更省事。",
         check=_check_wsh),
    Rule("KR-LOGS-01", "logs", "Security 事件日志过小或循环覆盖",
         "warn", 8, "日志太小会很快覆盖；清日志本身也常是入侵收尾动作。",
         check=_check_logs),
    Rule("KR-TROJAN-01", "trojan", "发现可疑持久化或进程线索",
         "warn", 8, "木马落地通常先留下“持久化 + 外联”；先看启动项、进程名和落点，不凭文件名定罪。",
         check=_check_trojan),
    Rule("KR-ROOTKIT-01", "rootkit", "Rootkit：驱动/服务/启动链需要人工核对",
         "warn", 8, "Rootkit 核心是隐藏；防守方盯住新增内核驱动、服务、启动链和签名是否对得上，不做隐藏技巧。",
         mode="manual"),
    Rule("KR-INJECTION-01", "injection", "注入：输入边界需要应用侧核对",
         "warn", 8, "SQL/命令/脚本注入的共同点是输入越过数据边界；看参数化、编码和最小权限，不提供 payload。",
         mode="manual"),
    Rule("KR-KALI-01", "kali", "扫描/枚举：看边界日志与端口暴露",
         "warn", 8, "Kali 只是工具箱；防守侧只需识别短时间端口/目录探测和 IDS/防火墙告警。",
         mode="manual"),
    Rule("KR-DDOS-01", "ddos", "DDoS：看流量洪峰、半连接与降级预案",
         "warn", 8, "DDoS 是流量洪峰，不是单机技巧；防守靠限速、清洗、熔断和保留流量证据。",
         mode="manual"),
    Rule("KR-PHISHING-01", "phishing", "钓鱼/弱口令：看登录来源与域名",
         "warn", 8, "再好的边界设备也挡不住用户主动交出口令；先验证来源，再开多因素认证。",
         mode="manual"),
]


def catalog() -> list:
    """返回可序列化的规则目录，供安全页/Agent 工具展示。"""
    out = []
    for r in RULES:
        card = CARD_BY_ID.get(r.card) or {}
        out.append({
            "id": r.id, "card": r.card, "title": r.title,
            "level": r.level, "weight": r.weight, "mode": r.mode,
            "why": r.why, "signals": list(card.get("signals") or []),
            "defense": list(card.get("defense") or []),
            "source": card.get("source", ""),
        })
    return out


def evaluate(posture: dict, ports: Optional[list] = None,
             startup: Optional[list] = None, suspect: Optional[list] = None) -> dict:
    """按规则评估一次；自动规则生成 issue，人工规则只留核对项。"""
    facts = {
        "posture": posture or {},
        "ports": ports or [],
        "startup": startup or [],
        "suspect": suspect or [],
    }
    results, issues = [], []
    for r in RULES:
        hit = None
        if r.mode == "auto" and r.check:
            hit = r.check(facts)
        if r.mode != "auto":
            card = CARD_BY_ID.get(r.card) or {}
            detail = "未自动检查；人工核对：" + "；".join(card.get("signals") or [])
            results.append({
                "id": r.id, "card": r.card, "title": r.title,
                "level": r.level, "weight": r.weight,
                "status": "manual", "detail": detail,
            })
            continue
        if hit:
            detail = str(hit.get("detail") or "")
            level = str(hit.get("level") or r.level)
            issue = {
                "level": level,
                "text": r.title + (("：" + detail) if detail else ""),
                "rule": r.id,
                "card": r.card,
                "weight": int(hit.get("weight") or r.weight),
                "why": r.why,
            }
            issues.append(issue)
            results.append({
                "id": r.id, "card": r.card, "title": r.title,
                "level": level, "weight": issue["weight"],
                "status": "hit", "detail": detail,
            })
        else:
            results.append({
                "id": r.id, "card": r.card, "title": r.title,
                "level": r.level, "weight": r.weight,
                "status": "pass", "detail": "",
            })
    hit_ids = [x["id"] for x in results if x["status"] == "hit"]
    manual_ids = [x["id"] for x in results if x["status"] == "manual"]
    summary = {
        "total": len(RULES),
        "auto": sum(1 for r in RULES if r.mode == "auto"),
        "manual": sum(1 for r in RULES if r.mode != "auto"),
        "pass": sum(1 for x in results if x["status"] == "pass"),
        "hit": len(hit_ids),
        "hit_ids": hit_ids,
        "manual_ids": manual_ids,
    }
    return {"summary": summary, "results": results, "issues": issues}
