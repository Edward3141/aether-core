"""Cross-platform capability catalog. Command strings are descriptive, never executable input.

The registry intentionally separates diagnostic command references from the typed
repair-action allow-list. No model-provided command or script is ever executed.
"""
from __future__ import annotations

import platform
import shutil
from dataclasses import asdict, dataclass
from typing import Literal

Role = Literal["SCOUT", "ANALYST", "FIXER", "AUDITOR", "EXECUTOR"]
PlatformName = Literal["linux", "macos", "windows", "other"]


@dataclass(frozen=True)
class Capability:
    capability_id: str
    category: str
    purpose: str
    roles: tuple[str, ...]
    platforms: tuple[str, ...]
    command_references: dict[str, tuple[str, ...]]
    access: str
    executable: bool = False
    implementation_status: str = "metadata_only"
    notes: str = ""


ALL_ROLES = ("SCOUT", "ANALYST", "FIXER", "AUDITOR", "EXECUTOR")
IMPLEMENTATION_STATUSES = {
    "implemented_read_only", "partial_read_only", "windows_only",
    "metadata_only", "proposal_contract_only", "not_implemented",
    "partial_one_action",
}
READ_ROLES = ("SCOUT", "ANALYST", "AUDITOR")
FIX_ROLES = ("FIXER", "AUDITOR", "EXECUTOR")

# References are for operator context and diagnostics planning only. They are
# never passed to a shell or subprocess. Actual repair remains separately typed.
_CATALOG = (
    Capability("system.identity", "system", "Identify OS, release, architecture and runtime",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows", "other"),
               {"linux": ("uname -a", "cat /etc/os-release"), "macos": ("sw_vers", "uname -a"),
                "windows": ("Get-ComputerInfo", "systeminfo")},
               "read_only", implementation_status="implemented_read_only", notes="Uses Python platform APIs."),
    Capability("process.inspect", "process", "Inspect running processes and resource use",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("ps aux", "top -b -n 1"), "macos": ("ps aux", "top -l 1"),
                "windows": ("Get-Process", "tasklist")},
               "read_only", implementation_status="partial_read_only"),
    Capability("service.inspect", "services", "Inspect service state without changing it",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("systemctl list-units --type=service", "service --status-all"),
                "macos": ("launchctl list",), "windows": ("Get-Service", "sc.exe query")},
               "read_only", implementation_status="windows_only", notes="Windows service inventory uses psutil; Linux/macOS service adapters are not yet implemented."),
    Capability("storage.inspect", "storage", "Inspect filesystems, volumes and free space",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("df -h", "lsblk"), "macos": ("df -h", "diskutil list"),
                "windows": ("Get-Volume", "Get-PSDrive")},
               "read_only", implementation_status="partial_read_only"),
    Capability("memory.inspect", "resources", "Inspect memory and virtual-memory pressure",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("free -h", "vmstat"), "macos": ("vm_stat",), 
                "windows": ("Get-CimInstance Win32_OperatingSystem",)},
               "read_only", implementation_status="implemented_read_only"),
    Capability("network.inspect", "network", "Inspect interfaces, routes and connections",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("ip address", "ip route", "ss -tulpen"),
                "macos": ("ifconfig", "netstat -rn", "scutil --dns"),
                "windows": ("Get-NetIPConfiguration", "Get-NetTCPConnection", "route print")},
               "read_only", implementation_status="partial_read_only"),
    Capability("logs.inspect", "logs", "Inspect system and application logs",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("journalctl -n 200", "dmesg --ctime"),
                "macos": ("log show --last 1h",),
                "windows": ("Get-WinEvent -LogName System -MaxEvents 200",)},
               "read_only", implementation_status="metadata_only", notes="No log collection adapter is implemented yet."),
    Capability("filesystem.inspect", "filesystem", "Inspect paths, permissions and symbolic links",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("stat", "findmnt"), "macos": ("stat", "mount"),
                "windows": ("Get-Acl", "Get-Item")},
               "read_only", implementation_status="metadata_only"),
    Capability("packages.inspect", "packages", "Inventory installed software and package managers",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("rpm -qa", "dpkg-query -W"), "macos": ("pkgutil --pkgs", "brew list"),
                "windows": ("winget list", "Get-Package")},
               "read_only", implementation_status="metadata_only", notes="Package inventory adapters are not implemented yet."),
    Capability("security.inspect", "security", "Review firewall, updates and security posture",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("nft list ruleset", "ufw status"), "macos": ("/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate",),
                "windows": ("Get-NetFirewallProfile", "Get-MpComputerStatus")},
               "read_only", implementation_status="metadata_only", notes="Security posture probes are not implemented yet."),
    Capability("configuration.plan", "configuration", "Prepare a typed, scoped configuration change",
               ("FIXER", "AUDITOR", "EXECUTOR"), ("linux", "macos", "windows", "other"),
               {"linux": (), "macos": (), "windows": (), "other": ()},
               "proposal_only", implementation_status="proposal_contract_only", notes="FIXER proposes; AUDITOR reviews; EXECUTOR needs per-action human approval."),
    Capability("backup.plan", "recovery", "Plan and verify a backup before an approved change",
               ("FIXER", "AUDITOR", "EXECUTOR"), ("linux", "macos", "windows", "other"),
               {"linux": (), "macos": (), "windows": (), "other": ()},
               "proposal_only", implementation_status="not_implemented", notes="Backup and rollback handlers are not implemented."),
    Capability("repair.execute", "repair", "Execute a versioned typed repair action after human approval",
               ("EXECUTOR",), ("linux", "macos"),
               {"linux": (), "macos": (), "windows": (), "other": ()},
               "human_approval_required", implementation_status="partial_one_action", notes="Only ensure_directory is currently registered in repair_actions.py."),
)


