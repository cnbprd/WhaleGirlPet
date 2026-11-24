# -*- coding: utf-8 -*-
"""养成数值：饱食度 / 心情 / 口渴 / 亲密度 / 等级经验 / 金币 / 背包。

v2.9.7：
- 零食货架搬到 snacks.py（分类、联网补货、通胀护栏都在那边）；
- 加「口渴」条与「背包」：买来的零食先落背包，吃的时候才走背包；
- 吃一份零食不再当场扣钱，改为先从背包取（旧调用会自动买一份，兼容面板老代码）。
"""
import random

from snacks import SNACKS, by_key


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


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
        self.intimacy = _clamp(self.intimacy + snack.get("intimacy", 0))
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
        self.add_exp(2)
        return True, random.choice([
            "咕咚咕咚——水喝下去了，喉咙舒服多了。",
            "喝水时间到，一口气灌了半杯。",
            "喝完水，尾巴都精神了。",
        ])


    def pat(self):
        self.mood = _clamp(self.mood + 2)
        self.intimacy = _clamp(self.intimacy + 1)
        self.add_exp(2)

    def chat_bonus(self):
        self.mood = _clamp(self.mood + 1)
        self.intimacy = _clamp(self.intimacy + 1)
        self.add_exp(3)

    def decay(self):
        """周期性自然衰减；返回要不要喊人（饿/渴/低落）。"""
        self.hunger = _clamp(self.hunger - random.uniform(0.6, 1.2))
        self.thirst = _clamp(self.thirst - random.uniform(0.8, 1.6))
        if self.hunger < 30 or self.thirst < 30:
            self.mood = _clamp(self.mood - random.uniform(0.6, 1.4))
        else:
            self.mood = _clamp(self.mood - random.uniform(0.2, 0.6))
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
