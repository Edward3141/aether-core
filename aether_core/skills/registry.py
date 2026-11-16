"""Explicit registry for deterministic, bounded AETHER CORE skills.

Skills are Python handlers registered by the application. No dynamic imports,
shell execution, eval, or model-authored code is supported.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..extended.knowledge import KnowledgeStore
from ..extended.monitor import collect_snapshot
from ..extended.quality import AgentScorecard
from ..extended.reports import build_report


@dataclass(frozen=True)
class SkillSpec:
    name: str
    description: str
    allowed_callers: tuple[str, ...]
    handler: Callable[[dict[str, Any]], Any]


class SkillRegistry:
    """Allow-listed skill dispatcher with caller and argument validation."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillSpec] = {}

    def register(self, skill: SkillSpec) -> None:
        if not skill.name or skill.name in self._skills:
            raise ValueError("skill name must be non-empty and unique")
        if not skill.allowed_callers:
            raise ValueError("a skill must declare at least one allowed caller")
        self._skills[skill.name] = skill

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "allowed_callers": list(skill.allowed_callers),
                "execution": "local deterministic handler",
            }
            for skill in sorted(self._skills.values(), key=lambda item: item.name)
        ]

    def execute(
        self, name: str, *, caller: str, arguments: dict[str, Any] | None = None
    ) -> Any:
        skill = self._skills.get(name)
        if skill is None:
            raise ValueError("skill is not registered")
        identity = caller.strip().upper()
        if identity not in skill.allowed_callers:
            raise PermissionError("caller is not allowed to use this skill")
        payload = arguments or {}
        if not isinstance(payload, dict):
            raise ValueError("skill arguments must be an object")
        return skill.handler(payload)


def build_builtin_registry(
    knowledge: KnowledgeStore, scorecard: AgentScorecard
) -> SkillRegistry:
    """Create the safe built-in skill set used by the core workflow."""
    registry = SkillRegistry()
    callers = ("SCOUT", "ANALYST", "FIXER", "AUDITOR", "HUMAN", "SYSTEM", "MCP")

    def no_arguments(args: dict[str, Any]) -> None:
        if args:
            raise ValueError("this skill does not accept arguments")

    def system_snapshot(args: dict[str, Any]) -> dict[str, Any]:
        no_arguments(args)
        return collect_snapshot().to_dict()

    def knowledge_stats(args: dict[str, Any]) -> dict[str, int]:
        no_arguments(args)
        return {
            "unverified": knowledge.count(status="unverified"),
            "verified": knowledge.count(status="verified"),
            "rejected": knowledge.count(status="rejected"),
            "total": knowledge.count(),
        }

    def knowledge_search(args: dict[str, Any]) -> list[dict[str, Any]]:
        if set(args) - {"topic", "limit"}:
            raise ValueError("unsupported knowledge.search argument")
        topic = args.get("topic")
        limit = args.get("limit", 20)
        if not isinstance(topic, str) or len(topic) > 120:
            raise ValueError("topic must be a string of at most 120 characters")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ValueError("limit must be an integer between 1 and 50")
        # Unverified AI/system observations are never supplied as trusted context.
        return knowledge.search(topic, verified_only=True, limit=limit)

    def report_generate(args: dict[str, Any]) -> dict[str, Any]:
        no_arguments(args)
        metrics = [item.__dict__ for item in scorecard.snapshot()]
        stats = knowledge_stats({})
        return build_report(
            snapshot=system_snapshot({}),
            agent_metrics=metrics,
            findings=[{
                "title": "Knowledge ledger",
                "description": (
                    f"{stats['unverified']} unverified; {stats['verified']} verified; "
                    f"{stats['rejected']} rejected"
                ),
            }],
        )

    registry.register(SkillSpec(
        "system.snapshot", "Collect read-only platform, CPU, memory and disk metadata.",
        callers, system_snapshot
    ))
    registry.register(SkillSpec(
        "knowledge.search", "Search verified evidence only; unverified entries are excluded.",
        ("ANALYST", "AUDITOR", "HUMAN", "MCP"), knowledge_search
    ))
    registry.register(SkillSpec(
        "knowledge.stats", "Read counts for verified, unverified and rejected evidence.",
        callers, knowledge_stats
    ))
    registry.register(SkillSpec(
        "report.generate", "Build a JSON-compatible system, agent and evidence report.",
        ("HUMAN", "SYSTEM", "MCP"), report_generate
    ))
    return registry
