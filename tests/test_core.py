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
