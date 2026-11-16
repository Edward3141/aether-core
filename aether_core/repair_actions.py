"""Registered, low-impact repair actions. Created by Edward Tejada.

This module deliberately contains no shell runner and accepts no model-authored commands.
Only fixed action identifiers with strict parameters can be dispatched.
"""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EnsureDirectoryParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    relative_path: str = Field(min_length=1, max_length=240)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        # Use portable separators and reject absolute paths, traversal and drive prefixes.
        normalized = value.replace("\\", "/")
        path = PurePosixPath(normalized)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError("Path must be a clean relative path without traversal.")
        if ":" in normalized or "\x00" in normalized:
            raise ValueError("Path contains a forbidden character.")
        if len(path.parts) > 8:
            raise ValueError("Path is too deep.")
        return normalized


class ActionResult(BaseModel):
    action_id: str
    status: str
    detail: str


def _ensure_directory(params: EnsureDirectoryParams, root: Path) -> ActionResult:
    """Create one directory under an explicitly configured repair root."""
    root.mkdir(parents=True, exist_ok=True)
    root_real = root.resolve(strict=True)
    target = root_real.joinpath(*PurePosixPath(params.relative_path).parts)

    # Reject symlinks in every existing path component, including the root.
    cursor = root_real
    for part in PurePosixPath(params.relative_path).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlink path components are not allowed.")
    resolved_parent = target.parent.resolve(strict=True)
    if os.path.commonpath((str(root_real), str(resolved_parent))) != str(root_real):
        raise ValueError("Target escapes the configured repair root.")
    if target.exists():
        if target.is_dir():
            return ActionResult(
                action_id="ensure_directory",
                status="already_satisfied",
                detail="Directory already exists; no change was made.",
            )
        raise ValueError("Target exists and is not a directory.")

    target.mkdir()
    return ActionResult(
        action_id="ensure_directory",
        status="succeeded",
        detail=f"Created directory {params.relative_path!r} under the configured repair root.",
    )


# Registry entries are fixed code, never supplied by the language model.
_ACTIONS: dict[str, tuple[type[BaseModel], Callable]] = {
    "ensure_directory": (EnsureDirectoryParams, _ensure_directory),
}


def execute_registered_action(action_id: str, parameters: dict, root: Path) -> ActionResult:
    """Validate and dispatch a registered action. Approval enforcement is a separate gate."""
    if action_id not in _ACTIONS:
        raise ValueError("Repair action is not registered.")
    schema, handler = _ACTIONS[action_id]
    validated = schema.model_validate(parameters)
    return handler(validated, root)
