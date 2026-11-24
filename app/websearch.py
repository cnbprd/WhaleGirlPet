# -*- coding: utf-8 -*-
"""联网搜索：抓 Bing 国内版结果页，给聊天提供实时外部知识。

只发送查询词，不发送本机任何数据；解析失败或断网时返回空，由上层降级为纯本地回答。
"""
import re
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

BING = "https://cn.bing.com/search?q={q}&setlang=zh-Hans"
TAG_RE = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    s = TAG_RE.sub("", s or "")
    s = (s.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
         .replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", s).strip()


def _fetch(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def search(query: str, k: int = 5) -> list:
    """返回 [{'title','snippet','url'}]；失败返回空列表。"""
    query = (query or "").strip()
    if not query:
        return []
    try:
        html = _fetch(BING.format(q=urllib.parse.quote(query)))
    except Exception:  # noqa: BLE001
        return []
    html = html.replace("\r", "").replace("\n", "")
    out = []
    # 每条结果：<h2><a href="...">标题</a></h2> ... <p ...>摘要</p>
    for m in re.finditer(r'<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>(.*?)(?=<h2|$)', html):
        url, title, tail = m.group(1), _clean(m.group(2)), m.group(3)
        if not title or "bing.com" in url and "cc=" in url:
            continue
        pm = re.search(r"<p[^>]*>(.*?)</p>", tail)
        snippet = _clean(pm.group(1))[:220] if pm else ""
        if not snippet:
            sm = re.search(r'<span[^>]*class="[^"]*b_lineclamp[^"]*"[^>]*>(.*?)</span>', tail)
            snippet = _clean(sm.group(1))[:220] if sm else ""
        if title in ("搜狗输入法官方下载",) or "sogou" in url:
            continue   # 常见置顶推广位
        out.append({"title": title[:120], "snippet": snippet, "url": url})
        if len(out) >= k:
            break
    return out


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
