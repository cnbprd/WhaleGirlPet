# -*- coding: utf-8 -*-
"""联网搜索：给聊天提供实时外部知识。

v3.0.7：从「只抓 Bing」改成多引擎链式兜底 —— Bing（国内版）→ 百度 → 360。
某一源被反爬、改版或断网时，自动换下一个；只发查询词，不发本机任何数据。
解析失败就让上层降级为纯本地回答，不抛异常。
"""
import html as _html
import re
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

BING = "https://cn.bing.com/search?q={q}&setlang=zh-Hans"
BAIDU = "https://www.baidu.com/s?wd={q}&ie=utf-8"
SO360 = "https://www.so.com/s?q={q}"

TAG_RE = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    s = TAG_RE.sub("", s or "")
    try:
        s = _html.unescape(s)     # 把 &ensp; &#0183; &amp; 这类实体一次解干净
    except Exception:  # noqa: BLE001
        pass
    s = s.replace("&nbsp;", " ").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip()


def _fetch(url: str, timeout: int = 12, referer: str = "") -> str:
    headers = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9",
               "Accept": "text/html,application/xhtml+xml"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


# ---------------- 各引擎解析 ----------------

def _parse_bing(html: str, k: int) -> list:
    html = html.replace("\r", "").replace("\n", "")
    out = []
    for m in re.finditer(r'<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>(.*?)(?=<h2|$)', html):
        url, title, tail = m.group(1), _clean(m.group(2)), m.group(3)
        if not title or ("bing.com" in url and "cc=" in url):
            continue
        pm = re.search(r"<p[^>]*>(.*?)</p>", tail)
        snippet = _clean(pm.group(1))[:220] if pm else ""
        if not snippet:
            sm = re.search(r'<span[^>]*class="[^"]*b_lineclamp[^"]*"[^>]*>(.*?)</span>', tail)
            snippet = _clean(sm.group(1))[:220] if sm else ""
        if "sogou" in url:      # 常见置顶推广位
            continue
        out.append({"title": title[:120], "snippet": snippet, "url": url, "engine": "bing"})
        if len(out) >= k:
            break
    return out


def _parse_baidu(html: str, k: int) -> list:
    out = []
    # 标题：<h3 class="t ..."><a href="...">标题</a>
    for m in re.finditer(r'<h3[^>]*class="[^"]*\bt\b[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                         html, re.S):
        url, title = m.group(1), _clean(m.group(2))
        if not title:
            continue
        # 摘要：紧跟着的一段 div/span（百度几个版本 class 不同，抓不到就留空）
        tail = html[m.end():m.end() + 3000]
        sm = (re.search(r'<div[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</div>', tail, re.S)
              or re.search(r'<span[^>]*class="[^"]*content-right[^"]*"[^>]*>(.*?)</span>', tail, re.S)
              or re.search(r'<div[^>]*class="[^"]*c-span[^"]*"[^>]*>(.*?)</div>', tail, re.S))
        snippet = _clean(sm.group(1))[:220] if sm else ""
        out.append({"title": title[:120], "snippet": snippet, "url": url, "engine": "baidu"})
        if len(out) >= k:
            break
    return out


def _parse_so360(html: str, k: int) -> list:
    out = []
    for m in re.finditer(r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        url, title = m.group(1), _clean(m.group(2))
        if not title:
            continue
        tail = html[m.end():m.end() + 2500]
        sm = re.search(r'<p[^>]*class="[^"]*res-desc[^"]*"[^>]*>(.*?)</p>', tail, re.S)
        snippet = _clean(sm.group(1))[:220] if sm else ""
        out.append({"title": title[:120], "snippet": snippet, "url": url, "engine": "so360"})
        if len(out) >= k:
            break
    return out


def _engine_list(query: str):
    q = urllib.parse.quote(query)
    return [
        ("bing", BING.format(q=q), "", _parse_bing),
        ("baidu", BAIDU.format(q=q), "https://www.baidu.com/", _parse_baidu),
        ("so360", SO360.format(q=q), "https://www.so.com/", _parse_so360),
    ]


def search(query: str, k: int = 5) -> list:
    """多引擎链式搜索，返回 [{'title','snippet','url','engine'}]；全失败返回空列表。

    按顺序问，每个引擎拿到的结果合并去重；凑够 k 条就停，凑不够继续问下一个。
    """
    query = (query or "").strip()
    if not query:
        return []
    out, seen, seen_title = [], set(), set()
    for name, url, referer, parser in _engine_list(query):
        if len(out) >= k:
            break
        try:
            html = _fetch(url, referer=referer)
            hits = parser(html, k)
        except Exception:  # noqa: BLE001
            continue
        for h in hits:
            key = (h["title"], h["url"])
            tkey = h["title"].strip()
            if key in seen or (tkey and tkey in seen_title):
                continue
            seen.add(key)
            if tkey:
                seen_title.add(tkey)
            out.append(h)
            if len(out) >= k:
                break
    return out[:k]


def context_block(query: str, k: int = 4, max_chars: int = 900) -> str:
    hits = search(query, k)
    if not hits:
        return ""
    lines = [f"- {h['title']}：{h['snippet']}" for h in hits if h["snippet"] or h["title"]]
    if not lines:
        return ""
    return ("【联网搜索到的资料（可能过时，请自行判断）】\n" + "\n".join(lines))[:max_chars]


def looks_like_query(text: str) -> bool:
    """判断一句话是否值得联网查（问句、含"最新/现在/多少/是什么"等）。"""
    t = (text or "").strip()
    if len(t) < 4:
        return False
    keys = ("最新", "现在", "今天", "明天", "多少钱", "是什么", "怎么样", "为什么",
            "谁", "哪", "?", "？", "查一下", "搜一下", "新闻", "行情", "天气")
    return any(k in t for k in keys)
