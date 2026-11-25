# -*- coding: utf-8 -*-
"""三层记忆（结构借鉴 Letta/MemGPT，代码自写）。

  Core     常驻上下文的小块文本（每轮都进 system prompt，有字数预算）
  Recall   最近对话 + 2-gram 检索（直接复用 MemoryStore）
  Archival 冷存：长期没被用到的事实归档，需要时再翻出来

三件事：
  tick_decay()  按半衰期给事实降权，又冷又老的归档，避免"什么都记得 = 什么都记不牢"
  compress()    把高度相似的重复事实合并成一条（权重相加、封顶），对应 MemGPT 的"重复信息压成原则"
  agenda()      把"还没做完的事"挑出来，交给主动开口用

为什么不做"让模型自己改记忆"：本项目 4B 本地模型改写记忆块极易写坏，
先用规则化的衰减/压缩把底座稳住，自编辑留到有可靠 JSON 约束时再说。
"""
import re
import sqlite3
import time

from memory import MemoryStore, _tokens

SCHEMA = """
CREATE TABLE IF NOT EXISTS blocks(
  label TEXT PRIMARY KEY, text TEXT NOT NULL, ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS archival(
  key TEXT NOT NULL, value TEXT NOT NULL, weight REAL, ts REAL, moved REAL
);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
"""

# 「还没做完」的线索词：命中就进议程
PENDING_HINTS = ("要", "想", "待", "记得", "下次", "明天", "后天", "改天", "回头", "还没", "欠", "约")

DEFAULT_HALF_LIFE = 45.0      # 45 天掉一半权重
ARCHIVE_BELOW = 0.20          # 权重低于这个
ARCHIVE_AFTER_DAYS = 60.0     # 且超过 60 天没动过


