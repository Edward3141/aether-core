"""Portable report builders for extension data."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any

def build_report(*, snapshot: dict[str, Any] | None = None, agent_metrics: list[dict[str, Any]] | None = None,
                 findings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_snapshot": snapshot or {}, "agent_metrics": agent_metrics or [], "findings": findings or [],
        "safety_notice": "Metrics are descriptive; AI output is advisory; no repair is authorized by this report."}

def report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)

def report_markdown(report: dict[str, Any]) -> str:
    lines = ["# AETHER CORE report", "", f"Generated: {report.get('generated_at', 'unknown')}", "",
        "> AI output is advisory. This report does not authorize repairs.", "", "## Agent metrics", ""]
    metrics = report.get("agent_metrics", [])
    if not metrics: lines.append("No agent metrics recorded.")
    for item in metrics: lines.append(f"- **{item.get('agent', 'Unknown')}**: {item.get('successful', 0)}/{item.get('runs', 0)} successful runs")
    lines.extend(["", "## Findings", ""])
    findings = report.get("findings", [])
    if not findings: lines.append("No findings supplied.")
    for item in findings: lines.append(f"- {item.get('title', 'Finding')}: {item.get('description', 'No description')}")
    lines.extend(["", "## Safety", "", report.get("safety_notice", "")])
    return "\n".join(lines) + "\n"
