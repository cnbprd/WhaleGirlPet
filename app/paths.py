# -*- coding: utf-8 -*-
"""路径与常量定义。"""
import os
import sys

APP_NAME = "鲸鱼娘桌宠"
APP_KEY = "WhaleGirlPet_2026"
ORG_NAME = "WhaleGirlPet"
APP_VERSION = "2.9.4"

# 当前活跃账号 slug；空表示使用旧版单档案目录（向后兼容）
_ACTIVE = {"slug": ""}


def set_active_account(slug: str):
    _ACTIVE["slug"] = (slug or "").strip()


def resource_path(rel: str) -> str:
    """兼容 PyInstaller 打包后的资源路径（_MEIPASS）。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, rel)


def asset_path(rel: str) -> str:
    return resource_path(os.path.join("assets", rel))


def data_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "WhaleGirlPet")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def accounts_file() -> str:
    return os.path.join(data_dir(), "accounts.json")


def account_dir(slug: str = "") -> str:
    """账号独立目录；slug 为空时回退到旧版单档案目录。"""
    slug = slug or _ACTIVE["slug"]
    root = data_dir()
    if not slug:
        return root
    d = os.path.join(root, "accounts", slug)
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def runtime_dir() -> str:
    """本地模型与推理程序目录（不打进 exe，位于程序同级 runtime/）。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    return os.path.join(base, "runtime")


def voice_dir() -> str:
    d = os.path.join(account_dir(), "voices")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def config_file() -> str:
    return os.path.join(account_dir(), "config.json")


# ---- 素材注册表 ----
SKINS = {
    "default":   ("蓝女仆·溟月", "skins/default.png"),
    "longmaid":  ("星绣长裙女仆", "skins/longmaid.png"),
    "blackgown": ("暗夜礼服", "skins/blackgown.png"),
    "blackgreen":("墨绿女仆", "skins/blackgreen.png"),
    "blackred":  ("绯红女仆", "skins/blackred.png"),
    "jk":        ("日式学生制服", "skins/jk.png"),
    "hanfu":     ("汉服襦裙", "skins/hanfu.png"),
    "loli":      ("萝莉·溟月", "loli/default.png"),
    "mature":    ("富江·成熟写实", "skins/mature.png"),
}

# 形态：成熟体 / 萝莉体，切换时自动落到该形态的默认皮肤
SKIN_FORM = {
    "default": "mature", "longmaid": "mature", "blackgown": "mature",
    "blackgreen": "mature", "blackred": "mature", "jk": "mature", "hanfu": "mature",
    "loli": "loli",
}
FORM_LABELS = {"mature": "成熟形态", "loli": "萝莉形态"}
FORM_DEFAULT_SKIN = {"mature": "default", "loli": "loli"}
FORM_SKINS = {
    "mature": ["default", "longmaid", "blackgown", "blackgreen", "blackred", "jk", "hanfu"],
    "loli": ["loli"],
}

EXPRESSIONS = {
    "idle":    "expressions/idle.png",
    "happy":   "expressions/happy.png",
    "eat":     "expressions/eat.png",
    "walk":    "expressions/walk.png",
    "sleep":   "expressions/sleep.png",
    "sleepy":  "expressions/sleepy.png",
    "shy":     "expressions/shy.png",
    "angry":   "expressions/angry.png",
    "curious": "expressions/curious.png",
    "pat":     "expressions/pat.png",
}

# 专属动作立绘（与表情分开，动作结束后回到默认皮肤/表情）
ACTIONS = {
    "wave":     ("开心挥手", "actions/wave.png"),
    "dance":    ("跳支舞", "actions/dance.png"),
    "type":     ("敲电脑", "actions/type.png"),
    "balloon":  ("吹气球", "actions/balloon.png"),
    "fireworks":("放烟花", "actions/fireworks.png"),
    "lion":     ("舞狮", "actions/lion.png"),
    "change":   ("换衣服", "actions/change.png"),
}

# 三档大小
SIZE_LEVELS = {"小": 0.7, "中": 1.0, "大": 1.35}

DEFAULT_NAME = "溟月"

# 可绑定本地音频的动作
AUDIO_ACTIONS = [
    ("pat", "摸头"),
    ("feed", "投喂"),
    ("happy", "开心"),
    ("angry", "生气"),
    ("shy", "害羞"),
    ("coin", "金币"),
    ("done", "完成"),
    ("water", "喝水提醒"),
    ("sedentary", "久坐提醒"),
    ("walk", "散步"),
    ("sleep", "睡觉"),
    ("wake", "醒来"),
    ("chat", "聊天回复"),
    ("error", "出错提示"),
    ("wave", "挥手"),
    ("dance", "跳舞"),
    ("change", "换装"),
    ("clean", "清理垃圾"),
    ("wipe", "擦桌面"),
    ("chore", "做家务"),
    ("panic", "慌张"),
]
AUDIO_ACTION_LABELS = dict(AUDIO_ACTIONS)

# ---- 外部浏览器（可选集成：把搜索交给本机装好的 Chromium 系浏览器）----
BROWSER_CANDIDATES = [
    r"D:\Tabbit Browser\Application\Tabbit Browser.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Tabbit\Application\Tabbit Browser.exe"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Tabbit Browser\Application\Tabbit Browser.exe"),
]


def find_browser() -> str:
    """返回可用的外部浏览器路径（优先 Tabbit）；都没装则返回空串。"""
    for p in BROWSER_CANDIDATES:
        if p and os.path.exists(p):
            return p
    return ""
