# AETHER CORE — Five-Component Verification and Release Gates

AETHER CORE consists of **four intelligence agents plus one supervised execution engine**:
01 SCOUT → 02 ANALYST → 03 FIXER → 04 AUDITOR → **05 EXECUTOR**.

This document defines the evidence required before a release may be described as complete.
A green CI run is necessary, but is never sufficient by itself.

## Non-negotiable safety invariants

- Components 01–04 (SCOUT, ANALYST, FIXER, AUDITOR) cannot perform system changes.
- Component 05 (EXECUTOR) is the only role allowed to invoke a registered repair handler.
- Every action has a separate human approval. Approval is bound to the exact action,
  validated parameters, target identity, target root, and content digest.
- Approval is single-use, expires, and is consumed atomically.
- Non-interactive execution, arbitrary shell/script execution, unknown action IDs,
  extra parameters, path traversal, and symlink escapes must fail closed.
- Model output, MCP tool calls, skill registration, and an AUDITOR recommendation
  are never human consent.
- A repair is not successful until independent postconditions have been checked.
- A failed or unverifiable repair is reported as failed/unknown, never as successful.

## Required release evidence

### 1. Agent workflow
- Integration tests prove the order SCOUT → ANALYST → FIXER → AUDITOR.
- Tests prove each agent's permissions and that none can call repair handlers.
- Evidence, hypotheses, uncertainty, and historical memory are kept distinct.
- Model-provider failure leaves safe diagnostics available and cannot authorize changes.

### 2. Human authorization and EXECUTOR
- Each proposed action is displayed separately with exact target, parameters,
  effects, risk, backup, rollback, digest, and expiry.
- Negative tests cover no approval, wrong text, wrong hash, changed parameters,
  changed target, expired plan, replay, concurrent approval, and non-interactive use.
- MCP and all public APIs cannot bypass the human approval gate.
- The audit record identifies the human attestation and exact action digest.

### 3. Repair safety and recovery
- Every action has a strict typed schema and a reviewed allow-list implementation.
- No AI-generated shell, source code, SQL, or script is executed.
- Path operations are protected against traversal, symlink/reparse-point attacks,
  and time-of-check/time-of-use races on every supported operating system.
- Backups are verified before destructive changes.
- Rollback is implemented and tested with injected failures, not merely described.
- Destructive and irreversible operations remain disabled unless separately designed
  and reviewed.

### 4. Post-repair verification
- A verifier independent from the repair handler checks the exact postconditions.
- SCOUT gathers fresh observations after the change; ANALYST compares them with
  the pre-change baseline; AUDITOR checks evidence and release criteria.
- Verification is repeated at defined intervals and includes relevant service,
  process, resource, dependency, and application health checks.
- Missing evidence, inconsistent results, or a failed check block success status.
- A failed verification triggers a safe stop and a tested rollback when available.

### 5. Skills
- Each advertised skill has a real implementation, a documented input/output contract,
  role/caller restrictions, functional tests, and negative tests.
- Contract-only or generic advisory handlers are labelled as such and are not counted
  as operational capabilities.
- The published inventory matches the implementations actually shipped.

### 6. Monitoring, interfaces, and integrations
- Monitoring reports only metrics that are actually collected and labels unavailable
  measurements as unavailable.
- CLI and MCP behavior is tested end-to-end; MCP cannot authorize or execute repairs.
- Any web UI, alerts, plugin, PDF, or external integration is described as complete
  only after implementation and integration tests exist.

### 7. Build, platform, and security
- Package installation and CLI startup are tested on supported Python versions.
- CI matrix covers Ubuntu, Windows, and macOS for Python 3.11, 3.12, and 3.13.
- Ruff, pytest, pip-audit, Bandit, and CodeQL complete successfully on the exact
  release commit.
- Security tests include adversarial inputs and concurrency/failure injection.
- Documentation, examples, release notes, and badges match the exact tested commit.

## Current verified baseline (2026-11-16)

The main branch commit `8d367786487ed3a66a0504a23e8268321694066c` had:
- 67 tests passing in the recorded CI security run;
- the nine-job OS/Python test matrix passing;
- Ruff passing;
- pip-audit reporting no known vulnerabilities;
- Bandit reporting no issues;
- CodeQL analysis completing successfully.

These results are a baseline, not proof of project completion.

The current repair allow-list contains only `ensure_directory`. The skill registry
contains registered entries whose generic advisory handlers are not equivalent to
independent operational implementations. The system snapshot is limited to basic
host/resource metadata. Full independent multi-agent post-repair verification,
general backup/rollback, Windows-safe filesystem mutation, and a complete trusted
human approval interface remain release blockers until implemented and tested.

## Release decision

A release may be marked complete only when every applicable gate above has
implementation evidence, automated test evidence, and a successful CI result tied
to the exact release commit. Any skipped, unavailable, mocked-only, or unverified
check must be disclosed and cannot be counted as a pass.
