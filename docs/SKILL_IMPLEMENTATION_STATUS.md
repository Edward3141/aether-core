# Skill implementation status

## Verified registry state

The registry contains exactly 50 named entries for each of SCOUT, ANALYST,
FIXER and AUDITOR (200 role-scoped entries), plus four shared service skills.

The role-scoped entries currently use a common bounded
`structured_advisory` handler. They validate the supplied subject, evidence
and context, preserve those inputs, identify the intended agent and skill, and
state their limitations. They do **not** independently inspect the host,
query external systems, perform domain-specific analysis, modify files, run
commands, approve proposals or execute repairs.

Therefore, registry count and contract tests must not be represented as 200
completed operational capabilities.

## Shared services with concrete implementations

- `system.snapshot`: read-only platform, CPU, memory and disk snapshot using
  the implemented monitor.
- `knowledge.search`: verified-only SQLite evidence search.
- `knowledge.stats`: SQLite evidence status counts.
- `report.generate`: structured report assembled from the snapshot,
  scorecard and evidence ledger.

## Exhaustive role-skill contract tests

`tests/test_all_skill_contracts.py` exercises all 200 registered entries,
including exact counts, role ownership, cross-agent denial, bounded input
validation and structured advisory output. These are dispatcher and safety
contract tests, not proof of domain-specific operational behavior.

## Work required before claiming all 200 are operational

Implement and test each capability against a documented input/output schema
and an explicitly permitted data source or deterministic algorithm. Host
inspection must remain read-only and scoped. Analysis must preserve provenance
and uncertainty. FIXER must only produce allow-listed plans. AUDITOR must
remain advisory and never authorize execution. A capability without its
required source, permission, and behavioral tests must report unavailable
rather than fabricate a result.
