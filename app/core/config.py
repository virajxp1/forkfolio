import configparser
import os
from pathlib import Path

from dotenv import load_dotenv


class Settings:
    """Application settings loaded from a single config file."""

    def __init__(self):
        repo_root = Path(__file__).resolve().parents[2]
        # Single source of truth for env vars: repo-root .env only.
        load_dotenv(dotenv_path=repo_root / ".env")

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
            "api", "rate_limit_per_minute", fallback=120
        )
        self.MAX_REQUEST_SIZE_MB: int = self._cfg.getint(
            "api", "max_request_size_mb", fallback=1
        )
        self.REQUEST_TIMEOUT_SECONDS: float = self._cfg.getfloat(
            "api", "request_timeout_seconds", fallback=120.0
        )
        self.API_AUTH_TOKEN: str = os.getenv("API_AUTH_TOKEN", "").strip()
        self.SEMANTIC_SEARCH_MAX_DISTANCE: float = self._cfg.getfloat(
            "api", "semantic_search_max_distance", fallback=0.22
        )
        self.SEMANTIC_SEARCH_RERANK_ENABLED: bool = self._cfg.getboolean(
            "api", "semantic_search_rerank_enabled", fallback=True
        )
        self.SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT: int = self._cfg.getint(
            "api", "semantic_search_rerank_candidate_count", fallback=15
        )
        rerank_min_score = self._cfg.getfloat(
            "api", "semantic_search_rerank_min_score", fallback=0.40
        )
        self.SEMANTIC_SEARCH_RERANK_MIN_SCORE: float = min(
            max(rerank_min_score, 0.0), 1.0
        )
        rerank_fallback_min_score = self._cfg.getfloat(
            "api", "semantic_search_rerank_fallback_min_score", fallback=0.25
        )
        self.SEMANTIC_SEARCH_RERANK_FALLBACK_MIN_SCORE: float = min(
            max(rerank_fallback_min_score, 0.0), 1.0
        )
        rerank_weight = self._cfg.getfloat(
            "api", "semantic_search_rerank_weight", fallback=0.70
        )
        self.SEMANTIC_SEARCH_RERANK_WEIGHT: float = min(max(rerank_weight, 0.0), 1.0)
        rerank_cuisine_boost = self._cfg.getfloat(
            "api", "semantic_search_rerank_cuisine_boost", fallback=0.15
        )
        self.SEMANTIC_SEARCH_RERANK_CUISINE_BOOST: float = min(
            max(rerank_cuisine_boost, 0.0), 1.0
        )
        rerank_family_boost = self._cfg.getfloat(
            "api", "semantic_search_rerank_family_boost", fallback=0.10
        )
        self.SEMANTIC_SEARCH_RERANK_FAMILY_BOOST: float = min(
            max(rerank_family_boost, 0.0), 1.0
        )
        self.SEMANTIC_SEARCH_HEURISTICS_ENABLED: bool = self._cfg.getboolean(
            "api", "semantic_search_heuristics_enabled", fallback=True
        )

        # Observability
        self.BRAINTRUST_TRACING_ENABLED = self._cfg.getboolean(
            "observability",
            "braintrust_enabled",
            fallback=False,
        )
        configured_project_id = self._cfg.get(
            "observability",
            "braintrust_project_id",
            fallback=self._cfg.get(
                "observability",
                "braintrust_project",
                fallback="4e61341a-cc9a-4ce4-a107-4f9980e76b1a",
            ),
        )
        self.BRAINTRUST_PROJECT_ID: str = os.getenv(
            "BRAINTRUST_PROJECT_ID",
            configured_project_id,
        ).strip()
        self.BRAINTRUST_APP_URL: str = os.getenv(
            "BRAINTRUST_APP_URL",
            self._cfg.get(
                "observability",
                "braintrust_app_url",
                fallback="https://www.braintrust.dev",
            ),
        ).strip()

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
        self.LLM_STRUCTURED_MAX_TOKENS: int = self._cfg.getint(
            "llm", "structured_max_tokens", fallback=3500
        )
        structured_attempts = self._cfg.getint(
            "llm", "structured_output_max_attempts", fallback=2
        )
        self.LLM_STRUCTURED_OUTPUT_MAX_ATTEMPTS: int = max(1, structured_attempts)
        recipe_unit_system = os.getenv(
            "RECIPE_UNIT_SYSTEM",
            self._cfg.get("llm", "recipe_unit_system", fallback="us"),
        )
        normalized_unit_system = recipe_unit_system.strip().lower()
        if normalized_unit_system in {"metric", "si"}:
            self.RECIPE_UNIT_SYSTEM = "metric"
        elif normalized_unit_system == "both":
            self.RECIPE_UNIT_SYSTEM = "both"
        else:
            self.RECIPE_UNIT_SYSTEM = "us"

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

        # Search behavior
        default_keywords_path = repo_root / "config" / "search_keywords.json"
        configured_keywords_file = os.getenv(
            "SEARCH_KEYWORDS_FILE", ""
        ).strip() or self._cfg.get(
            "search",
            "keywords_file",
            fallback=str(default_keywords_path.relative_to(repo_root)),
        )
        self.SEARCH_KEYWORDS_FILE: Path = self._resolve_repo_path(
            configured_keywords_file,
            default_keywords_path,
        )

        # Secrets: environment-only.
        self.OPEN_ROUTER_API_KEY: str = os.getenv("OPEN_ROUTER_API_KEY", "").strip()
        self.SUPABASE_PASSWORD: str = os.getenv("SUPABASE_PASSWORD", "").strip()
        self.BRAINTRUST_API_KEY: str = os.getenv("BRAINTRUST_API_KEY", "").strip()

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

    def _resolve_repo_path(self, raw_path: str, fallback: Path) -> Path:
        normalized = (raw_path or "").strip()
        if not normalized:
            return fallback
        candidate = Path(normalized).expanduser()
        if not candidate.is_absolute():
            candidate = self._repo_root / candidate
        return candidate


settings = Settings()
