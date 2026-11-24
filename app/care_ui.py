# -*- coding: utf-8 -*-
"""v2.9.7 新增的四个小窗口：

- ActionAskBubble  偶尔蹦出来问「现在做哪个动作」，两个选项，倒计时不选就随机；
- StatusBarWindow  「可显现状态栏」：饿/渴/心情差/快没钱时弹出的大气泡，带打工·投喂·喝水三键；
- SnackShopWindow  零食商城：分类货架、金币购买、联网补货；
- BackpackWindow   背包：饿了才主动亮出来，平时也能手动打开看存货。

全部用 theme.palette() 取色，浅色/深色主题下都不会出现深底白字。
"""
import random

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QPushButton,
                              QScrollArea, QVBoxLayout, QWidget)

import theme
from snacks import CATEGORIES, items_of, price_note


def _qss(ctl) -> str:
    pal = theme.palette(ctl.config.get("theme", theme.DEFAULT))
    return f"""
    QWidget {{ color: {pal['label']}; font-family: 'Microsoft YaHei'; font-size: 12px; }}
    QLabel#hint {{ color: {pal['hint']}; font-size: 11px; }}
    QLabel#title {{ font-size: 14px; font-weight: 600; }}
    QPushButton {{ background-color: {pal['input_bg']}; color: {pal['label']};
                   border: 1px solid {pal['input_border']};
                   border-radius: 8px; padding: 5px 10px; }}
    QPushButton:hover {{ border-color: {pal['accent']}; }}
    QPushButton:disabled {{ color: {pal['hint']}; border-color: {pal['chat_border']}; }}
    QPushButton#accent {{ background-color: {pal['accent']}; color: #ffffff; border: none; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QWidget#card {{ background: {pal['chat_bg']}; border: 1px solid {pal['chat_border']};
                    border-radius: 14px; }}
    """


class _Card(QWidget):
    """统一的无边框圆角小窗底座。"""

    def __init__(self, ctl, title: str, w: int = 320, h: int = 220):
        super().__init__(None, Qt.Tool | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.ctl = ctl
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(_qss(ctl))
        self.resize(w, h)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        self.card = QWidget()
        self.card.setObjectName("card")
        outer.addWidget(self.card)
        self.body = QVBoxLayout(self.card)
        self.body.setContentsMargins(14, 12, 14, 12)
        self.body.setSpacing(8)
        head = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("title")
        head.addWidget(self.lbl_title, 1)
        btn_close = QPushButton("X")
        btn_close.setFixedSize(24, 24)
        btn_close.setStyleSheet("font-weight:700; padding:0;")
        btn_close.clicked.connect(self.close)
        head.addWidget(btn_close)
        self.body.addLayout(head)

    def place_near_pet(self):
        """贴着桌宠右上角显示，越界就翻到另一边。"""
        pet = getattr(self.ctl, "pet", None)
        scr = QGuiApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()
        if pet is None:
            x, y = scr.right() - w - 40, scr.bottom() - h - 80
        else:
            x = pet.x() + pet.width() - 40
            y = pet.y() - h + 40
            if x + w > scr.right():
                x = pet.x() - w + 40
            if y < scr.top():
                y = pet.y() + 40
        self.move(max(scr.left() + 8, min(x, scr.right() - w - 8)),
                 max(scr.top() + 8, min(y, scr.bottom() - h - 8)))


class ActionAskBubble(_Card):
    """选项气泡：动作提问 / 打工选项共用。超时没选就随机取一个。"""

    def __init__(self, ctl, pairs, timeout_ms=12000, title="现在想做哪个？",
                 tip="挑一个，或者不理我——过一会儿我自己随便来一个。", on_pick=None):
        super().__init__(ctl, title, w=310, h=154)
        self._pairs = pairs
        self._done = False
        self._on_pick = on_pick
        hint = QLabel(tip)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        self.body.addWidget(hint)
        row = QHBoxLayout()
        for key, label in pairs:
            b = QPushButton(label)
            b.setMinimumHeight(38)
            b.clicked.connect(lambda _=False, k=key: self._pick(k))
            row.addWidget(b)
        self.body.addLayout(row)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._timeout)
        self._timer.start(timeout_ms)
        self.place_near_pet()
        self.show()
        self.raise_()

    def _pick(self, key):
        if self._done:
            return
        self._done = True
        self._timer.stop()
        if self._on_pick:
            self._on_pick(key)
        else:
            self.ctl.do_action(key)
        self.close()

    def _timeout(self):
        if self._done:
            return
        self._done = True
        key = self._pairs[random.randrange(len(self._pairs))][0]
        if self._on_pick:
            self._on_pick(key)
        else:
            self.ctl.do_action(key)
        self.close()



