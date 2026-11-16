"""Workflow coordinator with integrated intelligence telemetry and evidence memory."""
from .agents import Analyst, Auditor, Fixer, Scout
from .database import Database
from .models import AuditReport, RemediationProposal
from .extended.knowledge import KnowledgeStore
from .extended.monitor import collect_snapshot
from .extended.quality import AgentScorecard
from .extended.reports import build_report


class Orchestrator:
    def __init__(self, database: Database):
        self.db = database
        self.scout, self.analyst = Scout(), Analyst()
        self.fixer, self.auditor = Fixer(), Auditor()
        # Integrated services use a sibling SQLite file; existing database schema is untouched.
        memory_path = database.path.with_name("aether-core-knowledge.sqlite3")
        self.knowledge = KnowledgeStore(memory_path)
        self.scorecard = AgentScorecard()

    async def audit(self) -> tuple[AuditReport, str]:
        try:
            report = await self.scout.inspect()
            self.scorecard.record("SCOUT", success=True)
            self.db.save_audit(report)
            # Diagnostic observations are stored as unverified; they are not promoted to facts.
            for finding in report.findings:
                self.knowledge.add(
                    finding.title, finding.detail, source="SCOUT",
                    evidence={"risk": finding.risk.value, "hypothesis": finding.hypothesis,
                              "confidence": finding.confidence, "evidence": finding.evidence},
                )
            analysis = await self.analyst.analyze(report)
            self.scorecard.record("ANALYST", success=True)
            return report, analysis
        except Exception:
            # Record failed stage conservatively; do not suppress the original error.
            if "report" not in locals():
                self.scorecard.record("SCOUT", success=False)
            else:
                self.scorecard.record("ANALYST", success=False)
            raise

    async def plan(self, analysis: str) -> tuple[RemediationProposal, dict]:
        try:
            proposal = await self.fixer.propose(analysis)
            self.scorecard.record("FIXER", success=True)
            self.db.save_proposal(proposal)
            review = await self.auditor.review(proposal)
            self.scorecard.record("AUDITOR", success=True)
            return proposal, review
        except Exception:
            if "proposal" not in locals():
                self.scorecard.record("FIXER", success=False)
            else:
                self.scorecard.record("AUDITOR", success=False)
            raise

    def intelligence_report(self) -> dict:
        """Current process metrics plus a read-only system snapshot and memory count."""
        snapshot = collect_snapshot()
        metrics = [metric.__dict__ for metric in self.scorecard.snapshot()]
        unverified = self.knowledge.search("", verified_only=False, limit=100)
        verified = self.knowledge.search("", verified_only=True, limit=100)
        return build_report(
            snapshot=snapshot.to_dict(),
            agent_metrics=metrics,
            findings=[{"title": "Knowledge ledger", "description":
                       f"{len(unverified)} unverified observations; {len(verified)} verified entries"}],
        )
