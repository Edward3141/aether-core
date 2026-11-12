from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
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
    proposal = RemediationProposal(title="Test", rationale="Test rationale",
                                   steps=["Review manually"])
    digest = db.save_proposal(proposal)
    record = ApprovalRecord(proposal_id=proposal.id, proposal_hash=digest,
        decision="approved", approved_by="human",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5))
    db.save_approval(record)
    bad = record.model_copy(update={"proposal_hash": "0" * 64})
    with pytest.raises(ValueError):
        db.save_approval(bad)

def test_expired_approval_is_rejected(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    proposal = RemediationProposal(title="Test", rationale="Test rationale",
                                   steps=["Review manually"])
    digest = db.save_proposal(proposal)
    now = datetime.now(timezone.utc)
    record = ApprovalRecord(proposal_id=proposal.id, proposal_hash=digest,
        decision="approved", approved_by="human", created_at=now,
        expires_at=now - timedelta(seconds=1))
    with pytest.raises(ValueError):
        db.save_approval(record)
