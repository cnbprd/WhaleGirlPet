# -*- coding: utf-8 -*-
"""v2.9.7 行为决策：讨零食、零食的去向（吃/存/逗你一下）、随机动作提问。

这里只放"她现在怎么想"，不放界面也不放持久化，方便单独跑测试。
"""
import random

EAT_STYLES = ("eat", "bag", "tease")


def decide_food_destiny(st, from_bag: bool = False) -> str:
    """拿到一份零食后怎么处理。

    - 很饿（饱食<30）：直接吃，不磨叽；
    - 半饱（30~55）：七成存背包，留着下次饿的时候翻出来；
    - 不太饿（>55）：心情好就皮一下（先问你吃不吃，再自己塞嘴里），
      心情一般就乖乖存背包。
    从背包里拿出来的，默认当场吃掉（都翻出来了）。
    """
    if from_bag:
        return "eat"
    if st.hunger < 30:
        return "eat"
    if st.hunger < 55:
        return "bag" if random.random() < 0.7 else "eat"
    if st.mood >= 65 and random.random() < 0.55:
        return "tease"
    return "bag"


def tease_line(user_name: str, snack: dict) -> str:
    """"xxx，你要吃么？"——问完不等回答，自己先吃掉。"""
    return f"{user_name}，你要吃么？"


def beg_line(st, snack: dict = None) -> str:
    """饿了/嘴馋时向用户撒娇讨要的说法。"""
    name = f"{snack['emoji']}{snack['name']}" if snack else "零食"
    if st.hunger < 25:
        pool = [
            f"肚子空空的……能给我来点{name}么？就一点点。",
            f"我饿得尾巴都没力气摆了，{name}，拜托拜托。",
            f"再不吃东西我要啃桌角了——{name}行不行？",
        ]
    elif st.hunger < 45:
        pool = [
            f"有点饿，{name}可以分我一口么？",
            f"闻到好吃的味道了……{name}，我盯着呢。",
            f"我现在能吃掉一份{name}，真的。",
        ]
    else:
        pool = [
            f"其实不太饿，但{name}看起来太香了，能给我买一份么？",
            f"嘴巴有点寂寞，想吃{name}。",
        ]
    return random.choice(pool)


def bag_line(snack: dict) -> str:
    """把零食收进背包时说的话。"""
    return random.choice([
        f"{snack['emoji']}{snack['name']}先收进背包，等饿了再翻出来。",
        f"这个{snack['name']}我留着当夜宵，塞背包里了。",
        f"背包还有位置，{snack['name']}放进去啦。",
    ])


def eat_line(snack: dict) -> str:
    return random.choice([
        f"{snack['emoji']}{snack['name']}——开动！",
        f"啊呜一口，{snack['name']}真好吃。",
        f"嚼嚼嚼……{snack['name']}下一份什么时候有？",
    ])


def empty_bag_line() -> str:
    return random.choice([
        "背包空了，我得再去讨点吃的。",
        "翻遍了背包，什么都没有……",
    ])


def action_pairs(actions: list) -> list:
    """从可选动作里随机抽两个不同的，返回 [(key, 中文名)]。"""
    pool = [a for a in actions if a]
    if len(pool) < 2:
        return [(k, k) for k in pool]
    two = random.sample(pool, 2)
    return [(k, ACTION_LABELS.get(k, k)) for k in two]


ACTION_LABELS = {
    "wave": "挥挥手", "dance": "跳个舞", "lion": "舞狮", "balloon": "吹气球",
    "fireworks": "放烟花", "type": "打字", "boggle": "歪头", "stretch": "伸懒腰",
    "bounce": "弹一弹", "run": "跑一圈", "tumble": "摔一跤", "hop": "蹦蹦跳",
    "crab": "横着走", "trot": "小碎步", "floatstep": "慢悠悠晃", "look": "看书",
    "eatrice": "扒饭", "change": "换装", "brawl": "打闹",
}


def need_line(kind: str) -> str:
    return {
        "hungry": "饿了，肚子咕咕叫。",
        "thirsty": "渴了，想喝水。",
        "mood": "心情不太好，需要你哄一下。",
        "coins": "金币快见底了，得去打份工。",
    }.get(kind, "想跟你互动一下。")
