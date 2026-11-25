# -*- coding: utf-8 -*-
"""v3.0.23 第 2/3/4/5/6/7/8/10 条的程序化复验（真实窗口，不改用户配置）。"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

import main as main_mod  # noqa: E402
import splash  # noqa: E402

R = []


def ck(name, cond, extra=""):
    R.append((name, bool(cond)))
    print(("  ok   " if cond else "  FAIL ") + name + ("  " + str(extra) if extra else ""))


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctl = main_mod.Controller(app)
    ctl.open_panel()
    p = ctl.panel
    p.resize(780, 920)
    p.show()
    p.raise_()
    app.processEvents()
    time.sleep(0.2)
    app.processEvents()

    # 2 启动屏尺寸缩半
    ck("启动屏缩半", (splash.W, splash.H) == (190, 290) and splash.ART_H == 235,
       f"{splash.W}x{splash.H} artH={splash.ART_H}")

    # 6 面板不再置顶
    ck("面板非置顶", not bool(p.windowFlags() & Qt.WindowStaysOnTopHint),
       f"flags={int(p.windowFlags())}")

    # 10 侧栏顺序 12 项
    want = ["账号状态", "养成", "聊天", "桌宠行为", "定时任务", "语音唤醒",
            "音频库", "储存位置", "天气资讯", "自定义模型", "安全体检", "关于与更新"]
    got = [p.side.item(i).text() for i in range(p.side.count())]
    ck("侧栏 12 项顺序", got == want, " / ".join(got))

    # 5 打工并入养成：没有独立「打工」页，养成页有「打工任务」
    ck("无独立打工页", p.tabs.count() == 12 and "打工" not in got)
    idx_feed = got.index("养成")
    texts = [w.text() for w in p.tabs.widget(idx_feed).findChildren(QLabel)]
    ck("养成页含打工任务", any("打工任务" in t for t in texts),
       next((t for t in texts if "打工任务" in t), ""))

    # 7 聊天打开即贴底
    idx_chat = got.index("聊天")
    p.tabs.setCurrentIndex(idx_chat)
    app.processEvents()
    time.sleep(0.25)
    app.processEvents()
    bar = p.chat_scroll.verticalScrollBar()
    ck("聊天打开贴底", bar.value() == bar.maximum(), f"{bar.value()}/{bar.maximum()}")

    # 3 自定义模型页配色跟随主题
    idx_api = got.index("自定义模型")
    p.tabs.setCurrentIndex(idx_api)
    app.processEvents()
    card = p.api_card
    ck("API 卡片配色跟随主题", card.styleSheet().find("chat_bg") < 0 and "0f1621" in card.styleSheet().lower().replace("#", ""),
       card.styleSheet()[:60].replace("\n", " "))

    # 4 编辑中刷新不覆盖
    card.ed_endpoint.setText("https://example.com/v1")
    card.ed_key.setText("sk-test-dirty")
    card._mark_dirty()
    card.refresh()
    app.processEvents()
    ck("编辑中刷新不丢字", card.ed_endpoint.text() == "https://example.com/v1"
       and card.ed_key.text() == "sk-test-dirty",
       card.ed_endpoint.text() + " / " + card.ed_key.text()[:6])
    # 清掉草稿，别把测试值留给用户
    try:
        ctl.config.pop("api_draft", None)
        ctl.save_config()
    except Exception:  # noqa: BLE001
        pass

    # 8 聊天出声：tts 默认开，回复走 priority=1
    ck("tts_on 默认开", bool(ctl.config.get("tts_on", True)))
    src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
    ck("回复 TTS priority=1", "_speak(content, 4200, priority=1)" in src)

    bad = [x for x in R if not x[1]]
    print(f"\n{len(R) - len(bad)} passed, {len(bad)} failed")
    ctl.quit_app()


if __name__ == "__main__":
    main()
