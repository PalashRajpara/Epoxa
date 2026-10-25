"""
Unit tests for CoreSettings and environment validation.
"""

from epoxa_core.settings import CoreSettings


def test_core_settings_defaults() -> None:
    settings = CoreSettings()
    assert settings.ENVIRONMENT in ("local", "staging", "production")
    assert settings.DEFAULT_PHONE_REGION == "IN"
    assert settings.DEFAULT_TIMEZONE == "Asia/Kolkata"
    assert settings.BUSINESS_HOURS_START == 9
    assert settings.BUSINESS_HOURS_END == 18
    assert settings.CONCURRENT_CALL_CAP >= 1


def test_cors_origins_parsing() -> None:
    settings = CoreSettings(CORS_ORIGINS="http://localhost:3000, http://localhost:3001, ")
    origins = settings.cors_origins_list
    assert "http://localhost:3000" in origins
    assert "http://localhost:3001" in origins
    assert len(origins) == 2


def test_database_url_asyncpg_normalization() -> None:
    settings = CoreSettings(DATABASE_URL="postgresql://user:pass@localhost:5432/db")
    assert settings.DATABASE_URL.startswith("postgresql+asyncpg://")

    settings_alt = CoreSettings(DATABASE_URL="postgres://user:pass@localhost:5432/db")
    assert settings_alt.DATABASE_URL.startswith("postgresql+asyncpg://")
