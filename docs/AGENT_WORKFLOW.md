# AETHER CORE — Five Components: Four Intelligence Agents + Executor

Created by Edward Tejada.

## Five-component sequence

AETHER CORE has **five cooperating components**: four intelligence agents followed by one supervised execution engine. The fifth component is not counted as a fifth reasoning agent; it is the controlled final-action component.

1. **01 — SCOUT:** runs fixed local diagnostics using explicit executable paths, argument arrays, timeouts and no shell. It records raw findings. Its configured model may write a clearly labelled summary; if the model is unavailable, fixed diagnostics still complete.
2. **02 — ANALYST:** receives the structured audit report and produces an evidence-based assessment. It must distinguish facts from hypotheses and explain uncertainty.
3. **03 — FIXER:** receives the analysis and returns a validated Pydantic remediation proposal. Invalid JSON is rejected and replaced with a conservative manual-investigation proposal.
4. **04 — AUDITOR:** reviews the proposal and every typed action request for evidence gaps, privileges, scope, side effects and rollback. Its model output is advisory only. It cannot approve, authorize or execute anything.
5. **05 — EXECUTOR:** the final execution component. It receives only locally registered, schema-validated action plans produced after AUDITOR review. It displays the exact action, parameters, target, expiry and digest, then asks the human for a plan-specific confirmation. It executes only after the human types the exact authorization phrase. It cannot run model-generated shell commands or actions outside the local allow-list.

**The fifth component is the execution boundary:** the first four components prepare and review; EXECUTOR carries out only the exact action the human explicitly authorizes.

## Human control

The specialist workflow ends with a proposal, its SHA-256 digest, an advisory review and (when requested) pending action plans. The final EXECUTOR asks the human for approval separately for each exact action. The confirmation binds the action ID, validated parameters, canonical target and digest; it expires and can be consumed only once. Rejection/cancellation has no side effect. Proposal approval/rejection records remain a separate audit mechanism and do not run repairs.

## Failure behavior

- SCOUT preserves fixed diagnostic evidence if its optional summary model is unavailable.
- ANALYST and FIXER failures stop the AI workflow; the application must not invent a successful result.
- Invalid FIXER JSON produces a conservative manual-review proposal.
- AUDITOR model failure produces a manual-review advisory and never grants permission.
- No model-generated command is executed.

## Model configuration

Each intelligence agent can have its own model, API base and API key through AETHER_SCOUT_*, AETHER_ANALYST_*, AETHER_FIXER_* and AETHER_AUDITOR_*. Shared AETHER_MODEL, AETHER_API_BASE and AETHER_API_KEY values are fallbacks. Credentials must stay outside source control.

## Built-in Skills

Skills are reusable, deterministic capabilities separate from agent roles. The core registry includes:

- `system.snapshot` — read-only OS, CPU, memory and disk metadata.
- `knowledge.search` — evidence lookup restricted to verified entries and bounded results.
- `knowledge.stats` — counts for verified, unverified and rejected records.
- `report.generate` — combines system metadata, durable agent metrics and evidence counts.

Each skill declares permitted callers. Unknown names, unauthorized callers, extra arguments and invalid values are rejected. Registration is explicit in Python code; the model cannot add code or grant itself a skill.

CLI:

```bash
aether-core skills
aether-core skill system.snapshot
aether-core skill knowledge.search --input '{"topic":"disk","limit":10}'
aether-core skill report.generate
```

All current built-in skills are read-only. They do not execute commands or repairs.

## Role-specific Skill catalog

The core registry contains exactly 50 skills for each of the four intelligence agents (200 total), separate from the four shared core service skills. Each intelligence agent can invoke only its own role-scoped skills (and a human operator can inspect/use them through authorized interfaces).

- **SCOUT (50):** host/platform inventory, OS/kernel, CPU/memory/disk, filesystems/mounts, network interfaces/routes/DNS, processes/services, package/runtime/container inventory, configuration/log discovery, hardware/resource snapshots, security-control metadata, event and evidence provenance, collection completeness and scope boundaries.
- **ANALYST (50):** evidence classification, provenance/confidence, hypotheses, root cause, temporal/cross-source correlation, anomalies/trends, performance/capacity, network/DNS/TLS, permissions/configuration/vulnerability/dependency risk, threat modeling, blast radius, incident severity/timeline, uncertainty, evidence gaps and recommendation ranking.
- **FIXER (50):** repair scope, pre/postconditions, allow-list matching, parameter schemas, path/symlink safety, least privilege, backup/rollback, idempotency, dry-run plans, configuration/package/service/disk/network/database/deployment plans, sandbox/resource/network constraints, testing, execution gates and manual fallback.
- **AUDITOR (50):** proposal and approval integrity, human consent, single-use/expiry binding, allow-list/schema/shell/code-injection checks, privilege/sandbox/network/filesystem/secret audits, backup/rollback, audit logs, provenance, confidence, false claims, test coverage, privacy/compliance, access control, MCP boundary, post-execution verification and release gate.

Role skills currently run as bounded structured-advisory handlers over explicitly supplied input. They do not pretend to perform external scans or mutate systems. The workflow invokes representative skills at each agent stage; the complete role catalogs are available through the registry. Any future skill that performs real observation or changes must have a concrete implementation, tests and its own permission boundary before being marked operational.

## Executor scope and limitations

The first end-to-end Executor handler is `ensure_directory`, a bounded operation below an existing selected root. No general shell, script, package installation, service restart, network or privileged execution is enabled. Unsupported action IDs and parameters are rejected. A new handler must be typed, versioned, allow-listed and tested for path safety, preconditions, impact, rollback and verification before it can be executed.

The CLI command `execute-action` delegates to the **05 EXECUTOR** component, which presents the request and asks for the exact phrase `AUTHORIZE PLAN_ID SHA256`. The MCP server can create and return pending plans but cannot answer the human prompt or execute them.
