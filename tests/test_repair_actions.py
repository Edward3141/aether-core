"""Tests for allow-listed human-authorized repair execution."""
import pytest
from pydantic import ValidationError

from aether_core.database import Database
from aether_core.repair_actions import (
    EnsureDirectoryParams, Executor, approve_and_execute, create_action_plan,
    _supports_race_safe_directory_creation, _execute_approved_plan,
)


def _execute_as_human(db, plan, root, monkeypatch, response=None):
    from types import SimpleNamespace
    monkeypatch.setattr("aether_core.repair_actions.sys.stdin", SimpleNamespace(isatty=lambda: True))
    expected = f"AUTHORIZE {plan['id']} {plan['sha256']}"
    monkeypatch.setattr("builtins.input", lambda _prompt: expected if response is None else response)
    return Executor(db).execute_after_human_prompt(
        plan["id"], plan["sha256"], "test-human", root
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


def test_human_approval_executes_exact_allowlisted_action_once(tmp_path, monkeypatch):
    db = Database(tmp_path / "test.db")
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "cache"}, tmp_path)
    assert not (tmp_path / "cache").exists()
    if not _supports_race_safe_directory_creation():
        with pytest.raises(PermissionError, match="race-safe directory APIs"):
            _execute_as_human(db, plan, tmp_path, monkeypatch)
        assert not (tmp_path / "cache").exists()
        assert db.get_action_plan(plan["id"])["status"] == "failed"
        return

    result = _execute_as_human(db, plan, tmp_path, monkeypatch)
    assert result.status == "succeeded"
    assert (tmp_path / "cache").is_dir()
    assert len(result.verification) == 3
    with pytest.raises(PermissionError, match="not awaiting authorization"):
        _execute_as_human(db, plan, tmp_path, monkeypatch)


def test_wrong_hash_and_wrong_target_do_not_execute(tmp_path, monkeypatch):
    db = Database(tmp_path / "test.db")
    root = tmp_path / "root"
    other = tmp_path / "other"
    root.mkdir()
    other.mkdir()
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "cache"}, root)
    from types import SimpleNamespace
    monkeypatch.setattr("aether_core.repair_actions.sys.stdin", SimpleNamespace(isatty=lambda: True))
    with pytest.raises(ValueError, match="hash mismatch"):
        Executor(db).execute_after_human_prompt(plan["id"], "0" * 64, "human", root)
    with pytest.raises(PermissionError, match="target"):
        _execute_as_human(db, plan, other, monkeypatch)
    assert not (root / "cache").exists()
    assert not (other / "cache").exists()


def test_symlink_escape_is_rejected(tmp_path, monkeypatch):
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
    if not _supports_race_safe_directory_creation():
        with pytest.raises(PermissionError, match="race-safe directory APIs"):
            _execute_as_human(db, plan, root, monkeypatch)
    else:
        with pytest.raises(PermissionError, match="Symlink"):
            _execute_as_human(db, plan, root, monkeypatch)
    assert not (outside / "escape").exists()



def test_expired_plan_is_rejected_without_side_effect(tmp_path, monkeypatch):
    db = Database(tmp_path / "test.db")
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "expired"}, tmp_path, 1)
    with db.connect() as connection:
        connection.execute(
            "UPDATE action_plans SET expires_at=? WHERE id=?",
            ("2000-01-01T00:00:00+00:00", plan["id"]),
        )
    with pytest.raises(PermissionError, match="expired"):
        _execute_as_human(db, plan, tmp_path, monkeypatch)
    assert not (tmp_path / "expired").exists()


def test_plan_is_bound_to_original_parameters(tmp_path, monkeypatch):
    db = Database(tmp_path / "test.db")
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "safe"}, tmp_path)
    with db.connect() as connection:
        connection.execute(
            "UPDATE action_plans SET params_json=? WHERE id=?",
            ('{"relative_path":"tampered"}', plan["id"]),
        )
    with pytest.raises(ValueError, match="integrity check"):
        _execute_as_human(db, plan, tmp_path, monkeypatch)
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



def test_executor_requests_exact_human_authorization_before_execution(tmp_path, monkeypatch):
    from aether_core.repair_actions import Executor

    db = Database(tmp_path / "test.db")
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "approved"}, tmp_path)
    from types import SimpleNamespace
    monkeypatch.setattr("aether_core.repair_actions.sys.stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt: f"AUTHORIZE {plan['id']} {plan['sha256']}",
    )
    seen = []
    if not _supports_race_safe_directory_creation():
        with pytest.raises(PermissionError, match="race-safe directory APIs"):
            Executor(db).execute_after_human_prompt(
                plan["id"], plan["sha256"], "human", tmp_path, seen.append
            )
        assert seen[0]["action"] == "ensure_directory"
        assert not (tmp_path / "approved").exists()
        return

    result = Executor(db).execute_after_human_prompt(
        plan["id"], plan["sha256"], "human", tmp_path, seen.append
    )
    assert seen[0]["action"] == "ensure_directory"
    assert seen[0]["parameters"] == {"relative_path": "approved"}
    assert result is not None and result.status == "succeeded"
    assert (tmp_path / "approved").is_dir()


