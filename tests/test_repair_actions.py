"""Tests for allow-listed human-authorized repair execution."""
import pytest
from pydantic import ValidationError

from aether_core.database import Database
from aether_core.repair_actions import (
    EnsureDirectoryParams, approve_and_execute, create_action_plan,
)


@pytest.mark.parametrize("path", ["../outside", "/tmp/outside", "C:/Windows/System32", "a/../../outside", ""])
def test_action_contract_rejects_unsafe_paths(path):
    with pytest.raises(ValidationError):
        EnsureDirectoryParams(relative_path=path)


def test_action_contract_rejects_extra_parameters():
    with pytest.raises(ValidationError):
        EnsureDirectoryParams.model_validate({"relative_path": "cache", "command": "rm -rf /"})


def test_unknown_action_is_rejected(tmp_path):
    db = Database(tmp_path / "test.db")
    with pytest.raises(ValueError, match="not registered"):
        create_action_plan(db, "run_shell", {"command": "whoami"}, tmp_path)


def test_human_approval_executes_exact_allowlisted_action_once(tmp_path):
    db = Database(tmp_path / "test.db")
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "cache"}, tmp_path)
    assert not (tmp_path / "cache").exists()
    result = approve_and_execute(db, plan["id"], plan["sha256"], "human", tmp_path)
    assert result.status == "succeeded"
    assert (tmp_path / "cache").is_dir()
    with pytest.raises(PermissionError, match="cannot be replayed"):
        approve_and_execute(db, plan["id"], plan["sha256"], "human", tmp_path)


def test_wrong_hash_and_wrong_target_do_not_execute(tmp_path):
    db = Database(tmp_path / "test.db")
    root = tmp_path / "root"
    other = tmp_path / "other"
    root.mkdir()
    other.mkdir()
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "cache"}, root)
    with pytest.raises(ValueError, match="digest mismatch"):
        approve_and_execute(db, plan["id"], "0" * 64, "human", root)
    with pytest.raises(PermissionError, match="target"):
        approve_and_execute(db, plan["id"], plan["sha256"], "human", other)
    assert not (root / "cache").exists()
    assert not (other / "cache").exists()


def test_symlink_escape_is_rejected(tmp_path):
    db = Database(tmp_path / "test.db")
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is unavailable on this runner.")
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "link/escape"}, root)
    with pytest.raises(PermissionError, match="Symlink"):
        approve_and_execute(db, plan["id"], plan["sha256"], "human", root)
    assert not (outside / "escape").exists()



def test_expired_plan_is_rejected_without_side_effect(tmp_path):
    db = Database(tmp_path / "test.db")
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "expired"}, tmp_path, 1)
    with db.connect() as connection:
        connection.execute(
            "UPDATE action_plans SET expires_at=? WHERE id=?",
            ("2000-01-01T00:00:00+00:00", plan["id"]),
        )
    with pytest.raises(PermissionError, match="expired"):
        approve_and_execute(db, plan["id"], plan["sha256"], "human", tmp_path)
    assert not (tmp_path / "expired").exists()


def test_plan_is_bound_to_original_parameters(tmp_path):
    db = Database(tmp_path / "test.db")
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "safe"}, tmp_path)
    with db.connect() as connection:
        connection.execute(
            "UPDATE action_plans SET params_json=? WHERE id=?",
            ('{"relative_path":"tampered"}', plan["id"]),
        )
    with pytest.raises(ValueError, match="integrity check"):
        approve_and_execute(db, plan["id"], plan["sha256"], "human", tmp_path)
    assert not (tmp_path / "tampered").exists()
    assert not (tmp_path / "safe").exists()



@pytest.mark.asyncio
async def test_agent_workflow_turns_fixer_action_into_unapproved_plan(tmp_path, monkeypatch):
    from aether_core import orchestrator
    from aether_core.models import RemediationProposal, RepairActionRequest

    proposal = RemediationProposal(
        title="Prepare cache directory",
        rationale="The application cache directory is missing.",
        steps=["Create the application cache directory."],
        actions=[RepairActionRequest(
            action_id="ensure_directory",
            parameters={"relative_path": "cache"},
        )],
    )

    async def fake_propose(self, analysis):
        return proposal

    async def fake_review(self, value):
        return {
            "proposal_id": value.id,
            "sha256": value.content_hash(),
            "execution_allowed": False,
            "human_approval_required": True,
            "advisory": "Reviewed; human authorization still required.",
            "message": "Human review required.",
        }

    monkeypatch.setattr(orchestrator.Fixer, "propose", fake_propose)
    monkeypatch.setattr(orchestrator.Auditor, "review", fake_review)
    db = Database(tmp_path / "state" / "aether.sqlite3")
    workflow = orchestrator.Orchestrator(db)
    saved, review = await workflow.plan("missing cache")
    assert saved.id == proposal.id
    assert len(review["action_plans"]) == 1
    action_plan = review["action_plans"][0]
    assert action_plan["action_id"] == "ensure_directory"
    assert action_plan["target_root"] == str(db.path.parent.resolve())
    assert db.get_action_plan(action_plan["id"])["status"] == "pending"
    assert not (db.path.parent / "cache").exists()
