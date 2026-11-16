# AETHER CORE Security Model

Created by Edward Tejada.

## Five-component trust boundaries

AETHER CORE has four intelligence agents and one supervised execution engine:

- **01 — SCOUT:** operating-system diagnostics are fixed in source code and use argument arrays with `shell=False`.
- **02 — ANALYST:** reasons over evidence; model output remains untrusted data.
- **03 — FIXER:** creates typed proposals only. It has no execution interface.
- **04 — AUDITOR:** reviews proposal scope and safety but cannot authorize a change.
- **05 — EXECUTOR:** the only component permitted to invoke a registered repair handler, and only after the human explicitly authorizes each exact action.

Model output, diagnostic strings, MCP inputs and stored JSON are untrusted data. Model-generated shell commands are never executed. An MCP call, skill invocation, proposal review or AUDITOR recommendation is not human consent.

## Approval record semantics

An approval record is not an execution token. It does not start a process, authorize a privileged action, or bypass operating-system controls. It records who made a decision, the exact proposal hash, and an expiry time. If a proposal changes, its hash changes and the old decision no longer matches it.

## Current limitations

- The Docker sandbox currently runs one fixed, read-only Python version check only; no repair executor or general-purpose command runner is included.
- No privilege escalation is implemented.
- No network-facing MCP authentication layer is implemented; do not expose the stdio server through an unauthenticated bridge.
- No independent penetration test or security audit has been performed.
- Local SQLite data is only as protected as the user's filesystem permissions and device.

## Reporting

Please do not publish secrets, access tokens, private keys, or sensitive diagnostic data in public issues. Report suspected vulnerabilities privately to the repository maintainer.
