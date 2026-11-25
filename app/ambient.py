# -*- coding: utf-8 -*-
"""环境播报：天气 + 科技新闻（IT之家 RSS）。

只向外发送城市名，不上传任何本机数据；结果只在内存里用一次。
天气走三源级联（本机实测：Open-Meteo 被网络阻断，wttr.in 可用）：
  1. wttr.in（城市名直接查，无需 key）
  2. itboy（中国天气网数据中转，需城市 code，内置常见城市表）
  3. Open-Meteo（需先地理编码；作为最后兜底）
"""
import json
import re
import urllib.parse
import urllib.request

from PySide6.QtCore import QThread, Signal

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

WTTR_URL = "https://wttr.in/{city}?format=j1&lang=zh"
ITBOY_URL = "http://t.weather.itboy.net/api/weather/city/{code}"
GEO_URL = ("https://geocoding-api.open-meteo.com/v1/search"
           "?name={q}&count=1&language=zh&format=json")
OM_URL = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
          "&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
          "weather_code,wind_speed_10m"
          "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
          "&timezone=auto")
NEWS_URL = "https://www.ithome.com/rss/"

# v2.9.8：资讯分六类。中新网各频道 RSS 与 IT之家实测均返回 30~60 条
# （娱乐频道 ent.xml 返回 0 条，改用文化频道 culture.xml）。
NEWS_FEEDS = {
    "news":    ("要闻", "https://www.chinanews.com.cn/rss/scroll-news.xml"),
    "sports":  ("体育", "https://www.chinanews.com.cn/rss/sports.xml"),
    "ent":     ("娱乐", "https://www.chinanews.com.cn/rss/culture.xml"),
    "tech":    ("科技", NEWS_URL),
    "finance": ("金融", "https://www.chinanews.com.cn/rss/finance.xml"),
    "politics":("时政", "https://www.chinanews.com.cn/rss/china.xml"),
}
NEWS_CATEGORIES = [(k, v[0]) for k, v in NEWS_FEEDS.items()]

# 中国天气网城市代码（常用城市，可自行扩充）
CITY_CODES = {
    "北京": "101010100", "上海": "101020100", "广州": "101280101", "深圳": "101280601",
    "郑州": "101180101", "洛阳": "101180901", "开封": "101180801", "新乡": "101180301",
    "天津": "101030100", "重庆": "101040100", "成都": "101270101", "杭州": "101210101",
    "南京": "101190101", "武汉": "101200101", "西安": "101110101", "长沙": "101250101",
    "沈阳": "101070101", "哈尔滨": "101050101", "长春": "101060101", "济南": "101120101",
    "青岛": "101120201", "合肥": "101220101", "福州": "101230101", "厦门": "101230201",
    "南昌": "101240101", "昆明": "101290101", "贵阳": "101260101", "南宁": "101300101",
    "海口": "101310101", "石家庄": "101090101", "太原": "101100101", "呼和浩特": "101080101",
    "兰州": "101160101", "银川": "101170101", "西宁": "101150101", "乌鲁木齐": "101130101",
    "拉萨": "101140101", "香港": "101320101", "澳门": "101330101", "台北": "101340101",
}

# Open-Meteo WMO 天气码 → 中文
CODES = {
    0: "晴", 1: "大致晴朗", 2: "多云", 3: "阴",
    45: "有雾", 48: "雾凇",
    51: "毛毛雨", 53: "小雨", 55: "中雨", 56: "冻雨", 57: "强冻雨",
    61: "小雨", 63: "中雨", 65: "大雨", 66: "冻雨", 67: "强冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "米雪",
    80: "阵雨", 81: "强阵雨", 82: "暴雨", 85: "阵雪", 86: "强阵雪",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "强雷暴伴冰雹",
}

# wttr.in（WorldWeatherOnline）天气码 → 中文
WWO_CODES = {
    113: "晴", 116: "多云", 119: "阴", 122: "阴",
    143: "有雾", 248: "有雾", 260: "冻雾",
    176: "阵雨", 263: "小毛毛雨", 266: "毛毛雨", 281: "冻毛毛雨", 284: "强冻毛毛雨",
    293: "小雨", 296: "小雨", 299: "中雨", 302: "中雨", 305: "大雨", 308: "大雨",
    311: "小冻雨", 314: "冻雨", 317: "小冻雨", 320: "雪",
    323: "小雪", 326: "小雪", 329: "中雪", 332: "中雪", 335: "大雪", 338: "大雪",
    350: "冰粒", 353: "小阵雨", 356: "阵雨", 359: "暴雨",
    362: "小阵雪", 365: "阵雪", 368: "小阵雪", 371: "强阵雪", 374: "冰粒", 377: "冰粒",
    386: "雷阵雨", 389: "强雷雨", 392: "雷雪", 395: "强雷雪",
}


