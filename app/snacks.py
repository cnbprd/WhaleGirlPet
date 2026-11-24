# -*- coding: utf-8 -*-
"""零食货架（v2.9.7）：内置基础货架 + 联网补货 + 通胀护栏。

定价原则（护栏，不允许通货膨胀）：
- 打工收入：每完成一次 5~15 金币（tasks.TASK_DEFS），周期 30~60 秒；
- 零食单价区间 4~45 金币，最贵的刺身/龙虾一顿约等于 3~4 次打工；
- 任何新增/联网零食都经 clamp_cost() 压回区间，且饱食度越高单价上限越低，
  防止"花 5 金币回 40 饱食"这种破坏经济的选择。
"""
import hashlib
import random

# 分类：主食 / 肉鱼 / 甜点 / 饮品 / 水果 / 高档
BASE = [
    # key,      名称,        表情, 价, 饱食, 心情, 亲密, 经验, 水分, 分类
    ("rice", "白米饭", "🍚", 8, 24, 3, 1, 5, 0, "主食"),
    ("bread", "面包", "🍞", 7, 16, 3, 1, 5, 0, "主食"),
    ("onigiri", "饭团", "🍙", 12, 22, 5, 1, 7, 0, "主食"),
    ("noodle", "泡面", "🍜", 15, 26, 4, 1, 8, 4, "主食"),
    ("fish", "小鱼干", "🐟", 12, 12, 10, 2, 8, 0, "肉鱼"),
    ("sausage", "烤肠", "🌭", 14, 18, 7, 1, 9, 0, "肉鱼"),
    ("chicken", "鸡胸肉", "🍗", 18, 24, 6, 1, 10, 0, "肉鱼"),
    ("salmon", "三文鱼刺身", "🍣", 40, 30, 12, 3, 20, 0, "肉鱼"),
    ("cake", "蓝莓蛋糕", "🍰", 26, 12, 20, 2, 14, 0, "甜点"),
    ("pudding", "布丁", "🍮", 14, 10, 14, 2, 12, 4, "甜点"),
    ("icecream", "冰淇淋", "🍦", 16, 8, 16, 2, 12, 6, "甜点"),
    ("chocolate", "巧克力", "🍫", 12, 6, 12, 1, 10, 0, "甜点"),
    ("dango", "草莓大福", "🍡", 20, 8, 18, 2, 13, 0, "甜点"),
    ("milktea", "鲸鱼奶茶", "🧋", 20, 6, 15, 1, 12, 20, "饮品"),
    ("cola", "冰可乐", "🥤", 12, 3, 10, 1, 8, 18, "饮品"),
    ("milk", "热牛奶", "🥛", 14, 8, 10, 2, 10, 20, "饮品"),
    ("lemonwater", "柠檬水", "🍋", 8, 2, 6, 1, 6, 30, "饮品"),
    ("coffee", "咖啡", "☕", 15, 2, 8, 1, 9, 15, "饮品"),
    ("apple", "苹果", "🍎", 5, 10, 5, 1, 5, 8, "水果"),
    ("banana", "香蕉", "🍌", 4, 8, 6, 1, 4, 4, "水果"),
    ("grape", "葡萄", "🍇", 10, 8, 10, 1, 6, 6, "水果"),
    ("watermelon", "西瓜", "🍉", 18, 14, 12, 1, 9, 15, "水果"),
    ("crab", "蟹黄包", "🦀", 30, 28, 14, 3, 18, 0, "高档"),
    ("lobster", "龙虾", "🦞", 45, 40, 18, 4, 25, 0, "高档"),
]

CATEGORIES = ["主食", "肉鱼", "甜点", "饮品", "水果", "高档", "新品"]

MIN_COST, MAX_COST = 4, 45


def clamp_cost(cost: int, hunger: int, mood: int) -> int:
    """通胀护栏：价必须落在区间，且"饱食度/金币"的性价比不能过高。"""
    cost = int(cost)
    if hunger >= 35:
        cost = max(cost, 22)      # 大份管饱的不许卖 5 金币
    elif hunger >= 20:
        cost = max(cost, 12)
    if mood >= 20:
        cost = max(cost, 20)      # 大份开心也不许贱卖
    return max(MIN_COST, min(MAX_COST, cost))


def _row(key, name, emoji, cost, hunger, mood, intimacy, exp, water, cat):
    return {
        "key": key, "name": name, "emoji": emoji,
        "cost": clamp_cost(cost, hunger, mood),
        "hunger": hunger, "mood": mood, "intimacy": intimacy,
        "exp": exp, "water": water, "cat": cat,
    }


SNACKS = {}
for _r in BASE:
    _s = _row(*_r)
    SNACKS[_s["key"]] = _s

# 新品（联网补货 / 内置彩蛋）单独存，可在商城里出现但不进旧的投喂网格
NEW_ITEMS = {}

