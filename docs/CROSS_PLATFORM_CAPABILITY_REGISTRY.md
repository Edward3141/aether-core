# AETHER CORE — Five-Component Cross-Platform Capability Registry

AETHER CORE is organized as **four intelligence agents plus one supervised execution engine**. This registry describes the role boundaries and platform-specific capability references for all five components across Linux, macOS and Windows. It is not a general-purpose shell and it does not execute command strings.

## Five component roles

- **01 — SCOUT:** read-only system, process, service, storage, memory, network, log, filesystem, package and security inspection.
- **02 — ANALYST:** evidence correlation, classification, uncertainty and risk analysis.
- **03 — FIXER:** structured repair proposals, configuration scope, backup and rollback plans. It cannot execute commands or make changes.
- **04 — AUDITOR:** independent review of action scope, privileges, risks and approval binding. It cannot approve on behalf of the human.
- **05 — EXECUTOR:** the only role with the repair-execution capability. It can execute only versioned typed handlers in the repair allow-list, after a separate human approval bound to the exact plan, parameters and target.

**Component 05 is the controlled final step:** the other four components prepare and review; only EXECUTOR can perform an allow-listed change after the human explicitly authorizes that exact action.

## Platform adapters

The registry maps capabilities to documented command references for Linux, macOS and
Windows. It detects the current platform and filters the catalog accordingly. It reports `available_command_binaries` by checking whether referenced executable binaries are present on PATH; this is advisory and does not run them. Native PowerShell cmdlets are listed as references but are not PATH binaries, so they are not reported as available by that lookup.

## Security invariants

1. All catalog entries are metadata; `executable` is always false.
2. Model output, command strings, scripts and shell snippets are never passed to a shell.
3. Diagnostic collection continues to use fixed application-owned probes.
4. Repair execution remains separate in `repair_actions.py`, with typed parameters,
   an explicit allow-list and one human authorization per action. The current
   `ensure_directory` handler uses descriptor-relative no-follow APIs and is enabled
   only on supported POSIX systems; unsupported platforms fail closed.
5. Unknown roles, capabilities, platforms and action IDs fail closed.
6. Command references may differ by distribution, OS release, installed tools and policy.
   A future catalog update is expected; no honest project can promise every command
   that exists today or in the future.

## Current scope

This initial registry includes system identity, process, service, storage, memory,
network, logs, filesystem, package, security, configuration planning, backup planning
and typed repair execution capabilities. It is a capability inventory, not a claim that
all platform-specific diagnostics, backup handlers or repair handlers are implemented.
