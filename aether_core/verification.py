"""Independent post-repair verification for allow-listed actions."""
from __future__ import annotations

import errno
import hashlib
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


def _verify_file_once(root: Path, relative_path: str, expected_sha256: str) -> None:
    """Verify a regular file's exact content through pinned no-follow descriptors."""
    if not _supports_descriptor_verification() or os.open not in os.supports_dir_fd:
        raise PermissionError("Descriptor-based file verification is unavailable.")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptors: list[int] = []
    file_descriptor = None
    try:
        descriptors.append(os.open(root.parts[0], flags))
        for part in root.parts[1:]:
            descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
        parts = relative_path.split("/")
        for part in parts[:-1]:
            descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
        file_descriptor = os.open(
            parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=descriptors[-1]
        )
        metadata = os.fstat(file_descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 16384:
            raise RuntimeError("File verification failed: target is not a bounded regular file.")
        chunks = []
        total = 0
        while True:
            chunk = os.read(file_descriptor, 4096)
            if not chunk:
                break
            total += len(chunk)
            if total > 16384:
                raise RuntimeError("File verification failed: content exceeds the action limit.")
            chunks.append(chunk)
        actual = hashlib.sha256(b"".join(chunks)).hexdigest()
        if actual != expected_sha256:
            raise RuntimeError("File verification failed: content digest does not match the approved plan.")
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        for descriptor in reversed(descriptors):
            os.close(descriptor)


class PostRepairVerifier:
    """Verify action postconditions independently from the action implementation."""

    def verify(self, action_id: str, parameters: dict, root: Path) -> list[str]:
        if action_id not in {"ensure_directory", "create_file"}:
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
        if action_id == "create_file":
            content = parameters.get("content")
            if not isinstance(content, str) or len(content.encode("utf-8")) > 16384:
                raise ValueError("Verifier received invalid or oversized file content.")
            expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
            for attempt in range(1, 4):
                _verify_file_once(canonical_root, normalized, expected)
                checks.append(f"pass-{attempt}: regular file content digest matches the approved plan")
            return checks
        # These are three independent descriptor walks, not timed health intervals.
        for attempt in range(1, 4):
            _verify_once(canonical_root, normalized)
            checks.append(
                f"pass-{attempt}: target components opened as real directories without following symlinks"
            )
        return checks