def detect_platform(system: str | None = None) -> PlatformName:
    name = (system or platform.system()).strip().lower()
    if name == "linux":
        return "linux"
    if name == "darwin":
        return "macos"
    if name in {"windows", "win32"}:
        return "windows"
    return "other"


class CapabilityRegistry:
    """Read-only registry of what each agent may inspect, analyze or propose."""

    def __init__(self, capabilities: tuple[Capability, ...] = _CATALOG):
        ids = [item.capability_id for item in capabilities]
        if len(ids) != len(set(ids)):
            raise ValueError("Capability IDs must be unique.")
        valid_platforms = {"linux", "macos", "windows", "other"}
        for item in capabilities:
            if item.executable:
                raise ValueError("Capability metadata must never enable command execution.")
            if item.implementation_status not in IMPLEMENTATION_STATUSES:
                raise ValueError(f"Capability {item.capability_id!r} has an invalid implementation status.")
            if not item.roles or not set(item.roles).issubset(ALL_ROLES):
                raise ValueError(f"Capability {item.capability_id!r} has invalid role scope.")
            if not item.platforms or not set(item.platforms).issubset(valid_platforms):
                raise ValueError(f"Capability {item.capability_id!r} has invalid platform scope.")
            if not set(item.command_references).issubset(valid_platforms):
                raise ValueError(f"Capability {item.capability_id!r} has invalid command platform.")
            if any(not isinstance(command, str) or not command.strip()
                   for commands in item.command_references.values() for command in commands):
                raise ValueError(f"Capability {item.capability_id!r} has an invalid command reference.")
        self._capabilities = {item.capability_id: item for item in capabilities}

    def list_for_role(self, role: str, system: str | None = None) -> list[dict]:
        normalized = role.upper()
        if normalized not in ALL_ROLES:
            raise ValueError(f"Unknown AETHER CORE role: {role}")
        target = detect_platform(system)
        results = []
        for item in self._capabilities.values():
            if normalized not in item.roles or target not in item.platforms:
                continue
            record = asdict(item)
            record["roles"] = list(item.roles)
            record["platforms"] = list(item.platforms)
            record["command_references"] = list(item.command_references.get(target, ()))
            record["available_command_binaries"] = [
                command.split()[0] for command in record["command_references"]
                if shutil.which(command.split()[0]) is not None
            ]
            # This checks PATH binaries only. Native PowerShell cmdlets are metadata
            # references, not PATH binaries, and are not reported as available here.
            # Availability is advisory only; no command is invoked.
            record["executable"] = False
            results.append(record)
        return results

    def get(self, capability_id: str) -> Capability:
        try:
            return self._capabilities[capability_id]
        except KeyError as exc:
            raise ValueError(f"Unknown capability: {capability_id}") from exc

    def summary(self, system: str | None = None) -> dict:
        target = detect_platform(system)
        return {
            "platform": target,
            "roles": {
                role: [item.capability_id for item in self._capabilities.values()
                       if role in item.roles and target in item.platforms]
                for role in ALL_ROLES
            },
            "catalog_size": len(self._capabilities),
            "implementation_status": {item.capability_id: item.implementation_status for item in self._capabilities.values()},
            "implemented_read_only_count": sum(item.implementation_status == "implemented_read_only" for item in self._capabilities.values()),
            "command_execution_enabled": False,
            "repair_execution_source": "typed allow-list only; individual human approval required",
        }
