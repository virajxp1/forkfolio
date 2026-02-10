import os
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    _repo_root = Path(__file__).resolve().parents[2]
    model_config = ConfigDict(
        env_file=str(_repo_root / ".env"),
        case_sensitive=True,
    )

    PROJECT_NAME: str = "ForkFolio"
    PROJECT_DESCRIPTION: str = "Recipe management API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # API tokens
    OPEN_ROUTER_API_KEY: str = os.environ.get("OPEN_ROUTER_API_KEY", "")
    SUPABASE_PASSWORD: str = os.environ.get("SUPABASE_PASSWORD", "")


settings = Settings()
