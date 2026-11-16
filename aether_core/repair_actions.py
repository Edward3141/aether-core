"""Allow-listed, human-authorized local repair actions.

Only typed operations are supported. Model-generated shell or script text is never run.
"""
import hashlib
import json
import os
import platform
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .database import Database


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


class ActionResult(BaseModel):
    action_id: str
    status: str
    detail: str


def target_identity(root: Path) -> str:
    """Bind plans to the canonical local target directory and host identity."""
    canonical = root.resolve(strict=True)
    if not canonical.is_dir():
        raise ValueError("Target root must be an existing directory.")
    material = f"{platform.node()}|{os.name}|{canonical}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _ensure_directory(params: EnsureDirectoryParams, root: Path) -> ActionResult:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Target root must be a directory.")
    current = root
    for part in params.relative_path.split("/"):
        current = current / part
        if current.exists() or current.is_symlink():
            if current.is_symlink():
                raise PermissionError("Symlink traversal is not allowed.")
            if not current.is_dir():
                raise FileExistsError("A target path component is not a directory.")
    target = root.joinpath(*params.relative_path.split("/"))
    target.mkdir(parents=True, exist_ok=True)
    resolved = target.resolve(strict=True)
    if resolved != target and root not in resolved.parents:
        raise PermissionError("Resolved target escaped the approved root.")
    return ActionResult(action_id="ensure_directory", status="succeeded",
                        detail=f"Directory exists: {params.relative_path}")


_HANDLERS = {"ensure_directory": (EnsureDirectoryParams, _ensure_directory)}


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


def approve_and_execute(db: Database, plan_id: str, digest: str,
                        approved_by: str, root: Path) -> ActionResult:
    """Consume a plan once, then execute its fixed handler; never runs arbitrary commands."""
    if not approved_by.strip() or len(approved_by) > 120:
        raise ValueError("A valid human approver identity is required.")
    root = root.resolve(strict=True)
    now = datetime.now(UTC)
    plan = db.get_action_plan(plan_id)
    if plan is None:
        raise ValueError("Action plan not found.")
    if digest != plan["digest"]:
        raise ValueError("Action plan digest mismatch.")
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
    claim = db.consume_action_plan(plan_id, digest, approved_by,
                                   expires.isoformat(), now.isoformat())
    action_id = claim["action_id"]
    schema, handler = _HANDLERS[action_id]
    try:
        params = schema.model_validate_json(claim["params_json"])
        result = handler(params, Path(claim["target_root"]))
        db.finish_action_plan(plan_id, "succeeded", result.model_dump_json())
        return result
    except Exception as exc:
        db.finish_action_plan(plan_id, "failed",
            json.dumps({"error_type": type(exc).__name__, "detail": str(exc)[:500]}))
        raise




class Executor:
    """Final execution role: requests explicit human authorization for each action."""

    def __init__(self, database: Database):
        self.database = database

    def execute_after_human_prompt(
        self, plan_id: str, digest: str, approved_by: str, root: Path,
        ask_human: Callable[[dict], str],
    ) -> ActionResult | None:
        plan = self.database.get_action_plan(plan_id)
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
        response = ask_human(review)
        expected = f"AUTHORIZE {plan['id']} {plan['digest']}"
        if response != expected:
            return None
        # Re-check state, expiry, target and digest inside the execution gate.
        return approve_and_execute(
            self.database, plan["id"], plan["digest"], approved_by, root
        )
