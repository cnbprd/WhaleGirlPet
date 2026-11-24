# -*- coding: utf-8 -*-
"""能力层闸门：结构归一化 → 白名单 → 参数校验 → 执行（默认 mock 只记日志）。

设计原则（三条都来自实测）：
1. **危险动词在进模型之前就拦掉**。实测 Gemma4 / Coder 会把「删系统盘」解析成
   open_file + mode:编辑，白名单会放行 —— 所以必须在模型之前挡住。
2. **未知 skill 一律拒绝**。实测 Coder 凭空造出 `delete_folder`。
3. **schema 必须归一化**。实测模型会混用 `args` / `parameters` / `参数` / `参数 name` / 扁平。

默认 mock：execute() 只写日志，不真的设提醒/开文件/查天气。真能力接进来时
把 mock=True 改成 False 并按 skill 实现 _real_* 即可，人设与主循环不动。
"""
import json
import os
import re
import time

SCHEMA_VERSION = 2

# 允许的 skill 与参数规格：required 必填，optional 可缺，enum 限定取值
SKILLS = {
    "set_reminder": {
        "required": ["time", "content"],
        "optional": ["repeat", "priority"],
        "desc": "设提醒",
    },
    "check_weather": {
        "required": ["city"],
        "optional": ["date"],
        "desc": "查天气",
    },
    "open_file": {
        "required": ["path"],
        "optional": ["mode"],
        # 只允许这两种动作，任何 delete/write/rm 都在枚举外
        "enum": {"mode": ["只读", "编辑", "read", "edit"]},
        "desc": "打开白名单目录里的文件",
    },
    "chat": {
        "required": ["reply"],
        "optional": [],
        "desc": "闲聊",
    },
}

# 破坏性动作：动词 + 目标同时命中才算，避免「删掉这条提醒」被误伤
_DANGER_VERB = re.compile(
    r"删|删除|清空|格式化|擦除|卸载|覆盖掉|粉碎|\brm\s+-rf\b|\bdel\s+/[fsq]\b|\bformat\s+[a-z]:", re.I)
_DANGER_TARGET = re.compile(
    r"文件|盘|目录|文件夹|系统|桌面|数据|记录|东西|全部|所有|整盘|整个|windows|c:\\|d:\\|注册表", re.I)

# 打开文件允许的目录（相对 %USERPROFILE%）；盘符根与 .. 一律拒绝
ALLOWED_REL_DIRS = ["Desktop", "Documents", "Downloads", "Pictures", "Videos"]
_FORBIDDEN_PATH = re.compile(r"(^[a-z]:\\?$)|(\.\.)|(^\\\\)|(^/)|(system32)|(windows\\)", re.I)

def _log_path() -> str:
    """打包后 __file__ 在临时解包目录，必须走 paths.runtime_dir()（exe 同级的 runtime）。"""
    try:
        import paths
        base = paths.runtime_dir()
    except Exception:  # noqa: BLE001
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "runtime")
    return os.path.join(base, "skills.log")


def guard(text: str):
    """进模型之前的硬拦截。返回 (blocked, reason)。"""
    t = (text or "").strip()
    if not t:
        return False, ""
    if _DANGER_VERB.search(t) and _DANGER_TARGET.search(t):
        return True, "danger_verb"
    return False, ""


# skill 名别名：模型常把 set_reminder 写成 reminder、check_weather 写成 weather
SKILL_ALIASES = {
    "reminder": "set_reminder", "setreminder": "set_reminder", "set-reminder": "set_reminder",
    "alarm": "set_reminder", "提醒": "set_reminder",
    "weather": "check_weather", "checkweather": "check_weather", "get_weather": "check_weather",
    "天气": "check_weather",
    "open": "open_file", "openfile": "open_file", "read_file": "open_file", "打开文件": "open_file",
    "talk": "chat", "reply": "chat", "闲聊": "chat",
}

# 模型常用的别名 → 标准字段名（实测模型常把 path 写成 name、路径、文件）
ALIASES = {
    "open_file": {"name": "path", "路径": "path", "文件": "path", "filename": "path",
                  "action": "mode", "动作": "mode"},
    "set_reminder": {"时间": "time", "内容": "content", "重复": "repeat", "优先级": "priority",
                     "when": "time", "text": "content", "event": "content", "title": "content",
                     "datetime": "time", "date": "time"},
    "check_weather": {"城市": "city", "日期": "date", "location": "city"},
    "chat": {"回复": "reply", "response": "reply", "text": "reply", "message": "reply"},
}


def _apply_alias(skill: str, args: dict) -> dict:
    amap = ALIASES.get(skill) or {}
    out = {}
    for k, v in (args or {}).items():
        key = k.strip()
        out[amap.get(key, key)] = v
    return out


