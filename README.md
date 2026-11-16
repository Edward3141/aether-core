# AETHER CORE
### Autonomous Multi-Agent System

**Intelligence working together. Humans stay in control.**

Open-source, cross-platform Python framework for system inspection, evidence-based analysis, and human-supervised remediation planning.

**Created by Edward Tejada** · MIT License

## Four agents

- **SCOUT** — fixed, read-only system diagnostics.
- **ANALYST** — evidence review, uncertainty and risk classification.
- **FIXER** — remediation proposals with backup and rollback guidance; never executes repairs.
- **AUDITOR** — proposal hash review and human oversight records.

## Current capabilities

- Python 3.11+ CLI and Pydantic data contracts.
- LiteLLM adapter with independent model, API base and API key settings per agent; shared settings are fallback values.
- SQLite audit, proposal and approval-record persistence, including proposal integrity checks.
- Local stdio MCP server with read-only diagnostics, audit lookup and proposal lookup.
- Fixed diagnostics; AI-generated commands are never executed.\n- Optional Docker sandbox for one fixed, read-only Python version check: no network, no host mounts, read-only root filesystem, dropped capabilities, non-root UID, and resource limits.
- Explicit CLI confirmation before recording an approval or rejection.
- GitHub Actions matrix for Linux, Windows and macOS (Python 3.11–3.13).

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
aether-core ask "Explain this system diagnostic"
aether-core audit
aether-core --help
pytest
ruff check . --select E4,E7,E9,F
```

To record a human decision for a proposal, first obtain its exact ID and SHA-256 from the stored proposal. Then run:

```bash
aether-core approve PROPOSAL_ID --hash SHA256 --by "Your name" --minutes 15
aether-core reject PROPOSAL_ID --hash SHA256 --by "Your name"
```

The CLI displays the proposal and requires typing the exact confirmation phrase. This records a time-limited decision only; it does not execute a repair. A decision is bound to the exact proposal hash.

## MCP

Run `aether-core-mcp` for a local stdio MCP server. Tools:

- `auditar_sistema`
- `consultar_auditoria`
- `consultar_propuesta`

The MCP interface is read-only. Do not expose an unauthenticated MCP server to a network.

## Roadmap

Broader allow-listed diagnostics, provider capability detection, per-agent integration tests, richer approval UX, rollback verification and security review. Roadmap items are not implemented features.

## License

MIT License — see [LICENSE](LICENSE).
