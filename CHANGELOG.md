# Changelog

## Unreleased
- Formalized the five-component architecture: four intelligence agents (SCOUT, ANALYST, FIXER, AUDITOR) plus the human-supervised 05 EXECUTOR.
- Added single-use, hash-bound human authorization for typed `ensure_directory` and `create_empty_file` repairs on supported POSIX systems, with independent postcondition checks and rollback limited to exact newly created objects when a later step fails.
- Added a role- and platform-scoped capability catalog; command references are metadata only and are never executed.
- Connected SCOUT, ANALYST, FIXER and AUDITOR into the CLI and MCP full workflow.
- Added model-assisted SCOUT summaries and AUDITOR proposal reviews with fail-safe advisory behavior.
- Added MCP tools for full workflow execution and human decision-history lookup.
- Added full four-agent orchestration integration tests.
- Added terminal-safe rendering for model-generated text.
- Documented agent roles, trust boundaries, model configuration and human approval semantics.
- Added an optional, fixed, read-only Docker diagnostic sandbox; it is separate from the narrowly scoped repair Executor and is not a general-purpose command runner.

## 0.1.0 — Initial public development baseline
- Four-agent architecture and conservative orchestration.
- Pydantic contracts and hash-bound approval records.
- Fixed read-only diagnostics; no arbitrary shell execution or repair execution.
- SQLite audit persistence.
- LiteLLM adapter, CLI, local stdio MCP tools.
- Starter tests and cross-platform GitHub Actions workflow.
