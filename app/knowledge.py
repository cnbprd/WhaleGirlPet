# -*- coding: utf-8 -*-
"""本地知识库：导入 txt/md 文档 -> 分块 -> 纯 Python BM25 检索 -> 供聊天注入上下文。

不使用向量模型，避免额外下载体积；分块与检索全部在本机完成。
"""
import math
import os
import re
import sqlite3
import time

from paths import account_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  path TEXT DEFAULT '',
  chars INTEGER DEFAULT 0,
  ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id INTEGER NOT NULL,
  ord INTEGER NOT NULL,
  text TEXT NOT NULL
);
"""

CHUNK_CHARS = 420
CHUNK_OVERLAP = 60


def kb_dir() -> str:
    d = os.path.join(account_dir(), "kb")
    os.makedirs(d, exist_ok=True)
    return d


def _tokens(text: str) -> list:
    text = (text or "").lower()
    words = re.findall(r"[a-z0-9_]+", text)
    zh = re.findall(r"[\u4e00-\u9fff]", text)
    grams = ["".join(zh[i:i + 2]) for i in range(max(0, len(zh) - 1))]
    return words + grams


def split_text(text: str) -> list:
    text = re.sub(r"\r\n?", "\n", text or "").strip()
    if not text:
        return []
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks, buf = [], ""
    for p in paras:
        if len(p) > CHUNK_CHARS:
            if buf:
                chunks.append(buf)
                buf = ""
            for i in range(0, len(p), CHUNK_CHARS - CHUNK_OVERLAP):
                chunks.append(p[i:i + CHUNK_CHARS])
            continue
        if len(buf) + len(p) + 1 <= CHUNK_CHARS:
            buf = (buf + "\n" + p).strip() if buf else p
        else:
            chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    return chunks


class KnowledgeBase:
    def __init__(self, path: str = ""):
        self.path = path or os.path.join(account_dir(), "knowledge.db")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self):
        try:
            self.db.close()
        except Exception:  # noqa: BLE001
            pass

    # ---------- 导入 ----------
    def import_file(self, file_path: str) -> dict:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in (".txt", ".md", ".markdown", ".csv", ".log"):
            return {"ok": False, "reason": f"不支持的文件类型 {ext}（支持 txt / md / csv / log）"}
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError as e:
            return {"ok": False, "reason": str(e)[:120]}
        return self.add_text(os.path.basename(file_path), text, file_path)

    def add_text(self, name: str, text: str, src_path: str = "") -> dict:
        chunks = split_text(text)
        if not chunks:
            return {"ok": False, "reason": "内容为空"}
        cur = self.db.execute("INSERT INTO docs(name,path,chars,ts) VALUES(?,?,?,?)",
                              (name[:120], src_path[:300], len(text), time.time()))
        doc_id = cur.lastrowid
        for i, c in enumerate(chunks):
            self.db.execute("INSERT INTO chunks(doc_id,ord,text) VALUES(?,?,?)", (doc_id, i, c))
        self.db.commit()
        return {"ok": True, "doc_id": doc_id, "chunks": len(chunks), "chars": len(text)}

    def docs(self) -> list:
        rows = self.db.execute("SELECT id,name,chars,ts FROM docs ORDER BY id DESC").fetchall()
        return [{"id": r[0], "name": r[1], "chars": r[2], "ts": r[3]} for r in rows]

    def remove(self, doc_id: int) -> bool:
        self.db.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        self.db.execute("DELETE FROM docs WHERE id=?", (doc_id,))
        self.db.commit()
        return True

    def stats(self) -> dict:
        n_docs = int(self.db.execute("SELECT COUNT(*) FROM docs").fetchone()[0])
        n_chunks = int(self.db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
        chars = int(self.db.execute("SELECT COALESCE(SUM(chars),0) FROM docs").fetchone()[0])
        return {"docs": n_docs, "chunks": n_chunks, "chars": chars}

    # ---------- 检索（BM25） ----------
    def search(self, query: str, k: int = 3) -> list:
        q = _tokens(query)
        if not q:
            return []
        rows = self.db.execute("SELECT c.id, c.text, d.name FROM chunks c JOIN docs d ON d.id=c.doc_id").fetchall()
        if not rows:
            return []
        qset = set(q)
        n = len(rows)
        avgdl = sum(len(r[1]) for r in rows) / max(1, n)
        df = {}
        doc_tokens = []
        for cid, text, name in rows:
            toks = _tokens(text)
            doc_tokens.append((cid, text, name, toks))
            for t in set(toks):
                if t in qset:
                    df[t] = df.get(t, 0) + 1

        k1, b = 1.4, 0.72
        scored = []
        for cid, text, name, toks in doc_tokens:
            dl = len(toks) or 1
            s = 0.0
            for t in qset:
                f = toks.count(t)
                if not f:
                    continue
                idf = math.log(1 + (n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
                s += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
            if s > 0:
                scored.append((s, text, name))
        scored.sort(key=lambda x: -x[0])
        return [{"score": round(s, 2), "text": t, "doc": d} for s, t, d in scored[:k]]

    def context_block(self, query: str, k: int = 2, max_chars: int = 700) -> str:
        hits = self.search(query, k)
        if not hits:
            return ""
        parts = [f"[{h['doc']}] {h['text']}" for h in hits]
        return ("【本地知识库摘录】" + "\n".join(parts))[:max_chars]
