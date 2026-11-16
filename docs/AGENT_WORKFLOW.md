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