"""Tests for independent post-repair verification."""
import pytest

from aether_core.verification import PostRepairVerifier, _supports_descriptor_verification


def test_verifier_requires_real_directory_and_repeats_checks(tmp_path):
    (tmp_path / "cache" / "nested").mkdir(parents=True)
    if not _supports_descriptor_verification():
        with pytest.raises(PermissionError, match="descriptor-based verification is unavailable"):
            PostRepairVerifier().verify(
                "ensure_directory", {"relative_path": "cache/nested"}, tmp_path
            )
        return
    checks = PostRepairVerifier().verify(
        "ensure_directory", {"relative_path": "cache/nested"}, tmp_path
    )
    assert len(checks) == 3
    assert all(item.startswith("pass-") for item in checks)


def test_verifier_fails_when_expected_path_is_missing(tmp_path):
    expected_error = (
        RuntimeError if _supports_descriptor_verification() else PermissionError
    )
    expected_message = (
        "path is missing" if _supports_descriptor_verification()
        else "descriptor-based verification is unavailable"
    )
    with pytest.raises(expected_error, match=expected_message):
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
    expected_message = (
        "symlink" if _supports_descriptor_verification()
        else "descriptor-based verification is unavailable"
    )
    with pytest.raises(PermissionError, match=expected_message):
        PostRepairVerifier().verify(
            "ensure_directory", {"relative_path": "link"}, root
        )


def test_verifier_rejects_traversal_and_absolute_paths(tmp_path):
    for path in ("../outside", "/tmp/outside", "a/../../outside"):
        with pytest.raises(ValueError, match="unsafe relative path"):
            PostRepairVerifier().verify("ensure_directory", {"relative_path": path}, tmp_path)


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
    expected_message = (
        "symlink" if _supports_descriptor_verification()
        else "descriptor-based verification is unavailable"
    )
    with pytest.raises(PermissionError, match=expected_message):
        PostRepairVerifier().verify(
            "ensure_directory", {"relative_path": "alias"}, root
        )
