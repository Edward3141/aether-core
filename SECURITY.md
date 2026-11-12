# Security Policy

Report vulnerabilities through a private GitHub Security Advisory.

Current boundaries:
- AI-generated commands are never executed.
- Diagnostics use fixed executable names and fixed argument lists.
- No shell interpolation or shell=True.
- This release does not execute repairs.
- MCP tools are local stdio and read-only.
- Approval records are hash-bound audit evidence, not execution authorization.

This early-stage project has not undergone an independent security audit.
Do not use it as a privileged unattended remediation system.
