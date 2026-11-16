"""Independent post-repair verification for allow-listed actions."""
from __future__ import annotations

import errno
import os
import stat
from pathlib import Path, PurePosixPath


def _supports_descriptor_verification() -> bool:
    return (
        os.name != "nt"
        and os.open in os.supports_dir_fd
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
    )


def _verify_once(root: Path, relative_path: str) -> None:
    """Walk the root and target through pinned descriptors without following links."""
    if not _supports_descriptor_verification():
        raise PermissionError(
            "Independent descriptor-based verification is unavailable on this platform."
        )
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptors: list[int] = []
    try:
        root_parts = root.parts
        descriptors.append(os.open(root_parts[0], flags))
        for part in root_parts[1:]:
            descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
        for part in relative_path.split("/"):
            try:
                child = os.open(part, flags, dir_fd=descriptors[-1])
            except OSError as exc:
                if exc.errno == errno.ENOENT:
                    raise RuntimeError(
                        "Post-repair verification failed: path is missing."
                    ) from exc
                if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
                    raise PermissionError(
                        "Post-repair verification failed: symlink or non-directory detected."
                    ) from exc
                raise
            if not stat.S_ISDIR(os.fstat(child).st_mode):
                os.close(child)
                raise RuntimeError(
                    "Post-repair verification failed: path component is not a directory."
                )
            descriptors.append(child)
        if not stat.S_ISDIR(os.fstat(descriptors[-1]).st_mode):
            raise RuntimeError("Post-repair verification failed: target is not a directory.")
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


class PostRepairVerifier:
    """Verify action postconditions independently from the action implementation."""

    def verify(self, action_id: str, parameters: dict, root: Path) -> list[str]:
        if action_id != "ensure_directory":
            raise ValueError("No independent post-repair verifier is registered for this action.")
        relative_path = parameters.get("relative_path")
        if not isinstance(relative_path, str) or not relative_path:
            raise ValueError("Verifier received invalid action parameters.")
        normalized = relative_path.replace("\\", "/")
        candidate = PurePosixPath(normalized)
        if (
            candidate.is_absolute()
            or any(part in {"", ".", ".."} for part in normalized.split("/"))
            or ":" in normalized
            or "\x00" in normalized
        ):
            raise ValueError("Verifier received an unsafe relative path.")

        canonical_root = root.resolve(strict=True)
        checks: list[str] = []
        # These are three independent descriptor walks, not timed health intervals.
        for attempt in range(1, 4):
            _verify_once(canonical_root, normalized)
            checks.append(
                f"pass-{attempt}: target components opened as real directories without following symlinks"
            )
        return checks
