# AETHER CORE Security Model

Created by Edward Tejada.

## Trust boundaries

- Operating-system diagnostics are fixed in source code and use argument arrays with `shell=False`.
- Model output, diagnostic strings, MCP inputs and stored JSON are untrusted data.
- Model-generated shell commands are not executed.
- FIXER creates proposals only. It has no execution interface.
- AUDITOR binds a human decision record to the SHA-256 hash of the exact proposal.
- The CLI requires an interactive confirmation phrase before writing a decision record.
- MCP tools are read-only and use local stdio transport.

## Approval record semantics

An approval record is not an execution token. It does not start a process, authorize a privileged action, or bypass operating-system controls. It records who made a decision, the exact proposal hash, and an expiry time. If a proposal changes, its hash changes and the old decision no longer matches it.

## Current limitations

- No Docker sandbox or repair executor is included.
- No privilege escalation is implemented.
- No network-facing MCP authentication layer is implemented; do not expose the stdio server through an unauthenticated bridge.
- No independent penetration test or security audit has been performed.
- Local SQLite data is only as protected as the user's filesystem permissions and device.

## Reporting

Please do not publish secrets, access tokens, private keys, or sensitive diagnostic data in public issues. Report suspected vulnerabilities privately to the repository maintainer.
