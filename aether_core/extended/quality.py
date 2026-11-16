"""Transparent agent quality metrics; scores do not alter agent decisions."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AgentMetric:
    agent: str
    runs: int
    successful: int
    failed: int
    success_rate: float
    updated_at: str


class AgentScorecard:
    def __init__(self) -> None:
        self._counts = defaultdict(lambda: {"success": 0, "failure": 0})

    def record(self, agent: str, *, success: bool) -> None:
        name = agent.strip().upper()
        if not name:
            raise ValueError("agent name is required")
        self._counts[name]["success" if success else "failure"] += 1

    def snapshot(self) -> list[AgentMetric]:
        now = datetime.now(timezone.utc).isoformat()
        result = []
        for agent, counts in sorted(self._counts.items()):
            total = counts["success"] + counts["failure"]
            result.append(
                AgentMetric(
                    agent,
                    total,
                    counts["success"],
                    counts["failure"],
                    counts["success"] / total,
                    now,
                )
            )
        return result
