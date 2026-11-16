# AETHER CORE
### Autonomous Multi-Agent System

**Intelligence working together. Humans stay in control.**

# 5-COMPONENT AUTONOMOUS ARCHITECTURE

**4 intelligence agents + 1 supervised execution engine.**

AETHER CORE is built around five cooperating components. The first four investigate, reason, propose and audit. The fifth — **05 EXECUTOR** — is the only component that can carry out an approved change, and it must obtain a separate, explicit human authorization for every action.

| Component | Responsibility |
|---|---|
| **01 — SCOUT** | Fixed, read-only system inspection and evidence collection. |
| **02 — ANALYST** | Evidence analysis, uncertainty, anomalies and risk classification. |
| **03 — FIXER** | Structured repair proposals; never executes changes. |
| **04 — AUDITOR** | Independent scope and safety review; never grants authorization. |
| **05 — EXECUTOR** | The final action component. Presents the exact operation and waits for the human's individual approval before executing. |

> **05 — EXECUTOR: the final step belongs to the human-supervised execution engine.**
>
> The Executor is the only component permitted to invoke a registered repair handler. No agent, model response, MCP request or audit recommendation can replace the human's explicit approval.

Created by Edward Tejada · MIT License

Open-source, cross-platform Python framework for system inspection, evidence-based analysis, and human-supervised remediation planning.

## Five-component workflow

SCOUT → ANALYST → FIXER → AUDITOR → **05 EXECUTOR**

The first four components prepare and review a proposed action. The fifth performs the final controlled step only after the human reviews and authorizes that exact action.

## Integrated intelligence capabilities

The intelligence services are now connected to the normal application workflow, not merely standalone examples:

- **Evidence memory:** every SCOUT finding is recorded in a dedicated local SQLite knowledge ledger as unverified. Only an explicit evidence-backed verification can promote an entry; search defaults to verified entries.
- **Agent performance metrics:** the orchestrator records successful and failed agent stages during audits and planning.
- **System monitoring:** read-only system snapshots collect platform, CPU count, load average where available, Linux memory where available, and disk capacity.
- **Reports:** versioned JSON and Markdown reports combine system snapshots, process metrics and knowledge-ledger counts.
- **CLI integration:** `aether-core status` displays an intelligence report; `aether-core report --format json` or `--format markdown` exports it. Use `--output report.json` to write a file.
- **Universal Cross-Platform Capability Registry:** a shared role-scoped catalog maps system, process, service, storage, memory, network, log, filesystem, package and security inspection references across Linux, macOS and Windows. It also describes proposal, audit, backup-planning and execution boundaries. The catalog is metadata only: it checks command availability but never executes command strings or model-generated scripts. Use `aether-core capabilities` or `aether-core capabilities --agent SCOUT` to inspect it.
- **Built-in Skills:** 50 role-scoped skills for each of the four intelligence agents (200 total), plus shared core services. SCOUT, ANALYST, FIXER and AUDITOR receive different capabilities in the primary workflow. Each skill validates bounded input and returns structured advisory output; the model cannot register code, execute shell commands, authorize changes or bypass human approval. Shared evidence search exposes verified entries only.
- No new third-party dependency is required. Existing agent contracts and original audit/proposal database schema remain unchanged. The new knowledge ledger is stored separately at `~/.aether-core/aether-core-knowledge.sqlite3` by default.

Metrics currently describe the current application process; they are not historical long-term agent benchmarks. System monitoring is read-only and does not claim temperature or service-health coverage.

## Current capabilities

- Python 3.11+ CLI and Pydantic data contracts.
- LiteLLM adapter with independent model, API base and API key settings per intelligence agent; shared settings are fallback values.
- SQLite audit, proposal and approval-record persistence, including proposal integrity checks.
- Local stdio MCP server exposing the four-agent intelligence workflow and pending action-plan output; MCP cannot authorize or execute repairs.
- Fixed diagnostics; AI-generated commands are never executed. The capability catalog is descriptive only and does not expand the repair allow-list.
- Optional Docker sandbox for one fixed, read-only Python version check: no network, no host mounts, read-only root filesystem, dropped capabilities, non-root UID, and resource limits.
- Explicit CLI confirmation before recording an approval or rejection. Decisions are records only and do not trigger repairs.
- GitHub Actions matrix for Linux, Windows and macOS (Python 3.11–3.13).

## Human-authorized repair execution

The target design is documented in [APPROVED_REPAIR_EXECUTION.md](docs/APPROVED_REPAIR_EXECUTION.md). The **05 EXECUTOR** component has a first end-to-end local execution path for one narrowly scoped action: `ensure_directory`, which creates a relative directory under an explicitly selected existing root. FIXER can request this typed action; the orchestrator validates it and creates a pending plan after AUDITOR review. EXECUTOR presents the exact action, parameters, target, expiry and digest, then asks the human to type the plan-specific authorization phrase. Rejection or cancellation causes no change. Approval is consumed atomically once, expires, is bound to the exact action parameters and target, and cannot be replayed. The handler never runs shell commands, scripts or arbitrary model text.

Example:

```bash
aether-core action-plan ensure_directory --params '{"relative_path":"cache"}' --root "$HOME"
aether-core execute-action PLAN_ID --hash SHA256 --by "Your identity" --root "$HOME"
```

The Executor displays the exact request and asks for the confirmation phrase. Every action is separately authorized.

This is a first narrow execution capability, not general-purpose command execution or complete autonomous repair. Only `ensure_directory` is currently in the allow-list. Additional typed handlers, full backup/rollback and postcondition verification, richer execution journaling, a trusted graphical approval UI, and independent security review remain pending.

## Safety limitations

This is an early development release, not a production-ready autonomous repair product. The Docker sandbox currently runs only one fixed, read-only version check; it is not a general-purpose command runner. Proposal-level approval records remain separate from execution authorization. MCP exposes plans but cannot approve or execute actions. This project has not undergone an independent security audit.

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
aether-core capabilities
aether-core capabilities --agent EXECUTOR
aether-core sandbox-check
aether-core ask "Explain this system diagnostic"
aether-core audit
aether-core status
aether-core report --format markdown
aether-core report --format json --output aether-report.json
aether-core skills
aether-core skill system.snapshot
aether-core skill knowledge.search --input '{"topic":"disk","limit":10}'
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
- `ejecutar_flujo_completo` (SCOUT → ANALYST → FIXER → AUDITOR; returns pending action plans only)
- `consultar_auditoria`
- `consultar_propuesta`
- `consultar_decisiones`
- `listar_habilidades`
- `ejecutar_habilidad` (only registered read-only skills)

The MCP interface is read-only. It does not perform the fifth component's human-authorized execution step. Do not expose an unauthenticated MCP server to a network.

## Roadmap

More allow-listed actions, full backup/rollback and postcondition verification, durable execution evidence, trusted graphical human approval, failure-injection coverage and independent security review. Roadmap items are not implemented features.

## License

MIT License — see [LICENSE](LICENSE).
