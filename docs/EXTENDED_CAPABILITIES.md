# Integrated intelligence layer

These capabilities are connected to the primary AETHER CORE orchestrator and CLI.

## Five-component runtime flow

1. **01 — SCOUT** collects fixed local diagnostics.
2. Each SCOUT finding is appended to the local knowledge ledger as **unverified**, with risk and evidence metadata. No model-generated observation is silently promoted to verified truth.
3. **02 — ANALYST** reviews the audit report.
4. **03 — FIXER** generates a structured remediation proposal.
5. **04 — AUDITOR** reviews it as advisory only; it cannot authorize execution.
6. The **05 — EXECUTOR** receives a validated pending action plan only through the separate controlled execution path. It presents the exact operation and waits for individual human authorization before invoking the registered handler.
7. Agent stage outcomes are recorded in the scorecard for the current orchestrator process.

The four intelligence agents produce and review the proposal; the fifth component is the supervised execution engine. MCP and model output cannot authorize this final step.

## User commands

- `aether-core status`: display the current read-only system snapshot, scorecard and knowledge-ledger counts.
- `aether-core report --format markdown`: print a Markdown report.
- `aether-core report --format json --output report.json`: write a JSON report.

## Data and compatibility

The original audit/proposal SQLite schema and agent Pydantic contracts are unchanged. Knowledge entries use a separate SQLite file beside the configured AETHER database. The scorecard is process-local and is not a durable historical benchmark. System snapshots do not change system state. The CLI's fixed diagnostics now include psutil-backed process-count, memory, storage, network-interface and uptime measurements; these are read-only observations, not remediation handlers.

## Important limits

This integration improves context retention and observability; it does not train model weights or guarantee more accurate reasoning. Memory is evidence-labelled and unverified by default. Reports and metrics never authorize repairs. The repair Executor is a separate, deliberately narrow execution path: the current allow-list contains only `ensure_directory`, requires a live terminal confirmation for every action, consumes the exact plan once, and verifies the resulting directory through no-follow descriptors. If a multi-component creation fails, newly created empty directories are removed when their inode identity still matches. This does not provide general backup/restore or broad autonomous repair.
