import os
from pathlib import Path

from dotenv import load_dotenv

# Ensure .env is loaded and config paths resolve from repo root.
repo_root = Path(__file__).resolve().parents[2]
os.environ.setdefault("LLM_CONFIG_FILE", str(repo_root / "config" / "llm.config.ini"))
load_dotenv(dotenv_path=repo_root / ".env")
