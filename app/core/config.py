# Standard library imports
import os
from pathlib import Path

# Third-party imports
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import dotenv_values, find_dotenv

_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables, .env file, or defaults.

    Priority order:
    1. OS environment variables (highest)
    2. .env file
    3. Default values (lowest)
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: str = "false"
    LOG_LEVEL: str = "INFO"
    PUBLISH_PORT: int = 8000

    @field_validator("LOG_LEVEL")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        level = value.strip().upper()
        if level not in _LOG_LEVELS:
            allowed = ", ".join(sorted(_LOG_LEVELS))
            raise ValueError(f"LOG_LEVEL must be one of: {allowed}")
        return level

    # Session / auth
    SECRET_KEY: str = "change-me-in-production"
    SESSION_COOKIE_NAME: str = "fastapi_htmx_bootstrap_session"
    # Demo user seeded when users table is empty (development convenience)
    DEMO_USERNAME: str = "admin"
    DEMO_PASSWORD: str = "admin123"

    # SQLite (relational demo). Example: sqlite:///./data/app.db
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # MongoDB
    MONGO_USER: str = "root"
    MONGO_PASS: str = "pass"
    MONGO_HOST: str = "mongodb"
    MONGO_PORT: str = "27017"
    MONGO_AUTH_SOURCE: str = "admin"
    MONGO_DATABASE: str = "fastapi_htmx_bootstrap"


settings = Settings()

VERSION: str = settings.VERSION
ENVIRONMENT: str = settings.ENVIRONMENT
DEBUG: bool = settings.DEBUG.lower() == "true"
LOG_LEVEL: str = settings.LOG_LEVEL
PUBLISH_PORT: int = settings.PUBLISH_PORT

SECRET_KEY: str = settings.SECRET_KEY
SESSION_COOKIE_NAME: str = settings.SESSION_COOKIE_NAME
DEMO_USERNAME: str = settings.DEMO_USERNAME
DEMO_PASSWORD: str = settings.DEMO_PASSWORD
DATABASE_URL: str = settings.DATABASE_URL

MONGO_USER: str = settings.MONGO_USER
MONGO_PASS: str = settings.MONGO_PASS
MONGO_HOST: str = settings.MONGO_HOST
MONGO_PORT: str = settings.MONGO_PORT
MONGO_AUTH_SOURCE: str = settings.MONGO_AUTH_SOURCE
MONGO_DATABASE: str = settings.MONGO_DATABASE

MONGO_URI: str = (
    f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/"
    f"{MONGO_DATABASE}?authSource={MONGO_AUTH_SOURCE}"
)


def sqlite_path_from_url(database_url: str = DATABASE_URL) -> Path:
    """Resolve filesystem path from a sqlite:/// URL."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError(
            f"Only sqlite:/// URLs are supported for DATABASE_URL, got: {database_url!r}"
        )
    raw = database_url[len(prefix):]
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def log_config_values() -> None:
    """Log configuration values with sources (DEBUG only; secrets masked)."""
    import logging

    log = logging.getLogger(__name__)
    env_file_path = Path(".env")
    env_file_data = {}
    if env_file_path.exists():
        env_file_data = dotenv_values(env_file_path)
    else:
        dotenv_path = find_dotenv()
        if dotenv_path:
            env_file_data = dotenv_values(dotenv_path)

    os_env = os.environ

    log.info("=== Configuration Values (with sources) ===")
    for field_name in settings.model_fields:
        value = getattr(settings, field_name)

        env_key = field_name
        if env_key in os_env:
            source = "[OS]"
        elif env_key in env_file_data:
            source = "[.env]"
        else:
            source = "[default]"

        if any(s in field_name for s in ("PASS", "PASSWORD", "SECRET")):
            display_value = "***" if value else "None"
        else:
            display_value = repr(value) if value is not None else "None"

        log.info("  %s: %s %s", field_name, display_value, source)

    log.info(
        "  MONGO_URI: mongodb://%s:***@%s:%s/%s?authSource=%s [computed]",
        MONGO_USER,
        MONGO_HOST,
        MONGO_PORT,
        MONGO_DATABASE,
        MONGO_AUTH_SOURCE,
    )
    log.info("  DEBUG (bool): %s [computed]", DEBUG)
    log.info("  SQLITE_PATH: %s [computed]", sqlite_path_from_url())
    log.info("=== Debug Information ===")
    log.info("  Working Directory: %s", os.getcwd())
    log.info("  PYTHONPATH: %s", os.getenv("PYTHONPATH", "Not set"))
    dotenv_path = find_dotenv() if not env_file_path.exists() else str(env_file_path)
    log.info("  ENV File: %s", dotenv_path if dotenv_path else "Not found")
