# -*- coding: utf-8 -*-
"""探针：Ollama 官方 registry / 网页库能不能抓，列表与权重直链长什么样。"""
import json
import sys
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

ACCEPT = ("application/vnd.docker.distribution.manifest.v2+json,"
          "application/vnd.oci.image.manifest.v1+json")


def get(url, headers=None, timeout=15):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def try_manifest(name, tag):
    url = f"https://registry.ollama.ai/v2/library/{name}/manifests/{tag}"
    try:
        st, body = get(url, {"Accept": ACCEPT})
        d = json.loads(body)
        layers = [(l.get("mediaType"), l.get("size"), l.get("digest")) for l in d.get("layers", [])]
        print(f"[manifest {name}:{tag}] {st} layers={len(layers)}")
        for mt, sz, dg in layers[:6]:
            print("   ", mt, round((sz or 0) / 1048576, 1), "MB", dg[:20])
    except Exception as e:  # noqa: BLE001
        print(f"[manifest {name}:{tag}] ERR {e!r}")


def try_blob_head(name, digest):
    url = f"https://registry.ollama.ai/v2/library/{name}/blobs/{digest}"
    try:
        st, body = get(url, {"Range": "bytes=0-1023"})
        print(f"[blob {name}] {st} first={body[:16]!r} len={len(body)}")
    except Exception as e:  # noqa: BLE001
        print(f"[blob {name}] ERR {e!r}")


def try_library_page():
    for u in ("https://ollama.com/library", "https://ollama.com/search?q="):
        try:
            st, body = get(u)
            txt = body.decode("utf-8", "ignore")
            print(f"[page {u}] {st} bytes={len(txt)}")
            import re
            names = re.findall(r'href="/library/([a-zA-Z0-9._-]+)"', txt)
            seen = []
            for n in names:
                if n not in seen:
                    seen.append(n)
            print("   抓到模型名数量:", len(seen), "前 12:", seen[:12])
        except Exception as e:  # noqa: BLE001
            print(f"[page {u}] ERR {e!r}")


if __name__ == "__main__":
    try_manifest("qwen3.5", "4b")
    try_manifest("gemma4", "e2b")
    try_manifest("deepseek-coder", "6.7b-instruct")
    try_library_page()
    try_blob_head("qwen3.5", "sha256:a9d0a3e1d8c91732a3812becd31f8d4a8ff57414903f226306069f0437e2ac50")
