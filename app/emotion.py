# -*- coding: utf-8 -*-
"""情绪库与性格自生长。

八个情绪维度（0-100）描述"此刻"，四个性格参数（0-100，基准 50）描述"长期"。
每次互动同时改情绪和（极小幅地）改性格：反复被摸头会变黏人、被冷落会变傲娇，
形成缓慢自生长；性格始终向基准回归一点，避免长期跑成极端。
"""
import json
import os
import time

EMOTIONS = {
    "joy": "开心", "anger": "生气", "sad": "失落", "fear": "不安",
    "surprise": "惊讶", "shy": "害羞", "tired": "疲倦", "proud": "得意",
}

TRAITS = {
    "tsundere": "傲娇度", "clingy": "黏人度", "sarcasm": "毒舌度", "gentle": "温柔度",
}

# 事件 -> 情绪增量 / 性格增量（性格增量是万分位级别，累积才明显）
EVENTS = {
    "pat":      ({"joy": 6, "shy": 5, "sad": -3},              {"clingy": 0.9, "tsundere": -0.5}),
    "feed_like":({"joy": 14, "tired": -4, "sad": -5},          {"clingy": 0.6, "gentle": 0.4}),
    "feed_hate":({"anger": 8, "joy": -5},                      {"sarcasm": 0.6}),
    "chat":     ({"joy": 4, "tired": -2},                      {"gentle": 0.3}),
    "ignore":   ({"sad": 5, "anger": 2},                       {"tsundere": 0.8, "clingy": -0.5}),
    "run":      ({"joy": 8, "tired": 6, "surprise": 4},        {"tsundere": -0.3}),
    "collide":  ({"surprise": 12, "fear": 6, "anger": 3},      {"sarcasm": 0.4}),
    "task_done":({"proud": 12, "joy": 6, "tired": 5},          {"gentle": 0.3}),
    "task_fail":({"sad": 8, "anger": 4},                       {"tsundere": 0.5}),
    "praise":   ({"joy": 10, "proud": 8, "shy": 3},            {"gentle": 0.8, "sarcasm": -0.4}),
    "scold":    ({"anger": 10, "sad": 6},                      {"tsundere": 0.7, "sarcasm": 0.5}),
    "night":    ({"tired": 8},                                  {}),
    "rest":     ({"tired": -14, "joy": 3},                     {}),
}

DECAY_PER_MIN = 0.12   # 情绪每分钟向 0 回落
MEAN_REVERT = 0.004    # 性格每次事件向 50 回归的比例


def _clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


