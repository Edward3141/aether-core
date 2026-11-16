"""Local read-only MCP server. Created by Edward Tejada."""
import json
from mcp.server.fastmcp import FastMCP

from ..config import database_path
from ..database import Database
from ..diagnostics import collect_diagnostics
from ..orchestrator import Orchestrator

mcp = FastMCP("AETHER CORE")
db = Database(database_path())


@mcp.tool()
def recopilar_diagnosticos() -> dict:
    """Collect fixed, read-only local diagnostics without invoking AI."""
    report = collect_diagnostics()
    db.save_audit(report)
    return report.model_dump(mode="json")


@mcp.tool()
async def ejecutar_flujo_completo() -> dict:
    """Run SCOUT, ANALYST, FIXER and AUDITOR; this never executes repairs."""
    workflow = Orchestrator(db)
    report, analysis = await workflow.audit()
    proposal, review = await workflow.plan(analysis)
    return {
        "audit": report.model_dump(mode="json"),
        "analysis": analysis,
        "proposal": proposal.model_dump(mode="json"),
        "proposal_sha256": proposal.content_hash(),
        "auditor_review": review,
        "execution_allowed": False,
        "human_approval_required": True,
    }


@mcp.tool()
def consultar_auditoria(audit_id: str) -> dict:
    """Retrieve a stored audit report by exact ID."""
    if not audit_id or len(audit_id) > 80:
        raise ValueError("Invalid audit ID.")
    report = db.get_audit(audit_id)
    if report is None:
        raise ValueError("Audit not found.")
    return report.model_dump(mode="json")


@mcp.tool()
def consultar_propuesta(proposal_id: str) -> dict:
    """Retrieve a stored remediation proposal; this tool never approves or executes it."""
    if not proposal_id or len(proposal_id) > 80:
        raise ValueError("Invalid proposal ID.")
    proposal = db.get_proposal(proposal_id)
    if proposal is None:
        raise ValueError("Proposal not found.")
    return {
        "proposal": proposal.model_dump(mode="json"),
        "sha256": proposal.content_hash(),
        "execution_allowed": False,
    }


@mcp.tool()
def listar_habilidades() -> list[dict]:
    """List registered, policy-controlled built-in skills."""
    return Orchestrator(db).skills.list()


@mcp.tool()
def ejecutar_habilidad(nombre: str, argumentos: dict | None = None) -> dict | list | str | int | float | bool:
    """Execute one registered read-only skill; unknown or unauthorized skills fail closed."""
    return Orchestrator(db).skills.execute(
        nombre, caller="MCP", arguments=argumentos or {}
    )


@mcp.tool()
def consultar_decisiones(proposal_id: str) -> list[dict]:
    """List human approval/rejection records for a proposal; does not change them."""
    if not proposal_id or len(proposal_id) > 80:
        raise ValueError("Invalid proposal ID.")
    return [
        record.model_dump(mode="json")
        for record in db.list_approvals(proposal_id)
    ]


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