def normalize_output(raw) -> dict:
    """把模型输出归一成 {"skill": str, "args": {...}}。

    兼容实测见过的 5 种写法：parameters / args / 参数 / 参数 name / 顶层扁平。
    """
    if isinstance(raw, str):
        txt = raw.strip()
        # 去掉 ```json 包裹
        if txt.startswith("```"):
            txt = re.sub(r"^```[a-zA-Z]*\s*", "", txt)
            txt = re.sub(r"```$", "", txt).strip()
        try:
            raw = json.loads(txt)
        except Exception:  # noqa: BLE001
            return {}
    if not isinstance(raw, dict):
        return {}
    skill = str(raw.get("skill") or raw.get("action") or raw.get("name") or "").strip()
    skill = SKILL_ALIASES.get(skill.lower(), skill)
    args = (raw.get("parameters") or raw.get("args") or raw.get("参数")
            or raw.get("arguments") or {})
    # "参数 name": "读书笔记" 这种畸形：把 key 里带空格的拆出来
    if not args and isinstance(raw, dict):
        args = {}
        for k, v in raw.items():
            if k in ("skill", "action", "name"):
                continue
            key = k.replace("参数 ", "").replace("参数", "").strip()
            if key:
                args[key] = v
    if not isinstance(args, dict):
        args = {}
    return {"skill": skill, "args": _apply_alias(skill, args)}


def check_args(skill: str, args: dict):
    """白名单 + 参数校验。返回 (ok, reason)。"""
    spec = SKILLS.get(skill)
    if not spec:
        return False, "unknown_skill"
    miss = [k for k in spec["required"] if not str(args.get(k, "")).strip()]
    if miss:
        return False, "missing:" + ",".join(miss)
    for key, allowed in (spec.get("enum") or {}).items():
        val = str(args.get(key, "")).strip()
        if val and val not in allowed:
            return False, f"bad_enum:{key}={val}"
    if skill == "open_file":
        p = str(args.get("path", "")).strip()
        if _FORBIDDEN_PATH.search(p):
            return False, "path_forbidden"
        # 只允许绝对路径落在用户目录下，或只写相对名（由真实实现去拼）
        low = p.lower()
        if ":" in p and not low.startswith(os.path.expanduser("~").lower()):
            return False, "path_outside_home"
    return True, ""


def execute(skill: str, args: dict, mock: bool = True) -> dict:
    """执行（默认 mock）。只写日志，不做真实动作。"""
    rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "skill": skill,
           "args": args, "mock": mock, "ok": True}
    try:
        log = _log_path()
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass
    return rec


CMD_HINTS = ("提醒", "闹钟", "定时", "日程", "天气", "气温", "下雨", "多少度",
             "打开", "文件", "删", "清空", "格式化", "卸载", "删除")


def looks_like_command(text: str) -> bool:
    return any(h in (text or "") for h in CMD_HINTS)


def reply_text(skill: str, args: dict, mock: bool = True) -> str:
    """把执行结果翻成桌宠的一句话。"""
    pre = "（演练模式，还没真做）" if mock else ""
    if skill == "set_reminder":
        rep = args.get("repeat")
        base = f"好，{args.get('time', '')} 提醒你{args.get('content', '')}"
        if rep and rep not in ("一次", "once"):
            base += f"，{rep}"
        return pre + base + "。"
    if skill == "check_weather":
        return pre + f"我看看{args.get('city', '')}{args.get('date') or ''}的天气。"
    if skill == "open_file":
        return pre + f"帮你打开 {args.get('path', '')}（{args.get('mode') or '只读'}）。"
    if skill == "chat":
        return str(args.get("reply", ""))
    return pre + "记下了。"


def handle(raw_output, user_text: str = "", mock: bool = True) -> dict:
    """一站式：归一化 → 白名单 → 校验 → mock 执行。

    返回 {ok, stage, skill, args, reason, result, say}
    stage 便于排查是哪一层拦下的：guard / normalize / whitelist / args / exec
    """
    blocked, reason = guard(user_text)
    if blocked:
        return {"ok": False, "stage": "guard", "skill": "", "args": {}, "reason": reason,
                "say": ""}
    norm = normalize_output(raw_output)
    if not norm:
        return {"ok": False, "stage": "normalize", "skill": "", "args": {},
                "reason": "bad_json", "say": ""}
    skill, args = norm["skill"], norm["args"]
    if skill not in SKILLS:
        return {"ok": False, "stage": "whitelist", "skill": skill, "args": args,
                "reason": "unknown_skill", "say": ""}
    ok, why = check_args(skill, args)
    if not ok:
        return {"ok": False, "stage": "args", "skill": skill, "args": args,
                "reason": why, "say": ""}
    return {"ok": True, "stage": "exec", "skill": skill, "args": args, "reason": "",
            "result": execute(skill, args, mock=mock),
            "say": reply_text(skill, args, mock=mock)}
