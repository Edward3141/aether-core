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
    notes: str = ""


ALL_ROLES = ("SCOUT", "ANALYST", "FIXER", "AUDITOR", "EXECUTOR")
READ_ROLES = ("SCOUT", "ANALYST", "AUDITOR")
FIX_ROLES = ("FIXER", "AUDITOR", "EXECUTOR")

# References are for operator context and diagnostics planning only. They are
# never passed to a shell or subprocess. Actual repair remains separately typed.
_CATALOG = (
    Capability("system.identity", "system", "Identify OS, release, architecture and runtime",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows", "other"),
               {"linux": ("uname -a", "cat /etc/os-release"), "macos": ("sw_vers", "uname -a"),
                "windows": ("Get-ComputerInfo", "systeminfo")},
               "read_only", notes="Prefer Python platform APIs where possible."),
    Capability("process.inspect", "process", "Inspect running processes and resource use",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("ps aux", "top -b -n 1"), "macos": ("ps aux", "top -l 1"),
                "windows": ("Get-Process", "tasklist")},
               "read_only"),
    Capability("service.inspect", "services", "Inspect service state without changing it",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("systemctl list-units --type=service", "service --status-all"),
                "macos": ("launchctl list",), "windows": ("Get-Service", "sc.exe query")},
               "read_only", notes="Service managers and service scopes differ by OS."),
    Capability("storage.inspect", "storage", "Inspect filesystems, volumes and free space",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("df -h", "lsblk"), "macos": ("df -h", "diskutil list"),
                "windows": ("Get-Volume", "Get-PSDrive")},
               "read_only"),
    Capability("memory.inspect", "resources", "Inspect memory and virtual-memory pressure",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("free -h", "vmstat"), "macos": ("vm_stat",), 
                "windows": ("Get-CimInstance Win32_OperatingSystem",)},
               "read_only"),
    Capability("network.inspect", "network", "Inspect interfaces, routes and connections",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("ip address", "ip route", "ss -tulpen"),
                "macos": ("ifconfig", "netstat -rn", "scutil --dns"),
                "windows": ("Get-NetIPConfiguration", "Get-NetTCPConnection", "route print")},
               "read_only"),
    Capability("logs.inspect", "logs", "Inspect system and application logs",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("journalctl -n 200", "dmesg --ctime"),
                "macos": ("log show --last 1h",),
                "windows": ("Get-WinEvent -LogName System -MaxEvents 200",)},
               "read_only", notes="Log access may require elevated privileges."),
    Capability("filesystem.inspect", "filesystem", "Inspect paths, permissions and symbolic links",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("stat", "findmnt"), "macos": ("stat", "mount"),
                "windows": ("Get-Acl", "Get-Item")},
               "read_only"),
    Capability("packages.inspect", "packages", "Inventory installed software and package managers",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("rpm -qa", "dpkg-query -W"), "macos": ("pkgutil --pkgs", "brew list"),
                "windows": ("winget list", "Get-Package")},
               "read_only", notes="Package managers vary by distribution and installation."),
    Capability("security.inspect", "security", "Review firewall, updates and security posture",
               READ_ROLES + ("FIXER", "EXECUTOR"), ("linux", "macos", "windows"),
               {"linux": ("nft list ruleset", "ufw status"), "macos": ("/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate",),
                "windows": ("Get-NetFirewallProfile", "Get-MpComputerStatus")},
               "read_only", notes="Some checks are unavailable or restricted on managed devices."),
    Capability("configuration.plan", "configuration", "Prepare a typed, scoped configuration change",
               ("FIXER", "AUDITOR", "EXECUTOR"), ("linux", "macos", "windows", "other"),
               {"linux": (), "macos": (), "windows": (), "other": ()},
               "proposal_only", notes="FIXER proposes; AUDITOR reviews; EJECUTOR needs per-action human approval."),
    Capability("backup.plan", "recovery", "Plan and verify a backup before an approved change",
               ("FIXER", "AUDITOR", "EXECUTOR"), ("linux", "macos", "windows", "other"),
               {"linux": (), "macos": (), "windows": (), "other": ()},
               "proposal_only", notes="Backup and rollback handlers are not implied by this catalog."),
    Capability("repair.execute", "repair", "Execute a versioned typed repair action after human approval",
               ("EXECUTOR",), ("linux", "macos", "windows", "other"),
               {"linux": (), "macos": (), "windows": (), "other": ()},
               "human_approval_required", notes="Only actions registered in repair_actions.py can execute."),
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
            record["available_commands"] = [
                command.split()[0] for command in record["command_references"]
                if shutil.which(command.split()[0]) is not None
            ]
            # Availability is advisory only; no command is invoked.
            record["executable"] = False
            results.append(record)
        return results

    def get(self, capability_id: str) -> Capability:
        try:
            return self._capabilities[capability_id]
        except KeyError as exc:
            raise ValueError(f"Unknown capability: {capability_id}") from exc

    def summary(self) -> dict:
        return {
            "platform": detect_platform(),
            "roles": {
                role: [item.capability_id for item in self._capabilities.values()
                       if role in item.roles]
                for role in ALL_ROLES
            },
            "catalog_size": len(self._capabilities),
            "command_execution_enabled": False,
            "repair_execution_source": "typed allow-list only; individual human approval required",
        }
