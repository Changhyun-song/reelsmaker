import logging
import sys
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Core infra ────────────────────────────────────
    database_url: str = "postgresql+asyncpg://reelsmaker:reelsmaker@localhost:5432/reelsmaker"
    redis_url: str = "redis://localhost:6379/0"

    # ── Object storage ────────────────────────────────
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "reelsmaker"
    s3_region: str = "us-east-1"
    s3_public_endpoint: str = ""

    # ── AI providers — keys ──────────────────────────
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    google_api_key: str = ""
    fal_key: str = ""
    runway_api_key: str = ""
    luma_api_key: str = ""
    higgsfield_api_key_id: str = ""
    higgsfield_api_key_secret: str = ""
    elevenlabs_api_key: str = ""

    # ── AI providers — selection ──────────────────────
    # "mock" uses local placeholder; real provider name enables API calls
    image_provider: str = "mock"       # "mock" | "fal" | "openai" | "gemini" | "higgsfield"
    video_provider: str = "mock"       # "mock" | "runway" | "kling" | "luma" | "higgsfield"
    tts_provider: str = "mock"         # "mock" | "elevenlabs"

    # ── AI providers — behavior ──────────────────────
    provider_timeout_sec: int = 120
    fal_image_model: str = "fal-ai/flux/schnell"
    openai_image_model: str = "gpt-image-1"
    gemini_image_model: str = "gemini-2.5-flash-image"
    runway_model: str = "gen4_turbo"
    kling_model: str = "fal-ai/kling-video/v2/master/image-to-video"
    luma_model: str = "ray-2"
    higgsfield_model: str = "higgsfield-ai/dop/standard"
    higgsfield_image_model: str = "higgsfield-ai/soul/standard"
    elevenlabs_model: str = "eleven_multilingual_v2"
    elevenlabs_default_voice: str = ""

    # ── App behavior ──────────────────────────────────
    debug: bool = True
    log_level: str = "INFO"
    sql_echo: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    auto_seed: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


def setup_logging(name: str = "reelsmaker") -> logging.Logger:
    """Configure structured logging for the application."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    fmt = "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        stream=sys.stderr,
        force=True,
    )

    # Quiet noisy libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("s3transfer").setLevel(logging.WARNING)

    if not settings.sql_echo:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return logging.getLogger(name)
