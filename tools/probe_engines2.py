# -*- coding: utf-8 -*-
"""探针二：百度 / 360 的标题与摘要能不能解析出来。"""
import re
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
TAG = re.compile(r"<[^>]+>")
Q = "郑州天气"


def clean(s):
    s = TAG.sub("", s or "")
    s = (s.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
         .replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", s).strip()


def fetch(url, ref=""):
    h = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9",
         "Accept": "text/html,application/xhtml+xml"}
    if ref:
        h["Referer"] = ref
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("gbk", "ignore")


def baidu():
    html = fetch("https://www.baidu.com/s?wd=" + urllib.parse.quote(Q), "https://www.baidu.com/")
    out = []
    for m in re.finditer(r'<h3[^>]*class="[^"]*t[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        url, title = m.group(1), clean(m.group(2))
        if title:
            out.append((title[:60], url[:60]))
    return out


def so360():
    html = fetch("https://www.so.com/s?q=" + urllib.parse.quote(Q), "https://www.so.com/")
    out = []
    for m in re.finditer(r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        url, title = m.group(1), clean(m.group(2))
        if title:
            out.append((title[:60], url[:60]))
    return out


for tag, fn in (("baidu", baidu), ("so360", so360)):
    try:
        r = fn()
        print(f"== {tag}: {len(r)} 条")
        for x in r[:5]:
            print("   ", x)
    except Exception as e:  # noqa: BLE001
        print(f"== {tag} ERR", repr(e))
