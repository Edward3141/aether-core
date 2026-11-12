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
- LiteLLM model adapter.
- SQLite audit, proposal and approval-record persistence.
- Local stdio MCP server with read-only diagnostic tools.
- Fixed diagnostics; AI-generated commands are never executed.
- GitHub Actions matrix for Linux, Windows and macOS.

## Safety limitations
This is an early development release, not an autonomous repair product. No repair executor or Docker sandbox is included. Approval records are audit evidence, not authorization to run arbitrary code. MCP tools are local and read-only. This project has not undergone an independent security audit.

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

Copy .env.example to .env and configure AETHER_MODEL, AETHER_API_BASE and AETHER_API_KEY. Never commit secrets. The default model is ollama/qwen2.5:7b; ensure it is available locally.

## Commands
```bash
aether-core doctor
aether-core ask "Explain this system diagnostic"
aether-core audit
aether-core-mcp
pytest
ruff check .
```

MCP tools: auditar_sistema and consultar_auditoria. Do not expose an unauthenticated MCP server to a network.

## Roadmap
Per-agent model settings, provider capability detection, expanded allow-listed diagnostics, reviewed Docker isolation, richer approval UX, rollback verification and integration tests. Roadmap items are not implemented features.

MIT License — see LICENSE.
