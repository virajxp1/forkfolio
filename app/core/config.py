import os

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=True)

    PROJECT_NAME: str = "ForkFolio"
    PROJECT_DESCRIPTION: str = "Portfolio management API for tracking investments"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # API tokens
    HUGGINGFACE_API_TOKEN: str = os.environ.get("HUGGINGFACE_API_TOKEN", "")
    OPEN_ROUTER_API_KEY: str = os.environ.get("OPEN_ROUTER_API_KEY", "")

    # Add more settings as needed (database, security, etc.)


settings = Settings()
