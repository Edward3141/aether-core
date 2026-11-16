"""Command line interface. Created by Edward Tejada."""
import argparse
import json
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
from .extended.reports import report_json, report_markdown

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
    sub.add_parser("audit", help="Run all four agents and update integrated intelligence services")
    sub.add_parser("status", help="Show integrated system snapshot, agent metrics and knowledge ledger")
    skills = sub.add_parser("skills", help="List the built-in, policy-controlled skills")
    skills.add_argument("--agent", choices=("SCOUT", "ANALYST", "FIXER", "AUDITOR"),
                        help="Show only one specialist's 50 skills")

    skill = sub.add_parser("skill", help="Execute one registered read-only skill")
    skill.add_argument("name", help="Exact registered skill name")
    skill.add_argument("--input", default="{}", help="JSON object with skill arguments")

    report = sub.add_parser("report", help="Export an AETHER CORE intelligence report")
    report.add_argument("--format", choices=("json", "markdown"), default="markdown")
    report.add_argument("--output", help="Write report to this path; otherwise print it")

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
        console.print(Panel(Text(result.output or "(no output)"),
                            title=f"Docker sandbox: {result.check_id} — exit {result.exit_code}"))
        return result.exit_code

    if args.command == "doctor":
        report = collect_diagnostics()
        console.print(Panel(Text("AETHER CORE diagnostic report")))
        for finding in report.findings:
            console.print(Text(f"{finding.risk.value} {finding.title}: {finding.detail}"))
        return 0

    if args.command in {"status", "report", "skills", "skill"}:
        workflow = Orchestrator(db)
        if args.command == "skills":
            catalog = workflow.skills.for_agent(args.agent) if args.agent else workflow.skills.list()
            console.print(Text(json.dumps(catalog, ensure_ascii=False, indent=2)))
            return 0
        if args.command == "skill":
            try:
                skill_args = json.loads(args.input)
            except json.JSONDecodeError as exc:
                raise ValueError("skill --input must be valid JSON") from exc
            result = workflow.skills.execute(
                args.name, caller="HUMAN", arguments=skill_args
            )
            console.print(Text(json.dumps(result, ensure_ascii=False, indent=2, default=str)))
            return 0
        payload = workflow.intelligence_report()
        rendered = report_json(payload) if args.command == "report" and args.format == "json" else (
            report_markdown(payload) if args.command == "report" else report_markdown(payload))
        if args.command == "report" and args.output:
            from pathlib import Path
            Path(args.output).write_text(rendered, encoding="utf-8")
            console.print(f"Report written to {args.output}")
        else:
            console.print(Text(rendered))
        return 0

    if args.command == "audit":
        workflow = Orchestrator(db)
        report, analysis = await workflow.audit()
        proposal, review = await workflow.plan(analysis)
        console.print(f"[green]Audit saved:[/] {report.id}")
        console.print(Panel(Text(report.summary), title="SCOUT"))
        console.print(Panel(Text(analysis), title="ANALYST"))
        proposal_text = (f"{proposal.title}\nID: {proposal.id}\n"
            f"SHA-256: {proposal.content_hash()}\nRisk: {proposal.risk.value}\n\n"
            + "\n".join(f"- {step}" for step in proposal.steps))
        console.print(Panel(Text(proposal_text), title="FIXER — Proposal only"))
        console.print(Panel(Text(review["advisory"]), title="AUDITOR — Advisory review"))
        console.print("[yellow]No repair was executed. Human review is required.[/]")
        console.print("[cyan]Integrated intelligence metrics and evidence memory updated.[/]")
        return 0

    if args.command == "plan":
        proposal, review = await Orchestrator(db).plan(" ".join(args.analysis))
        proposal_text = (f"{proposal.title}\nID: {proposal.id}\n"
            f"SHA-256: {proposal.content_hash()}\nRisk: {proposal.risk.value}\n\n"
            + "\n".join(f"- {step}" for step in proposal.steps)
            + "\n\nThis is a proposal only; no action was executed.")
        console.print(Panel(Text(proposal_text), title="FIXER — Remediation proposal"))
        console.print(Text(review["message"]))
        console.print(Text(review["advisory"]))
        return 0

    if args.command == "ask":
        from .providers import ask_model
        answer = await ask_model("You are AETHER CORE, a careful assistant.", " ".join(args.message))
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
        review_text = (f"{proposal.title}\nID: {proposal.id}\n"
            f"SHA-256: {proposal.content_hash()}\nDecision: {decision.upper()}\n"
            "This records a human decision only. It does not execute repairs.")
        console.print(Panel(Text(review_text), title="AETHER CORE — Human review"))
        expected = f"{decision.upper()} {proposal.id}"
        typed = console.input(f"Type exactly '{expected}' to continue: ")
        if typed != expected:
            console.print("[yellow]Decision cancelled; no record was saved.[/]")
            return 2
        now = datetime.now(UTC)
        record = ApprovalRecord(proposal_id=proposal.id, proposal_hash=proposal.content_hash(),
            decision=decision, approved_by=args.approved_by, created_at=now,
            expires_at=now + timedelta(minutes=args.minutes))
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
