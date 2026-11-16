"""Core persistence and safety tests. Created by Edward Tejada."""
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aether_core.config import model_settings
from aether_core.database import Database
from aether_core.diagnostics import collect_diagnostics
from aether_core.models import ApprovalRecord, RemediationProposal


def test_diagnostics_are_report():
    report = collect_diagnostics()
    assert report.platform
    assert report.findings


def test_audit_roundtrip(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    report = collect_diagnostics()
    db.save_audit(report)
    loaded = db.get_audit(report.id)
    assert loaded is not None and loaded.id == report.id


def test_proposal_hash_bound_approval(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    proposal = RemediationProposal(
        title="Test", rationale="Test rationale", steps=["Review manually"]
    )
    digest = db.save_proposal(proposal)
    record = ApprovalRecord(
        proposal_id=proposal.id,
        proposal_hash=digest,
        decision="approved",
        approved_by="human",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    db.save_approval(record)
    assert db.list_approvals(proposal.id) == [record]
    bad = record.model_copy(update={"proposal_hash": "0" * 64})
    with pytest.raises(ValueError, match="hash mismatch"):
        db.save_approval(bad)


def test_expired_approval_is_rejected(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    proposal = RemediationProposal(
        title="Test", rationale="Test rationale", steps=["Review manually"]
    )
    digest = db.save_proposal(proposal)
    now = datetime.now(UTC)
    record = ApprovalRecord(
        proposal_id=proposal.id,
        proposal_hash=digest,
        decision="approved",
        approved_by="human",
        created_at=now - timedelta(minutes=10),
        expires_at=now - timedelta(seconds=1),
    )
    with pytest.raises(ValueError, match="expired"):
        db.save_approval(record)


def test_proposal_integrity_is_checked_on_read(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    proposal = RemediationProposal(
        title="Test", rationale="Test rationale", steps=["Review manually"]
    )
    db.save_proposal(proposal)
    with db.connect() as connection:
        connection.execute(
            "UPDATE proposals SET content_hash=? WHERE id=?",
            ("0" * 64, proposal.id),
        )
    with pytest.raises(ValueError, match="integrity"):
        db.get_proposal(proposal.id)


def test_agent_model_configuration_falls_back(monkeypatch):
    monkeypatch.setenv("AETHER_MODEL", "ollama/shared")
    monkeypatch.setenv("AETHER_ANALYST_MODEL", "openai/custom")
    monkeypatch.setenv("AETHER_API_BASE", "http://localhost:11434")
    settings = model_settings("analyst")
    assert settings.model == "openai/custom"
    assert settings.api_base == "http://localhost:11434"


def test_agent_model_configuration_can_override_provider(monkeypatch):
    monkeypatch.setenv("AETHER_MODEL", "ollama/shared")
    monkeypatch.setenv("AETHER_ANALYST_MODEL", "openai/custom")
    monkeypatch.setenv("AETHER_ANALYST_API_BASE", "https://api.example.test")
    monkeypatch.setenv("AETHER_ANALYST_API_KEY", "test-only-secret")
    settings = model_settings("analyst")
    assert settings.model == "openai/custom"
    assert settings.api_base == "https://api.example.test"
    assert settings.api_key == "test-only-secret"


def test_cli_approval_requires_hash_and_actor():
    from aether_core.cli import build_parser

    args = build_parser().parse_args([
        "approve", "proposal-123", "--hash", "a" * 64, "--by", "human"
    ])
    assert args.command == "approve"
    assert args.proposal_id == "proposal-123"
    assert args.proposal_hash == "a" * 64
    assert args.approved_by == "human"
    assert args.minutes == 15



def test_sandbox_rejects_unknown_checks():
    from aether_core.sandbox.docker_runner import run_check

    with pytest.raises(ValueError, match="not allow-listed"):
        run_check("arbitrary-shell-command")


def test_sandbox_requires_docker(monkeypatch):
    from aether_core.sandbox import docker_runner

    monkeypatch.setattr(docker_runner.shutil, "which", lambda _: None)
    with pytest.raises(docker_runner.SandboxUnavailable, match="Docker CLI"):
        docker_runner.run_check("python-version")


def test_sandbox_uses_isolated_fixed_command(monkeypatch):
    from types import SimpleNamespace

    from aether_core.sandbox import docker_runner

    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="Python 3.12", stderr="")

    monkeypatch.setattr(docker_runner.shutil, "which", lambda _: "/usr/bin/docker")
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)
    result = docker_runner.run_check("python-version")

    assert result.exit_code == 0
    assert "--network=none" in captured["command"]
    assert "--read-only" in captured["command"]
    assert "--cap-drop=ALL" in captured["command"]
    assert "--security-opt=no-new-privileges:true" in captured["command"]
    assert "--pull=never" in captured["command"]
    assert "--privileged" not in captured["command"]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["timeout"] == 15



@pytest.mark.asyncio
async def test_scout_uses_model_only_for_labelled_summary(monkeypatch):
    from aether_core import agents

    async def fake_model(system_prompt, user_prompt, agent=None):
        assert agent == "SCOUT"
        assert "diagnostic" in user_prompt.lower()
        return "Two fixed checks completed."

    monkeypatch.setattr(agents, "ask_model", fake_model)
    report = await agents.Scout().inspect()
    assert report.findings
    assert report.summary.startswith("AI-generated summary")


@pytest.mark.asyncio
async def test_scout_falls_back_when_model_unavailable(monkeypatch):
    from aether_core import agents

    async def unavailable(*args, **kwargs):
        raise RuntimeError("provider offline")

    monkeypatch.setattr(agents, "ask_model", unavailable)
    report = await agents.Scout().inspect()
    assert report.findings
    assert "AI summary unavailable" in report.summary
    assert "provider offline" not in report.summary


@pytest.mark.asyncio
async def test_auditor_model_review_never_grants_execution(monkeypatch):
    from aether_core import agents

    async def fake_model(system_prompt, user_prompt, agent=None):
        assert agent == "AUDITOR"
        return "Consider adding stronger rollback verification."

    monkeypatch.setattr(agents, "ask_model", fake_model)
    proposal = RemediationProposal(
        title="Review", rationale="Evidence review", steps=["Inspect logs"]
    )
    review = await agents.Auditor().review(proposal)
    assert review["advisory"].startswith("Consider adding")
    assert review["execution_allowed"] is False
    assert review["human_approval_required"] is True


@pytest.mark.asyncio
async def test_auditor_fails_closed_when_model_unavailable(monkeypatch):
    from aether_core import agents

    async def unavailable(*args, **kwargs):
        raise RuntimeError("provider offline")

    monkeypatch.setattr(agents, "ask_model", unavailable)
    proposal = RemediationProposal(
        title="Review", rationale="Evidence review", steps=["Inspect logs"]
    )
    review = await agents.Auditor().review(proposal)
    assert review["execution_allowed"] is False
    assert "manual review is required" in review["advisory"]



@pytest.mark.asyncio
async def test_orchestrator_runs_four_agents_and_persists_results(tmp_path, monkeypatch):
    from aether_core import orchestrator
    from aether_core.models import AuditReport, Finding, Risk

    events = []
    report = AuditReport(
        platform="test-platform",
        findings=[Finding(title="Test fact", detail="Observed", risk=Risk.INFO)],
    )
    proposal = RemediationProposal(
        title="Safe review", rationale="Evidence reviewed", steps=["Review manually"]
    )

    async def scout_inspect(self):
        events.append("SCOUT")
        return report

    async def analyst_analyze(self, value):
        events.append("ANALYST")
        assert value.id == report.id
        return "Evidence-based analysis"

    async def fixer_propose(self, analysis):
        events.append("FIXER")
        assert analysis == "Evidence-based analysis"
        return proposal

    async def auditor_review(self, value):
        events.append("AUDITOR")
        assert value.id == proposal.id
        return {
            "proposal_id": value.id,
            "sha256": value.content_hash(),
            "execution_allowed": False,
            "human_approval_required": True,
            "advisory": "Manual review",
            "message": "Human review required.",
        }

    monkeypatch.setattr(orchestrator.Scout, "inspect", scout_inspect)
    monkeypatch.setattr(orchestrator.Analyst, "analyze", analyst_analyze)
    monkeypatch.setattr(orchestrator.Fixer, "propose", fixer_propose)
    monkeypatch.setattr(orchestrator.Auditor, "review", auditor_review)

    db = Database(tmp_path / "workflow.db")
    workflow = orchestrator.Orchestrator(db)
    saved_report, analysis = await workflow.audit()
    saved_proposal, review = await workflow.plan(analysis)

    assert events == ["SCOUT", "ANALYST", "FIXER", "AUDITOR"]
    assert db.get_audit(saved_report.id) is not None
    assert db.get_proposal(saved_proposal.id) is not None
    assert review["execution_allowed"] is False
