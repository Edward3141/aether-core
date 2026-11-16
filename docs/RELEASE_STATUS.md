# AETHER CORE — Release 0.1 scope and verification

## What this release is

AETHER CORE 0.1 is a cross-platform, evidence-based system-inspection framework with four intelligence agents and one narrowly scoped, human-supervised execution component. It is a complete release only within the explicit scope below. It is **not** a general-purpose autonomous repair tool, remote administration product, or production-certified security product.

## Included and implemented

- Five distinct components: SCOUT, ANALYST, FIXER, AUDITOR and 05 EXECUTOR.
- Fixed, read-only diagnostics and bounded host inspection using psutil.
- Native, application-owned probes for supported service, package, log and firewall metadata on Linux, macOS and Windows, with missing tools/permissions reported as unavailable.
- Evidence and proposal persistence, local knowledge ledger, agent-stage metrics, CLI reports and local stdio MCP workflow.
- Role-scoped capability catalog that reports implementation status; catalog references are never executed.
- Optional Docker sandbox for its single fixed, read-only Python version check.
- Two local filesystem actions on supported Linux/macOS systems only: create directories below an existing approved root, and create new empty files with mode 0600. Each action requires its own interactive human authorization, a digest-bound single-use expiring plan, and independent postcondition verification.
- No arbitrary shell, AI-generated script, privilege escalation, network-enabled execution, overwrite or destructive repair.

## Explicitly outside this release

- General-purpose Linux/Windows/macOS command execution.
- General service start/stop/restart, package install/remove/update, firewall changes or configuration editing.
- General backup/restore and rollback of existing user data.
- Windows filesystem mutation; it fails closed rather than using weaker path protections.
- A graphical approval interface, remote approval, authenticated network MCP service, alerts, plugin marketplace, PDF reporting, or third-party integrations.
- A claim that 200 advisory skill entries represent 200 independent operational capabilities.
- Independent penetration testing, formal security certification, or production-readiness assurance.

These are not silently implied by the catalog, roadmap, documentation examples, or AI-generated proposals. They require separate implementations, threat review and tests before being advertised as supported.

## Verification evidence for this candidate

Candidate commit: `39d36ad8b455e52165df7011f724993bd1495e40`

GitHub Actions results on that exact candidate:
- OS/Python matrix: 9/9 jobs passed (Ubuntu, Windows and macOS × Python 3.11, 3.12 and 3.13).
- Security workflow: passed, including 104 tests passed and 1 platform-conditional test skipped.
- Ruff: passed.
- pip-audit: no known vulnerabilities reported.
- Bandit: no issues identified at the configured severity/confidence threshold.
- CodeQL: passed.

The skipped test is not counted as an executed pass. CI results are evidence of automated checks, not proof that every operating-system configuration, third-party utility, filesystem race, model provider, or deployment environment is defect-free.

## Operational guidance

Use the CLI locally, keep the SQLite data directory protected by operating-system permissions, do not expose the stdio MCP server through an unauthenticated network bridge, and review every proposed action before typing its exact authorization phrase. Keep backups of important user data independently. Do not run on production systems on the assumption that AETHER CORE can repair arbitrary failures.

## Completion statement

The release scope above is implemented and tested by the cited CI candidate. The broader autonomous-repair vision is intentionally not declared complete. Future work must be introduced as new, separately reviewed releases without weakening the human-authorization boundary.
