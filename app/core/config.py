import os

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=True)

    PROJECT_NAME: str = "ForkFolio"
    PROJECT_DESCRIPTION: str = "Recipe management API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # API tokens
    OPEN_ROUTER_API_KEY: str = os.environ.get("OPEN_ROUTER_API_KEY", "")
    HUGGINGFACE_API_TOKEN: str = os.environ.get("HUGGINGFACE_API_TOKEN", "")
    SUPABASE_PASSWORD: str = os.environ.get("SUPABASE_PASSWORD", "")
    SUPABASE_API_KEY: str = os.environ.get("SUPABASE_API_KEY", "")
    SUPABASE_ACCESS_TOKEN: str = os.environ.get("SUPABASE_ACCESS_TOKEN", "")
    SUPABASE_PROJECT_ID: str = os.environ.get("SUPABASE_PROJECT_ID", "")


settings = Settings()
