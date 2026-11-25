# -*- coding: utf-8 -*-
"""渲染档自动判定（v3.0.21）：没有独显的机器不该照着高配跑。

判据（按顺序）：
1. 远程桌面会话（SESSIONNAME 以 RDP- 开头）→ low：远程编码本身就是瓶颈
2. nvidia-smi 能报出显卡 → high
3. 其余（Intel/AMD 核显、虚拟机显卡）→ low

实测依据（267x512 立绘，30fps 采样）：
high 8×20 网格 320 三角 → 中位 12.3~12.8ms；
low 6×12 网格 144 三角 + 关平滑采样 → 中位 6.2~6.7ms，约省 48%。
"""
import os


def remote_session() -> bool:
    return str(os.environ.get("SESSIONNAME", "")).upper().startswith("RDP-")


def has_discrete_gpu() -> bool:
    try:
        import hwinfo
        return bool((hwinfo.snapshot() or {}).get("gpu"))
    except Exception:  # noqa: BLE001
        return False


def detect_quality() -> str:
    if remote_session():
        return "low"
    return "high" if has_discrete_gpu() else "low"


def resolve_quality(value: str) -> str:
    """配置里写 high/mid/low 就照办，写 auto 或空则自动判定。"""
    v = str(value or "auto").strip().lower()
    if v in ("high", "mid", "low"):
        return v
    return detect_quality()


def frame_ms_for(quality: str, override: int = 0) -> int:
    """低配档 40ms（25fps），其余 33ms（30fps）；override>0 时以它为准（夹 16~120）。"""
    if int(override or 0) > 0:
        return max(16, min(120, int(override)))
    return 40 if quality == "low" else 33
