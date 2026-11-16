# Integrated intelligence layer

These capabilities are connected to the primary AETHER CORE orchestrator and CLI.

## Runtime flow

1. SCOUT collects fixed local diagnostics.
2. Each SCOUT finding is appended to the local knowledge ledger as **unverified**, with risk and evidence metadata. No model-generated observation is silently promoted to verified truth.
3. ANALYST reviews the audit report.
4. FIXER generates a structured remediation proposal.
5. AUDITOR reviews it as advisory only; it cannot authorize execution.
6. Agent stage outcomes are recorded in the scorecard for the current orchestrator process.

## User commands

- `aether-core status`: display the current read-only system snapshot, scorecard and knowledge-ledger counts.
- `aether-core report --format markdown`: print a Markdown report.
- `aether-core report --format json --output report.json`: write a JSON report.

## Data and compatibility

The original audit/proposal SQLite schema and agent Pydantic contracts are unchanged. Knowledge entries use a separate SQLite file beside the configured AETHER database. The scorecard is process-local and is not a durable historical benchmark. System snapshots do not change system state.

## Important limits

This integration improves context retention and observability; it does not train model weights or guarantee more accurate reasoning. Memory is evidence-labelled and unverified by default. Reports and metrics never authorize repairs. The repair executor and one-time approval consumption remain separate work and are not implied by these capabilities.
