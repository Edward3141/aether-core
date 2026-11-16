"""Read-only cross-platform system snapshot using psutil and Python APIs."""
from __future__ import annotations

import os
import platform
import psutil
import shutil
import time
from dataclasses import asdict, dataclass


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
    process_count: int
    network_interfaces_up: int

    def to_dict(self) -> dict:
        return asdict(self)


def _memory() -> tuple[int | None, int | None]:
    """Return cross-platform physical RAM totals from psutil."""
    try:
        memory = psutil.virtual_memory()
    except (psutil.Error, OSError):
        return None, None
    return int(memory.total), int(memory.available)


def collect_snapshot(path: str | os.PathLike[str] = ".") -> SystemSnapshot:
    """Collect resource metadata without changing system state."""
    try:
        load = os.getloadavg()
    except (AttributeError, OSError):
        load = None
    total, available = _memory()
    disk = shutil.disk_usage(path)
    try:
        process_count = len(psutil.pids())
    except (psutil.Error, OSError):
        process_count = 0
    try:
        network_interfaces_up = sum(1 for item in psutil.net_if_stats().values() if item.isup)
    except (psutil.Error, OSError):
        network_interfaces_up = 0
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
        process_count,
        network_interfaces_up,
    )