def _fetch(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def code_text(code) -> str:
    try:
        return CODES.get(int(code), "说不清的天")
    except (TypeError, ValueError):
        return "说不清的天"


def wwo_text(code) -> str:
    try:
        return WWO_CODES.get(int(code), "")
    except (TypeError, ValueError):
        return ""


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# 只有 wttr 兜底时会给英文描述，按关键词粗译，避免气泡里蹦英文
_EN_MAP = (("thunder", "雷阵雨"), ("heavy rain", "大雨"), ("moderate rain", "中雨"),
           ("light rain", "小雨"), ("patchy rain", "零星小雨"), ("rain", "雨"),
           ("heavy snow", "大雪"), ("light snow", "小雪"), ("snow", "雪"),
           ("freezing", "冻雨"), ("overcast", "阴"), ("partly cloudy", "多云"),
           ("cloudy", "多云"), ("mist", "薄雾"), ("fog", "有雾"), ("haze", "霾"),
           ("smoky", "霾"), ("sunny", "晴"), ("clear", "晴"))


def _en_text(desc) -> str:
    s = ""
    try:
        s = str((desc or [{}])[0].get("value") or "").lower()
    except (IndexError, AttributeError, TypeError):
        s = str(desc or "").lower()
    for k, v in _EN_MAP:
        if k in s:
            return v
    return ""


# ---------------- 天气三源 ----------------
def _wttr_weather(city: str) -> dict:
    try:
        data = json.loads(_fetch(WTTR_URL.format(city=urllib.parse.quote(city)), timeout=12))
    except Exception:  # noqa: BLE001
        return {}
    cur = (data or {}).get("current_condition") or []
    day = (data or {}).get("weather") or []
    if not cur:
        return {}
    c = cur[0]
    t = _num(c.get("temp_C"))
    if t is None:
        return {}
    text = wwo_text(c.get("weatherCode")) or _en_text(c.get("weatherDesc"))
    tmax = tmin = pop = None
    if day:
        d0 = day[0]
        tmax, tmin = _num(d0.get("maxtempC")), _num(d0.get("mintempC"))
        hrs = d0.get("hourly") or []
        pops = [_num(h.get("chanceofrain")) for h in hrs]
        pops = [p for p in pops if p is not None]
        if pops:
            pop = max(pops)
    return {"t": round(t, 1), "feels": _num(c.get("FeelsLikeC")),
            "hum": int(_num(c.get("humidity")) or 0),
            "wind": _num(c.get("windspeedKmph")),
            "text": text,
            "tmax": None if tmax is None else round(tmax, 1),
            "tmin": None if tmin is None else round(tmin, 1),
            "pop": pop, "src": "wttr"}


def _itboy_weather(city: str) -> dict:
    """中国天气网数据中转（国内 CDN，实测最稳）：实况 + 今日高低温 + 空气。"""
    code = CITY_CODES.get((city or "").strip())
    if not code:
        return {}
    try:
        data = json.loads(_fetch(ITBOY_URL.format(code=code), timeout=12))
    except Exception:  # noqa: BLE001
        return {}
    d = (data or {}).get("data") or {}
    t = _num(d.get("wendu"))
    if t is None:
        return {}
    fc = (d.get("forecast") or [])
    f0 = fc[0] if fc else {}

    def _t(v):
        return _num(str(v or "").replace("高温", "").replace("低温", "")
                    .replace("℃", "").strip())

    return {"t": round(t, 1), "feels": None,
            "hum": _num(str(d.get("shidu") or "").replace("%", "")),
            "wind": None, "text": str(f0.get("type") or ""),
            "tmax": _t(f0.get("high")), "tmin": _t(f0.get("low")),
            "pop": None, "air": str(d.get("quality") or ""),
            "src": "itboy"}


def _openmeteo_weather(city: str) -> dict:
    try:
        geo = json.loads(_fetch(GEO_URL.format(q=urllib.parse.quote(city)), timeout=10))
    except Exception:  # noqa: BLE001
        return {}
    res = (geo or {}).get("results") or []
    if not res:
        return {}
    it = res[0]
    try:
        wx = json.loads(_fetch(OM_URL.format(lat=float(it["latitude"]), lon=float(it["longitude"]))))
    except Exception:  # noqa: BLE001
        return {}
    cur = (wx or {}).get("current") or {}
    daily = (wx or {}).get("daily") or {}
    if not cur:
        return {}

    def _one(d, k):
        v = d.get(k)
        return v[0] if isinstance(v, list) and v else v

    return {"t": _num(cur.get("temperature_2m")), "feels": _num(cur.get("apparent_temperature")),
            "hum": _num(cur.get("relative_humidity_2m")), "wind": _num(cur.get("wind_speed_10m")),
            "text": code_text(cur.get("weather_code")),
            "tmax": _num(_one(daily, "temperature_2m_max")),
            "tmin": _num(_one(daily, "temperature_2m_min")),
            "pop": _one(daily, "precipitation_probability_max"), "src": "open-meteo"}


def fetch_weather(city: str) -> dict:
    """级联取天气，返回 {t,feels,hum,wind,text,tmax,tmin,pop,air,src}；全失败返回 {}。"""
    for fn in (_itboy_weather, _wttr_weather, _openmeteo_weather):
        try:
            w = fn(city)
        except Exception:  # noqa: BLE001
            w = {}
        if w and w.get("t") is not None:
            return w
    return {}


def _rss_titles(url: str, limit: int = 3) -> list:
    """抓一个 RSS，取前 limit 条标题；网络失败或格式不对返回 []。"""
    try:
        xml = _fetch(url, timeout=15)
    except Exception:  # noqa: BLE001
        return []
    titles = []
    for m in re.finditer(r"<item>(.*?)</item>", xml, re.S):
        tm = re.search(r"<title>(.*?)</title>", m.group(1), re.S)
        if not tm:
            continue
        t = tm.group(1)
        t = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", t, flags=re.S)
        t = re.sub(r"<[^>]+>", "", t)
        t = (t.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
             .replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " "))
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) >= 8:
            titles.append(t[:80])
        if len(titles) >= limit:
            break
    return titles


