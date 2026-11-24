# -*- coding: utf-8 -*-
"""v2.9.0 验收：环境播报（天气/新闻）、全屏检测、电源检测、台词拼装、权重不回归。

离线部分必须全过；在线部分断网只跳过，不判失败。
    .venv/Scripts/python.exe test_v29.py
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

FAIL = []


def check(name, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(name)


def offline():
    print("[离线]")
    import ambient
    import awareness

    # 1. WMO 天气码中文
    check("weathercode 0→晴", ambient.code_text(0) == "晴")
    check("weathercode 61→小雨", ambient.code_text(61) == "小雨")
    check("weathercode 未知→兜底", ambient.code_text(12345) == "说不清的天")
    check("weathercode 非数字→兜底", ambient.code_text(None) == "说不清的天")

    # 2. 天气台词拼装（含体感差、降水、高温）
    w = {"t": 34.5, "feels": 39.0, "hum": 60, "wind": 5.0, "text": "晴",
         "tmax": 37, "tmin": 28, "pop": 20}
    line = ambient.weather_line(w, "郑州")
    print("    天气台词:", line)
    check("台词含城市", "郑州" in line)
    check("台词含温度", "34.5" in line)
    check("台词含体感", "体感39" in line)
    check("整数不带 .0", "37℃" in line and "28到" in line)
    check("高温提醒", "多喝水" in line)
    check("台词是单句不换行", "\n" not in line)

    w2 = {"t": 2.0, "text": "小雨", "pop": 80, "tmax": 5, "tmin": -1}
    line2 = ambient.weather_line(w2, "郑州")
    print("    寒冷台词:", line2)
    check("低温提醒", "多穿点" in line2)
    check("降水提醒", "带伞" in line2)

    check("空天气→空串", ambient.weather_line({}, "郑州") == "")

    # 3. 新闻台词
    n = ambient.news_line("某厂发布新芯片")
    check("新闻台词含标题", "某厂发布新芯片" in n)

    # 4. 电源 / 全屏（本机只读调用不抛异常）
    ps = awareness.power_status()
    print("    电源:", ps)
    check("power_status 返回三键", set(ps.keys()) == {"on_battery", "percent", "has_battery"})
    check("power_status 不抛异常", isinstance(ps["on_battery"], bool))
    check("桌面机判定不拔电", awareness.on_battery() is False or ps["has_battery"] is True)

    fs = awareness.foreground_fullscreen(0)
    print("    前台全屏:", fs)
    check("fullscreen 返回 bool", isinstance(fs, bool))


def online():
    print("[在线]")
    import ambient
    w = ambient.fetch_weather("郑州")
    print("    天气:", w)
    check("拿到当前温度", w.get("t") is not None)
    check("拿到天气描述", bool(w.get("text")))
    check("标出来源", bool(w.get("src")), str(w.get("src")))
    news = ambient.fetch_news(3)
    print("    新闻条数:", len(news))
    for t in news:
        print("      -", t[:60])
    check("新闻至少 1 条", len(news) >= 1)
    line = ambient.weather_line(w, "郑州")
    print("    实际播报:", line)
    check("实际播报非空", bool(line))


def weights():
    print("[回归] 自主行动权重池仍按心情分档")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication([])  # noqa: F841
    import main as m
    c = m.Controller.__new__(m.Controller)   # 不跑 __init__，只测纯函数
    c.config = {"schedule": {"night_on": True}}

    class S:
        mood = 20
    c.state = S()
    p20 = c.auto_weights()
    S.mood = 90
    p90 = c.auto_weights()
    print("    mood20:", p20)
    print("    mood90:", p90)
    check("低心情 sleep 权重最高", p20["sleep"] == max(p20.values()))
    check("高心情 run 权重明显升高", p90["run"] > p20["run"])
    check("高心情 sleep 权重很低", p90["sleep"] <= 2)


if __name__ == "__main__":
    for fn in (offline, online, weights):
        try:
            fn()
        except Exception:  # noqa: BLE001
            print(f"  EXC  {fn.__name__}")
            traceback.print_exc()
            FAIL.append(fn.__name__ + " 异常")
    print()
    if FAIL:
        print("失败项:", FAIL)
        sys.exit(1)
    print("全部通过")
