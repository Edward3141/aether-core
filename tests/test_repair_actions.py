"""Tests for the registered repair action boundary. Created by Edward Tejada."""
import pytest

from aether_core.repair_actions import execute_registered_action


def test_registered_action_creates_directory_only_inside_root(tmp_path):
    root = tmp_path / "repair-root"
    result = execute_registered_action(
        "ensure_directory", {"relative_path": "cache"}, root
    )
    assert result.status == "succeeded"
    assert (root / "cache").is_dir()


def test_registered_action_is_idempotent(tmp_path):
    root = tmp_path / "repair-root"
    (root / "cache").mkdir(parents=True)
    result = execute_registered_action(
        "ensure_directory", {"relative_path": "cache"}, root
    )
    assert result.status == "already_satisfied"


@pytest.mark.parametrize(
    "path",
    ["../outside", "/tmp/outside", "C:/Windows/System32", "a/../../outside", ""],
)
def test_registered_action_rejects_unsafe_paths(tmp_path, path):
    with pytest.raises(ValueError):
        execute_registered_action("ensure_directory", {"relative_path": path}, tmp_path)


def test_registered_action_rejects_unknown_action(tmp_path):
    with pytest.raises(ValueError, match="not registered"):
        execute_registered_action("run_shell", {"command": "whoami"}, tmp_path)


def test_registered_action_rejects_extra_parameters(tmp_path):
    with pytest.raises(ValueError):
        execute_registered_action(
            "ensure_directory",
            {"relative_path": "cache", "command": "rm -rf /"},
            tmp_path,
        )


def test_registered_action_rejects_symlink_escape(tmp_path):
    root = tmp_path / "repair-root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="Symlink"):
        execute_registered_action(
            "ensure_directory", {"relative_path": "link/child"}, root
        )