class EmotionState:
    def __init__(self):
        self.emotions = {k: 20.0 for k in EMOTIONS}
        self.emotions["joy"] = 55.0
        self.traits = {k: 50.0 for k in TRAITS}
        self.traits["tsundere"] = 62.0
        self.traits["gentle"] = 44.0
        self.counts = {}
        self.last_ts = time.time()
        self.history = []   # [(ts, event, dominant)]，只留最近 200 条

    # ---------- 事件 ----------
    def apply(self, event: str, strength: float = 1.0):
        emo_d, tr_d = EVENTS.get(event, ({}, {}))
        for k, v in emo_d.items():
            if k in self.emotions:
                self.emotions[k] = _clamp(self.emotions[k] + v * strength)
        for k, v in tr_d.items():
            if k in self.traits:
                cur = self.traits[k]
                cur += v * strength
                cur += (50.0 - cur) * MEAN_REVERT * strength
                self.traits[k] = _clamp(cur)
        self.counts[event] = self.counts.get(event, 0) + 1
        self.history.append((time.time(), event, self.dominant()))
        if len(self.history) > 200:
            self.history = self.history[-200:]

    # ---------- v2.9.6 聊天内容驱动的性格生长 ----------
    # 性格只由"实际聊过的话 + 互动事件"慢慢长出来，不提供任何手动改性格的底层入口。
    CHAT_CUES = {
        "praise": ("喜欢你", "可爱", "好乖", "厉害", "真棒", "爱你", "谢谢", "贴心",
                   "漂亮", "可爱死", "乖"),
        "scold": ("笨", "烦", "滚", "讨厌", "闭嘴", "没用", "生气", "别吵"),
        "miss": ("想你", "陪我", "在吗", "抱抱", "别走", "黏", "亲亲"),
        "tired": ("累", "难过", "压力", "焦虑", "失眠", "烦死", "撑不住", "委屈"),
    }

    def apply_text(self, text: str, strength: float = 1.0):
        """从一句聊天里读出倾向，极小幅改情绪与性格（真正的"聊着聊着变了"）。"""
        t = text or ""
        if not t:
            return
        hit = [k for k, words in self.CHAT_CUES.items() if any(w in t for w in words)]
        if "praise" in hit:
            self.apply("praise", 0.45 * strength)
        if "scold" in hit:
            self.apply("scold", 0.45 * strength)
        if "miss" in hit:
            self.apply("pat", 0.4 * strength)          # 撒娇/黏人，靠近摸头的效果
        if "tired" in hit:
            # 主人示弱：她会软下来一点、也跟着低落一点
            self.emotions["sad"] = _clamp(self.emotions["sad"] + 5 * strength)
            self.emotions["joy"] = _clamp(self.emotions["joy"] - 3 * strength)
            cur = self.traits["gentle"]
            cur += 0.7 * strength
            cur += (50.0 - cur) * MEAN_REVERT * strength
            self.traits["gentle"] = _clamp(cur)
            self.counts["care"] = self.counts.get("care", 0) + 1
        if hit:
            self.history.append((time.time(), "chat:" + "+".join(hit), self.dominant()))
            if len(self.history) > 200:
                self.history = self.history[-200:]

    def decay(self):
        """按经过时间回落情绪。"""
        now = time.time()
        minutes = max(0.0, (now - self.last_ts) / 60.0)
        self.last_ts = now
        for k in self.emotions:
            self.emotions[k] = _clamp(self.emotions[k] - DECAY_PER_MIN * minutes * 1.2
                                      if k != "joy" else self.emotions[k] - DECAY_PER_MIN * 0.4 * minutes)
        return minutes

    # ---------- 解读 ----------
    def dominant(self) -> str:
        top = max(self.emotions.items(), key=lambda kv: kv[1])
        return top[0] if top[1] >= 22 else "calm"

    def mood_score(self) -> float:
        pos = self.emotions["joy"] + self.emotions["proud"] * 0.6 + self.emotions["shy"] * 0.3
        neg = (self.emotions["anger"] + self.emotions["sad"] + self.emotions["fear"]
               + self.emotions["tired"] * 0.8)
        return _clamp(50 + (pos - neg) * 0.4)

    def expression_hint(self) -> str:
        d = self.dominant()
        return {
            "joy": "happy", "anger": "angry", "sad": "sleepy", "fear": "curious",
            "surprise": "curious", "shy": "shy", "tired": "sleep",
            "proud": "happy", "calm": "idle",
        }.get(d, "idle")

    def voice_hint(self) -> dict:
        """语速与音调随情绪微调，交给 TTS。"""
        e = self.emotions
        rate = 0
        pitch = 0
        rate += int((e["joy"] - 50) / 12) - int((e["sad"] - 20) / 14)
        pitch += int((e["joy"] - 50) / 10) - int((e["tired"] - 30) / 12)
        return {"rate_pct": max(-18, min(22, rate)),
                "pitch_hz": max(-20, min(20, pitch))}

    def trait_word(self) -> str:
        t = self.traits
        if t["tsundere"] >= 62:
            return "tsundere"
        if t["clingy"] >= 62:
            return "clingy"
        if t["sarcasm"] >= 62:
            return "sarcasm"
        if t["gentle"] >= 62:
            return "gentle"
        return "balanced"

    def describe(self) -> str:
        e = self.emotions
        top = sorted(e.items(), key=lambda kv: -kv[1])[:3]
        parts = "、".join(f"{EMOTIONS[k]} {v:.0f}" for k, v in top)
        tr = "、".join(f"{TRAITS[k]} {v:.0f}" for k, v in self.traits.items())
        return f"当前情绪：{parts}；性格：{tr}；主导人格：{self.trait_word()}"

    def to_prompt(self) -> str:
        """给大模型的一句话性格提示。"""
        t = self.traits
        bits = []
        if t["tsundere"] > 55:
            bits.append("嘴上很傲，喜欢否认自己的关心")
        if t["clingy"] > 55:
            bits.append("很黏人，容易追问你在不在")
        if t["sarcasm"] > 55:
            bits.append("爱开小毒舌，损人不伤人")
        if t["gentle"] > 55:
            bits.append("会认真安慰人，语气软")
        if not bits:
            bits.append("性格均衡，随当天心情变化")
        return "；".join(bits)

    # ---------- 序列化 ----------
    def to_dict(self) -> dict:
        return {
            "emotions": {k: round(v, 1) for k, v in self.emotions.items()},
            "traits": {k: round(v, 1) for k, v in self.traits.items()},
            "counts": self.counts,
            "ts": self.last_ts,
        }

    def from_dict(self, d: dict):
        if not isinstance(d, dict):
            return
        for k in EMOTIONS:
            if k in d.get("emotions", {}):
                self.emotions[k] = _clamp(float(d["emotions"][k]))
        for k in TRAITS:
            if k in d.get("traits", {}):
                self.traits[k] = _clamp(float(d["traits"][k]))
        self.counts = {str(k): int(v) for k, v in (d.get("counts") or {}).items()}
        try:
            self.last_ts = float(d.get("ts", self.last_ts))
        except (TypeError, ValueError):
            pass
