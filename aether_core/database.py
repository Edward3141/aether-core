"""SQLite persistence. Created by Edward Tejada."""
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .models import AuditReport, ApprovalRecord, RemediationProposal


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS audits (
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS proposals (
                    id TEXT PRIMARY KEY, content_hash TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT NOT NULL, proposal_hash TEXT NOT NULL,
                    decision TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audits_created_at ON audits(created_at);
                CREATE INDEX IF NOT EXISTS idx_approvals_proposal_id ON approvals(proposal_id);
                CREATE TABLE IF NOT EXISTS action_plans (
                    id TEXT PRIMARY KEY, action_id TEXT NOT NULL, params_json TEXT NOT NULL,
                    target_root TEXT NOT NULL, target_identity TEXT NOT NULL, digest TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending', approved_by TEXT,
                    expires_at TEXT, consumed_at TEXT, result_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_action_plans_status ON action_plans(status);
                """
            )

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def create_action_plan(self, plan_id: str, action_id: str, params_json: str,
                           target_root: str, target_identity: str, digest: str,
                           created_at: str, expires_at: str) -> None:
        with self.connect() as db:
            db.execute(
                """INSERT INTO action_plans
                   (id, action_id, params_json, target_root, target_identity, digest, created_at, expires_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
                (plan_id, action_id, params_json, target_root, target_identity, digest, created_at, expires_at),
            )

    def get_action_plan(self, plan_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute(
                """SELECT id, action_id, params_json, target_root, target_identity, digest,
                          created_at, status, approved_by, expires_at, consumed_at, result_json
                   FROM action_plans WHERE id=?""", (plan_id,)
            ).fetchone()
        if row is None:
            return None
        keys = ("id", "action_id", "params_json", "target_root", "digest",
                "created_at", "status", "approved_by", "expires_at",
                "consumed_at", "result_json")
        return dict(zip(keys, row))

    def consume_action_plan(self, plan_id: str, digest: str, approved_by: str,
                            expires_at: str, consumed_at: str) -> dict:
        """Atomically claim one exact pending plan before any side effect."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT action_id, params_json, target_root, target_identity, digest, status, expires_at
                   FROM action_plans WHERE id=?""", (plan_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Action plan not found.")
            action_id, params_json, target_root, stored_identity, stored_digest, status, stored_expiry = row
            if status != "pending":
                raise PermissionError("Action plan is not pending; approvals cannot be replayed.")
            if stored_digest != digest:
                raise ValueError("Action plan digest mismatch.")
            if stored_expiry <= consumed_at:
                raise PermissionError("Action plan expired; create and review a new plan.")
            db.execute(
                """UPDATE action_plans SET status='consumed', approved_by=?,
                   expires_at=?, consumed_at=? WHERE id=? AND status='pending'""",
                (approved_by, expires_at, consumed_at, plan_id),
            )
            if db.total_changes != 1:
                raise PermissionError("Action plan could not be consumed exactly once.")
            return {"action_id": action_id, "params_json": params_json,
                    "target_root": target_root, "target_identity": stored_identity, "digest": stored_digest}

    def finish_action_plan(self, plan_id: str, status: str, result_json: str) -> None:
        if status not in {"succeeded", "failed"}:
            raise ValueError("Invalid action completion status.")
        with self.connect() as db:
            db.execute(
                "UPDATE action_plans SET status=?, result_json=? WHERE id=? AND status='consumed'",
                (status, result_json, plan_id),
            )

    def save_audit(self, report: AuditReport) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO audits VALUES (?, ?, ?)",
                (report.id, report.created_at.isoformat(), report.model_dump_json()),
            )

    def get_audit(self, audit_id: str) -> AuditReport | None:
        with self.connect() as db:
            row = db.execute("SELECT payload FROM audits WHERE id=?", (audit_id,)).fetchone()
        return AuditReport.model_validate_json(row[0]) if row else None

    def save_proposal(self, proposal: RemediationProposal) -> str:
        digest = proposal.content_hash()
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO proposals VALUES (?, ?, ?)",
                (proposal.id, digest, proposal.model_dump_json()),
            )
        return digest

    def get_proposal(self, proposal_id: str) -> RemediationProposal | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT payload, content_hash FROM proposals WHERE id=?", (proposal_id,)
            ).fetchone()
        if not row:
            return None
        proposal = RemediationProposal.model_validate_json(row[0])
        if proposal.content_hash() != row[1]:
            raise ValueError("Stored proposal integrity check failed.")
        return proposal

    def save_approval(self, record: ApprovalRecord) -> None:
        now = datetime.now(UTC)
        if record.created_at > now:
            raise ValueError("Approval creation time cannot be in the future.")
        if record.expires_at <= now:
            raise ValueError("Approval is expired and cannot be recorded as current.")
        with self.connect() as db:
            row = db.execute(
                "SELECT content_hash FROM proposals WHERE id=?", (record.proposal_id,)
            ).fetchone()
            if not row or row[0] != record.proposal_hash:
                raise ValueError("Approval rejected: proposal missing or hash mismatch.")
            db.execute(
                "INSERT INTO approvals (proposal_id, proposal_hash, decision, payload) "
                "VALUES (?, ?, ?, ?)",
                (
                    record.proposal_id,
                    record.proposal_hash,
                    record.decision,
                    record.model_dump_json(),
                ),
            )

    def list_approvals(self, proposal_id: str) -> list[ApprovalRecord]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT payload FROM approvals WHERE proposal_id=? ORDER BY id DESC",
                (proposal_id,),
            ).fetchall()
        return [ApprovalRecord.model_validate_json(row[0]) for row in rows]

    def list_audits(self, limit: int = 20) -> list[AuditReport]:
        limit = max(1, min(int(limit), 100))
        with self.connect() as db:
            rows = db.execute(
                "SELECT payload FROM audits ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [AuditReport.model_validate_json(row[0]) for row in rows]
