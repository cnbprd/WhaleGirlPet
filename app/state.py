# -*- coding: utf-8 -*-
"""养成数值：饱食度 / 心情 / 口渴 / 亲密度 / 等级经验 / 金币 / 背包。

v2.9.7：
- 零食货架搬到 snacks.py（分类、联网补货、通胀护栏都在那边）；
- 加「口渴」条与「背包」：买来的零食先落背包，吃的时候才走背包；
- 吃一份零食不再当场扣钱，改为先从背包取（旧调用会自动买一份，兼容面板老代码）。
"""
import random
import time

from snacks import SNACKS, by_key


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


# ================= v3.0.0 数值模型 =================
# 参考依据（联网查的公开玩法参数，按桌宠节奏折算）：
#   拓麻歌子社区实测：成长期饥饿约 50 分钟掉 1 心；Dilder 设计文档 hunger -1/10min、
#   happiness -1/15min；MiroPets hunger -2/h、happiness -1/h（偏休闲）；
#   QQ 宠物：打工/玩耍消耗明显高于空挂，泡温泉反而回状态。
# 这里取折中：饱食 100 → 0 约 14 小时，差不多“白天开一天，晚上回来才要饭”的节奏。
BASE_HUNGER_PER_MIN = 0.12      # 醒着每分钟饱食下降（v3.0.25：从 0.30 调慢，用户反馈掉太快）
SLEEP_FACTOR = 0.35             # 睡觉时基础代谢降到 35%
THIRST_RATIO = 0.55             # 水分降速 = 饱食的 55%（100 → 0 约 25 小时）
MOOD_IDLE_GRACE_MIN = 25        # 无沟通无互动满 25 分钟后心情才开始掉
MOOD_PER_MIN = 0.30             # 心情每分钟下降
MOOD_SLEEP_PAUSE = True         # 睡着时不计心情流失

# 动作一次性消耗（饱食, 水分）：做了什么动作就扣多少，和"空挂"分开算
ACTION_DRAIN = {
    "walk": (1.2, 0.7),         # 散步 8 秒
    "run": (4.0, 2.4),          # 满屏跑 60 秒
    "dance": (2.4, 1.4),        # 跳舞
    "jump": (0.6, 0.35),        # 跳一下
    "squish": (0.3, 0.2),       # 被捏
    "work_study": (3.0, 1.8),
    "work_run": (6.0, 3.6),
    "work_rest": (1.0, 0.6),    # 摸鱼反而省
    "work_clean": (5.0, 3.0),
    "work_wipe": (4.0, 2.4),
    "work_chores": (6.0, 3.6),
    "play": (3.0, 1.8),         # 玩玩具
}

# 亲密度成长（互动类型 → 单次加成；每日次数上限，超过后只按两折计）
INTIMACY_GAIN = {
    "pat": (1.0, 40),           # 摸头：少量、可多次
    "chat": (1.0, 20),          # 聊天：一次一句
    "feed": (1.0, 6),           # 普通零食
    "feed_fav": (2.0, 4),       # 她爱吃的（心情加成高）
    "play": (3.0, 3),           # 玩玩具：中等至大量
    "toy_buy": (5.0, 1),        # 第一次买新玩具
    "clean_like": (0.5, 4),     # 洗澡/清理类照料
}
INTIMACY_LABELS = ((80, "挚友"), (60, "亲密"), (40, "朋友"), (20, "熟悉"), (0, "陌生"))


