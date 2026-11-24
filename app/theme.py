# -*- coding: utf-8 -*-
"""主题解析：跟随系统 / 浅色 / 深色。

面板一直挂着深色夜海主题（assets/ui/theme.qss），在浅色桌面上数值条读不清。
这里按 Windows 的浅色开关决定用哪套 qss，并给内联样式提供同一套调色板。
"""
import os

from paths import asset_path

MODES = [("auto", "跟随系统"), ("light", "浅色"), ("dark", "深色")]
DEFAULT = "auto"


def system_is_light() -> bool:
    """读注册表 AppsUseLightTheme（1 = 系统浅色）。读不到就按深色处理。"""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        try:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        finally:
            winreg.CloseKey(key)
        return int(value) == 1
    except Exception:
        return False


def resolve(mode: str) -> str:
    mode = str(mode or DEFAULT).lower()
    if mode == "light":
        return "light"
    if mode == "dark":
        return "dark"
    return "light" if system_is_light() else "dark"


def qss_path(mode: str = DEFAULT) -> str:
    name = "theme_light.qss" if resolve(mode) == "light" else "theme.qss"
    return asset_path(os.path.join("ui", name))


def load_qss(mode: str = DEFAULT) -> str:
    try:
        with open(qss_path(mode), "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def palette(mode: str = DEFAULT) -> dict:
    """给 code 里写死颜色的地方用同一套色，避免浅色主题下出现深底白字。"""
    if resolve(mode) == "light":
        return {
            "chat_bg": "#ffffff", "chat_border": "#c9d8e8",
            "input_bg": "#ffffff", "input_border": "#c9d8e8",
            "hint": "#7b8ca0", "sub": "#657a90",
            "label": "#24303f", "accent": "#2f6fb0",
            "bar_track": "#eef4fa", "bar_fill": "#2f6fb0",
        }
    return {
        "chat_bg": "#131a26", "chat_border": "#223046",
        "input_bg": "#0f1621", "input_border": "#2a3b55",
        "hint": "#7c869c", "sub": "#888888",
        "label": "#e6f1ff", "accent": "#3f7fbf",
        "bar_track": "#1d3552", "bar_fill": "#3f7fbf",
    }
