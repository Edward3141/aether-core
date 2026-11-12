"""Environment-backed configuration. Created by Edward Tejada."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def database_path() -> Path:
    path = Path(os.getenv("AETHER_DATABASE", "~/.aether-core/aether.db")).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

MODEL = os.getenv("AETHER_MODEL", "ollama/qwen2.5:7b")
API_BASE = os.getenv("AETHER_API_BASE") or None
API_KEY = os.getenv("AETHER_API_KEY") or None
