from pydantic_settings import BaseSettings
from typing import Any, Dict, List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "ForkFolio"
    PROJECT_DESCRIPTION: str = "Portfolio management API for tracking investments"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Add more settings as needed (database, security, etc.)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
