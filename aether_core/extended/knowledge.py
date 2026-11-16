"""Evidence-aware local memory; AI suggestions are never promoted automatically."""
from __future__ import annotations
import json, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

class KnowledgeStore:
    """Append-only knowledge ledger with explicit verification state."""
    def __init__(self, path: str | Path = "aether_extended_memory.sqlite3") -> None:
        self.path = str(path)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL, content TEXT NOT NULL,
                source TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('unverified','verified','rejected')),
                evidence TEXT NOT NULL, created_at TEXT NOT NULL, verified_at TEXT)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON knowledge(topic, status)")
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db
    def add(self, topic: str, content: str, *, source: str, evidence: dict[str, Any] | None = None) -> int:
        values = [topic.strip(), content.strip(), source.strip()]
        if not all(values): raise ValueError("topic, content and source must be non-empty")
        with self._connect() as db:
            cur = db.execute("INSERT INTO knowledge(topic,content,source,status,evidence,created_at) VALUES(?,?,?,'unverified',?,?)",
                (*values, json.dumps(evidence or {}, sort_keys=True), datetime.now(timezone.utc).isoformat()))
            return int(cur.lastrowid)
    def verify(self, entry_id: int, *, evidence: dict[str, Any]) -> bool:
        if not evidence or not any(str(v).strip() for v in evidence.values()):
            raise ValueError("non-empty verification evidence is required")
        with self._connect() as db:
            cur = db.execute("UPDATE knowledge SET status='verified', evidence=?, verified_at=? WHERE id=? AND status='unverified'",
                (json.dumps(evidence, sort_keys=True), datetime.now(timezone.utc).isoformat(), entry_id))
            return cur.rowcount == 1
    def reject(self, entry_id: int, *, reason: str) -> bool:
        if not reason.strip(): raise ValueError("a rejection reason is required")
        with self._connect() as db:
            cur = db.execute("UPDATE knowledge SET status='rejected', evidence=? WHERE id=? AND status='unverified'",
                (json.dumps({"rejection_reason": reason}, sort_keys=True), entry_id))
            return cur.rowcount == 1
    def search(self, topic: str, *, verified_only: bool = True, limit: int = 20) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100: raise ValueError("limit must be between 1 and 100")
        sql, args = "SELECT * FROM knowledge WHERE topic LIKE ?", [f"%{topic}%"]
        if verified_only: sql += " AND status='verified'"
        sql += " ORDER BY id DESC LIMIT ?"; args.append(limit)
        with self._connect() as db: rows = db.execute(sql, args).fetchall()
        return [dict(row) | {"evidence": json.loads(row["evidence"])} for row in rows]
