"""Settings: production safety checks, env parsing and backend/.env.example."""

import secrets
from pathlib import Path
from typing import Any

import pytest
from dotenv import dotenv_values
from pydantic import ValidationError

from salary_api.core.config import DEV_PLACEHOLDER, Settings
from tests.factories import make_settings, settings_from_environment

ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"

SAFE_PRODUCTION: dict[str, Any] = {
    "app_env": "production",
    "jwt_secret": secrets.token_urlsafe(32),  # made at run time: no key-like literal in git
    "cookie_secure": True,
    "database_url": "sqlite+libsql://salary-prod-acme.turso.io?secure=true",
}


def test_production_accepts_safe_settings() -> None:
    settings = make_settings(**SAFE_PRODUCTION)

    assert settings.app_env == "production"


@pytest.mark.parametrize(
    "jwt_secret",
    [
        DEV_PLACEHOLDER,
        "please-change-me-please-change-me-please",
        "x" * 31,
    ],
)
def test_production_refuses_a_placeholder_or_short_jwt_secret(jwt_secret: str) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET") as error:
        make_settings(**SAFE_PRODUCTION | {"jwt_secret": jwt_secret})

    assert jwt_secret not in str(error.value)


def test_production_refuses_insecure_cookies() -> None:
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        make_settings(**SAFE_PRODUCTION | {"cookie_secure": False})


@pytest.mark.parametrize(
    "database_url",
    ["sqlite:///./dev.db", "sqlite:////var/data/app.db", "sqlite://", "sqlite:///:memory:"],
)
def test_production_refuses_a_local_or_in_memory_sqlite_database(database_url: str) -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        make_settings(**SAFE_PRODUCTION | {"database_url": database_url})


def test_production_accepts_a_hosted_postgres_database() -> None:
    settings = make_settings(
        **SAFE_PRODUCTION | {"database_url": "postgresql+psycopg://app@db.example.com/salary"}
    )

    assert settings.database_url.startswith("postgresql")


def test_cors_origins_env_var_is_a_comma_separated_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, http://127.0.0.1:3000")

    settings = settings_from_environment()

    assert settings.cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_empty_cors_origins_env_var_means_no_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "")

    settings = settings_from_environment()

    assert settings.cors_origins == []


def test_env_example_documents_every_setting_with_a_valid_value() -> None:
    values = dotenv_values(ENV_EXAMPLE)

    settings = make_settings(**{name.lower(): value for name, value in values.items()})

    assert {name.upper() for name in Settings.model_fields} <= values.keys()
    assert settings.app_env == "development"
