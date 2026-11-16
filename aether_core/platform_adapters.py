"""Fixed, bounded, read-only native platform probes.

Only application-owned argument vectors are invoked. No shell, model text, user
arguments, network access, or unbounded log contents are accepted.
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from .models import Finding, Risk

_TIMEOUT_SECONDS = 5
_MAX_OUTPUT = 64_000
_SECRET_PATTERNS = (
    re.compile(r"(?i)(password|passwd|token|secret|api[_-]?key)(\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)(\S+)"),
    re.compile(r"(?i)(https?://)([^/@\s]+:[^/@\s]+@)"),
)


def _redact(value: str) -> str:
    value = value[:_MAX_OUTPUT]
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub(r"\1\2[REDACTED]", value)
    return value


def _run_fixed(argv: tuple[str, ...]) -> tuple[int, str] | None:
    """Run one fixed application-owned probe with a bounded environment and timeout."""
    if not argv:
        return None
    executable = shutil.which(argv[0])
    if executable is None:
        return None
    try:
        result = subprocess.run(
            [executable, *argv[1:]],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_TIMEOUT_SECONDS,
            check=False,
            shell=False,
            close_fds=True,
            env={"PATH": os.defpath, "LC_ALL": "C", "LANG": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.returncode, _redact(result.stdout + "\n" + result.stderr)


def _finding(title: str, detail: str, evidence: list[str], risk: Risk = Risk.INFO) -> Finding:
    return Finding(title=title, detail=detail[:4000], evidence=evidence[:30],
                   risk=risk, confidence=1.0)


def _probe_count(title: str, argv: tuple[str, ...], evidence: str,
                 risk_on_output: Risk = Risk.INFO) -> Finding:
    result = _run_fixed(argv)
    if result is None:
        return _finding(title, "Probe unavailable: required native tool is absent, timed out, or failed to start.",
                        [evidence], Risk.LOW)
    code, output = result
    if code != 0:
        return _finding(title, f"Probe returned exit code {code}; details intentionally omitted.",
                        [evidence], Risk.LOW)
    lines = [line for line in output.splitlines() if line.strip()]
    return _finding(title, f"Probe completed; {len(lines)} non-empty records observed. Raw output is not retained.",
                    [evidence], risk_on_output)


def collect_native_findings() -> list[Finding]:
    """Collect service, package, log and firewall metadata for the current OS."""
    system = platform.system()
    findings: list[Finding] = []

    if system == "Linux":
        findings.append(_probe_count(
            "Linux service health",
            ("systemctl", "list-units", "--type=service", "--state=failed", "--no-legend", "--no-pager"),
            "fixed systemctl failed-service inventory",
            Risk.MEDIUM,
        ))
        package_probes = (
            ("dpkg-query", "-W", "-f=${binary:Package}\n"),
            ("rpm", "-qa", "--qf", "%{NAME}\n"),
        )
        package = next((_run_fixed(argv) for argv in package_probes if shutil.which(argv[0])), None)
        if package is None:
            findings.append(_finding("Package inventory", "No supported dpkg/rpm inventory tool is available.",
                                     ["fixed dpkg-query/rpm inventory"], Risk.LOW))
        elif package[0] == 0:
            findings.append(_finding("Package inventory",
                                     f"{len([x for x in package[1].splitlines() if x.strip()])} installed package records observed.",
                                     ["fixed dpkg-query/rpm inventory"]))
        else:
            findings.append(_finding("Package inventory", "Package inventory probe failed; output omitted.",
                                     ["fixed dpkg-query/rpm inventory"], Risk.LOW))
        findings.append(_probe_count(
            "System error log summary",
            ("journalctl", "-p", "err", "-n", "100", "--no-pager", "--output=cat"),
            "fixed journalctl error-level sample (maximum 100 records)",
            Risk.MEDIUM,
        ))
        firewall = _run_fixed(("ufw", "status"))
        if firewall is None:
            firewall = _run_fixed(("firewall-cmd", "--state"))
        if firewall is None:
            findings.append(_finding("Firewall posture", "No supported ufw/firewalld status tool is available.",
                                     ["fixed firewall status probes"], Risk.LOW))
        else:
            code, output = firewall
            state = "active" if code == 0 and ("status: active" in output.lower() or output.strip().lower() == "running") else "inactive_or_unknown"
            findings.append(_finding("Firewall posture", f"Firewall probe state: {state}.",
                                     ["fixed ufw/firewall-cmd status probe"],
                                     Risk.INFO if state == "active" else Risk.MEDIUM))
    elif system == "Darwin":
        findings.append(_probe_count(
            "macOS service inventory", ("launchctl", "list"),
            "fixed launchctl list probe", Risk.MEDIUM))
        package = _run_fixed(("pkgutil", "--pkgs"))
        if package is None:
            findings.append(_finding("Package inventory", "pkgutil is unavailable.",
                                     ["fixed pkgutil package inventory"], Risk.LOW))
        elif package[0] == 0:
            findings.append(_finding("Package inventory",
                                     f"{len([x for x in package[1].splitlines() if x.strip()])} package receipt records observed.",
                                     ["fixed pkgutil package inventory"]))
        else:
            findings.append(_finding("Package inventory", "Package inventory probe failed; output omitted.",
                                     ["fixed pkgutil package inventory"], Risk.LOW))
        findings.append(_probe_count(
            "System error log summary",
            ("log", "show", "--last", "1h", "--style", "compact",
             "--predicate", "messageType == error"),
            "fixed macOS unified-log error sample limited to one hour", Risk.MEDIUM))
        firewall = _run_fixed(("/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"))
        if firewall is None:
            findings.append(_finding("Firewall posture", "macOS application firewall status is unavailable.",
                                     ["fixed socketfilterfw global-state probe"], Risk.LOW))
        else:
            code, output = firewall
            enabled = code == 0 and "enabled" in output.lower()
            findings.append(_finding("Firewall posture",
                                     "Application firewall reports enabled." if enabled else "Application firewall is disabled or state is unknown.",
                                     ["fixed socketfilterfw global-state probe"],
                                     Risk.INFO if enabled else Risk.MEDIUM))
    elif system == "Windows":
        findings.append(_finding(
            "Windows native services",
            "Windows service inventory is collected by the psutil adapter.",
            ["psutil.win_service_iter"], Risk.INFO))
        findings.append(_finding(
            "Package inventory",
            "No stable built-in package inventory adapter is enabled; optional package managers are not invoked.",
            ["Windows package inventory adapter not implemented"], Risk.LOW))
        findings.append(_finding(
            "System error log summary",
            "Windows event-log collection is not enabled in this release.",
            ["Windows event-log adapter not implemented"], Risk.LOW))
        firewall = _run_fixed(("netsh", "advfirewall", "show", "allprofiles", "state"))
        if firewall is None:
            findings.append(_finding("Firewall posture", "Windows firewall status is unavailable.",
                                     ["fixed netsh advfirewall state probe"], Risk.LOW))
        else:
            code, output = firewall
            enabled = code == 0 and "on" in output.lower()
            findings.append(_finding("Firewall posture",
                                     "At least one firewall profile reports ON." if enabled else "Firewall state is OFF or unknown.",
                                     ["fixed netsh advfirewall state probe"],
                                     Risk.INFO if enabled else Risk.MEDIUM))
    else:
        findings.append(_finding("Native platform probes",
                                 f"No native adapter is implemented for {system}.",
                                 ["platform.system"], Risk.LOW))

    home = Path.home()
    try:
        metadata = home.lstat()
        is_link = home.is_symlink()
        writable = os.access(home, os.W_OK)
        findings.append(_finding(
            "Home directory permissions",
            f"Home path exists; symlink={is_link}; owner-write-access={writable}; mode={metadata.st_mode & 0o777:o}.",
            ["Path.home", "Path.lstat", "os.access"],
            Risk.MEDIUM if is_link else Risk.INFO,
        ))
    except OSError as exc:
        findings.append(_finding("Home directory permissions", f"Inspection unavailable: {type(exc).__name__}.",
                                 ["Path.home", "Path.lstat"], Risk.LOW))
    return findings
