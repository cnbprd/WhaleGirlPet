# -*- coding: utf-8 -*-
"""真人音色提炼表：把真人语音的声学特征映射成 Edge TTS 能接受的参数。

只做声学统计（基频、语速、亮度），不保存原始音频、不做音色克隆。
来源见 assets/ref/voice_profile.json 与 docs/voice-profile.md。

实测数据（2026-11-24，本机 24kHz 合成 → 16kHz 单声道分析）：
  zh-CN-XiaoxiaoNeural 基准 F0 = 238.8Hz
      pitch 名义 0/20/40/60/90  →  实测 238.8/271.2/301.9/333.3/355.6
      ≥90 名义值后饱和在 355.6Hz（约基线的 1.49 倍）
  zh-CN-XiaoyiNeural 基准 F0 = 296.3Hz
      名义 0/20/40/60  →  实测 296.3/340.4/376.5/410.3
      ≥90 后回落，不稳定（音质已崩，不要用到那里）

结论：Edge 的 pitch 不是"加多少 Hz"，而是近似比例抬升，且上限约 1.45 倍。
所以这里用「实测斜率 + 饱和点」反查名义值，而不是直接把 Hz 差丢进去。
"""

# 音色基准（实测中位基频）
BASE_F0 = {
    "zh-CN-XiaoxiaoNeural": 238.8,
    "zh-CN-XiaoyiNeural": 296.3,
}
# 每个名义单位带来的实际 F0 变化（Hz/单位）
SLOPE = {
    "zh-CN-XiaoxiaoNeural": 1.575,
    "zh-CN-XiaoyiNeural": 2.15,
}
# 实测饱和点（超过就没意义，音质先崩）
CAP_F0 = {
    "zh-CN-XiaoxiaoNeural": 355.6,
    "zh-CN-XiaoyiNeural": 405.1,
}
DEFAULT_BASE = 250.0
DEFAULT_SLOPE = 1.70
DEFAULT_CAP_RATIO = 1.45

# 真人参考（B 站公开语音，仅测特征）
PROFILES = {
    "jingjing": {
        "title": "元气少女",
        "f0": 363.6,      # 中位基频
        "f0_p10": 266.7,
        "f0_p90": 432.4,
        "f0_std": 63.5,
        "source": "B站 BV1LUHN6hEhS《晶晶的表情包》真人自配，26.5s",
        "note": "音区偏高、起伏大，适合元气/傲娇短句",
    },
    "linluo": {
        "title": "温柔少女",
        "f0": 285.7,
        "f0_p10": 205.1,
        "f0_p90": 390.2,
        "f0_std": 77.0,
        "source": "B站 BV1FVPQzgEM3 有声书片段（CV泠落），35.4s",
        "note": "音区偏低、气声多，适合低声安抚、夜里说话",
    },
}
DEFAULT_PROFILE = "jingjing"
STRENGTH = 0.9   # 只靠近 90%，避免贴到饱和点导致音质劣化


def profile_names():
    return [(k, v["title"]) for k, v in PROFILES.items()]


def get_profile(name: str) -> dict:
    return PROFILES.get(name) or PROFILES[DEFAULT_PROFILE]


def _base(voice: str):
    return BASE_F0.get(voice, DEFAULT_BASE), SLOPE.get(voice, DEFAULT_SLOPE), CAP_F0.get(
        voice, BASE_F0.get(voice, DEFAULT_BASE) * DEFAULT_CAP_RATIO)


def pitch_for(voice: str, profile_name: str = DEFAULT_PROFILE, strength: float = STRENGTH):
    """返回 (pitch_nominal, goal_f0, reachable)。

    pitch_nominal 是可直接丢给 edge_tts 的整数；goal_f0 是目标基频；
    reachable 表示这个音色能不能真的够到目标（不够到就是 None）。
    """
    prof = get_profile(profile_name)
    base, slope, cap = _base(voice)
    raw_goal = base + (prof["f0"] - base) * max(0.0, min(1.0, strength))
    reachable = round(raw_goal, 1) if raw_goal <= cap + 0.5 else None
    goal = min(raw_goal, cap)
    nominal = int(round((goal - base) / slope))
    nominal = max(-45, min(70, nominal))
    return nominal, round(goal, 1), reachable


def describe(voice: str, profile_name: str = DEFAULT_PROFILE) -> str:
    prof = get_profile(profile_name)
    nominal, goal, reach = pitch_for(voice, profile_name)
    base, slope, cap = _base(voice)
    if reach:
        return (f"{prof['title']}：目标 {prof['f0']}Hz，{voice} 基准 {base}Hz，"
                f"实际拉到 {goal}Hz（pitch {nominal:+d}）")
    return (f"{prof['title']}：目标 {prof['f0']}Hz，{voice} 上限 {cap}Hz，"
            f"只能到 {goal}Hz（pitch {nominal:+d}），够不满，差距 "
            f"{round(prof['f0'] - goal, 1)}Hz")


def rate_for(profile_name: str = DEFAULT_PROFILE) -> int:
    """语速：真人样本的能量包络周期估算不可靠（背景音会干扰），
    所以这里不给百分比，返回 0，由情绪 hint 自己决定。"""
    return 0


def load_external():
    """可选：assets/ref/voice_profile.json 若存在，覆盖内置表（方便以后加新样本）。"""
    import json
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    path = os.path.join(root, "assets", "ref", "voice_profile.json")
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in (data.get("profiles") or {}).items():
            if isinstance(v, dict) and v.get("f0"):
                PROFILES[k] = v
        for k, v in (data.get("base_f0") or {}).items():
            BASE_F0[k] = float(v)
        return True
    except Exception:
        return False


load_external()
