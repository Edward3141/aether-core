"""Independent post-repair verification for allow-listed actions."""
from __future__ import annotations

import stat
from pathlib import Path


class PostRepairVerifier:
    """Verify action postconditions independently from the action implementation."""

    def verify(self, action_id: str, parameters: dict, root: Path) -> list[str]:
        if action_id != "ensure_directory":
            raise ValueError("No independent post-repair verifier is registered for this action.")
        relative_path = parameters.get("relative_path")
        if not isinstance(relative_path, str) or not relative_path:
            raise ValueError("Verifier received invalid action parameters.")

        canonical_root = root.resolve(strict=True)
        target = canonical_root.joinpath(*relative_path.split("/"))
        checks: list[str] = []
        for attempt in range(1, 4):
            current = canonical_root
            for part in relative_path.split("/"):
                current = current / part
                try:
                    mode = current.lstat().st_mode
                except FileNotFoundError as exc:
                    raise RuntimeError("Post-repair verification failed: path is missing.") from exc
                if stat.S_ISLNK(mode):
                    raise PermissionError("Post-repair verification failed: symlink detected.")
                if not stat.S_ISDIR(mode):
                    raise RuntimeError(
                        "Post-repair verification failed: path component is not a directory."
                    )
            resolved = target.resolve(strict=True)
            if resolved != target and canonical_root not in resolved.parents:
                raise PermissionError(
                    "Post-repair verification failed: target escaped approved root."
                )
            checks.append(
                f"pass-{attempt}: all components are real directories beneath approved root"
            )
        return checks
