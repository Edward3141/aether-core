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

    action_plan = sub.add_parser("action-plan", help="Create a reviewable plan for one allow-listed local action")
    action_plan.add_argument("action", choices=("ensure_directory",))
    action_plan.add_argument("--params", required=True, help="JSON parameters for the exact action")
    action_plan.add_argument("--root", required=True, help="Existing directory that bounds the change")
    action_plan.add_argument("--minutes", type=int, default=10)

    execute_action = sub.add_parser("execute-action", help="Human-authorize and execute one exact action plan")
    execute_action.add_argument("plan_id")
    execute_action.add_argument("--hash", required=True, dest="plan_hash")
    execute_action.add_argument("--by", required=True, dest="approved_by")
    execute_action.add_argument("--root", required=True, help="Same target root shown in the plan")

    for decision in ("approve", "reject"):
        action = sub.add_parser(decision, help=f"Record a human {decision} decision for a proposal")
        action.add_argument("proposal_id")
        action.add_argument("--hash", dest="proposal_hash", required=True)
        action.add_argument("--by", dest="approved_by", required=True)
        action.add_argument("--minutes", type=int, default=15)

    return parser


async def run(args):
    db = Database(database_path())
    if args.command == "action-plan":
        from pathlib import Path
        from .repair_actions import create_action_plan
        try:
            parameters = json.loads(args.params)
        except json.JSONDecodeError as exc:
            raise ValueError("--params must be a JSON object") from exc
        if not isinstance(parameters, dict):
            raise ValueError("--params must be a JSON object")
        plan = create_action_plan(db, args.action, parameters, Path(args.root), args.minutes)
        console.print(Panel(Text(json.dumps(plan, ensure_ascii=False, indent=2)),
                            title="AETHER CORE — Action plan; NOT YET AUTHORIZED"))
        console.print("[yellow]No change was made. Review every field before authorizing.[/]")
        return 0

    if args.command == "execute-action":
        from pathlib import Path
        from .repair_actions import approve_and_execute
        plan = db.get_action_plan(args.plan_id)
        if plan is None:
            raise ValueError("Action plan not found.")
        if plan["digest"] != args.plan_hash:
            raise ValueError("Action plan hash mismatch.")
        console.print(Panel(Text(json.dumps({
            "plan_id": plan["id"], "action": plan["action_id"],
            "parameters": json.loads(plan["params_json"]),
            "target_root": plan["target_root"], "sha256": plan["digest"],
            "status": plan["status"], "expires_at": plan["expires_at"],
        }, ensure_ascii=False, indent=2)), title="EXACT ACTION REQUIRING HUMAN APPROVAL"))
        expected = f"AUTHORIZE {plan['id']} {plan['digest']}"
        typed = console.input(f"Type exactly '{expected}' to authorize this one action: ")
        if typed != expected:
            console.print("[yellow]Cancelled. No action was executed.[/]")
            return 2
        result = approve_and_execute(db, plan["id"], args.plan_hash,
                                     args.approved_by, Path(args.root))
        console.print(Panel(Text(result.detail), title=f"Execution: {result.status}"))
        return 0

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
        if review.get("action_plans"):
            console.print(Panel(Text(json.dumps(review["action_plans"], ensure_ascii=False, indent=2)),
                                title="Actions awaiting individual human authorization"))
        if review.get("action_plan_errors"):
            console.print(Panel(Text(json.dumps(review["action_plan_errors"], ensure_ascii=False, indent=2)),
                                title="Actions rejected by local allow-list"))
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
        if review.get("action_plans"):
            console.print(Panel(Text(json.dumps(review["action_plans"], ensure_ascii=False, indent=2)),
                                title="Actions awaiting individual human authorization"))
        if review.get("action_plan_errors"):
            console.print(Panel(Text(json.dumps(review["action_plan_errors"], ensure_ascii=False, indent=2)),
                                title="Actions rejected by local allow-list"))
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
