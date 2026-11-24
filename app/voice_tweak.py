# -*- coding: utf-8 -*-
"""音色微调指令解析：把「再尖一点 / 慢 10% / 音量 60」这类人话变成三个参数。

只做确定性规则，不联网、不猜测：命中什么就改什么，没命中就如实说没听懂。
"""
import re

PITCH_RANGE = (-60, 60)
RATE_RANGE = (-50, 50)
VOL_RANGE = (10, 100)
VOL_DEFAULT = 80


def _clamp(v, r):
    return max(r[0], min(r[1], int(v)))


def parse(cmd: str, pitch: int = 0, rate: int = 0, volume: int = VOL_DEFAULT):
    """把一句中文指令解析成 (pitch, rate, volume, notes)。

    notes 是给用户看的逐条解释，界面直接显示。
    """
    t = (cmd or "").strip()
    notes = []
    if not t:
        return pitch, rate, volume, ["没填指令"]
    if re.search(r"(默认|还原|重置|恢复|reset|原样)", t, re.I):
        return 0, 0, VOL_DEFAULT, [f"已还原默认：音高 0 / 语速 0 / 音量 {VOL_DEFAULT}"]

    hit = {"pitch": False, "rate": False, "vol": False}

    # 1) 点名参数的绝对数值
    m = re.search(r"(?:音高|pitch)[^\d\-]{0,8}(\-?\d+)", t, re.I)
    if m:
        pitch = _clamp(int(m.group(1)), PITCH_RANGE)
        hit["pitch"] = True
        notes.append(f"音高 → {pitch:+d}Hz")
    m = re.search(r"(?:语速|速度|rate)[^\d\-%]{0,8}(\-?\d+)", t, re.I)
    if m:
        rate = _clamp(int(m.group(1)), RATE_RANGE)
        hit["rate"] = True
        notes.append(f"语速 → {rate:+d}%")
    m = re.search(r"(?:音量|volume)[^\d]{0,8}(\d+)", t, re.I)
    if m:
        volume = _clamp(int(m.group(1)), VOL_RANGE)
        hit["vol"] = True
        notes.append(f"音量 → {volume}")

    # 2) 带百分号的相对调整
    m = re.search(r"(?:慢|放慢|降速|减速)(?:一点|点儿)?[^\d%]{0,4}(\d+)\s*%", t)
    if m and not hit["rate"]:
        rate = _clamp(rate - int(m.group(1)), RATE_RANGE)
        hit["rate"] = True
        notes.append(f"语速 -{m.group(1)}% → {rate:+d}%")
    m = re.search(r"(?:快|加速|提速)(?:一点|点儿)?[^\d%]{0,4}(\d+)\s*%", t)
    if m and not hit["rate"]:
        rate = _clamp(rate + int(m.group(1)), RATE_RANGE)
        hit["rate"] = True
        notes.append(f"语速 +{m.group(1)}% → {rate:+d}%")

    # 3) 形容词（未点名参数时才生效，避免和数值打架）
    if not hit["pitch"]:
        if re.search(r"(尖|高音|亮|年轻|少女|萝莉|可爱|细)", t):
            pitch = _clamp(pitch + 8, PITCH_RANGE)
            notes.append(f"音高 +8 → {pitch:+d}Hz")
        elif re.search(r"(沉|低音|厚|哑|成熟|御姐|粗)", t):
            pitch = _clamp(pitch - 8, PITCH_RANGE)
            notes.append(f"音高 -8 → {pitch:+d}Hz")
    if not hit["rate"]:
        if re.search(r"(快|急|利索|干脆|赶)", t):
            rate = _clamp(rate + 6, RATE_RANGE)
            notes.append(f"语速 +6 → {rate:+d}%")
        elif re.search(r"(慢|缓|温柔|软|悠)", t):
            rate = _clamp(rate - 6, RATE_RANGE)
            notes.append(f"语速 -6 → {rate:+d}%")
    if not hit["vol"]:
        if re.search(r"(大声|响|有力|吵)", t):
            volume = _clamp(volume + 10, VOL_RANGE)
            notes.append(f"音量 +10 → {volume}")
        elif re.search(r"(小声|轻|安静|柔)", t):
            volume = _clamp(volume - 10, VOL_RANGE)
            notes.append(f"音量 -10 → {volume}")

    if not notes:
        notes.append("这条没听懂。可以点名参数（音高 20 / 语速 -10 / 音量 80），"
                     "或说「尖一点」「慢一点」「小声一点」。")
    return pitch, rate, volume, notes
