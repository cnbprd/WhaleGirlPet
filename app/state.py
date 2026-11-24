# -*- coding: utf-8 -*-
"""养成数值：饱食度 / 心情 / 亲密度 / 等级经验 / 金币，零食定义与衰减规则。"""
import random

SNACKS = {
    "rice":    {"name": "白米饭",   "cost": 10, "hunger": 25, "mood": 5,  "intimacy": 1, "exp": 6,  "emoji": "🍚"},
    "fish":    {"name": "小鱼干",   "cost": 20, "hunger": 15, "mood": 10, "intimacy": 2, "exp": 10, "emoji": "🐟"},
    "cake":    {"name": "蓝莓蛋糕", "cost": 30, "hunger": 10, "mood": 20, "intimacy": 2, "exp": 14, "emoji": "🍰"},
    "milktea": {"name": "鲸鱼奶茶", "cost": 25, "hunger": 8,  "mood": 15, "intimacy": 1, "exp": 12, "emoji": "🧋"},
}


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


class PetState:
    def __init__(self):
        self.hunger = 70.0      # 饱食度 0-100
        self.mood = 75.0        # 心情 0-100
        self.intimacy = 10.0    # 亲密度 0-100
        self.level = 1
        self.exp = 0
        self.coins = 30

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

    # ---------- 互动 ----------
    def feed(self, key):
        snack = SNACKS.get(key)
        if not snack:
            return False, "没有这种零食。"
        if self.coins < snack["cost"]:
            return False, "金币不够啦，先去挂钟攒一攒。"
        self.coins -= snack["cost"]
        self.hunger = _clamp(self.hunger + snack["hunger"])
        self.mood = _clamp(self.mood + snack["mood"])
        self.intimacy = _clamp(self.intimacy + snack["intimacy"])
        leveled = self.add_exp(snack["exp"])
        msg = f"{snack['emoji']} {snack['name']} {snack['name']}~"
        if leveled:
            msg += f"\n升到 Lv.{self.level}！奖励 20 金币。"
        return True, msg

    def pat(self):
        self.mood = _clamp(self.mood + 2)
        self.intimacy = _clamp(self.intimacy + 1)
        self.add_exp(2)

    def chat_bonus(self):
        self.mood = _clamp(self.mood + 1)
        self.intimacy = _clamp(self.intimacy + 1)
        self.add_exp(3)

    def decay(self):
        """周期性自然衰减；返回是否需要提醒（饿/低落）。"""
        self.hunger = _clamp(self.hunger - random.uniform(0.6, 1.2))
        if self.hunger < 30:
            self.mood = _clamp(self.mood - random.uniform(0.6, 1.4))
        else:
            self.mood = _clamp(self.mood - random.uniform(0.2, 0.6))
        return self.hunger < 25 or self.mood < 25

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
            "mood": round(self.mood, 1),
            "intimacy": round(self.intimacy, 1),
            "level": self.level,
            "exp": self.exp,
            "coins": self.coins,
        }

    def from_dict(self, d: dict):
        if not isinstance(d, dict):
            return
        self.hunger = _clamp(float(d.get("hunger", 70)))
        self.mood = _clamp(float(d.get("mood", 75)))
        self.intimacy = _clamp(float(d.get("intimacy", 10)))
        self.level = max(1, int(d.get("level", 1)))
        self.exp = max(0, int(d.get("exp", 0)))
        self.coins = max(0, int(d.get("coins", 30)))
