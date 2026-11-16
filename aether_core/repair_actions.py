"""Allow-listed, human-authorized local repair actions.

Only typed operations are supported. Model-generated shell or script text is never run.
"""
import errno
import hashlib
import json
import os
import platform
import stat
import sys
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .database import Database
from .verification import PostRepairVerifier


class EnsureDirectoryParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    relative_path: str = Field(min_length=1, max_length=240)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        path = PurePosixPath(normalized)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in normalized.split("/")):
            raise ValueError("Path must be a clean relative path without traversal.")
        if ":" in normalized or "\x00" in normalized or len(path.parts) > 8:
            raise ValueError("Path contains forbidden characters or is too deep.")
        return normalized



class CreateFileParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    relative_path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=16384)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        path = PurePosixPath(normalized)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in normalized.split("/")):
            raise ValueError("Path must be a clean relative path without traversal.")
        if ":" in normalized or "\x00" in normalized or len(path.parts) > 8:
            raise ValueError("Path contains forbidden characters or is too deep.")
        return normalized


class ActionResult(BaseModel):
    action_id: str
    status: str
    detail: str
    verification: list[str] = Field(default_factory=list)


def _identity_from_stat(canonical: Path, metadata: os.stat_result) -> str:
    material = (
        f"{platform.node()}|{os.name}|{canonical}|"
        f"{metadata.st_dev}|{metadata.st_ino}"
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def target_identity(root: Path) -> str:
    """Bind plans to the canonical local target directory and host identity."""
    canonical = root.resolve(strict=True)
    if not canonical.is_dir():
        raise ValueError("Target root must be an existing directory.")
    return _identity_from_stat(canonical, canonical.stat())


def _supports_race_safe_directory_creation() -> bool:
    """Return whether this runtime supports descriptor-relative no-follow creation."""
    return (
        platform.system() in {"Linux", "Darwin"}
        and all(
            operation in os.supports_dir_fd
            for operation in (os.open, os.mkdir, os.stat, os.rmdir)
        )
        and os.stat in os.supports_follow_symlinks
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
    )


def _mkdir_at(name: str, *, mode: int, dir_fd: int) -> None:
    """Small seam for deterministic failure-injection tests."""
    os.mkdir(name, mode=mode, dir_fd=dir_fd)


def _ensure_directory(
    params: EnsureDirectoryParams, root: Path, expected_target_identity: str | None = None
) -> ActionResult:
    """Create directories using pinned descriptors and roll back our empty directories on failure."""
    if not _supports_race_safe_directory_creation():
        raise PermissionError(
            "This platform does not provide the required race-safe directory APIs; "
            "the action is disabled here."
        )

    canonical_root = root.resolve(strict=True)
    if not canonical_root.is_dir():
        raise ValueError("Target root must be a directory.")

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptors: list[int] = []
    created: list[tuple[int, str, int, int]] = []
    try:
        # Pin every component of the approved root from the filesystem anchor.
        root_parts = canonical_root.parts
        descriptors.append(os.open(root_parts[0], flags))
        for root_part in root_parts[1:]:
            try:
                child = os.open(root_part, flags, dir_fd=descriptors[-1])
            except OSError as exc:
                if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
                    raise PermissionError("Approved root contains a Symlink or non-directory.") from exc
                raise
            descriptors.append(child)

        if expected_target_identity is not None:
            opened_identity = _identity_from_stat(canonical_root, os.fstat(descriptors[-1]))
            if opened_identity != expected_target_identity:
                raise PermissionError(
                    "Approved target changed before the filesystem operation began."
                )

        for part in params.relative_path.split("/"):
            parent = descriptors[-1]
            created_here = False
            try:
                _mkdir_at(part, mode=0o755, dir_fd=parent)
                created_here = True
            except FileExistsError:
                pass

            try:
                child = os.open(part, flags, dir_fd=parent)
            except OSError as exc:
                if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
                    raise PermissionError(
                        "Symlink traversal or a non-directory path component is not allowed."
                    ) from exc
                raise

            if created_here:
                # Confirm the opened directory is the exact inode created at this name.
                named = os.stat(part, dir_fd=parent, follow_symlinks=False)
                opened = os.fstat(child)
                if (
                    not stat.S_ISDIR(named.st_mode)
                    or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
                ):
                    os.close(child)
                    raise PermissionError(
                        "New directory was replaced during creation; refusing to continue."
                    )
                created.append((parent, part, opened.st_dev, opened.st_ino))
            descriptors.append(child)
    except Exception as original:
        rollback_errors: list[str] = []
        for parent, part, device, inode in reversed(created):
            try:
                current = os.stat(part, dir_fd=parent, follow_symlinks=False)
                if (
                    not stat.S_ISDIR(current.st_mode)
                    or (current.st_dev, current.st_ino) != (device, inode)
                ):
                    raise OSError("Directory identity changed; refusing unsafe rollback.")
                os.rmdir(part, dir_fd=parent)
            except FileNotFoundError:
                continue
            except OSError as rollback_error:
                rollback_errors.append(f"{part}: {type(rollback_error).__name__}")
        if rollback_errors:
            raise RuntimeError(
                "Directory action failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
            ) from original
        raise
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)

    return ActionResult(
        action_id="ensure_directory",
        status="executed",
        detail=(
            "Directory creation completed using pinned, no-follow filesystem descriptors: "
            f"{params.relative_path}"
        ),
    )


