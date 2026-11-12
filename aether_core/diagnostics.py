"""Fixed, read-only diagnostics; no AI-generated command execution."""
import platform
import shutil
import subprocess
from .models import AuditReport, Finding, Risk

CHECKS = {"python": ["--version"], "git": ["--version"]}

def collect_diagnostics() -> AuditReport:
    findings = [
        Finding(title="Operating system", detail=f"{platform.system()} {platform.release()}",
                risk=Risk.INFO, evidence=[platform.platform()], confidence=1.0),
        Finding(title="Python runtime", detail=platform.python_version(),
                risk=Risk.INFO, evidence=["platform.python_version()"], confidence=1.0),
    ]
    for executable, args in CHECKS.items():
        path = shutil.which(executable)
        if not path:
            findings.append(Finding(title=f"{executable} not found",
                detail=f"{executable} is not available on PATH.", risk=Risk.LOW,
                evidence=[f"shutil.which({executable!r}) returned None"], confidence=1.0))
            continue
        try:
            result = subprocess.run([path, *args], capture_output=True, text=True,
                                    timeout=5, check=False, shell=False)
            output = (result.stdout + result.stderr).strip()[:500]
            findings.append(Finding(title=f"{executable} diagnostic",
                detail=output or f"Exit code {result.returncode}",
                risk=Risk.INFO if result.returncode == 0 else Risk.LOW,
                evidence=[f"Fixed command: {executable} {' '.join(args)}"],
                confidence=1.0))
        except (OSError, subprocess.TimeoutExpired) as exc:
            findings.append(Finding(title=f"{executable} diagnostic failed",
                detail=type(exc).__name__, risk=Risk.LOW,
                evidence=["Fixed diagnostic invocation"], confidence=1.0))
    return AuditReport(platform=platform.platform(), findings=findings,
                       summary="Collected fixed, read-only local diagnostics.")
