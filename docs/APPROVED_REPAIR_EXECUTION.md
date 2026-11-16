# Human-Authorized Repair Execution

## Implemented first execution slice

AETHER CORE now supports one deliberately narrow, non-privileged operation:
`ensure_directory`. It can create a directory below an existing, explicitly
selected root. It cannot execute shell commands, scripts, arbitrary model text,
or caller-supplied programs.

## Human authorization lifecycle

1. The agent workflow may recommend an action, but cannot execute it.
2. A human creates/reviews a typed action plan with `action-plan`.
3. The plan binds the action ID, validated parameters, canonical target root,
   host identity and SHA-256 digest.
4. A human runs `execute-action`, reviews the complete plan and types the
   exact authorization phrase containing the plan ID and digest.
5. SQLite atomically consumes the pending plan before any filesystem side
   effect. A plan can be consumed only once.
6. The fixed local handler executes and records success/failure. A changed
   digest, wrong target, expired/consumed plan, unknown action or symlink
   traversal is rejected.

## CLI example

```bash
aether-core action-plan ensure_directory --params '{"relative_path":"cache"}' --root "$HOME"
aether-core execute-action PLAN_ID --hash SHA256_FROM_PLAN --by "your identity" --root "$HOME"
```

The second command requires interactive terminal confirmation. MCP tools and
model outputs cannot approve or execute actions. Every additional operation
must be implemented as a typed, versioned handler with bounded parameters,
preconditions, impact, timeout, verification and recovery tests before it is
added to the allow-list.

## Remaining work

This is the first controlled execution capability, not general-purpose shell
access and not completion of autonomous repair. More action handlers,
rollback support, richer execution journaling, per-platform tests, and a
trusted interactive approval UI remain necessary. Privileged, destructive,
irreversible and network-enabled actions remain blocked.
