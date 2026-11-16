"""Environment-backed configuration. Created by Edward Tejada."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ModelSettings:
    model: str
    api_base: str | None = None
    api_key: str | None = None


def database_path() -> Path:
    path = Path(os.getenv("AETHER_DATABASE", "~/.aether-core/aether.db")).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def model_settings(agent: str | None = None) -> ModelSettings:
    """Resolve per-agent settings, falling back to the shared provider settings."""
    prefix = f"AETHER_{agent.upper()}_" if agent else "AETHER_"
    model = os.getenv(f"{prefix}MODEL") or os.getenv("AETHER_MODEL", "ollama/qwen2.5:7b")
    api_base = os.getenv(f"{prefix}API_BASE") or os.getenv("AETHER_API_BASE") or None
    api_key = os.getenv(f"{prefix}API_KEY") or os.getenv("AETHER_API_KEY") or None
    return ModelSettings(model=model, api_base=api_base, api_key=api_key)


# Backwards-compatible aliases for integrations using the original configuration.
_DEFAULT_SETTINGS = model_settings()
MODEL = _DEFAULT_SETTINGS.model
API_BASE = _DEFAULT_SETTINGS.api_base
API_KEY = _DEFAULT_SETTINGS.api_key
