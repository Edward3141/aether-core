# Changelog

## Unreleased
- Connected SCOUT, ANALYST, FIXER and AUDITOR into the CLI and MCP full workflow.
- Added model-assisted SCOUT summaries and AUDITOR proposal reviews with fail-safe advisory behavior.
- Added MCP tools for full workflow execution and human decision-history lookup.
- Added full four-agent orchestration integration tests.
- Added terminal-safe rendering for model-generated text.
- Documented agent roles, trust boundaries, model configuration and human approval semantics.
- Added an optional, fixed, read-only Docker diagnostic sandbox; no general command runner or repair executor.

## 0.1.0 — Initial public development baseline
- Four-agent architecture and conservative orchestration.
- Pydantic contracts and hash-bound approval records.
- Fixed read-only diagnostics; no arbitrary shell execution or repair execution.
- SQLite audit persistence.
- LiteLLM adapter, CLI, local stdio MCP tools.
- Starter tests and cross-platform GitHub Actions workflow.
