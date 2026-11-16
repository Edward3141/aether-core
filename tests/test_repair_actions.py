"""Tests for the fail-closed repair action boundary. Created by Edward Tejada."""
import pytest
from pydantic import ValidationError

from aether_core.repair_actions import EnsureDirectoryParams, execute_registered_action


@pytest.mark.parametrize(
    "path",
    ["../outside", "/tmp/outside", "C:/Windows/System32", "a/../../outside", ""],
)
def test_action_contract_rejects_unsafe_paths(path):
    with pytest.raises(ValidationError):
        EnsureDirectoryParams(relative_path=path)


def test_action_contract_rejects_extra_parameters():
    with pytest.raises(ValidationError):
        EnsureDirectoryParams.model_validate(
            {"relative_path": "cache", "command": "rm -rf /"}
        )


def test_repair_execution_fails_closed_without_approval(tmp_path):
    with pytest.raises(PermissionError, match="one-time human approval"):
        execute_registered_action(
            "ensure_directory", {"relative_path": "cache"}, tmp_path
        )
    assert not (tmp_path / "cache").exists()


def test_unknown_action_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="not registered"):
        execute_registered_action("run_shell", {"command": "whoami"}, tmp_path)
