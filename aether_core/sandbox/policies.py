"""Static sandbox allowlist. Created by Edward Tejada."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SandboxCheck:
    image: str
    command: tuple[str, ...]


# Only fixed, read-only version checks are allowed. No caller-supplied arguments.
CHECKS: dict[str, SandboxCheck] = {
    "python-version": SandboxCheck("python:3.12-alpine", ("python", "--version")),
}
