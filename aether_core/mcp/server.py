"""Local read-only MCP server. Created by Edward Tejada."""
from mcp.server.fastmcp import FastMCP

from ..config import database_path
from ..database import Database
from ..diagnostics import collect_diagnostics

mcp = FastMCP("AETHER CORE")
db = Database(database_path())


@mcp.tool()
def auditar_sistema() -> dict:
    """Collect fixed, read-only diagnostics and persist the report."""
    report = collect_diagnostics()
    db.save_audit(report)
    return report.model_dump(mode="json")


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


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
