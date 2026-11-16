"""Tests for independent post-repair verification."""
import pytest

from aether_core.verification import PostRepairVerifier


def test_verifier_requires_real_directory_and_repeats_checks(tmp_path):
    (tmp_path / "cache" / "nested").mkdir(parents=True)
    checks = PostRepairVerifier().verify(
        "ensure_directory", {"relative_path": "cache/nested"}, tmp_path
    )
    assert len(checks) == 3
    assert all(item.startswith("pass-") for item in checks)


def test_verifier_fails_when_expected_path_is_missing(tmp_path):
    with pytest.raises(RuntimeError, match="path is missing"):
        PostRepairVerifier().verify(
            "ensure_directory", {"relative_path": "missing"}, tmp_path
        )


def test_verifier_rejects_symlink_components(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is unavailable on this runner.")
    with pytest.raises(PermissionError, match="symlink"):
        PostRepairVerifier().verify(
            "ensure_directory", {"relative_path": "link"}, root
        )


def test_verifier_fails_closed_for_unregistered_actions(tmp_path):
    with pytest.raises(ValueError, match="No independent post-repair verifier"):
        PostRepairVerifier().verify("unknown", {}, tmp_path)



def test_verifier_rejects_symlink_even_when_target_stays_inside_root(tmp_path):
    root = tmp_path / "root"
    (root / "real").mkdir(parents=True)
    try:
        (root / "alias").symlink_to(root / "real", target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is unavailable on this runner.")
    with pytest.raises(PermissionError, match="symlink"):
        PostRepairVerifier().verify(
            "ensure_directory", {"relative_path": "alias"}, root
        )
