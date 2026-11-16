# AETHER CORE
### Autonomous Multi-Agent System

**Intelligence working together. Humans stay in control.**

Open-source, cross-platform Python framework for system inspection, evidence-based analysis, and human-supervised remediation planning.

**Created by Edward Tejada** · MIT License

## Four integrated agents

- **SCOUT** — fixed, read-only system diagnostics plus an AI-generated summary explicitly labelled as advisory.
- **ANALYST** — evidence review, uncertainty and risk classification.
- **FIXER** — remediation proposals with backup and rollback guidance; never executes repairs.
- **AUDITOR** — AI-assisted proposal review, proposal hash checks and human oversight records. Its model can never grant execution permission.

## Integrated intelligence capabilities

The intelligence services are now connected to the normal application workflow, not merely standalone examples:

- **Evidence memory:** every SCOUT finding is recorded in a dedicated local SQLite knowledge ledger as unverified. Only an explicit evidence-backed verification can promote an entry; search defaults to verified entries.
- **Agent performance metrics:** the orchestrator records successful and failed agent stages during audits and planning.
- **System monitoring:** read-only system snapshots collect platform, CPU count, load average where available, Linux memory where available, and disk capacity.
- **Reports:** versioned JSON and Markdown reports combine system snapshots, process metrics and knowledge-ledger counts.
- **CLI integration:** `aether-core status` displays an intelligence report; `aether-core report --format json` or `--format markdown` exports it. Use `--output report.json` to write a file.
- **Built-in Skills:** an explicit registry provides `system.snapshot`, `knowledge.search`, `knowledge.stats`, and `report.generate`. Skills are deterministic local handlers, caller-restricted and schema-checked; evidence search exposes verified entries only. No dynamic code, shell, or model-generated scripts can be registered implicitly.
- No new third-party dependency is required. Existing agent contracts and original audit/proposal database schema remain unchanged. The new knowledge ledger is stored separately at `~/.aether-core/aether-core-knowledge.sqlite3` by default.

Metrics currently describe the current application process; they are not historical long-term agent benchmarks. System monitoring is read-only and does not claim temperature or service-health coverage.

## Current capabilities

- Python 3.11+ CLI and Pydantic data contracts.
- LiteLLM adapter with independent model, API base and API key settings per agent; shared settings are fallback values.
- SQLite audit, proposal and approval-record persistence, including proposal integrity checks.
- Local stdio MCP server with the complete four-agent workflow, read-only diagnostics, audit/proposal lookup and decision-history lookup.
- Fixed diagnostics; AI-generated commands are never executed.
- Optional Docker sandbox for one fixed, read-only Python version check: no network, no host mounts, read-only root filesystem, dropped capabilities, non-root UID, and resource limits.
- Explicit CLI confirmation before recording an approval or rejection. Decisions are records only and do not trigger repairs.
- GitHub Actions matrix for Linux, Windows and macOS (Python 3.11–3.13).

## Human-authorized repair execution

The target design is documented in [APPROVED_REPAIR_EXECUTION.md](docs/APPROVED_REPAIR_EXECUTION.md). AETHER CORE is intended to execute only registered, schema-validated repair actions after explicit approval of the exact proposal hash. Approval must be one-time, expire, and never authorize arbitrary model-generated shell commands. A first local action-registry foundation now exists: a strictly validated `ensure_directory` operation that accepts only a relative path under an explicitly supplied repair root. It has no shell execution path. The approval-consumption gate, execution journal, rollback/verification workflow, and trusted human authorization UI are still under development; therefore this is **not yet an enabled end-to-end repair feature**.

## Safety limitations

This is an early development release, not an autonomous repair product. No repair executor is included. The Docker sandbox currently runs only one fixed, read-only version check; it is not a general-purpose command runner. Approval records are audit evidence only; they do not authorize or trigger code execution. MCP tools are read-only. This project has not undergone an independent security audit.

## Install

Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Windows Command Prompt:
```cmd
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env`. Configure the shared `AETHER_MODEL`, `AETHER_API_BASE`, and `AETHER_API_KEY`, or use per-agent variables such as `AETHER_ANALYST_MODEL`, `AETHER_ANALYST_API_BASE`, and `AETHER_ANALYST_API_KEY`. The same pattern is supported for SCOUT, FIXER and AUDITOR. Never commit secrets.

The default model is `ollama/qwen2.5:7b`; ensure it is available locally if using the default configuration.

## Commands

```bash
aether-core doctor
aether-core sandbox-check
aether-core ask "Explain this system diagnostic"
aether-core audit
aether-core status
aether-core report --format markdown
aether-core report --format json --output aether-report.json
aether-core plan "Paste the analyst's evidence-based summary here"
aether-core --help
pytest
ruff check . --select E4,E7,E9,F
```

To record a human decision for a proposal, first obtain its exact ID and SHA-256 from the output of `aether-core plan`. Then run:

```bash
aether-core approve PROPOSAL_ID --hash SHA256 --by "Your name" --minutes 15
aether-core reject PROPOSAL_ID --hash SHA256 --by "Your name"
```

The CLI displays the proposal and requires typing the exact confirmation phrase. This records a time-limited decision only; it does not execute a repair. A decision is bound to the exact proposal hash.

## MCP

Run `aether-core-mcp` for a local stdio MCP server. Tools:

- `recopilar_diagnosticos`
- `ejecutar_flujo_completo` (SCOUT → ANALYST → FIXER → AUDITOR)
- `consultar_auditoria`
- `consultar_propuesta`
- `consultar_decisiones`

The MCP interface is read-only. Do not expose an unauthenticated MCP server to a network.

## Roadmap

One-time approval consumption, target binding, a fail-closed executor, more reversible OS-specific handlers, rollback verification, failure-injection tests and security review. Roadmap items are not implemented features.

## License

MIT License — see [LICENSE](LICENSE).