# 联网抓不到时也保证「新品」货架有东西（价格同样走 _stable_price，不随刷新变）
FALLBACK_NEW = [
    ("辣条", "🌶️", 8, 12), ("锅巴", "🍘", 12, 10), ("薯片", "🥔", 10, 14),
    ("海苔", "🍙", 8, 10), ("牛轧糖", "🍬", 10, 12), ("蛋黄酥", "🥮", 16, 14),
    ("麻薯", "🍡", 12, 12), ("肉松饼", "🥧", 14, 12), ("山楂片", "🍎", 6, 8),
    ("瓜子", "🌻", 6, 8), ("话梅", "🫐", 8, 10), ("爆米花", "🍿", 10, 12),
]


def by_key(key: str):
    return SNACKS.get(key) or NEW_ITEMS.get(key)


def all_items() -> list:
    return list(SNACKS.values()) + list(NEW_ITEMS.values())


def items_of(cat: str) -> list:
    return [s for s in all_items() if s.get("cat") == cat]


def _stable_price(name: str, hunger: int, mood: int) -> int:
    """按「管饱多少 + 多让人开心」定价：同样的属性永远同价，不随刷新浮动。"""
    base = int(round(hunger * 0.62 + mood * 0.42 + 2))
    return clamp_cost(base, hunger, mood)


def add_new(name: str, emoji: str = "🍬", hunger: int = 12, mood: int = 10,
            water: int = 0, cat: str = "新品"):
    """把联网搜到的一款零食加进货架；同名已存在就跳过。"""
    name = (name or "").strip()[:12]
    if not name:
        return None
    for s in all_items():
        if s["name"] == name:
            return None
    key = "new_" + hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
    item = {
        "key": key, "name": name, "emoji": emoji,
        "cost": _stable_price(name, hunger, mood),
        "hunger": hunger, "mood": mood, "intimacy": 1, "exp": 8,
        "water": water, "cat": cat,
    }
    NEW_ITEMS[key] = item
    return item


# ---------------- 联网补货 ----------------
_NAME_HINT = ("零食", "小吃", "糕点", "饼干", "薯片", "果冻", "糖果", "巧克力",
              "奶茶", "冰淇淋", "肉干", "蛋糕", "坚果", "布丁", "泡芙",
              # 具体食物后缀（联网摘要里多数是「花生、瓜子、碧根果」这种裸名字）
              "片", "果", "糖", "干", "条", "酥", "饼", "糕", "豆", "梅",
              "仁", "薯", "肠", "奶", "茶", "冻", "花", "米", "面", "包", "卷")

_BAD_WORDS = ("淘宝", "京东", "拼多多", "旗舰店", "官网", "价格", "多少钱", "包邮",
              "旗舰", "天猫", "优惠", "券", "批发", "排行", "十大", "推荐", "百科",
              "零食", "清单", "好吃", "不贵", "评价", "追剧", "年货", "必备", "必囤",
              "健康", "安全", "营养", "品牌", "好吃到", "合集", "测评", "攻略", "坚果", "水果")

_STOP = ("的", "了", "吗", "什么", "怎么", "哪些", "多少", "我们", "你们", "可以")


def _looks_like_snack(word: str) -> bool:
    word = (word or "").strip(" ·　")
    if not (2 <= len(word) <= 6):
        return False
    if any(b in word for b in _BAD_WORDS):
        return False
    if any(x in word for x in _STOP):
        return False
    if any(ch.isdigit() or ch.isascii() for ch in word):
        return False
    return any(h in word for h in _NAME_HINT)


def fetch_online(k: int = 6) -> list:
    """联网搜「常见零食名称」，从结果里挑像零食的短词补货。

    只发查询词，不带本机任何数据；断网/解析失败就返回空，商城照旧有内置新品。
    """
    try:
        import websearch
        pages = websearch.search("零食有哪些 常见零食名称", k=6)
    except Exception:  # noqa: BLE001
        return []
    found = []
    known = [x["name"] for x in all_items()]
    for p in pages:
        for field in ("snippet", "title"):
            text = (p.get(field) or "")
            text = text.replace("&ensp;", " ").replace("&nbsp;", " ")
            for sep in ("、", "，", ",", "；", ";", " ", "：", "。"):
                text = text.replace(sep, "|")
            for word in text.split("|"):
                word = word.strip()
                if _looks_like_snack(word) and word not in known and word not in found:
                    found.append(word)
    out = []
    for name in found[:k]:
        item = add_new(name)
        if item:
            out.append(item)
    return out


def ensure_fallback_new():
    """把内置新品补齐（只在还没有时补，不覆盖联网淘到的）。"""
    for name, emoji, hunger, mood in FALLBACK_NEW:
        add_new(name, emoji=emoji, hunger=hunger, mood=mood)


def price_note() -> str:
    """给商城页脚用的一句话，解释钱怎么来的、价怎么定的。"""
    return ("金币靠打工赚：联网听课 15、满屏跑腿 10、清理垃圾 14、做家务 12（每次 30~60 秒）。"
            f"零食 {MIN_COST}~{MAX_COST} 金币，最贵的一顿约等于三四次打工，价格不会随刷新上涨。")


ensure_fallback_new()