def fetch_news(limit: int = 3, category: str = "tech") -> list:
    """按分类取头条标题。category 见 NEWS_FEEDS；未知分类回退科技。失败返回 []。"""
    url = NEWS_FEEDS.get(category, NEWS_FEEDS["tech"])[1]
    return _rss_titles(url, limit)


# ---------------- 台词 ----------------
def _tc(v) -> str:
    """温度显示：整数不带 .0，非整数保留 1 位。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return str(int(round(f))) if abs(f - round(f)) < 0.05 else f"{f:.1f}"


def weather_line(w: dict, city: str) -> str:
    """把天气数据揉成一句鲸鱼娘口吻的话（单行，不换行）。"""
    if not w:
        return ""
    city = city or "这边"
    t, feels, txt = w.get("t"), w.get("feels"), str(w.get("text") or "")
    head = f"{city}现在{_tc(t)}℃"
    if feels is not None and t is not None:
        try:
            if abs(float(feels) - float(t)) >= 3:
                head += f"，体感{_tc(feels)}℃"
        except (TypeError, ValueError):
            pass
    head += f"，{txt}" if txt else ""
    parts = [head]
    if w.get("tmax") is not None and w.get("tmin") is not None:
        parts.append(f"今天{_tc(w['tmin'])}到{_tc(w['tmax'])}℃")
    if w.get("pop") is not None:
        try:
            if float(w["pop"]) >= 50:
                parts.append(f"降水概率{int(float(w['pop']))}%，出门记得带伞")
        except (TypeError, ValueError):
            pass
    air = str(w.get("air") or "")
    if air:
        parts.append(f"空气{air}")
    tail = ""
    try:
        t = float(w.get("t") or 0)
        if t <= 5:
            tail = "冷成这样，多穿点，别让我操心。"
        elif t >= 33:
            tail = "热得要化了，多喝水。"
        elif "雨" in txt:
            tail = "下着雨呢，别淋着。"
        elif "雪" in txt:
            tail = "下雪了，路滑，慢点走。"
        elif "晴" in txt:
            tail = "天不错，别一直闷在屏幕前。"
    except (TypeError, ValueError):
        tail = ""
    return ("，".join(parts) + "。" + tail).strip()


def news_line(title: str) -> str:
    return f"看到条新闻：{title}。就这样，我只负责念给你听。"


# ---------------- 后台线程 ----------------
class WeatherWorker(QThread):
    """v3.0.10：面板「天气资讯」页单独拉实况天气，不阻塞 UI。"""
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, city: str = ""):
        super().__init__()
        self.city = (city or "").strip()

    def run(self):
        if not self.city:
            self.failed.emit("没填城市")
            return
        try:
            w = fetch_weather(self.city)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e)[:120])
            return
        if not w:
            self.failed.emit("三个天气源都没拿到数据")
            return
        self.done.emit(w)


class AmbientWorker(QThread):
    """一次抓一轮：天气 + 新闻。任一可用即可，全失败发 failed。"""
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, city: str, want_news: bool = True):
        super().__init__()
        self.city = city or ""

    def run(self):
        out = {"city": self.city, "weather": {}, "news": []}
        try:
            if self.city:
                out["weather"] = fetch_weather(self.city)
            out["news"] = fetch_news(3)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e)[:120])
            return
        if not out["weather"] and not out["news"]:
            self.failed.emit("天气与新闻都没拿到")
            return
        self.done.emit(out)


class NewsWorker(QThread):
    """v2.9.8：按分类拉头条（面板「天气资讯 → 分类资讯」用），不阻塞 UI。"""
    done = Signal(list)
    failed = Signal(str)

    def __init__(self, category: str = "tech", limit: int = 6):
        super().__init__()
        self.category = category
        self.limit = limit

    def run(self):
        try:
            items = fetch_news(self.limit, self.category)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e)[:120])
            return
        self.done.emit(items)
