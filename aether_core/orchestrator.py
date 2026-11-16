"""Workflow coordinator with integrated intelligence telemetry and evidence memory."""
import json
from .agents import Analyst, Auditor, Fixer, Scout
from .database import Database
from .models import AuditReport, RemediationProposal
from .extended.knowledge import KnowledgeStore
from .extended.quality import AgentScorecard
from .skills import build_builtin_registry


class Orchestrator:
    def __init__(self, database: Database):
        self.db = database
        self.scout, self.analyst = Scout(), Analyst()
        self.fixer, self.auditor = Fixer(), Auditor()
        # Integrated services use a sibling SQLite file; existing database schema is untouched.
        memory_path = database.path.with_name("aether-core-knowledge.sqlite3")
        self.knowledge = KnowledgeStore(memory_path)
        self.scorecard = AgentScorecard(
            database.path.with_name("aether-core-agent-metrics.sqlite3")
        )
        self.skills = build_builtin_registry(self.knowledge, self.scorecard)
        for agent in (self.scout, self.analyst, self.fixer, self.auditor):
            agent.bind_skills(self.skills)

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
            # Give ANALYST only human-verified historical references; label them as context,
            # never as current machine evidence or executable instructions.
            verified_context = self.skills.execute(
                "knowledge.search", caller="ANALYST",
                arguments={"topic": "", "limit": 10},
            )
            analysis_report = report
            if verified_context:
                analysis_report = report.model_copy(deep=True)
                analysis_report.summary += (
                    "\nVerified historical context (reference only; not current evidence): "
                    + json.dumps(verified_context, ensure_ascii=False)
                )
            analysis = await self.analyst.analyze(analysis_report)
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
        return self.skills.execute("report.generate", caller="SYSTEM")
