"""Command line interface. Created by Edward Tejada."""
import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from . import __version__
from .config import database_path
from .database import Database
from .diagnostics import collect_diagnostics
from .models import ApprovalRecord
from .orchestrator import Orchestrator

console = Console()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="aether-core",
        description="AETHER CORE — human-supervised system diagnostics",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("doctor", help="Run fixed read-only local diagnostics")
    sub.add_parser("sandbox-check", help="Run a fixed diagnostic in the restricted Docker sandbox")
    sub.add_parser("audit", help="Collect evidence and analyze it with configured AI")

    ask = sub.add_parser("ask", help="Ask the configured default AI model")
    ask.add_argument("message", nargs="+")

    plan = sub.add_parser("plan", help="Generate a non-executable remediation proposal")
    plan.add_argument("analysis", nargs="+", help="Analysis text to turn into a proposal")

    for decision in ("approve", "reject"):
        action = sub.add_parser(decision, help=f"Record a human {decision} decision for a proposal")
        action.add_argument("proposal_id")
        action.add_argument("--hash", dest="proposal_hash", required=True)
        action.add_argument("--by", dest="approved_by", required=True)
        action.add_argument("--minutes", type=int, default=15)

    return parser


async def run(args):
    db = Database(database_path())
    if args.command == "sandbox-check":
        from .sandbox.docker_runner import run_check

        result = run_check("python-version")
        console.print(Panel(
            result.output or "(no output)",
            title=f"Docker sandbox: {result.check_id} — exit {result.exit_code}",
        ))
        return result.exit_code

    if args.command == "doctor":
        report = collect_diagnostics()
        console.print(Panel("AETHER CORE diagnostic report"))
        for finding in report.findings:
            console.print(Text(f"{finding.risk.value} {finding.title}: {finding.detail}"))
        return 0

    if args.command == "audit":
        workflow = Orchestrator(db)
        report, analysis = await workflow.audit()
        proposal, review = await workflow.plan(analysis)
        console.print(f"[green]Audit saved:[/] {report.id}")
        console.print(Panel(Text(report.summary), title="SCOUT"))
        console.print(Panel(Text(analysis), title="ANALYST"))
        console.print(Panel(
            f"[bold]{proposal.title}[/]\\nID: {proposal.id}\\n"
            f"SHA-256: {proposal.content_hash()}\\nRisk: {proposal.risk.value}\\n\\n"
            + "\\n".join(f"- {step}" for step in proposal.steps),
            title="FIXER — Proposal only",
        ))
        console.print(Panel(Text(review["advisory"]), title="AUDITOR — Advisory review"))
        console.print("[yellow]No repair was executed. Human review is required.[/]")
        return 0

    if args.command == "plan":
        proposal, review = await Orchestrator(db).plan(" ".join(args.analysis))
        console.print(Panel(
            f"[bold]{proposal.title}[/]\nID: {proposal.id}\n"
            f"SHA-256: {proposal.content_hash()}\nRisk: {proposal.risk.value}\n\n"
            + "\n".join(f"- {step}" for step in proposal.steps)
            + "\\n\\nThis is a proposal only; no action was executed.",
            title="FIXER — Remediation proposal",
        ))
        console.print(review["message"])
        return 0

    if args.command == "ask":
        from .providers import ask_model

        answer = await ask_model(
            "You are AETHER CORE, a careful assistant.", " ".join(args.message)
        )
        console.print(Text(answer))
        return 0

    if args.command in {"approve", "reject"}:
        if not args.proposal_id or len(args.proposal_id) > 80:
            raise ValueError("Invalid proposal ID.")
        if not 1 <= args.minutes <= 1440:
            raise ValueError("Approval validity must be between 1 and 1440 minutes.")
        proposal = db.get_proposal(args.proposal_id)
        if proposal is None:
            raise ValueError("Proposal not found.")
        if proposal.content_hash() != args.proposal_hash:
            raise ValueError("Proposal hash mismatch; review the current proposal.")
        decision = "approved" if args.command == "approve" else "rejected"
        console.print(Panel(
            f"[bold]{proposal.title}[/]\n"
            f"ID: {proposal.id}\nSHA-256: {proposal.content_hash()}\n"
            f"Decision: {decision.upper()}\n"
            "This records a human decision only. It does not execute repairs.",
            title="AETHER CORE — Human review",
        ))
        expected = f"{decision.upper()} {proposal.id}"
        typed = console.input(f"Type exactly '{expected}' to continue: ")
        if typed != expected:
            console.print("[yellow]Decision cancelled; no record was saved.[/]")
            return 2
        now = datetime.now(UTC)
        record = ApprovalRecord(
            proposal_id=proposal.id,
            proposal_hash=proposal.content_hash(),
            decision=decision,
            approved_by=args.approved_by,
            created_at=now,
            expires_at=now + timedelta(minutes=args.minutes),
        )
        db.save_approval(record)
        console.print(f"[green]Human decision recorded:[/] {decision}")
        console.print("[yellow]No repair was executed.[/]")
        return 0

    console.print("Choose a command. Use --help for details.")
    return 0


def entry_point():
    args = build_parser().parse_args()
    try:
        raise SystemExit(asyncio.run(run(args)))
    except KeyboardInterrupt:
        console.print("[yellow]Cancelled.[/]")
        raise SystemExit(130)
    except (ValueError, OSError) as exc:
        console.print(f"[red]Error:[/] {type(exc).__name__}: {exc}")
        raise SystemExit(1)
    except Exception as exc:
        console.print(f"[red]Unexpected error:[/] {type(exc).__name__}: {exc}")
        raise SystemExit(1)