def test_executor_rejection_never_changes_files(tmp_path, monkeypatch):
    from aether_core.repair_actions import Executor

    db = Database(tmp_path / "test.db")
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "denied"}, tmp_path)
    from types import SimpleNamespace
    monkeypatch.setattr("aether_core.repair_actions.sys.stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr("builtins.input", lambda _prompt: "NO")
    result = Executor(db).execute_after_human_prompt(
        plan["id"], plan["sha256"], "human", tmp_path,
    )
    assert result is None
    assert db.get_action_plan(plan["id"])["status"] == "pending"
    assert not (tmp_path / "denied").exists()


def test_direct_execution_api_is_disabled(tmp_path):
    db = Database(tmp_path / "test.db")
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "blocked"}, tmp_path)
    with pytest.raises(PermissionError, match="interactive human confirmation"):
        approve_and_execute(db, plan["id"], plan["sha256"], "human", tmp_path)
    assert not (tmp_path / "blocked").exists()


def test_executor_refuses_noninteractive_authorization(tmp_path, monkeypatch):
    db = Database(tmp_path / "test.db")
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "blocked"}, tmp_path)
    from types import SimpleNamespace
    monkeypatch.setattr("aether_core.repair_actions.sys.stdin", SimpleNamespace(isatty=lambda: False))
    with pytest.raises(PermissionError, match="live interactive terminal"):
        Executor(db).execute_after_human_prompt(plan["id"], plan["sha256"], "human", tmp_path)
    assert not (tmp_path / "blocked").exists()


def test_action_plan_can_be_consumed_only_once_under_concurrency(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from datetime import UTC, datetime
    from threading import Barrier

    db = Database(tmp_path / "test.db")
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "race"}, tmp_path)
    barrier = Barrier(2)

    def consume():
        barrier.wait()
        now = datetime.now(UTC).isoformat()
        return db.consume_action_plan(
            plan["id"], plan["sha256"], "human",
            plan["expires_at"], now,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(consume) for _ in range(2)]
        results = []
        failures = []
        for future in futures:
            try:
                results.append(future.result())
            except PermissionError as exc:
                failures.append(exc)

    assert len(results) == 1
    assert len(failures) == 1
    assert db.get_action_plan(plan["id"])["status"] == "consumed"
    assert not (tmp_path / "race").exists()



def test_directory_action_fails_closed_without_safe_descriptor_apis(tmp_path):
    from aether_core.repair_actions import _ensure_directory

    if _supports_race_safe_directory_creation():
        pytest.skip("This platform provides the required safe descriptor APIs.")
    with pytest.raises(PermissionError, match="race-safe directory APIs"):
        _ensure_directory(EnsureDirectoryParams(relative_path="blocked"), tmp_path)
    assert not (tmp_path / "blocked").exists()



def test_plan_rejects_replaced_target_directory(tmp_path, monkeypatch):
    db = Database(tmp_path / "state.db")
    root = tmp_path / "approved-root"
    root.mkdir()
    plan = create_action_plan(db, "ensure_directory", {"relative_path": "cache"}, root)
    moved = tmp_path / "original-root"
    root.rename(moved)
    root.mkdir()

    from types import SimpleNamespace
    monkeypatch.setattr("aether_core.repair_actions.sys.stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt: f"AUTHORIZE {plan['id']} {plan['sha256']}",
    )
    with pytest.raises(PermissionError, match="target"):
        Executor(db).execute_after_human_prompt(
            plan["id"], plan["sha256"], "human", root
        )
    assert not (root / "cache").exists()
    assert db.get_action_plan(plan["id"])["status"] == "pending"



def test_failed_multicomponent_creation_rolls_back_new_empty_directories(tmp_path, monkeypatch):
    if not _supports_race_safe_directory_creation():
        pytest.skip("Descriptor-relative directory creation is unavailable.")
    from aether_core import repair_actions

    db = Database(tmp_path / "test.db")
    plan = create_action_plan(
        db, "ensure_directory",
        {"relative_path": "new-parent/blocked/child"}, tmp_path,
    )
    real_mkdir_at = repair_actions._mkdir_at

    def fail_second_component(path, *, mode, dir_fd):
        if path == "blocked":
            raise PermissionError("simulated second-component failure")
        return real_mkdir_at(path, mode=mode, dir_fd=dir_fd)

    monkeypatch.setattr(repair_actions, "_mkdir_at", fail_second_component)
    from types import SimpleNamespace
    monkeypatch.setattr(
        "aether_core.repair_actions.sys.stdin",
        SimpleNamespace(isatty=lambda: True),
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt: f"AUTHORIZE {plan['id']} {plan['sha256']}",
    )
    with pytest.raises(PermissionError, match="simulated second-component failure"):
        Executor(db).execute_after_human_prompt(
            plan["id"], plan["sha256"], "human", tmp_path
        )
    assert not (tmp_path / "new-parent").exists()
    assert db.get_action_plan(plan["id"])["status"] == "failed"



def test_internal_execution_entrypoint_requires_live_human_confirmation(tmp_path, monkeypatch):
    db = Database(tmp_path / "test.db")
    plan = create_action_plan(
        db, "ensure_directory", {"relative_path": "internal-bypass"}, tmp_path
    )
    from types import SimpleNamespace
    monkeypatch.setattr(
        "aether_core.repair_actions.sys.stdin",
        SimpleNamespace(isatty=lambda: False),
    )
    with pytest.raises(PermissionError, match="live interactive terminal"):
        _execute_approved_plan(
            db, plan["id"], plan["sha256"], "audit-label", tmp_path
        )
    assert db.get_action_plan(plan["id"])["status"] == "pending"
    assert not (tmp_path / "internal-bypass").exists()
