"""Fail-closed repair action contracts. Created by Edward Tejada.

Repair execution remains disabled until a one-time, atomically consumed approval
executor is implemented. No action handler is exposed to callers in this release.
"""
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EnsureDirectoryParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    relative_path: str = Field(min_length=1, max_length=240)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
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


def execute_registered_action(action_id: str, parameters: dict, root) -> ActionResult:
    """Reject all repair execution until the trusted approval executor exists."""
    if action_id != "ensure_directory":
        raise ValueError("Repair action is not registered.")
    EnsureDirectoryParams.model_validate(parameters)
    raise PermissionError(
        "Repair execution is disabled: one-time human approval and atomic "
        "consumption are not implemented."
    )