class StatusBarWindow(_Card):
    """可显现的状态栏：需求提示 + 打工 / 投喂 / 喝水。"""

    NEED_TEXT = {
        "hungry": ("🍚", "肚子空了，吃点东西吧"),
        "thirsty": ("🥤", "有点渴，想喝水"),
        "mood": ("💧", "心情不太好，陪陪我"),
        "coins": ("🪙", "金币快见底了，得去打工"),
    }

    def __init__(self, ctl):
        super().__init__(ctl, "状态栏", w=340, h=228)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close)
        self.lbl_need = QLabel("")
        self.lbl_need.setWordWrap(True)
        self.body.addWidget(self.lbl_need)
        self.lbl_nums = QLabel("")
        self.lbl_nums.setObjectName("hint")
        self.lbl_nums.setWordWrap(True)
        self.body.addWidget(self.lbl_nums)
        row = QHBoxLayout()
        for text, slot in (("去打工", self._work), ("投喂", self._feed), ("喝水", self._drink)):
            b = QPushButton(text)
            b.setMinimumHeight(36)
            b.clicked.connect(slot)
            row.addWidget(b)
        self.body.addLayout(row)
        tip = QLabel("点一下就去办，不理我 40 秒后自己收起来。")
        tip.setObjectName("hint")
        self.body.addWidget(tip)

    def show_need(self, kind: str):
        emoji, text = self.NEED_TEXT.get(kind, ("💬", "陪我一会儿"))
        st = self.ctl.state
        self.lbl_title.setText("状态栏")
        self.lbl_need.setText(f"{emoji} {text}")
        self.lbl_nums.setText(
            f"饱食 {st.hunger:.0f}　水分 {st.thirst:.0f}　心情 {st.mood:.0f}　金币 {st.coins}")
        self.place_near_pet()
        self.show()
        self.raise_()
        self._timer.start(40_000)

    def _work(self):
        self.ctl.offer_work()
        self.close()

    def _feed(self):
        self.ctl.beg_snack()
        self.close()

    def _drink(self):
        self.ctl.do_drink()
        self.close()


class SnackShopWindow(_Card):
    """零食商城：分类货架，金币购买，联网补货。"""

    def __init__(self, ctl):
        super().__init__(ctl, "零食商城", w=420, h=430)
        self._cat = "主食"
        row = QHBoxLayout()
        row.setSpacing(4)
        self.cat_btns = {}
        for cat in CATEGORIES:
            b = QPushButton(cat)
            b.setCheckable(True)
            b.setFixedHeight(26)
            b.clicked.connect(lambda _=False, c=cat: self.switch(c))
            self.cat_btns[cat] = b
            row.addWidget(b)
        self.body.addLayout(row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.holder = QWidget()
        self.holder.setObjectName("holder")
        self.holder.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self.holder)
        self.grid.setSpacing(6)
        self.scroll.setWidget(self.holder)
        self.body.addWidget(self.scroll, 1)

        foot = QHBoxLayout()
        self.lbl_coins = QLabel("")
        foot.addWidget(self.lbl_coins, 1)
        btn_online = QPushButton("联网补货")
        btn_online.clicked.connect(self.refresh_online)
        foot.addWidget(btn_online)
        self.body.addLayout(foot)
        self.lbl_msg = QLabel("")
        self.lbl_msg.setObjectName("hint")
        self.lbl_msg.setWordWrap(True)
        self.body.addWidget(self.lbl_msg)
        note = QLabel(price_note())
        note.setObjectName("hint")
        note.setWordWrap(True)
        self.body.addWidget(note)

        self.switch("主食")
        self.place_near_pet()

    def switch(self, cat: str):
        self._cat = cat
        for c, b in self.cat_btns.items():
            b.setChecked(c == cat)
        self.rebuild()

    def rebuild(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        items = items_of(self._cat)
        if not items:
            tip = QLabel("这个货架还空着，点「联网补货」去找点新口味。")
            tip.setObjectName("hint")
            self.grid.addWidget(tip, 0, 0, 1, 2)
        for i, it in enumerate(items):
            b = QPushButton(f"{it['emoji']} {it['name']}\n{it['cost']} 金币")
            b.setMinimumHeight(50)
            b.setEnabled(self.ctl.state.coins >= it["cost"])
            b.clicked.connect(lambda _=False, k=it["key"]: self.buy(k))
            self.grid.addWidget(b, i // 2, i % 2)
        self.lbl_coins.setText(f"金币：{self.ctl.state.coins}")

    def buy(self, key):
        ok, msg = self.ctl.buy_snack(key)
        self.lbl_msg.setText(msg)
        self.rebuild()

    def refresh_online(self):
        self.lbl_msg.setText("正在联网找货……几秒就好。")
        self.repaint()
        added = self.ctl.refresh_shop_online()
        if added:
            self.switch("新品")
            self.lbl_msg.setText("淘到 %d 款新零食：%s" % (
                len(added), "、".join(x["name"] for x in added)))
        elif added == []:
            self.lbl_msg.setText("这次没淘到新的，架子上这些先吃着。")
        else:
            self.lbl_msg.setText("联网没成功，先看现有货架。")
        self.rebuild()


class BackpackWindow(_Card):
    """背包：显示存着的零食，点一下就吃一份。"""

    def __init__(self, ctl):
        super().__init__(ctl, "大肥鱼的背包", w=340, h=300)
        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        self.body.addLayout(self.grid)
        self.lbl_tip = QLabel("")
        self.lbl_tip.setObjectName("hint")
        self.lbl_tip.setWordWrap(True)
        self.body.addWidget(self.lbl_tip, 1)
        self.place_near_pet()
        self.rebuild()

    def rebuild(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        bag = self.ctl.state.bag_list()
        if not bag:
            self.lbl_tip.setText("背包是空的。饿了的时候我会自己翻一遍——你也可以先塞点进来。")
            return
        for i, (it, n) in enumerate(bag):
            b = QPushButton(f"{it['emoji']} {it['name']} ×{n}")
            b.setMinimumHeight(38)
            b.clicked.connect(lambda _=False, k=it["key"]: self.eat(k))
            self.grid.addWidget(b, i // 2, i % 2)
        self.lbl_tip.setText("点一份就吃掉；背包空了我再自己去讨。")

    def eat(self, key):
        self.ctl.eat_from_bag(key)
        self.rebuild()
        if not self.ctl.state.bag_list():
            QTimer.singleShot(1200, self.close)
