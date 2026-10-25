from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import re

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core Application Settings
    APP_ENV: str = Field(default="development", description="Application environment: development, staging, production")
    APP_NAME: str = Field(default="Epoxa", description="Application name")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    FRONTEND_ORIGIN: str = Field(default="http://localhost:5173", description="Allowed CORS origin")
    BACKEND_BASE_URL: str = Field(default="http://localhost:8000", description="Backend public URL")

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./epoxa_dev.db",
        description="Database connection string (Supabase PostgreSQL or test DB)"
    )

    # Supabase Auth
    SUPABASE_URL: Optional[str] = Field(default=None, description="Supabase project URL")
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = Field(default=None, description="Supabase anon/publishable key")
    SUPABASE_ANON_KEY: Optional[str] = Field(default=None, description="Legacy alias for anon key")
    JWT_EXPECTED_AUDIENCE: str = Field(default="authenticated", description="Expected audience claim in Supabase JWT")

    # LiveKit (Real-time voice transport)
    LIVEKIT_URL: Optional[str] = Field(default=None, description="LiveKit server WebSocket URL")
    LIVEKIT_API_KEY: Optional[str] = Field(default=None, description="LiveKit API key")
    LIVEKIT_API_SECRET: Optional[str] = Field(default=None, description="LiveKit API secret")

    # Deepgram (STT / TTS)
    DEEPGRAM_API_KEY: Optional[str] = Field(default=None, description="Deepgram API key")

    # LLM Providers
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq API key")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key (optional fallback)")
    DEFAULT_LLM_MODEL: str = Field(default="qwen/qwen3.8-27b", description="Default LLM model name")

    # Retention Policy
    TRANSCRIPT_RETENTION_DAYS: int = Field(default=30, description="Retention limit in days for speech transcript content")

    @property
    def cors_origins(self) -> List[str]:
        origins = [self.FRONTEND_ORIGIN.rstrip("/")]
        # Also allow localhost:5173, 5174 and 3000 in development
        if self.APP_ENV == "development":
            origins.extend([
                "http://localhost:5173",
                "http://localhost:5174",
                "http://localhost:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174"
            ])
        return list(set(origins))

    def _normalize_db_url(self, raw_url: str, driver: str) -> str:
        if "sqlite" in raw_url:
            if driver == "asyncpg":
                return raw_url.replace("sqlite://", "sqlite+aiosqlite://", 1) if not raw_url.startswith("sqlite+aiosqlite://") else raw_url
            return raw_url.replace("sqlite+aiosqlite://", "sqlite://", 1) if raw_url.startswith("sqlite+aiosqlite://") else raw_url

        if "://" in raw_url:
            _, rest = raw_url.split("://", 1)
            if "@" in rest:
                last_at_idx = rest.rfind("@")
                creds = rest[:last_at_idx]
                host_db = rest[last_at_idx + 1:]
                if ":" in creds:
                    user, pwd = creds.split(":", 1)
                    import urllib.parse
                    encoded_pwd = urllib.parse.quote_plus(pwd)
                    if driver == "asyncpg":
                        return f"postgresql+asyncpg://{user}:{encoded_pwd}@{host_db}"
                    else:
                        return f"postgresql+psycopg://{user}:{encoded_pwd}@{host_db}"
        return raw_url

    @property
    def async_database_url(self) -> str:
        """Returns an async-compatible SQLAlchemy URL."""
        return self._normalize_db_url(self.DATABASE_URL, "asyncpg")

    @property
    def sync_database_url(self) -> str:
        """Returns a sync-compatible SQLAlchemy URL for Alembic migrations or scripts."""
        return self._normalize_db_url(self.DATABASE_URL, "psycopg")

    def redacted_summary(self) -> dict:
        """Safe non-secret summary for startup verification and diagnostics."""
        def redact(val: Optional[str]) -> str:
            if not val:
                return "<not configured>"
            if len(val) <= 8:
                return "***"
            return f"{val[:4]}...{val[-4:]}"

        # Redact database URL host and hide password
        redacted_db = "<not configured>"
        if self.DATABASE_URL:
            # Match schema://user:pass@host:port/db
            redacted_db = re.sub(r"://([^:@]+):([^@]+)@", r"://\1:***@", self.DATABASE_URL)

        return {
            "app_env": self.APP_ENV,
            "app_name": self.APP_NAME,
            "log_level": self.LOG_LEVEL,
            "frontend_origin": self.FRONTEND_ORIGIN,
            "database_configured": bool(self.DATABASE_URL),
            "database_target": redacted_db,
            "supabase_configured": bool(self.SUPABASE_URL),
            "livekit_configured": bool(self.LIVEKIT_URL and self.LIVEKIT_API_KEY and self.LIVEKIT_API_SECRET),
            "deepgram_configured": bool(self.DEEPGRAM_API_KEY),
            "groq_configured": bool(self.GROQ_API_KEY),
            "openai_configured": bool(self.OPENAI_API_KEY),
            "retention_days": self.TRANSCRIPT_RETENTION_DAYS,
        }

settings = Settings()
