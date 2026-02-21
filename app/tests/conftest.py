import os
from pathlib import Path

from dotenv import load_dotenv

# Ensure .env is loaded and config paths resolve from repo root.
repo_root = Path(__file__).resolve().parents[2]
os.environ.setdefault("APP_CONFIG_FILE", str(repo_root / "config" / "app.config.ini"))

# Load repo .env, then allow a local .context/.env to override for secrets.
load_dotenv(dotenv_path=repo_root / ".env")
load_dotenv(dotenv_path=repo_root / ".context" / ".env", override=True)
