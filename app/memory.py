# -*- coding: utf-8 -*-
"""本地记忆库（SQLite）：对话消息、事实条目、自动摘要，全部留在这台电脑上。

检索用字符 n-gram 倒排 + 时间衰减打分，不依赖向量模型，零额外体积。
"""
import os
import re
import sqlite3
import time

from paths import account_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS facts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  weight REAL DEFAULT 1.0,
  ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS notes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  text TEXT NOT NULL,
  ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_msg_ts ON messages(ts);
"""


def _tokens(text: str) -> list:
    """中文 2-gram + 英文单词，够用且轻量。"""
    text = (text or "").lower()
    words = re.findall(r"[a-z0-9_]+", text)
    zh = re.findall(r"[\u4e00-\u9fff]", text)
    grams = ["".join(zh[i:i + 2]) for i in range(max(0, len(zh) - 1))]
    return words + grams


class MemoryStore:
    def __init__(self, path: str = ""):
        self.path = path or os.path.join(account_dir(), "memory.db")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self):
        try:
            self.db.close()
        except Exception:  # noqa: BLE001
            pass

    # ---------- 消息 ----------
    def add_message(self, role: str, content: str):
        self.db.execute("INSERT INTO messages(role,content,ts) VALUES(?,?,?)",
                        (role, (content or "")[:2000], time.time()))
        self.db.commit()

    def recent(self, n: int = 10) -> list:
        rows = self.db.execute(
            "SELECT role,content FROM messages ORDER BY id DESC LIMIT ?", (n,)).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def count(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM messages").fetchone()[0])

    # ---------- 事实 ----------
    def add_fact(self, key: str, value: str):
        key, value = (key or "").strip()[:80], (value or "").strip()[:400]
        if not key or not value:
            return
        old = self.db.execute("SELECT id,value FROM facts WHERE key=?", (key,)).fetchone()
        if old and old[1] == value:
            self.db.execute("UPDATE facts SET weight=weight+0.5, ts=? WHERE id=?", (time.time(), old[0]))
        elif old:
            self.db.execute("DELETE FROM facts WHERE id=?", (old[0],))
            self.db.execute("INSERT INTO facts(key,value,weight,ts) VALUES(?,?,?,?)",
                            (key, value, 1.0, time.time()))
        else:
            self.db.execute("INSERT INTO facts(key,value,weight,ts) VALUES(?,?,?,?)",
                            (key, value, 1.0, time.time()))
        self.db.commit()

    def facts(self, n: int = 20) -> list:
        rows = self.db.execute(
            "SELECT key,value FROM facts ORDER BY weight DESC, ts DESC LIMIT ?", (n,)).fetchall()
        return [{"key": r[0], "value": r[1]} for r in rows]

    def forget_all(self) -> int:
        n = self.count()
        self.db.execute("DELETE FROM messages")
        self.db.execute("DELETE FROM facts")
        self.db.execute("DELETE FROM notes")
        self.db.commit()
        return n

    # ---------- 检索 ----------
    def search(self, query: str, k: int = 4) -> list:
        toks = set(_tokens(query))
        if not toks:
            return []
        rows = self.db.execute("SELECT role,content,ts FROM messages ORDER BY id DESC LIMIT 2000").fetchall()
        scored = []
        now = time.time()
        for role, content, ts in rows:
            ct = set(_tokens(content))
            if not ct:
                continue
            overlap = len(toks & ct)
            if overlap == 0:
                continue
            age_day = max(0.0, (now - ts) / 86400.0)
            score = overlap * 2.0 - min(3.0, age_day * 0.25)
            scored.append((score, role, content))
        scored.sort(key=lambda x: -x[0])
        return [{"role": r, "content": c} for _s, r, c in scored[:k]]

    def context_block(self, query: str, n_recent: int = 6, n_facts: int = 6) -> str:
        """给大模型拼一段记忆提示，超出预算自动截断。"""
        parts = []
        facts = self.facts(n_facts)
        if facts:
            parts.append("【你记住的关于鱼片的事】" + "；".join(f"{f['key']}={f['value']}" for f in facts))
        hits = self.search(query, 3)
        if hits:
            parts.append("【相关旧对话】" + " / ".join(h["content"][:90] for h in hits))
        return "\n".join(parts)[:900]

    # ---------- 摘要 ----------
    def add_note(self, text: str):
        self.db.execute("INSERT INTO notes(text,ts) VALUES(?,?)",
                        ((text or "")[:1200], time.time()))
        self.db.commit()

    def notes(self, n: int = 10) -> list:
        rows = self.db.execute("SELECT text,ts FROM notes ORDER BY id DESC LIMIT ?", (n,)).fetchall()
        return [{"text": r[0], "ts": r[1]} for r in rows]


FACT_PATTERNS = [
    (r"我(?:的)?名字(?:叫|是)\s*([^\s，。,\.!?！？]{1,12})", "用户名"),
    (r"我(?:今年|现在)?\s*(\d{1,2})\s*岁", "年龄"),
    (r"我(?:住在|家在|在)\s*([^\s，。,\.!?！？]{2,10})", "所在地"),
    (r"我(?:在|是做)\s*([^\s，。,\.!?！？]{2,12})(?:上班|工作|干活)", "职业"),
    (r"我(?:喜欢|最爱)\s*([^\s，。,\.!?！？]{1,16})", "喜好"),
]


def extract_facts(text: str) -> list:
    """从用户发言里抽取可长期记住的事实，规则化，宁可少记不乱记。"""
    out = []
    for pat, key in FACT_PATTERNS:
        m = re.search(pat, text or "")
        if m:
            val = m.group(1).strip()
            if val and len(val) <= 20:
                out.append((key, val))
    return out
