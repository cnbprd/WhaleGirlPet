# -*- coding: utf-8 -*-
"""本机使用统计：定时采样前台窗口，累计各应用使用时长，用于每日开机播报。

数据只写本机 usage.json（按日期分桶），不上传。只记录进程名与累计时长，
不保存窗口标题内容。
"""
import ctypes
import json
import os
import time
from ctypes import wintypes

from paths import account_dir

user32 = ctypes.windll.user32
GetForegroundWindow = user32.GetForegroundWindow
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
OpenProcess = ctypes.windll.kernel32.OpenProcess
QueryFullProcessImageName = ctypes.windll.kernel32.QueryFullProcessImageNameW
CloseHandle = ctypes.windll.kernel32.CloseHandle

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

FRIENDLY = {
    "chrome.exe": "浏览器", "msedge.exe": "浏览器", "firefox.exe": "浏览器",
    "code.exe": "VS Code", "pycharm64.exe": "PyCharm", "devenv.exe": "Visual Studio",
    "wechat.exe": "微信", "qq.exe": "QQ", "dingtalk.exe": "钉钉", "feishu.exe": "飞书",
    "doubao.exe": "豆包", "wps.exe": "WPS", "winword.exe": "Word", "excel.exe": "Excel",
    "powerpnt.exe": "PowerPoint", "notion.exe": "Notion", "obsidian.exe": "Obsidian",
    "explorer.exe": "资源管理器", "potplayermini64.exe": "播放器", "wmplayer.exe": "播放器",
    "steam.exe": "Steam", "game.exe": "游戏", "tabbit browser.exe": "浏览器",
    "python.exe": "Python", "cmd.exe": "终端", "powershell.exe": "终端", "windowsterminal.exe": "终端",
}


def _foreground_process() -> str:
    hwnd = GetForegroundWindow()
    if not hwnd:
        return ""
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""
    h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not h:
        return ""
    buf = ctypes.create_unicode_buffer(1024)
    size = wintypes.DWORD(1024)
    ok = QueryFullProcessImageName(h, 0, buf, ctypes.byref(size))
    CloseHandle(h)
    if not ok:
        return ""
    return os.path.basename(buf.value).lower()


def friendly(name: str) -> str:
    return FRIENDLY.get(name, name)


class UsageTracker:
    def __init__(self, sample_sec: int = 20):
        self.path = os.path.join(account_dir(), "usage.json")
        self.sample_sec = sample_sec
        self.data = self._load()
        self.today = self._today()
        self._dirty = False
        self.session_start = time.time()

    # ---------- 存储 ----------
    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
        except (OSError, ValueError):
            pass
        return {}

    def save(self, force: bool = False):
        if not self._dirty and not force:
            return
        try:
            # 只保留最近 30 天
            for k in sorted(self.data.keys())[:-30]:
                self.data.pop(k, None)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False)
            self._dirty = False
        except OSError:
            pass

    def _today(self) -> str:
        return time.strftime("%Y-%m-%d")

    def _bucket(self, day: str = "") -> dict:
        day = day or self._today()
        b = self.data.setdefault(day, {})
        b.setdefault("apps", {})
        b.setdefault("active_sec", 0)
        b.setdefault("first", "")
        b.setdefault("last", "")
        return b

    # ---------- 采样 ----------
    def tick(self) -> str:
        """采样一次，返回当前前台进程名。"""
        day = self._today()
        if day != self.today:
            self.save(force=True)
            self.today = day
        name = _foreground_process()
        if not name:
            return ""
        b = self._bucket(day)
        if not b["first"]:
            b["first"] = time.strftime("%H:%M")
        b["last"] = time.strftime("%H:%M")
        b["apps"][name] = int(b["apps"].get(name, 0)) + self.sample_sec
        b["active_sec"] = int(b.get("active_sec", 0)) + self.sample_sec
        self._dirty = True
        return name

    # ---------- 汇总 ----------
    def yesterday_key(self) -> str:
        t = time.localtime(time.time() - 86400)
        return time.strftime("%Y-%m-%d", t)

    def report(self, day: str = "") -> dict:
        day = day or self.yesterday_key()
        b = self.data.get(day)
        if not b:
            return {"day": day, "empty": True, "apps": [], "active_sec": 0, "first": "", "last": ""}
        apps = sorted(b.get("apps", {}).items(), key=lambda kv: -kv[1])
        return {
            "day": day,
            "empty": False,
            "active_sec": int(b.get("active_sec", 0)),
            "first": b.get("first", ""),
            "last": b.get("last", ""),
            "apps": [(friendly(n), int(s)) for n, s in apps],
        }

    @staticmethod
    def fmt_duration(sec: int) -> str:
        h, m = divmod(sec // 60, 60)
        if h:
            return f"{h} 小时 {m} 分"
        return f"{m} 分钟"

    def report_text(self, day: str = "") -> str:
        r = self.report(day)
        if r["empty"]:
            return f"{r['day']} 那天本鱼没检测到开机记录，估计你休息去了。"
        total = self.fmt_duration(r["active_sec"])
        head = f"{r['day']} 你在电脑前待了 {total}"
        if r["first"] and r["last"]:
            head += f"（{r['first']}—{r['last']}）"
        top = r["apps"][:5]
        if not top:
            return head + "，没记到具体在忙什么。"
        detail = "、".join(f"{n} {self.fmt_duration(s)}" for n, s in top)
        return head + f"。花得最多的是：{detail}。"