class PetState:
    def __init__(self):
        self.hunger = 70.0      # 饱食度 0-100
        self.thirst = 65.0      # 水分 0-100（低于 35 会喊渴）
        self.mood = 75.0        # 心情 0-100
        self.intimacy = 10.0    # 亲密度 0-100
        self.level = 1
        self.exp = 0
        self.coins = 30
        self.bag = {}           # 背包：{零食 key: 份数}
        # v3.0.0：数值模型要用到的时间戳与每日计数
        self.last_interact = time.time()   # 最近一次被沟通/互动
        self._last_decay = time.time()     # 上次结算衰减的墙钟
        self._gain_day = time.strftime("%Y-%m-%d")
        self._gain_count = {}              # {互动类型: 今日次数}
        # v3.0.1：首启新人礼包只发一次，靠这个标记记住（存进 config 的 save 里）
        self.gift_v3 = False
        self._gift_just_sent = False   # 本次启动是否刚发过礼包（main 用它决定立刻落盘）

    # ---------- 等级 ----------
    def exp_need(self):
        return self.level * 100

    def add_exp(self, n):
        self.exp += n
        leveled = False
        while self.exp >= self.exp_need():
            self.exp -= self.exp_need()
            self.level += 1
            self.coins += 20
            leveled = True
        return leveled

    # ---------- 背包 ----------
    def bag_count(self) -> int:
        return sum(int(v) for v in self.bag.values() if v > 0)

    def bag_list(self) -> list:
        """[(item, 份数)]，按货架顺序排。"""
        out = []
        for k, n in self.bag.items():
            if n > 0:
                it = by_key(k)
                if it:
                    out.append((it, int(n)))
        return out

    def add_to_bag(self, key: str, n: int = 1):
        self.bag[key] = int(self.bag.get(key, 0)) + int(n)

    def take_from_bag(self, key: str) -> bool:
        if int(self.bag.get(key, 0)) <= 0:
            return False
        self.bag[key] = int(self.bag[key]) - 1
        if self.bag[key] <= 0:
            self.bag.pop(key, None)
        return True

    def buy(self, key: str):
        """买一份放背包（不立刻吃）。返回 (ok, msg)。"""
        snack = by_key(key)
        if not snack:
            return False, "货架上没有这种零食。"
        if self.coins < snack["cost"]:
            return False, f"金币不够，还差 {snack['cost'] - self.coins}。先去打会儿工吧。"
        self.coins -= snack["cost"]
        self.add_to_bag(key, 1)
        return True, f"买了一份 {snack['emoji']}{snack['name']}，放进背包了（剩 {self.coins} 金币）。"

    # ---------- 互动 ----------
    def _apply_snack(self, snack: dict):
        self.hunger = _clamp(self.hunger + snack.get("hunger", 0))
        self.thirst = _clamp(self.thirst + snack.get("water", 0))
        self.mood = _clamp(self.mood + snack.get("mood", 0))
        # v3.0.0：她爱吃的（心情加成 ≥15）算「喜好食物」，亲密度给双份
        kind = "feed_fav" if int(snack.get("mood", 0)) >= 15 else "feed"
        self.gain_intimacy(kind)
        return self.add_exp(snack.get("exp", 0))

    def eat(self, key: str, auto_buy: bool = True):
        """吃一份：优先吃背包里的；背包没有且 auto_buy 就现场买一份。"""
        snack = by_key(key)
        if not snack:
            return False, "没有这种零食。"
        if not self.take_from_bag(key):
            if not auto_buy:
                return False, f"背包里没有 {snack['name']} 了。"
            if self.coins < snack["cost"]:
                return False, "金币不够啦，先去打会儿工攒一攒。"
            self.coins -= snack["cost"]
        leveled = self._apply_snack(snack)
        msg = f"{snack['emoji']} {snack['name']}，吃掉了。"
        if leveled:
            msg += f"\n升到 Lv.{self.level}！奖励 20 金币。"
        return True, msg

    def feed(self, key):
        """旧接口：面板/语音还在调它。等价于「吃一份」。"""
        return self.eat(key, auto_buy=True)

    def drink(self):
        """喝水：补水，顺带一点点心情。成功返回 (True, msg)。"""
        if self.thirst >= 92:
            return False, "刚喝过，肚子都晃荡了。"
        self.thirst = _clamp(self.thirst + 32)
        self.mood = _clamp(self.mood + 2)
        self.gain_intimacy("clean_like")
        self.add_exp(2)
        return True, random.choice([
            "咕咚咕咚——水喝下去了，喉咙舒服多了。",
            "喝水时间到，一口气灌了半杯。",
            "喝完水，尾巴都精神了。",
        ])


    # ---------- v3.0.0 互动、亲密度、衰减 ----------
    def touch(self):
        """记录一次「被沟通 / 被互动」，心情从这一刻重新计时。"""
        self.last_interact = time.time()

    def _gain_cap(self, kind: str) -> float:
        """每日次数上限：超过上限后只按两折给，防止狂点刷满亲密度。"""
        gain, cap = INTIMACY_GAIN.get(kind, (1.0, 10))
        day = time.strftime("%Y-%m-%d")
        if day != self._gain_day:
            self._gain_day = day
            self._gain_count = {}
        n = int(self._gain_count.get(kind, 0))
        self._gain_count[kind] = n + 1
        return gain if n < cap else gain * 0.2

    def gain_intimacy(self, kind: str):
        self.intimacy = _clamp(self.intimacy + self._gain_cap(kind))
        self.touch()

    def bond_label(self) -> str:
        for th, name in INTIMACY_LABELS:
            if self.intimacy >= th:
                return name
        return "陌生"

    def spend(self, action: str):
        """动作一次性消耗：做什么动作扣多少，和空挂的基础代谢分开算。"""
        h, w = ACTION_DRAIN.get(action, (0.0, 0.0))
        if h:
            self.hunger = _clamp(self.hunger - h)
        if w:
            self.thirst = _clamp(self.thirst - w)

    def pat(self):
        self.mood = _clamp(self.mood + 2)
        self.gain_intimacy("pat")
        self.add_exp(2)

    def chat_bonus(self):
        self.mood = _clamp(self.mood + 1)
        self.gain_intimacy("chat")
        self.add_exp(3)

    def decay(self, sleeping: bool = False, now: float | None = None):
        """按真实经过时间结算；心情只在「无沟通无互动」超过 25 分钟后才掉。"""
        now = time.time() if now is None else now
        dt = max(0.0, min(now - self._last_decay, 6 * 3600))   # 跨休眠最多补 6 小时
        self._last_decay = now
        mins = dt / 60.0
        factor = SLEEP_FACTOR if sleeping else 1.0
        drop = BASE_HUNGER_PER_MIN * mins * factor
        self.hunger = _clamp(self.hunger - drop)
        self.thirst = _clamp(self.thirst - drop * THIRST_RATIO)
        idle_min = (now - self.last_interact) / 60.0
        if not (sleeping and MOOD_SLEEP_PAUSE) and idle_min > MOOD_IDLE_GRACE_MIN:
            self.mood = _clamp(self.mood - MOOD_PER_MIN * mins)
        return self.hunger < 25 or self.mood < 25 or self.thirst < 25

    # ---------- 需求判断（状态栏 / 讨零食用） ----------
    def is_hungry(self, threshold: float = 45) -> bool:
        return self.hunger < threshold

    def is_thirsty(self, threshold: float = 40) -> bool:
        return self.thirst < threshold

    def is_broke(self) -> bool:
        """金币接近枯竭：剩余不足 20%。基线取 200 金币。"""
        return self.coins < max(20, int(200 * 0.2))

    def need_kind(self):
        """返回当前最该互动的需求：hungry / thirsty / mood / coins / None。"""
        if self.hunger < 35:
            return "hungry"
        if self.thirst < 35:
            return "thirsty"
        if self.mood < 35:
            return "mood"
        if self.is_broke():
            return "coins"
        return None

    def critical_need(self, threshold: float = 5) -> str:
        """归零级需求：hungry / thirsty / both / ""。

        单独于 need_kind()，因为 hunger 先判会让“又饿又渴”永远只报饿。
        """
        hungry = self.hunger <= threshold
        thirsty = self.thirst <= threshold
        if hungry and thirsty:
            return "both"
        if thirsty:
            return "thirsty"
        if hungry:
            return "hungry"
        return ""


    def earn(self, n):
        self.coins += n

    def reward(self, exp=0, coins=0, mood=0):
        self.mood = _clamp(self.mood + mood)
        self.coins += coins
        leveled = self.add_exp(exp)
        return leveled

    def suggest_expression(self):
        """根据当前数值建议默认表情。"""
        if self.mood < 25 or self.hunger < 20:
            return "sleepy"
        if self.mood > 80:
            return "happy"
        return "idle"

    # ---------- v3.0.1 首启新人礼包 ----------
    def apply_welcome_gift(self) -> bool:
        """v3 第一次启动：饱食 / 水分 / 心情低于 70 的直接抬到 70（只升不降）。

        只发一次——靠 gift_v3 标记记住，之后再饿到 0 也不会偷偷复活，
        否则养成数值就没意义了。返回 True 表示这次真的发了。
        """
        if self.gift_v3:
            return False
        self.gift_v3 = True
        self._gift_just_sent = True
        self.hunger = max(self.hunger, 70.0)
        self.thirst = max(self.thirst, 70.0)
        self.mood = max(self.mood, 70.0)
        self._last_decay = time.time()
        self.touch()
        return True

    # ---------- 序列化 ----------
    def to_dict(self):
        return {
            "hunger": round(self.hunger, 1),
            "thirst": round(self.thirst, 1),
            "mood": round(self.mood, 1),
            "intimacy": round(self.intimacy, 1),
            "level": self.level,
            "exp": self.exp,
            "coins": self.coins,
            "bag": dict(self.bag),
            "gift_v3": bool(self.gift_v3),
        }

    def from_dict(self, d: dict):
        if not isinstance(d, dict):
            return
        self.hunger = _clamp(float(d.get("hunger", 70)))
        self.thirst = _clamp(float(d.get("thirst", 65)))
        self.mood = _clamp(float(d.get("mood", 75)))
        self.intimacy = _clamp(float(d.get("intimacy", 10)))
        self.level = max(1, int(d.get("level", 1)))
        self.exp = max(0, int(d.get("exp", 0)))
        self.coins = max(0, int(d.get("coins", 30)))
        bag = d.get("bag", {})
        self.bag = {str(k): max(0, int(v)) for k, v in bag.items() if int(v) > 0} if isinstance(bag, dict) else {}
        # v3.0.1：本次启动如果是 v3 首启，直接发一次新人礼包（只发一次）
        self.gift_v3 = bool(d.get("gift_v3", False))
        self.apply_welcome_gift()