class MemoryTiers:
    def __init__(self, store: MemoryStore = None):
        self.store = store or MemoryStore()
        self.db = self.store.db
        self.db.executescript(SCHEMA)
        self.db.commit()

    # ---------------- 衰减与归档 ----------------
    def _meta(self, k: str, default: float) -> float:
        row = self.db.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        try:
            return float(row[0]) if row else default
        except (TypeError, ValueError):
            return default

    def _set_meta(self, k: str, v: float):
        self.db.execute("INSERT INTO meta(k,v) VALUES(?,?) "
                        "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, repr(v)))

    def tick_decay(self, half_life_days: float = DEFAULT_HALF_LIFE,
                   archive_below: float = ARCHIVE_BELOW,
                   archive_after_days: float = ARCHIVE_AFTER_DAYS) -> dict:
        """增量衰减：只按"距上次衰减过的天数"乘，反复调用不会叠加掉光。"""
        now = time.time()
        last = self._meta("last_decay", now)
        delta_days = (now - last) / 86400.0
        if delta_days < 0.01:
            return {"decayed": 0, "archived": 0, "skipped": True}

        factor = 0.5 ** (delta_days / float(half_life_days))
        rows = self.db.execute("SELECT id,key,value,weight,ts FROM facts").fetchall()
        decayed = archived = 0
        for fid, key, value, weight, ts in rows:
            age_days = max(0.0, (now - ts) / 86400.0)
            nw = float(weight or 1.0) * factor
            if nw < archive_below and age_days > archive_after_days:
                self.db.execute(
                    "INSERT INTO archival(key,value,weight,ts,moved) VALUES(?,?,?,?,?)",
                    (key, value, float(weight or 1.0), ts, now))
                self.db.execute("DELETE FROM facts WHERE id=?", (fid,))
                archived += 1
            elif abs(nw - float(weight or 1.0)) > 1e-3:
                self.db.execute("UPDATE facts SET weight=? WHERE id=?", (nw, fid))
                decayed += 1
        self._set_meta("last_decay", now)
        self.db.commit()
        return {"decayed": decayed, "archived": archived, "factor": round(factor, 4)}

    # ---------------- 压缩 ----------------
    def compress(self, jaccard: float = 0.6, cap: float = 3.0) -> int:
        """把说同一件事的事实并成一条：保留权重高的、内容长的，权重相加封顶。"""
        rows = self.db.execute("SELECT id,key,value,weight,ts FROM facts").fetchall()
        merged = 0
        used = set()
        toks = {r[0]: set(_tokens(r[2])) for r in rows}
        for i, a in enumerate(rows):
            if a[0] in used or not toks[a[0]]:
                continue
            for b in rows[i + 1:]:
                if b[0] in used or not toks[b[0]]:
                    continue
                inter = len(toks[a[0]] & toks[b[0]])
                union = len(toks[a[0]] | toks[b[0]]) or 1
                if inter / union < jaccard:
                    continue
                keep, drop = (a, b) if (a[3], len(a[2])) >= (b[3], len(b[2])) else (b, a)
                text = keep[2] if len(keep[2]) >= len(drop[2]) else drop[2]
                w = min(cap, float(keep[3] or 1.0) + float(drop[3] or 1.0))
                self.db.execute("UPDATE facts SET value=?, weight=?, ts=? WHERE id=?",
                                (text, w, max(keep[4], drop[4]), keep[0]))
                self.db.execute("DELETE FROM facts WHERE id=?", (drop[0],))
                used.add(drop[0])
                merged += 1
        self.db.commit()
        return merged

    # ---------------- 三层读取 ----------------
    def blocks(self) -> list:
        rows = self.db.execute("SELECT label,text,ts FROM blocks ORDER BY ts DESC").fetchall()
        return [{"label": r[0], "text": r[1], "ts": r[2]} for r in rows]

    def set_block(self, label: str, text: str):
        self.db.execute(
            "INSERT INTO blocks(label,text,ts) VALUES(?,?,?) "
            "ON CONFLICT(label) DO UPDATE SET text=excluded.text, ts=excluded.ts",
            ((label or "").strip()[:40] or "未命名", (text or "").strip()[:600], time.time()))
        self.db.commit()

    def core(self, budget: int = 520, n_facts: int = 8) -> str:
        """常驻块：预算内的一段话，直接拼进 system prompt。"""
        parts = []
        facts = self.store.facts(n_facts)
        if facts:
            parts.append("【她记着的】" + "；".join(f"{f['key']}={f['value']}" for f in facts))
        bl = self.blocks()
        if bl:
            parts.append("【当前在意】" + "；".join(f"{b['label']}:{b['text']}" for b in bl[:2]))
        notes = self.store.notes(1)
        if notes:
            parts.append("【上一件聊过的事】" + str(notes[0]["text"])[:100])
        return "\n".join(parts)[:budget]

    def recall(self, query: str, k: int = 3) -> list:
        return self.store.search(query, k)

    def archival(self, n: int = 6) -> list:
        rows = self.db.execute(
            "SELECT key,value,weight FROM archival ORDER BY weight DESC, moved DESC LIMIT ?",
            (n,)).fetchall()
        return [{"key": r[0], "value": r[1], "weight": r[2]} for r in rows]

    def archival_search(self, query: str, k: int = 2) -> list:
        toks = set(_tokens(query))
        if not toks:
            return []
        out = []
        for r in self.db.execute("SELECT key,value,weight FROM archival").fetchall():
            vt = set(_tokens(str(r[1])))
            if vt and len(toks & vt) / (len(toks | vt) or 1) >= 0.25:
                out.append({"key": r[0], "value": r[1], "weight": r[2]})
        return out[:k]

    # ---------------- 议程（主动性） ----------------
    def agenda(self, n: int = 3) -> list:
        """从事实和笔记里挑"还没做完"的事，作为主动开口的候选话题。"""
        cands = []
        for f in self.store.facts(20):
            s = f"{f['key']}={f['value']}"
            if any(h in s for h in PENDING_HINTS):
                cands.append((f["key"], str(f["value"])))
        for nt in self.store.notes(5):
            t = str(nt["text"])
            for sent in re.split(r"[。！？\n]", t):
                sent = sent.strip()
                if len(sent) >= 4 and any(h in sent for h in PENDING_HINTS):
                    cands.append((sent[:12], sent[:60]))
        # 去重 + 截断
        seen, out = set(), []
        for k, s in cands:
            if k in seen:
                continue
            seen.add(k)
            out.append(s)
        return out[:n]

    def stats(self) -> dict:
        return {
            "messages": self.store.count(),
            "facts": int(self.db.execute("SELECT COUNT(*) FROM facts").fetchone()[0]),
            "archival": int(self.db.execute("SELECT COUNT(*) FROM archival").fetchone()[0]),
            "blocks": int(self.db.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]),
            "last_decay": self._meta("last_decay", 0.0),
        }
