# -*- coding: utf-8 -*-
"""路径与常量定义。"""
import os
import sys

APP_NAME = "鲸鱼娘桌宠"
APP_KEY = "WhaleGirlPet_2026"
ORG_NAME = "WhaleGirlPet"
APP_VERSION = "3.0.26"

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


def default_data_dir() -> str:
    """出厂默认数据目录（%APPDATA%\\WhaleGirlPet），也是储存位置指针文件的所在地。"""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "WhaleGirlPet")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def data_dir() -> str:
    """当前数据目录；若用户改过储存位置，读默认目录下的 data_root.txt 指向新位置。"""
    root_file = os.path.join(default_data_dir(), "data_root.txt")
    d = ""
    try:
        if os.path.exists(root_file):
            with open(root_file, encoding="utf-8") as f:
                d = f.read().strip()
    except OSError:
        d = ""
    if not d or not os.path.isdir(d):
        d = default_data_dir()
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def accounts_file() -> str:
    return os.path.join(data_dir(), "accounts.json")


def cleanup_pending() -> int:
    """v2.9.9：储存位置迁移后，被进程占用没删掉的旧文件，下次启动再清一遍。

    迁移时把删不掉的项写进 `%APPDATA%\\WhaleGirlPet\\pending_cleanup.json`；
    这里读出来重试，全部清干净就删掉标记文件。返回本次删掉的项数。
    """
    import json
    import shutil

    marker = os.path.join(default_data_dir(), "pending_cleanup.json")
    if not os.path.exists(marker):
        return 0
    try:
        with open(marker, encoding="utf-8") as f:
            info = json.load(f)
    except (OSError, ValueError):
        try:
            os.remove(marker)
        except OSError:
            pass
        return 0
    src = info.get("src") or ""
    names = [n for n in (info.get("names") or []) if n and n != "data_root.txt"]
    # v3.0.21 审计：这个 json 是外部可写的，旧实现直接 os.path.join(src, name) 后 rmtree，
    # 一条 "names": ["..\\..\\Desktop"] 就能借桌宠的权限删掉用户任意目录。
    # 现在只接受「纯文件名」且解析后仍落在 src 之内。
    src_abs = os.path.abspath(src) if src else ""
    left, removed = [], 0
    for name in names:
        if os.path.basename(str(name)) != str(name) or ".." in str(name):
            continue
        p = os.path.abspath(os.path.join(src_abs, str(name))) if src_abs else ""
        try:
            inside = bool(p) and os.path.normcase(
                os.path.commonpath([p, src_abs])) == os.path.normcase(src_abs)
        except ValueError:
            inside = False
        if not inside:
            continue
        try:
            if os.path.isdir(p):
                shutil.rmtree(p)
            elif os.path.exists(p):
                os.remove(p)
            removed += 1
        except OSError:
            left.append(name)
    try:
        if left:
            with open(marker, "w", encoding="utf-8") as f:
                json.dump({"src": src, "names": left}, f, ensure_ascii=False)
        else:
            os.remove(marker)
    except OSError:
        pass
    return removed


def _safe_slug(slug: str) -> str:
    """账号 slug 只接受纯名字：accounts.json 被外部改动时不能变成路径穿越。"""
    s = str(slug or "").strip()
    if not s or s in (".", "..") or s.startswith(".."):
        return ""
    if any(ch in s for ch in ("/", "\\", ":", "*", "?", '"', "<", ">", "|")):
        return ""
    return s


def account_dir(slug: str = "") -> str:
    """账号独立目录；slug 为空时回退到旧版单档案目录。"""
    raw = slug or _ACTIVE["slug"]
    root = data_dir()
    if not raw:
        return root
    safe = _safe_slug(raw)
    if not safe:
        # 非法 slug 不返回数据根：调用方（accounts.delete）会 rmtree 返回值，
        # 回退到根等于把整个数据目录删掉
        return os.path.join(root, "accounts", "_invalid_slug")
    d = os.path.join(root, "accounts", safe)
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

# ---- 外部浏览器（把搜索交给用户本机装的浏览器）----
# v3.0.7 实测教训：旧版只硬编码了 Tabbit 一个浏览器，换台电脑（用户装的是 Chrome /
# Edge / 360 / QQ 浏览器）就一个都找不到，只能退回默认浏览器。
# 现在的顺序：① 系统默认浏览器（注册表 UserChoice）② App Paths 注册表 ③ 常见安装路径。

# 同名品牌 → 家族，决定开新窗口的参数
_CHROMIUM_KEYS = ("chrome", "msedge", "brave", "opera", "vivaldi", "tabbit",
                  "360se", "360chrome", "qqbrowser", "sogouexplorer", "2345explorer",
                  "yandex", "chromium")
