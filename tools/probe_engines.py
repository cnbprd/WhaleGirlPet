# -*- coding: utf-8 -*-
"""探针：看几个搜索源在本机网络下能不能抓、能解析出多少条。"""
import re
import sys
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

Q = "郑州天气"


def fetch(url, extra=None):
    h = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9",
         "Accept": "text/html,application/xhtml+xml"}
    if extra:
        h.update(extra)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "ignore")


def t(tag, fn):
    try:
        print(tag, fn(), flush=True)
    except Exception as e:  # noqa: BLE001
        print(tag, "ERR", repr(e), flush=True)


def bing():
    html = fetch("https://cn.bing.com/search?q=" + urllib.parse.quote(Q))
    return len(re.findall(r'<h2[^>]*><a', html))+0


def sogou():
    html = fetch("https://www.sogou.com/web?query=" + urllib.parse.quote(Q),
                 {"Referer": "https://www.sogou.com/"})
    hits = len(re.findall(r'<h3[^>]*class="vr-title"', html))
    alt = len(re.findall(r'<h3[^>]*>\s*<a[^>]*href="/link\?url=', html))
    return f"vr-title={hits} h3link={alt} len={len(html)}"


def baidu():
    html = fetch("https://www.baidu.com/s?wd=" + urllib.parse.quote(Q),
                 {"Referer": "https://www.baidu.com/"})
    return f"result={len(re.findall(r'class=\"result', html))} len={len(html)}"


def ddg():
    html = fetch("https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote(Q))
    return f"links={len(re.findall(r'class=\"result-link\"', html))} len={len(html)}"


if __name__ == "__main__":
    t("bing  ", bing)
    t("sogou ", sogou)
    t("baidu ", baidu)
    t("ddg   ", ddg)
