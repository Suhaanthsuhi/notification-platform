# core/config.py
"""
Application Configuration Module

This module centralizes configuration management for the
notification platform using environment variables and Pydantic
BaseSettings.

Purpose:

- Provide a single source of truth for service configuration
- Support environment-based configuration (dev, staging, prod)
- Expose strongly typed settings across the application
- Construct derived configuration values (e.g., database URL)

Core Responsibilities:

1. Environment Loading
   - Loads variables from a `.env` file using python-dotenv
   - Supports fallback defaults for local development

2. Service Configuration
   - Service metadata (name, environment, debug)
   - Redis connection details and stream names
   - Database credentials and connection details
   - Firebase service account configuration

3. Derived Properties
   - `database_url` dynamically builds the async SQLAlchemy
     connection string for PostgreSQL (asyncpg driver)

4. Singleton Access Pattern
   - `get_settings()` uses @lru_cache to ensure a single
     Settings instance across the application
   - Prevents redundant reloading of environment variables

Design Principles:

- Environment-driven architecture
- Strong typing via Pydantic BaseSettings
- Lazy evaluation of computed properties
- Clean separation between configuration and business logic

Why This Matters:

This module ensures that infrastructure configuration
(Redis, PostgreSQL, Firebase) remains decoupled from
application logic, enabling smooth deployment across
multiple environments without code changes.

All workers (enricher, engine, delivery) and API routes
depend on this module for consistent configuration.
"""

import os
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv
from pydantic.v1 import BaseSettings

basedir = Path(__file__).parents[1]
load_dotenv(basedir / ".env")


class Settings(BaseSettings):
    name: str = os.getenv("SERVICE_NAME", "notifty")
    env: str = os.getenv("ENV", "dev")

    debug: bool = os.getenv("DEBUG", "1") in ("1", "true", "True")

    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    redis_raw_stream: str = os.getenv("REDIS_RAW_STREAM", "notif_events_raw")
    redis_enriched_stream: str = os.getenv("REDIS_ENRICHED_STREAM", "notif_events_enriched")
    redis_delivery_stream: str = os.getenv("REDIS_DELIVERY_STREAM", "notif_delivery_tasks")
    redis_dlq_stream: str = os.getenv("REDIS_DLQ_STREAM", "notif_events_dlq")

    # Stream TTL in seconds — events older than this are automatically trimmed (default: 2 days)
    redis_stream_ttl_seconds: int = int(os.getenv("REDIS_STREAM_TTL_SECONDS", str(2 * 24 * 60 * 60)))

    # Max events to keep per stream — acts as a size cap alongside TTL (default: 10,000)
    redis_stream_max_length: int = int(os.getenv("REDIS_STREAM_MAX_LENGTH", "100000"))

    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "notification_db")
    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "postgres")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    firebase_service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")


@lru_cache
def get_settings():
    return Settings()

__all__ = [
    "get_settings",
    "Settings",
]