_APP_PATH_EXES = ("chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe",
                  "vivaldi.exe", "360se.exe", "360Chrome.exe", "QQBrowser.exe",
                  "sogouexplorer.exe", "2345Explorer.exe", "Tabbit Browser.exe")

BROWSER_CANDIDATES = [
    r"D:\Tabbit Browser\Application\Tabbit Browser.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Tabbit\Application\Tabbit Browser.exe"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Tabbit Browser\Application\Tabbit Browser.exe"),
]


def _browser_family(exe: str) -> str:
    low = (exe or "").lower()
    if "firefox" in low:
        return "firefox"
    if any(k in low for k in _CHROMIUM_KEYS):
        return "chromium"
    return "other"


def _exe_from_command(cmd: str) -> str:
    """从 '"C:\\...\\chrome.exe" -- "%1"' 这样的注册表命令行里抠出 exe 路径。"""
    import re
    cmd = (cmd or "").strip()
    if not cmd:
        return ""
    if cmd.startswith('"'):
        end = cmd.find('"', 1)
        if end > 1:
            return cmd[1:end]
    m = re.match(r"(.+?\.exe)", cmd, re.I)
    return m.group(1).strip() if m else ""


def _reg_value(root, path: str, name: str = ""):
    try:
        import winreg
        with winreg.OpenKey(root, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except (OSError, ImportError):
        return None


def default_browser() -> str:
    """系统当前默认浏览器 exe（打不开 http 链接的那个）。拿不到返回空串。"""
    try:
        import winreg
    except ImportError:
        return ""
    for proto in ("http", "https"):
        prog = _reg_value(
            winreg.HKEY_CURRENT_USER,
            rf"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\{proto}\UserChoice",
            "ProgId")
        if not prog:
            continue
        cmd = _reg_value(winreg.HKEY_CLASSES_ROOT, rf"{prog}\shell\open\command")
        exe = _exe_from_command(cmd)
        if exe and os.path.exists(exe):
            return exe
    return ""


def browsers() -> list:
    """本机所有能用的浏览器，按「默认浏览器优先」排序，返回 [{exe,name,family}]。"""
    out, seen = [], set()

    def _add(exe: str):
        if not exe or not os.path.exists(exe):
            return
        key = os.path.normcase(os.path.abspath(exe))
        if key in seen:
            return
        seen.add(key)
        out.append({"exe": exe, "name": os.path.basename(exe).replace(".exe", ""),
                    "family": _browser_family(exe)})

    _add(default_browser())

    try:
        import winreg
        for exe_name in _APP_PATH_EXES:
            for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                p = _reg_value(root,
                               rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}")
                if p:
                    _add(_exe_from_command(p) or p)
    except ImportError:
        pass

    for p in BROWSER_CANDIDATES:
        _add(p)
    la = os.environ.get("LOCALAPPDATA", "")
    pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    pf86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    for p in (
        os.path.join(pf, r"Google\Chrome\Application\chrome.exe"),
        os.path.join(pf86, r"Google\Chrome\Application\chrome.exe"),
        os.path.join(la, r"Google\Chrome\Application\chrome.exe"),
        os.path.join(pf86, r"Microsoft\Edge\Application\msedge.exe"),
        os.path.join(pf, r"Microsoft\Edge\Application\msedge.exe"),
        os.path.join(pf, r"Mozilla Firefox\firefox.exe"),
        os.path.join(pf86, r"Mozilla Firefox\firefox.exe"),
        os.path.join(la, r"360se6\Application\360se.exe"),
        os.path.join(la, r"360Chrome\Chrome\Application\360chrome.exe"),
        os.path.join(pf86, r"Tencent\QQBrowser\QQBrowser.exe"),
        os.path.join(la, r"Tencent\QQBrowser\Application\QQBrowser.exe"),
        os.path.join(pf86, r"SogouExplorer\SogouExplorer.exe"),
    ):
        _add(p)
    return out


def find_browser() -> str:
    """兼容老调用：返回首选浏览器 exe，都没装返回空串（上层会退回系统默认浏览器）。"""
    bs = browsers()
    return bs[0]["exe"] if bs else ""


def pick_browser() -> tuple:
    """返回 (exe, family)。family: chromium / firefox / other。"""
    bs = browsers()
    if not bs:
        return "", ""
    return bs[0]["exe"], bs[0]["family"]


def browser_args(exe: str, url: str) -> list:
    """按浏览器家族给「新窗口打开」参数。

    Chromium 系：--new-window（否则 URL 会被塞进已有标签页，用户看不到）
    Firefox：-new-window
    其它：不给参数，直接丢 URL
    """
    fam = _browser_family(exe)
    if fam == "chromium":
        return ["--new-window", url]
    if fam == "firefox":
        return ["-new-window", url]
    return [url]



