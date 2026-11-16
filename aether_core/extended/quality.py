"""Persistent, transparent agent quality metrics; scores never alter decisions."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class AgentMetric:
    agent: str
    runs: int
    successful: int
    failed: int
    success_rate: float
    updated_at: str


class AgentScorecard:
    """Record agent outcomes in SQLite when a path is supplied; memory-only otherwise."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = str(path) if path is not None else None
        self._counts: dict[str, dict[str, int]] = {}
        if self.path is not None:
            with self._connect() as db:
                db.execute(
                    """CREATE TABLE IF NOT EXISTS agent_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent TEXT NOT NULL,
                        success INTEGER NOT NULL CHECK(success IN (0, 1)),
                        recorded_at TEXT NOT NULL
                    )"""
                )
                db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_agent_runs_agent ON agent_runs(agent)"
                )

    def _connect(self) -> sqlite3.Connection:
        if self.path is None:
            raise RuntimeError("Persistent storage is not configured")
        return sqlite3.connect(self.path, timeout=10)

    def record(self, agent: str, *, success: bool) -> None:
        name = agent.strip().upper()
        if not name:
            raise ValueError("agent name is required")
        recorded_at = datetime.now(timezone.utc).isoformat()
        if self.path is None:
            counts = self._counts.setdefault(name, {"success": 0, "failure": 0})
            counts["success" if success else "failure"] += 1
            return
        with self._connect() as db:
            db.execute(
                "INSERT INTO agent_runs(agent, success, recorded_at) VALUES (?, ?, ?)",
                (name, int(success), recorded_at),
            )

    def snapshot(self) -> list[AgentMetric]:
        if self.path is None:
            rows = [
                (agent, counts["success"], counts["failure"], "")
                for agent, counts in sorted(self._counts.items())
            ]
        else:
            with self._connect() as db:
                rows = db.execute(
                    """SELECT agent, SUM(success), COUNT(*) - SUM(success), MAX(recorded_at)
                       FROM agent_runs GROUP BY agent ORDER BY agent"""
                ).fetchall()
        now = datetime.now(timezone.utc).isoformat()
        return [
            AgentMetric(
                agent=agent,
                runs=int(successful) + int(failed),
                successful=int(successful),
                failed=int(failed),
                success_rate=int(successful) / (int(successful) + int(failed)),
                updated_at=updated_at or now,
            )
            for agent, successful, failed, updated_at in rows
        ]
