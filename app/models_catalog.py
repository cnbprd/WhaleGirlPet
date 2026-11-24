# -*- coding: utf-8 -*-
"""内置本地模型清单：品牌、文件名、精确大小、下载地址。

数据口径（2026-11-24 实核，非搜索页宣传）：
- 仓库存在性与文件大小：HuggingFace 镜像 REST API（/api/models/<repo>/tree/main）
- 下载可用性：对每个单文件地址发 HEAD，全部返回 200，Content-Length 与 tree 一致

分片模型（Hy4 flash / Kimi K3）只给仓库页，不提供一键下载：动辄 100GB+。
"""

HF = "https://hf-mirror.com"

CATALOG = [
    {
        "id": "qwen3-4b",
        "brand": "Qwen",
        "name": "Qwen3-4B（推荐）",
        "file": "Qwen3-4B-Q4_K_M.gguf",
        "size_mb": 2382,
        "url": f"{HF}/Qwen/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf",
        "repo": f"{HF}/Qwen/Qwen3-4B-GGUF",
        "fits": True,
        "note": "默认模型。Q4_K_M，CPU 实测约 6 tok/s，4GB 显存或 8GB 内存可跑",
    },
    {
        "id": "deepseek-1.5b",
        "brand": "DeepSeek",
        "name": "DeepSeek-R1-Distill-1.5B（最轻）",
        "file": "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
        "size_mb": 1066,
        "url": f"{HF}/unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
        "repo": f"{HF}/unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF",
        "fits": True,
        "note": "1.5B 蒸馏版，下载最快、响应最快，适合低配机器",
    },
    {
        "id": "deepseek-7b",
        "brand": "DeepSeek",
        "name": "DeepSeek-R1-Distill-7B",
        "file": "DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
        "size_mb": 4466,
        "url": f"{HF}/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
        "repo": f"{HF}/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF",
        "fits": True,
        "note": "7B 蒸馏版，推理与写作更稳，CPU 约 3 tok/s",
    },
    {
        "id": "glm-4-9b",
        "brand": "GLM（智谱）",
        "name": "GLM-4-9B-Chat",
        "file": "glm-4-9b-chat-Q4_K_M.gguf",
        "size_mb": 5961,
        "url": f"{HF}/second-state/GLM-4-9B-Chat-GGUF/resolve/main/glm-4-9b-chat-Q4_K_M.gguf",
        "repo": f"{HF}/second-state/GLM-4-9B-Chat-GGUF",
        "fits": True,
        "note": "9B 中文对话较好，CPU 约 2–3 tok/s；官方 glm-4-9b-chat 仓库本身无 GGUF，用此第三方量化",
    },
    {
        "id": "hunyuan-a13b",
        "brand": "混元（腾讯）",
        "name": "Hunyuan-A13B-Instruct",
        "file": "Hunyuan-A13B-Instruct-Q4_K_M.gguf",
        "size_mb": 46522,
        "url": f"{HF}/tencent/Hunyuan-A13B-Instruct-GGUF/resolve/main/Hunyuan-A13B-Instruct-Q4_K_M.gguf",
        "repo": f"{HF}/tencent/Hunyuan-A13B-Instruct-GGUF",
        "fits": False,
        "note": "官方 GGUF，80B 总参/13B 激活，Q4 需 45GB+ 内存，本机跑不动",
    },
    {
        "id": "hy4-flash",
        "brand": "混元 Hy4",
        "name": "Hy4 flash（IQ2 分片）",
        "file": "",
        "size_mb": 128742,
        "url": "",
        "repo": f"{HF}/AngelSlim/Hy4-flash-GGUF",
        "fits": False,
        "note": "Hy4 flash 224B 总参，IQ2_AH 两分片共约 126GB；第三方量化",
    },
    {
        "id": "hy4",
        "brand": "混元 Hy4",
        "name": "Hy4（770B 官方权重）",
        "file": "",
        "size_mb": 0,
        "url": "",
        "repo": f"{HF}/tencent/Hy4",
        "fits": False,
        "note": "770B 总参/49B 激活，2026-11-04 发布、11-20 开源；官方仓库无 GGUF，原生权重约 1.5TB",
    },
    {
        "id": "kimi-k3",
        "brand": "Kimi",
        "name": "Kimi K3（1-bit 分片）",
        "file": "",
        "size_mb": 555000,
        "url": "",
        "repo": f"{HF}/unsloth/Kimi-K3-GGUF",
        "fits": False,
        "note": "2.8T 总参/104B 激活，最小 1-bit GGUF 约 15 个分片、509–594GB；需 600GB 级内存",
    },
]


def by_id(item_id: str):
    for it in CATALOG:
        if it["id"] == item_id:
            return it
    return None


def can_download(item: dict) -> bool:
    """只有单文件、且本机跑得动的模型才给一键下载。"""
    return bool(item.get("url")) and bool(item.get("fits"))


def fmt_size(mb: float) -> str:
    if not mb:
        return "—"
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.0f} MB"
