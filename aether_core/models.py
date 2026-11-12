"""Validated contracts between agents. Created by Edward Tejada."""
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import uuid
from pydantic import BaseModel, Field

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Risk(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Finding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(min_length=1, max_length=160)
    detail: str = Field(min_length=1, max_length=4000)
    risk: Risk = Risk.INFO
    evidence: list[str] = Field(default_factory=list, max_length=30)
    hypothesis: bool = False
    confidence: float = Field(default=0.5, ge=0, le=1)

class AuditReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=utcnow)
    platform: str = Field(min_length=1, max_length=300)
    findings: list[Finding] = Field(default_factory=list, max_length=200)
    summary: str = Field(default="", max_length=4000)

class RemediationProposal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=utcnow)
    title: str = Field(min_length=1, max_length=160)
    rationale: str = Field(min_length=1, max_length=4000)
    steps: list[str] = Field(min_length=1, max_length=20)
    affected_files: list[str] = Field(default_factory=list, max_length=50)
    privileges: str = Field(default="No execution; review required", max_length=300)
    side_effects: list[str] = Field(default_factory=list, max_length=20)
    backup_plan: str = Field(default="Back up affected data before any manual change.", max_length=2000)
    rollback_plan: str = Field(default="Restore the verified backup.", max_length=2000)
    risk: Risk = Risk.MEDIUM

    def content_hash(self) -> str:
        payload = self.model_dump(mode="json", exclude={"created_at"})
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

class ApprovalRecord(BaseModel):
    proposal_id: str
    proposal_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    decision: str = Field(pattern=r"^(approved|rejected)$")
    approved_by: str = Field(min_length=1, max_length=120)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
