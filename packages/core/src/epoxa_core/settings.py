"""
Typed settings and environment configuration for Epoxa.
Uses pydantic-settings with SecretStr to ensure secrets are never leaked into logs.
"""

from typing import List, Optional
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    """Shared core configuration consumed across API and Agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: str = Field(default="local", description="local, staging, or production")
    LOG_LEVEL: str = Field(default="INFO", description="Standard logging level")

    # Database URLs
    # Runtime URL uses Supavisor Transaction Pooler on port 6543
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/epoxa",
        description="Asyncpg database URL for runtime queries",
    )
    # Migration URL uses Direct or Session Mode on port 5432
    MIGRATION_DATABASE_URL: Optional[str] = Field(
        default=None,
        description="Alembic migration database URL (Session mode / Direct 5432)",
    )

    # Supabase Cloud
    SUPABASE_URL: str = Field(
        default="https://placeholder.supabase.co",
        description="Supabase project URL",
    )
    SUPABASE_ANON_KEY: Optional[str] = Field(
        default=None,
        description="Supabase anon public key (used for client validation / JWKS)",
    )
    SUPABASE_SERVICE_ROLE_KEY: Optional[SecretStr] = Field(
        default=None,
        description="Supabase service role secret (server-side administrative only)",
    )
    SUPABASE_JWT_SECRET: Optional[SecretStr] = Field(
        default=None,
        description="Supabase legacy HS256 JWT secret for fallback token verification",
    )

    # LiveKit Cloud
    LIVEKIT_URL: str = Field(
        default="wss://placeholder.livekit.cloud",
        description="LiveKit Cloud WebRTC endpoint",
    )
    LIVEKIT_API_KEY: SecretStr = Field(
        default=SecretStr("placeholder-key"),
        description="LiveKit API Key",
    )
    LIVEKIT_API_SECRET: SecretStr = Field(
        default=SecretStr("placeholder-secret"),
        description="LiveKit API Secret",
    )

    # Groq Cloud LLM
    GROQ_API_KEY: SecretStr = Field(
        default=SecretStr("placeholder-groq-key"),
        description="Groq inference API key",
    )
    LLM_MODEL: str = Field(
        default="llama-3.1-8b-instant",
        description="LLM model identifier on Groq",
    )
    LLM_TEMPERATURE: float = Field(default=0.3, ge=0.0, le=1.0)
    LLM_TIMEOUT_SECONDS: float = Field(default=15.0, gt=0.0)

    # Speech-to-Text & Text-to-Speech
    DEEPGRAM_API_KEY: SecretStr = Field(
        default=SecretStr("placeholder-deepgram-key"),
        description="Unified Deepgram API key for STT and TTS",
    )
    DEEPGRAM_STT_MODEL: str = Field(default="nova-2-general")
    DEEPGRAM_TTS_MODEL: str = Field(default="aura-asteria-en")
    CARTESIA_API_KEY: Optional[SecretStr] = Field(default=None)

    # Default Business Rules (configurable per tenant)
    DEFAULT_PHONE_REGION: str = Field(default="IN", description="Default ISO country code for phone normalization")
    DEFAULT_TIMEZONE: str = Field(default="Asia/Kolkata", description="Default IANA timezone")
    BUSINESS_HOURS_START: int = Field(default=9, ge=0, le=23, description="Opening hour (24-hour clock)")
    BUSINESS_HOURS_END: int = Field(default=18, ge=0, le=23, description="Closing hour (24-hour clock)")
    APPOINTMENT_SLOT_MINUTES: int = Field(default=30, gt=0)

    # Public Abuse & Cost Protection (D7)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, gt=0)
    CONCURRENT_CALL_CAP: int = Field(default=10, gt=0, description="Global cap on concurrent active calls")
    MAX_CALL_DURATION_MINUTES: int = Field(default=10, gt=0, description="Hard cap on call duration")

    # API Server Settings
    PORT: int = Field(default=8000, gt=0)
    HOST: str = Field(default="0.0.0.0")
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:3001,http://localhost:5173",
        description="Comma-separated CORS origins allowlist",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: Optional[str]) -> str:
        if not v:
            return "postgresql+asyncpg://postgres:postgres@localhost:5432/epoxa"
        # Ensure asyncpg driver dialect is present
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v


# Global singleton instance
settings = CoreSettings()


def get_settings() -> CoreSettings:
    """Returns the cached singleton application settings instance."""
    return settings
