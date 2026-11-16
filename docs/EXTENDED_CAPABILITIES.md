# AETHER CORE — Additive capabilities

This extension layer is separate from the original core modules. It adds reusable building blocks without changing existing agents, orchestrator, CLI, database, providers, MCP server, or repair registry.

## Included

- Evidence-aware memory: entries begin as unverified; only an explicit verification call with non-empty evidence can promote them. Search defaults to verified entries only. This is a knowledge ledger, not automatic model training.
- Agent scorecard: transparent success/failure counts and rates. It does not alter agent behavior, decide truth, or grant permissions.
- Read-only system snapshot: platform, CPU count, load average where available, Linux memory where available, and disk capacity. Unknown values remain null.
- Portable reports: versioned JSON and Markdown exports with an explicit safety notice.

## Example

    from aether_core.extended import KnowledgeStore, AgentScorecard, collect_snapshot
    from aether_core.extended.reports import build_report, report_json

    memory = KnowledgeStore("aether-memory.sqlite3")
    entry_id = memory.add("disk", "Disk usage warning", source="SCOUT")
    # After a human independently checks the evidence:
    memory.verify(entry_id, evidence={"reviewer": "operator", "result": "confirmed"})

    scorecard = AgentScorecard()
    scorecard.record("SCOUT", success=True)
    report = build_report(snapshot=collect_snapshot().to_dict(),
                          agent_metrics=[m.__dict__ for m in scorecard.snapshot()])
    print(report_json(report))

## Safety and limitations

- The extension is opt-in and is not wired into the existing workflow or CLI.
- No automatic training, self-modifying code, background daemon, network listener, or repair execution is added.
- Memory entries from models remain unverified until independently checked.
- Metrics are descriptive and are not a standalone measure of intelligence or correctness.
- Monitoring is read-only and intentionally does not claim temperature or service-health coverage.
- No new third-party dependency is required.
