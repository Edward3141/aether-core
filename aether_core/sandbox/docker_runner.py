"""Ephemeral, network-isolated Docker runner. Created by Edward Tejada."""
import shutil
import subprocess
from dataclasses import dataclass

from .policies import CHECKS


@dataclass(frozen=True)
class SandboxResult:
    check_id: str
    exit_code: int
    output: str


class SandboxUnavailable(RuntimeError):
    """Raised when Docker or the preloaded sandbox image is unavailable."""


def run_check(check_id: str, timeout_seconds: int = 15) -> SandboxResult:
    """Run one fixed allow-listed diagnostic without mounting host files."""
    if check_id not in CHECKS:
        raise ValueError("Sandbox check is not allow-listed.")
    if not 1 <= timeout_seconds <= 60:
        raise ValueError("Sandbox timeout must be between 1 and 60 seconds.")

    docker = shutil.which("docker")
    if docker is None:
        raise SandboxUnavailable("Docker CLI is not installed or not on PATH.")

    check = CHECKS[check_id]
    command = [
        docker, "run", "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--pids-limit=32",
        "--memory=128m",
        "--cpus=0.5",
        "--user=65532:65532",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        check.image,
        *check.command,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SandboxUnavailable("Sandbox diagnostic timed out.") from exc
    except OSError as exc:
        raise SandboxUnavailable("Docker could not be started.") from exc

    output = (result.stdout + result.stderr).strip()[:2000]
    if result.returncode != 0 and "No such image" in output:
        raise SandboxUnavailable(
            f"Required image {check.image} is not preloaded; pull it manually before retrying."
        )
    return SandboxResult(check_id, result.returncode, output)
