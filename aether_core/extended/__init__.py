"""Additive extensions; original core modules remain untouched."""
from .knowledge import KnowledgeStore
from .quality import AgentScorecard
from .monitor import SystemSnapshot, collect_snapshot
from .reports import build_report
__all__ = ["KnowledgeStore", "AgentScorecard", "SystemSnapshot", "collect_snapshot", "build_report"]
