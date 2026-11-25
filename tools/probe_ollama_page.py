# -*- coding: utf-8 -*-
"""探针三：ollama.com 的库页 / tags 页结构，怎么稳定抠出模型名、tag、大小。"""
import re
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "ignore")


lib = get("https://ollama.com/library")
i = lib.find('href="/library/llama3.1"')
print("=== library 卡片片段 ===")
print(lib[max(0, i - 300):i + 700].replace("\n", " ")[:900])

print("\n=== 名称提取 ===")
names = []
for m in re.finditer(r'<a[^>]*href="/library/([a-zA-Z0-9._\-]+)"[^>]*>', lib):
    n = m.group(1)
    if n not in names:
        names.append(n)
print("names", len(names), names[:10])

tags = get("https://ollama.com/library/qwen3.5/tags")
print("\n=== tags 页 ===")
print("bytes", len(tags))
cand = re.findall(r'href="/library/qwen3\.5:([a-zA-Z0-9._\-]+)"', tags)
print("tag 候选", len(cand), cand[:12])
m = re.search(r'href="/library/qwen3\.5:([a-zA-Z0-9._\-]+)"', tags)
if m:
    p = m.start()
    print("片段:", tags[max(0, p - 200):p + 600].replace("\n", " ")[:800])
sizes = re.findall(r"(\d+(?:\.\d+)?\s?(?:GB|MB))", tags)
print("size 候选", len(sizes), sizes[:10])
