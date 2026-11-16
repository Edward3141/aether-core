# Human-Authorized Repair Execution

## Implemented first execution slice

AETHER CORE supports two deliberately narrow, non-privileged operations:
`ensure_directory` creates directories below an existing, explicitly selected root;
`create_empty_file` creates a new empty file below that root with mode 0600 and
refuses to overwrite any existing path. Both fail closed on unsupported platforms.
Neither action executes shell commands, scripts, arbitrary model text, or programs.

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

Agent proposals may include typed action requests. The orchestrator validates each request against the local allow-list and creates a pending action plan rooted only in the application's data directory. The CLI and MCP workflow return these plans for review; neither an agent nor an MCP call can approve them.

## CLI example

```bash
aether-core action-plan ensure_directory --params '{"relative_path":"cache"}' --root "$HOME"
aether-core action-plan create_empty_file --params '{"relative_path":"cache/marker.txt"}' --root "$HOME"
aether-core execute-action PLAN_ID --hash SHA256_FROM_PLAN --by "your identity" --root "$HOME"
```

The second command requires interactive terminal confirmation. MCP tools and
model outputs cannot approve or execute actions. Every additional operation
must be implemented as a typed, versioned handler with bounded parameters,
preconditions, impact, timeout, verification and recovery tests before it is
added to the allow-list.

## Remaining work

This remains a narrow controlled execution capability, not general-purpose shell
access or completion of autonomous repair. More action handlers, verified backup/restore
and rollback for future state-changing operations, richer execution journaling, broader
per-platform failure-injection tests, and a trusted interactive approval UI remain
necessary. `ensure_directory` removes only newly created empty directories after a
later-step failure. `create_empty_file` removes only the exact newly created file if
its post-write checks fail. Neither action modifies existing user data or provides
general backup/restore. Privileged, destructive,
irreversible and network-enabled actions remain blocked.