def _create_file(
    params: CreateFileParams, root: Path, expected_target_identity: str | None = None
) -> ActionResult:
    """Create one new UTF-8 file without overwriting existing content or following links."""
    if not _supports_race_safe_directory_creation() or os.unlink not in os.supports_dir_fd:
        raise PermissionError(
            "This platform does not provide the required race-safe file APIs; the action is disabled."
        )
    canonical_root = root.resolve(strict=True)
    if not canonical_root.is_dir():
        raise ValueError("Target root must be a directory.")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptors: list[int] = []
    file_descriptor = None
    created_identity = None
    filename = params.relative_path.split("/")[-1]
    try:
        root_parts = canonical_root.parts
        descriptors.append(os.open(root_parts[0], flags))
        for part in root_parts[1:]:
            descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
        if expected_target_identity is not None:
            opened_identity = _identity_from_stat(canonical_root, os.fstat(descriptors[-1]))
            if opened_identity != expected_target_identity:
                raise PermissionError("Approved target changed before file creation.")
        for part in params.relative_path.split("/")[:-1]:
            descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
        parent = descriptors[-1]
        file_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        file_descriptor = os.open(filename, file_flags, 0o600, dir_fd=parent)
        metadata = os.fstat(file_descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise PermissionError("Created target is not a regular file.")
        created_identity = (metadata.st_dev, metadata.st_ino)
        data = params.content.encode("utf-8")
        offset = 0
        while offset < len(data):
            written = os.write(file_descriptor, data[offset:])
            if written <= 0:
                raise OSError("File write made no progress.")
            offset += written
        os.fsync(file_descriptor)
        named = os.stat(filename, dir_fd=parent, follow_symlinks=False)
        if (
            not stat.S_ISREG(named.st_mode)
            or (named.st_dev, named.st_ino) != created_identity
        ):
            raise PermissionError("Created file was replaced during write; refusing to continue.")
    except Exception as original:
        if created_identity is not None and descriptors:
            try:
                parent = descriptors[-1]
                current = os.stat(filename, dir_fd=parent, follow_symlinks=False)
                if (
                    stat.S_ISREG(current.st_mode)
                    and (current.st_dev, current.st_ino) == created_identity
                ):
                    os.unlink(filename, dir_fd=parent)
            except FileNotFoundError:
                pass
            except OSError as rollback_error:
                raise RuntimeError(
                    "File creation failed and safe rollback was incomplete: "
                    + type(rollback_error).__name__
                ) from original
        raise
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        for descriptor in reversed(descriptors):
            os.close(descriptor)

    return ActionResult(
        action_id="create_file",
        status="executed",
        detail=(
            "New UTF-8 file created without overwrite using no-follow descriptors; "
            f"path={params.relative_path}; bytes={len(params.content.encode('utf-8'))}."
        ),
    )

_HANDLERS = {
    "ensure_directory": (EnsureDirectoryParams, _ensure_directory),
    "create_file": (CreateFileParams, _create_file),
}


def registered_action_ids() -> tuple[str, ...]:
    """Return the immutable names of typed repair handlers currently registered."""
    return tuple(sorted(_HANDLERS))


def _plan_digest(action_id: str, parameters: dict, root: Path, identity: str) -> str:
    payload = {
        "action_id": action_id,
        "parameters": parameters,
        "target_identity": identity,
        "target_root": str(root),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def create_action_plan(db: Database, action_id: str, parameters: dict,
                       root: Path, ttl_minutes: int = 10) -> dict:
    if action_id not in _HANDLERS:
        raise ValueError("Action is not registered in the local allow-list.")
    if not 1 <= ttl_minutes <= 30:
        raise ValueError("Action plan lifetime must be between 1 and 30 minutes.")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Target root must be an existing directory.")
    schema, _handler = _HANDLERS[action_id]
    validated = schema.model_validate(parameters)
    identity = target_identity(root)
    normalized_parameters = validated.model_dump(mode="json")
    payload = {
        "action_id": action_id,
        "parameters": normalized_parameters,
        "target_identity": identity,
        "target_root": str(root),
    }
    digest = _plan_digest(action_id, normalized_parameters, root, identity)
    plan_id = str(uuid.uuid4())
    created = datetime.now(UTC)
    expires = created + timedelta(minutes=ttl_minutes)
    db.create_action_plan(plan_id, action_id,
        json.dumps(validated.model_dump(mode="json"), sort_keys=True),
        str(root), identity, digest, created.isoformat(), expires.isoformat())
    return {"id": plan_id, **payload, "sha256": digest,
            "expires_at": expires.isoformat()}


def _execute_approved_plan(
    db: Database, plan_id: str, digest: str, approved_by: str, root: Path,
    present_review: Callable[[dict], None] | None = None,
) -> ActionResult | None:
    """Single execution boundary: even internal callers must obtain live human confirmation."""
    if not sys.stdin.isatty():
        raise PermissionError("Human authorization requires a live interactive terminal.")

    plan = db.get_action_plan(plan_id)
    if plan is None:
        raise ValueError("Action plan not found.")
    if plan["digest"] != digest:
        raise ValueError("Action plan hash mismatch.")
    if plan["status"] != "pending":
        raise PermissionError("Action plan is not awaiting authorization.")

    review = {
        "plan_id": plan["id"],
        "action": plan["action_id"],
        "parameters": json.loads(plan["params_json"]),
        "target_root": plan["target_root"],
        "target_identity": plan["target_identity"],
        "sha256": plan["digest"],
        "expires_at": plan["expires_at"],
        "status": plan["status"],
        "effects": "Executes only the registered typed action; no shell or arbitrary scripts.",
    }
    if present_review is not None:
        present_review(review)
    expected = f"AUTHORIZE {plan['id']} {plan['digest']}"
    response = input(
        "Authorize this exact repair by typing "
        f"{expected!r}: "
    )
    if response != expected:
        return None

    # Reload after the human prompt: reject expiry, replay, edits or target replacement.
    plan = db.get_action_plan(plan_id)
    if plan is None or plan["status"] != "pending":
        raise PermissionError("Action plan is no longer awaiting authorization.")
    if plan["digest"] != digest:
        raise ValueError("Action plan digest changed during human review.")
    if not approved_by.strip() or len(approved_by) > 120:
        raise ValueError("A valid human approver audit label is required.")

    root = root.resolve(strict=True)
    now = datetime.now(UTC)
    expires = datetime.fromisoformat(plan["expires_at"])
    if now >= expires:
        raise PermissionError("Action plan expired; create and review a new plan.")
    if str(root) != plan["target_root"] or target_identity(root) != plan["target_identity"]:
        raise PermissionError("Approved target does not match the current target.")
    action_id = plan["action_id"]
    if action_id not in _HANDLERS:
        raise PermissionError("Action is no longer present in the local allow-list.")
    schema, _handler = _HANDLERS[action_id]
    try:
        stored_parameters = schema.model_validate_json(plan["params_json"]).model_dump(mode="json")
    except Exception as exc:
        raise ValueError("Stored action parameters failed schema validation.") from exc
    if _plan_digest(action_id, stored_parameters, root, plan["target_identity"]) != digest:
        raise ValueError("Action plan integrity check failed; parameters or target were changed.")

    claim = db.consume_action_plan(
        plan_id, digest, approved_by, expires.isoformat(), now.isoformat()
    )
    action_id = claim["action_id"]
    schema, handler = _HANDLERS[action_id]
    try:
        params = schema.model_validate_json(claim["params_json"])
        result = handler(
            params, Path(claim["target_root"]), claim["target_identity"]
        )
        verification = PostRepairVerifier().verify(
            action_id, params.model_dump(mode="json"), Path(claim["target_root"])
        )
        result = result.model_copy(update={
            "status": "succeeded",
            "detail": result.detail + " Independent post-repair verification passed.",
            "verification": verification,
        })
        db.finish_action_plan(plan_id, "succeeded", result.model_dump_json())
        return result
    except Exception as exc:
        db.finish_action_plan(
            plan_id, "failed",
            json.dumps({"error_type": type(exc).__name__, "detail": str(exc)[:500]}),
        )
        raise



def approve_and_execute(*_args, **_kwargs):
    """Unsafe direct execution is deliberately disabled; use the interactive Executor."""
    raise PermissionError(
        "Direct repair execution is disabled. A live interactive human confirmation is required."
    )


class Executor:
    """Final execution role: requires a live interactive terminal confirmation per action."""

    def __init__(self, database: Database):
        self.database = database
        self.capability_registry = None

    def bind_capabilities(self, registry) -> None:
        self.capability_registry = registry

    def available_capabilities(self, system: str | None = None) -> list[dict]:
        """List executor capabilities for the host, or an explicitly inspected platform."""
        if self.capability_registry is None:
            return []
        return self.capability_registry.list_for_role("EXECUTOR", system)

    def execute_after_human_prompt(
        self, plan_id: str, digest: str, approved_by: str, root: Path,
        present_review: Callable[[dict], None] | None = None,
    ) -> ActionResult | None:
        # The underlying execution boundary also prompts, so importing/calling it
        # directly cannot bypass the human authorization requirement.
        return _execute_approved_plan(
            self.database, plan_id, digest, approved_by, root, present_review
        )
