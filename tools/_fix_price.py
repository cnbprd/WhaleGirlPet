# -*- coding: utf-8 -*-
"""修 v2.9.7 零食定价：按属性算价，去掉哈希抖动，避免「辣条 23 金币」这种通胀。"""
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "snacks.py")
s = open(P, encoding="utf-8").read()

OLD = '''def _stable_price(name: str, hunger: int, mood: int) -> int:
    """同名零食价格固定（同一名字每次刷新不掉价不涨价），避免随机通胀。"""
    h = int(hashlib.md5(name.encode("utf-8")).hexdigest()[:4], 16)
    base = 8 + h % 16
    return clamp_cost(base + hunger // 3, hunger, mood)'''

NEW = '''def _stable_price(name: str, hunger: int, mood: int) -> int:
    """按「管饱多少 + 多让人开心」定价：同样的属性永远同价，不随刷新浮动。"""
    base = int(round(hunger * 0.62 + mood * 0.42 + 2))
    return clamp_cost(base, hunger, mood)'''

assert OLD in s, "旧定价函数没找到"
s = s.replace(OLD, NEW)

OLD2 = '"健康", "安全", "营养", "品牌", "好吃到", "合集", "测评", "攻略")'
NEW2 = '"健康", "安全", "营养", "品牌", "好吃到", "合集", "测评", "攻略", "坚果", "水果")'
assert OLD2 in s, "停用词表没找到"
s = s.replace(OLD2, NEW2)

open(P, "w", encoding="utf-8").write(s)
print("patched", P)
