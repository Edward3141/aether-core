"""Real, bounded, read-only cross-platform host inspection using psutil.

This module never invokes a shell or executes model-provided commands. Unsupported
platform-specific measurements are reported as unavailable, not guessed.
"""
from __future__ import annotations

import os
import platform
import time

import psutil

from .models import Finding, Risk


def _finding(title: str, detail: str, evidence: list[str], risk: Risk = Risk.INFO) -> Finding:
    return Finding(title=title, detail=detail[:4000], evidence=evidence[:30],
                   risk=risk, confidence=1.0)


def collect_platform_findings() -> list[Finding]:
    """Collect bounded host, process, memory, storage and network metadata."""
    findings: list[Finding] = []
    findings.append(_finding(
        "System identity",
        f"{platform.system()} {platform.release()} ({platform.machine()}); "
        f"Python {platform.python_version()}",
        ["platform.system", "platform.release", "platform.machine",
         "platform.python_version"],
    ))

    try:
        processes = list(psutil.process_iter(attrs=["pid"], ad_value=None))
        findings.append(_finding(
            "Process inventory",
            f"{len(processes)} processes were visible to the current user.",
            ["psutil.process_iter(attrs=['pid'])"],
        ))
    except (psutil.Error, OSError) as exc:
        findings.append(_finding(
            "Process inventory unavailable", type(exc).__name__,
            ["psutil.process_iter"], Risk.LOW,
        ))

    try:
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        findings.append(_finding(
            "Memory usage",
            f"RAM: {memory.percent:.1f}% used; {memory.available} bytes available "
            f"of {memory.total}. Swap: {swap.percent:.1f}% used.",
            ["psutil.virtual_memory", "psutil.swap_memory"],
            Risk.MEDIUM if memory.percent >= 95 else Risk.INFO,
        ))
    except (psutil.Error, OSError) as exc:
        findings.append(_finding(
            "Memory inspection unavailable", type(exc).__name__,
            ["psutil.virtual_memory", "psutil.swap_memory"], Risk.LOW,
        ))

    try:
        partitions = psutil.disk_partitions(all=False)
        checked = 0
        low_space: list[str] = []
        for partition in partitions[:32]:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
            except (psutil.Error, OSError, PermissionError):
                continue
            checked += 1
            if usage.percent >= 95:
                low_space.append(f"{partition.mountpoint} ({usage.percent:.1f}% used)")
        detail = f"Checked {checked} mounted filesystems."
        if low_space:
            detail += " Low free space: " + ", ".join(low_space[:8])
        findings.append(_finding(
            "Storage inventory", detail,
            ["psutil.disk_partitions", "psutil.disk_usage"],
            Risk.HIGH if low_space else Risk.INFO,
        ))
    except (psutil.Error, OSError) as exc:
        findings.append(_finding(
            "Storage inspection unavailable", type(exc).__name__,
            ["psutil.disk_partitions", "psutil.disk_usage"], Risk.LOW,
        ))

    try:
        interfaces = psutil.net_if_stats()
        active = sorted(name for name, stats in interfaces.items() if stats.isup)
        findings.append(_finding(
            "Network interfaces",
            f"{len(interfaces)} interfaces detected; {len(active)} reported up. "
            f"Names: {', '.join(active[:12]) or 'none'}. IP addresses and traffic "
            "contents are intentionally not collected.",
            ["psutil.net_if_stats"],
        ))
    except (psutil.Error, OSError) as exc:
        findings.append(_finding(
            "Network inspection unavailable", type(exc).__name__,
            ["psutil.net_if_stats"], Risk.LOW,
        ))

    try:
        uptime = max(0, int(time.time() - psutil.boot_time()))
        findings.append(_finding(
            "System uptime", f"{uptime} seconds since reported boot time.",
            ["psutil.boot_time"],
        ))
    except (psutil.Error, OSError, ValueError) as exc:
        findings.append(_finding(
            "System uptime unavailable", type(exc).__name__,
            ["psutil.boot_time"], Risk.LOW,
        ))

    # psutil exposes Windows service enumeration. Linux/macOS service managers
    # differ and are not queried with shell commands in this read-only adapter.
    if os.name == "nt" and hasattr(psutil, "win_service_iter"):
        try:
            services = list(psutil.win_service_iter())
            running = 0
            for service in services:
                try:
                    if service.status() == "running":
                        running += 1
                except (psutil.Error, OSError):
                    continue
            findings.append(_finding(
                "Windows service inventory",
                f"{len(services)} services enumerated; {running} reported running.",
                ["psutil.win_service_iter", "psutil.WinService.status"],
            ))
        except (psutil.Error, OSError) as exc:
            findings.append(_finding(
                "Windows service inspection unavailable", type(exc).__name__,
                ["psutil.win_service_iter"], Risk.LOW,
            ))
    else:
        findings.append(_finding(
            "Service inventory unavailable",
            "No native service-manager adapter is enabled for this platform yet; "
            "service health is not inferred.",
            ["platform-specific service adapter not implemented"],
            Risk.LOW,
        ))

    return findings
