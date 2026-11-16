"""Read-only cross-platform system snapshot using the Python standard library."""
from __future__ import annotations

import os
import platform
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class SystemSnapshot:
    captured_at: float
    hostname: str
    platform: str
    python_version: str
    cpu_count: int
    load_average: tuple[float, float, float] | None
    memory_total_bytes: int | None
    memory_available_bytes: int | None
    disk_total_bytes: int
    disk_free_bytes: int

    def to_dict(self) -> dict:
        return asdict(self)


def _memory() -> tuple[int | None, int | None]:
    path = Path("/proc/meminfo")
    if not path.is_file():
        return None, None
    values = {}
    try:
        for line in path.read_text(encoding="ascii").splitlines():
            key, raw = line.split(":", 1)
            if key in {"MemTotal", "MemAvailable"}:
                values[key] = int(raw.strip().split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        return None, None
    return values.get("MemTotal"), values.get("MemAvailable")


def collect_snapshot(path: str | os.PathLike[str] = ".") -> SystemSnapshot:
    """Collect resource metadata without changing system state."""
    try:
        load = os.getloadavg()
    except (AttributeError, OSError):
        load = None
    total, available = _memory()
    disk = shutil.disk_usage(path)
    return SystemSnapshot(
        time.time(),
        platform.node(),
        platform.platform(),
        platform.python_version(),
        os.cpu_count() or 1,
        load,
        total,
        available,
        disk.total,
        disk.free,
    )
