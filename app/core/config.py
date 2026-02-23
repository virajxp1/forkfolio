import configparser
import os
from pathlib import Path

from dotenv import load_dotenv


class Settings:
    """Application settings loaded from a single config file."""

    def __init__(self):
        repo_root = Path(__file__).resolve().parents[2]
        # Keep .env support for secrets without making it mandatory.
        load_dotenv(dotenv_path=repo_root / ".env")
        load_dotenv(dotenv_path=repo_root / ".context" / ".env", override=True)

        default_config_path = repo_root / "config" / "app.config.ini"
        config_path = Path(os.getenv("APP_CONFIG_FILE", str(default_config_path)))

        self._repo_root = repo_root
        self._config_path = config_path
        self._cfg = self._load_config(config_path)

        # App metadata
        self.PROJECT_NAME: str = self._cfg.get(
            "app", "project_name", fallback="ForkFolio"
        )
        self.PROJECT_DESCRIPTION: str = self._cfg.get(
            "app", "project_description", fallback="Recipe management API"
        )
        self.VERSION: str = self._cfg.get("app", "version", fallback="0.1.0")

        # API settings
        self.API_BASE_PATH: str = self._normalize_api_base_path(
            self._cfg.get("api", "base_path", fallback="/api/v1")
        )
        # Backward-compatible alias.
        self.API_V1_STR: str = self.API_BASE_PATH
        self.RATE_LIMIT_PER_MINUTE: int = self._cfg.getint(
            "api", "rate_limit_per_minute", fallback=60
        )
        self.MAX_REQUEST_SIZE_MB: int = self._cfg.getint(
            "api", "max_request_size_mb", fallback=1
        )
        self.REQUEST_TIMEOUT_SECONDS: float = self._cfg.getfloat(
            "api", "request_timeout_seconds", fallback=30.0
        )
        self.API_AUTH_TOKEN: str = os.getenv("API_AUTH_TOKEN", "").strip()
        self.SEMANTIC_SEARCH_MAX_DISTANCE: float = self._cfg.getfloat(
            "api", "semantic_search_max_distance", fallback=0.22
        )
        self.SEMANTIC_SEARCH_RERANK_ENABLED: bool = self._cfg.getboolean(
            "api", "semantic_search_rerank_enabled", fallback=False
        )
        self.SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT: int = self._cfg.getint(
            "api", "semantic_search_rerank_candidate_count", fallback=15
        )

        # DB settings
        self.DB_HOST: str = self._cfg.get("database", "host")
        self.DB_PORT: int = self._cfg.getint("database", "port", fallback=5432)
        self.DB_USER: str = self._cfg.get("database", "user")
        self.DB_NAME: str = self._cfg.get("database", "name", fallback="postgres")
        self.DB_SSLMODE: str = self._cfg.get("database", "sslmode", fallback="require")
        self.DB_POOL_MINCONN: int = self._cfg.getint(
            "database", "pool_minconn", fallback=2
        )
        self.DB_POOL_MAXCONN: int = self._cfg.getint(
            "database", "pool_maxconn", fallback=10
        )

        # LLM + embeddings
        self.LLM_MODEL_NAME: str = self._cfg.get(
            "llm", "model_name", fallback=""
        ).strip()
        self.EMBEDDINGS_MODEL_NAME: str = self._cfg.get(
            "embeddings", "model_name", fallback=""
        ).strip()
        self.LLM_MAX_RETRIES: int = self._cfg.getint("llm", "max_retries", fallback=3)
        self.LLM_RETRY_BASE_SECONDS: float = self._cfg.getfloat(
            "llm", "retry_base_seconds", fallback=1.0
        )
        self.LLM_RETRY_MAX_SECONDS: float = self._cfg.getfloat(
            "llm", "retry_max_seconds", fallback=10.0
        )

        # Dedupe
        self.DEDUPE_EMBEDDING_TYPE: str = self._cfg.get(
            "dedupe", "embedding_type", fallback="title_ingredients"
        )
        self.DEDUPE_STRICT_DUPLICATE_DISTANCE_THRESHOLD: float = self._cfg.getfloat(
            "dedupe", "strict_duplicate_threshold", fallback=0.05
        )
        self.DEDUPE_DISTANCE_THRESHOLD: float = self._cfg.getfloat(
            "dedupe", "distance_threshold", fallback=0.30
        )

        # Secrets: environment-only.
        self.OPEN_ROUTER_API_KEY: str = os.getenv("OPEN_ROUTER_API_KEY", "").strip()
        self.SUPABASE_PASSWORD: str = (
            os.getenv("SUPABASE_PASSWORD") or os.getenv("DB_PASSWORD") or ""
        ).strip()

    @staticmethod
    def _load_config(config_path: Path) -> configparser.ConfigParser:
        cfg = configparser.ConfigParser()
        if not cfg.read(config_path):
            raise FileNotFoundError(f"App config file not found: {config_path}")
        return cfg

    @staticmethod
    def _normalize_api_base_path(path: str) -> str:
        normalized = (path or "").strip()
        if not normalized:
            return "/api/v1"
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        normalized = normalized.rstrip("/")
        return normalized or "/api/v1"


settings = Settings()
