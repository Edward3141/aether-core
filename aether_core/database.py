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
                """
            )

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

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
