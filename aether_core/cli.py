"""Command line interface. Created by Edward Tejada."""
import argparse
import asyncio
from rich.console import Console
from rich.panel import Panel
from . import __version__
from .config import database_path
from .database import Database
from .diagnostics import collect_diagnostics
from .orchestrator import Orchestrator

console = Console()

def build_parser():
    parser = argparse.ArgumentParser(prog="aether-core",
        description="AETHER CORE — human-supervised system diagnostics")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("doctor", help="Run fixed read-only local diagnostics")
    sub.add_parser("audit", help="Collect evidence and analyze it with configured AI")
    ask = sub.add_parser("ask", help="Ask the configured AI model")
    ask.add_argument("message", nargs="+")
    return parser

async def run(args):
    db = Database(database_path())
    if args.command == "doctor":
        report = collect_diagnostics()
        console.print(Panel("AETHER CORE diagnostic report"))
        for finding in report.findings:
            console.print(f"[bold]{finding.risk.value}[/] {finding.title}: {finding.detail}")
        return 0
    if args.command == "audit":
        report, analysis = await Orchestrator(db).audit()
        console.print(f"[green]Audit saved:[/] {report.id}")
        console.print(Panel(analysis, title="ANALYST"))
        return 0
    if args.command == "ask":
        from .providers import ask_model
        answer = await ask_model("You are AETHER CORE, a careful assistant.", " ".join(args.message))
        console.print(answer)
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
    except Exception as exc:
        console.print(f"[red]Error:[/] {type(exc).__name__}: {exc}")
        raise SystemExit(1)
