"""Workflow coordinator. Created by Edward Tejada."""
from .agents import Analyst, Auditor, Fixer, Scout
from .database import Database
from .models import AuditReport, RemediationProposal


class Orchestrator:
    def __init__(self, database: Database):
        self.db = database
        self.scout, self.analyst = Scout(), Analyst()
        self.fixer, self.auditor = Fixer(), Auditor()

    async def audit(self) -> tuple[AuditReport, str]:
        report = await self.scout.inspect()
        self.db.save_audit(report)
        analysis = await self.analyst.analyze(report)
        return report, analysis

    async def plan(self, analysis: str) -> tuple[RemediationProposal, dict]:
        proposal = await self.fixer.propose(analysis)
        self.db.save_proposal(proposal)
        review = await self.auditor.review(proposal)
        return proposal, review
