# Universal Cross-Platform Command & Action Registry

AETHER CORE uses a shared, role-scoped capability catalog for Linux, macOS and Windows.
It describes diagnostic command equivalents and the responsibilities each agent may
perform. It is not a general-purpose shell and it does not execute command strings.

## Role boundaries

- **SCOUT:** read-only system, process, service, storage, memory, network, log,
  filesystem, package and security inspection.
- **ANALYST:** evidence correlation, classification, uncertainty and risk analysis.
- **FIXER:** structured repair proposals, configuration scope, backup and rollback plans.
  It cannot execute commands or make changes.
- **AUDITOR:** independent review of action scope, privileges, risks and approval binding.
  It cannot approve on behalf of the human.
- **EXECUTOR:** the only role with the repair-execution capability. It can execute only
  versioned typed handlers in the repair allow-list, after a separate human approval
  bound to the exact plan, parameters and target.

## Platform adapters

The registry maps capabilities to documented command references for Linux, macOS and
Windows. It detects the current platform and filters the catalog accordingly. It checks
whether referenced executables are present on PATH, but this is advisory and does not
run them. PowerShell cmdlets are listed as references and are not treated as executables.

## Security invariants

1. All catalog entries are metadata; `executable` is always false.
2. Model output, command strings, scripts and shell snippets are never passed to a shell.
3. Diagnostic collection continues to use fixed application-owned probes.
4. Repair execution remains separate in `repair_actions.py`, with typed parameters,
   an explicit allow-list and one human authorization per action.
5. Unknown roles, capabilities, platforms and action IDs fail closed.
6. Command references may differ by distribution, OS release, installed tools and policy.
   A future catalog update is expected; no honest project can promise every command
   that exists today or in the future.

## Current scope

This initial registry includes system identity, process, service, storage, memory,
network, logs, filesystem, package, security, configuration planning, backup planning
and typed repair execution capabilities. It is a capability inventory, not a claim that
all platform-specific diagnostics, backup handlers or repair handlers are implemented.
