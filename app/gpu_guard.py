# -*- coding: utf-8 -*-
"""判断当前是否在跑游戏：命中就不占 GPU，把推理退回 CPU 引擎。

只读进程名，不注入、不读其它进程内存；结果缓存 15 秒，避免每轮聊天都扫进程。
"""
import time

import psutil

# 命中规则：进程名（小写、去掉 .exe）包含下列任一片段
GAME_HINTS = (
    "cs2", "csgo", "dota2", "leagueclient", "league of legends", "valorant",
    "genshinimpact", "starrail", "wutheringwaves", "zenlesszonezero",
    "pubg", "game", "-win64-shipping", "shipping-win64",
    "eldenring", "sekiro", "blackmythwukong", "cyberpunk2077", "rdr2", "gta5",
    "minecraft", "apex_legends", "overwatch", "narakabladepoint",
    "deltaforce", "crossfire", "dnf", "wow", "honorofkings", "jyxq",
    "steam", "epicgameslauncher", "wegame", "battle.net", "ubisoft",
    "unityplayer", "unreal", "riotclientservices", "riotclientux",
)

# 明显不是游戏、但名字里带 game 的，排除掉
EXCLUDE = ("gamebar", "gamebarpresencewriter", "gameinput", "gamingapp", "gaming svc",
           "steamwebhelper", "steamservice", "epicwebhelper")

_cache = {"t": 0.0, "hit": False, "name": ""}
_TTL = 15.0


def _scan():
    try:
        procs = []
        for p in psutil.process_iter(["name"]):
            n = (p.info.get("name") or "").lower()
            if n.endswith(".exe"):
                n = n[:-4]
            if n:
                procs.append(n)
    except Exception:  # noqa: BLE001
        return False, ""
    for n in procs:
        if any(x in n for x in EXCLUDE):
            continue
        for h in GAME_HINTS:
            if h in n:
                return True, n
    return False, ""


def game_running(force: bool = False) -> bool:
    now = time.time()
    if force or now - _cache["t"] > _TTL:
        hit, name = _scan()
        _cache.update({"t": now, "hit": hit, "name": name})
    return bool(_cache["hit"])


def game_name() -> str:
    game_running()
    return _cache["name"]


def summary() -> str:
    if game_running():
        return f"检测到游戏运行（{game_name()}），推理走 CPU，不抢显卡"
    return "没检测到游戏，推理走 GPU"
