# AETHER CORE — Four-Agent Workflow

Created by Edward Tejada.

## Sequence

1. **SCOUT** runs fixed local diagnostics using explicit executable paths, argument arrays, timeouts and no shell. It records raw findings. Its configured model may write a clearly labelled summary; if the model is unavailable, fixed diagnostics still complete.
2. **ANALYST** receives the structured audit report and produces an evidence-based assessment. It must distinguish facts from hypotheses and explain uncertainty.
3. **FIXER** receives the analysis and returns a validated Pydantic remediation proposal. Invalid JSON is rejected and replaced with a conservative manual-investigation proposal.
4. **AUDITOR** reviews the proposal for evidence gaps, privileges, scope, side effects and rollback. Its model output is advisory only. It cannot approve, authorize or execute anything.

## Human control

The workflow ends with a proposal, its SHA-256 digest and an advisory review. A person may record an approval or rejection using the CLI after reviewing the exact proposal and typing a confirmation phrase. Approval records expire and are bound to the proposal hash. Recording a decision does not run a repair.

## Failure behavior

- SCOUT preserves fixed diagnostic evidence if its optional summary model is unavailable.
- ANALYST and FIXER failures stop the AI workflow; the application must not invent a successful result.
- Invalid FIXER JSON produces a conservative manual-review proposal.
- AUDITOR model failure produces a manual-review advisory and never grants permission.
- No model-generated command is executed.

## Model configuration

Each agent can have its own model, API base and API key through AETHER_SCOUT_*, AETHER_ANALYST_*, AETHER_FIXER_* and AETHER_AUDITOR_*. Shared AETHER_MODEL, AETHER_API_BASE and AETHER_API_KEY values are fallbacks. Credentials must stay outside source control.
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

The core registry contains exactly 50 skills for each specialist (200 total), separate from the four shared core service skills. Each specialist can invoke only its own role-scoped skills (and a human operator can inspect/use them through authorized interfaces).

- **SCOUT (50):** host/platform inventory, OS/kernel, CPU/memory/disk, filesystems/mounts, network interfaces/routes/DNS, processes/services, package/runtime/container inventory, configuration/log discovery, hardware/resource snapshots, security-control metadata, event and evidence provenance, collection completeness and scope boundaries.
- **ANALYST (50):** evidence classification, provenance/confidence, hypotheses, root cause, temporal/cross-source correlation, anomalies/trends, performance/capacity, network/DNS/TLS, permissions/configuration/vulnerability/dependency risk, threat modeling, blast radius, incident severity/timeline, uncertainty, evidence gaps and recommendation ranking.
- **FIXER (50):** repair scope, pre/postconditions, allow-list matching, parameter schemas, path/symlink safety, least privilege, backup/rollback, idempotency, dry-run plans, configuration/package/service/disk/network/database/deployment plans, sandbox/resource/network constraints, testing, execution gates and manual fallback.
- **AUDITOR (50):** proposal and approval integrity, human consent, single-use/expiry binding, allow-list/schema/shell/code-injection checks, privilege/sandbox/network/filesystem/secret audits, backup/rollback, audit logs, provenance, confidence, false claims, test coverage, privacy/compliance, access control, MCP boundary, post-execution verification and release gate.

Role skills currently run as bounded structured-advisory handlers over explicitly supplied input. They do not pretend to perform external scans or mutate systems. The workflow invokes representative skills at each agent stage; the complete role catalogs are available through the registry. Any future skill that performs real observation or changes must have a concrete implementation, tests and its own permission boundary before being marked operational.
