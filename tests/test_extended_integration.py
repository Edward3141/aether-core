"""Integration tests for the intelligence services in the primary workflow."""
from aether_core.database import Database
from aether_core.models import AuditReport, Finding, RemediationProposal
from aether_core.orchestrator import Orchestrator


def test_orchestrator_integrates_memory_metrics_and_snapshot(tmp_path, monkeypatch):
    from aether_core import orchestrator

    report = AuditReport(platform="test", findings=[
        Finding(title="Disk observation", detail="Low free space", evidence=["fixed disk check"])
    ])
    proposal = RemediationProposal(title="Review disk", rationale="Check evidence", steps=["Review"])
    async def scout(self): return report
    async def analyst(self, value): return "analysis"
    async def fixer(self, value): return proposal
    async def auditor(self, value):
        return {"proposal_id": value.id, "sha256": value.content_hash(),
                "execution_allowed": False, "human_approval_required": True,
                "advisory": "Review", "message": "Human review required."}
    monkeypatch.setattr(orchestrator.Scout, "inspect", scout)
    monkeypatch.setattr(orchestrator.Analyst, "analyze", analyst)
    monkeypatch.setattr(orchestrator.Fixer, "propose", fixer)
    monkeypatch.setattr(orchestrator.Auditor, "review", auditor)

    workflow = Orchestrator(Database(tmp_path / "aether.db"))
    import asyncio
    asyncio.run(workflow.audit())
    asyncio.run(workflow.plan("analysis"))

    entries = workflow.knowledge.search("Disk observation", verified_only=False)
    assert len(entries) == 1
    assert entries[0]["status"] == "unverified"
    metrics = {item.agent: item for item in workflow.scorecard.snapshot()}
    assert set(metrics) == {"SCOUT", "ANALYST", "FIXER", "AUDITOR"}
    assert all(item.successful == 1 for item in metrics.values())
    payload = workflow.intelligence_report()
    assert payload["system_snapshot"]["cpu_count"] >= 1
