# Human-Authorized Repair Execution

Created by Edward Tejada.

## Product requirement

AETHER CORE must be able to perform selected repairs after explicit human authorization. Approval is not a general permission to run arbitrary model-generated commands.

## Required lifecycle

1. SCOUT captures the relevant system facts and evidence.
2. ANALYST identifies likely causes, uncertainty and risk.
3. FIXER creates a structured repair plan. Every executable operation must use a registered action identifier and schema-validated parameters. Free-form shell commands are explanatory text only and are never executable.
4. AUDITOR checks the exact plan, action identifiers, parameter values, privileges, affected resources, backup, rollback and risk.
5. The user sees the complete immutable plan, its SHA-256 digest, target machine, expected effects and expiry. The user must explicitly approve that exact digest in an interactive trusted interface.
6. The executor re-loads the plan, verifies the digest, verifies the approval is approved and unexpired, atomically consumes the approval, and checks each action against the local allow-list.
7. Actions run sequentially with bounded timeouts and least privilege. The executor records start, output summary, exit status and verification results. Secrets are redacted.
8. On failure, execution stops. A rollback may run only if it was included in the approved plan and is itself registered, validated and safe to run. Otherwise the system reports the failure and recovery instructions.

## Non-negotiable controls

- One approval is bound to one proposal digest and one target machine.
- Editing the proposal, parameters, action order, target or rollback plan invalidates approval.
- Approvals are short-lived, one-time and atomically consumed to prevent replay.
- No wildcard approval, blanket consent, unattended approval, or approval inferred from an MCP request.
- MCP clients may request a plan and inspect its details. Execution requires a separate trusted human approval channel; a tool call alone is not consent.
- No arbitrary shell, Python, PowerShell, SQL, or script text from an LLM is executed.
- Every operation is a versioned, locally registered action with a strict parameter schema and per-platform implementation.
- Privileged operations require a separate operating-system authorization step. AETHER CORE must never collect or store the user's administrator password.
- Network access is disabled for repair execution by default. No Docker socket or unrestricted host mounts are exposed to a model.
- If Docker or another required isolation boundary is unavailable, the system must refuse actions that require it rather than silently running them on the host.
- Every action must have a defined precondition, impact description, timeout, verification method and recovery strategy.
- Destructive, irreversible, credential-changing, security-disabling, firmware, partitioning, and data-wiping actions remain blocked unless a separately reviewed policy explicitly supports them.

## Implementation status

This document defines the target behavior. The current public release does not execute repairs: its approval records are audit records only, and the Docker sandbox is a fixed read-only diagnostic. Do not describe this feature as implemented until the action registry, one-time approval consumption, executor, rollback/verification, tests and platform-specific handlers are present and passing.

## Delivery order

1. Add structured action contracts and a versioned allow-list.
2. Add immutable proposal digest binding, target binding, approval expiry and one-time atomic consumption.
3. Add an execution journal and a fail-closed executor that only dispatches registered handlers.
4. Add non-destructive, reversible repair handlers for each supported OS, with backups and verification.
5. Add failure-injection, replay, tampering, privilege, rollback and cross-platform tests.
6. Only after those checks, enable explicitly authorized repair execution in the CLI and a separately authenticated MCP approval flow.