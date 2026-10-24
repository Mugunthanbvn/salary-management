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


def test_app_env_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)

    with pytest.raises(ValidationError, match="app_env"):
        settings_from_environment()


@pytest.mark.parametrize("problem", ["missing APP_ENV", "unsafe production values"])
def test_settings_errors_never_show_secret_values(
    monkeypatch: pytest.MonkeyPatch, problem: str
) -> None:
    jwt_secret, auth_token = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    monkeypatch.setenv("JWT_SECRET", jwt_secret)
    monkeypatch.setenv("DATABASE_AUTH_TOKEN", auth_token)
    if problem == "missing APP_ENV":
        monkeypatch.delenv("APP_ENV", raising=False)
    else:
        monkeypatch.setenv("APP_ENV", "production")  # COOKIE_SECURE and DATABASE_URL are unsafe

    with pytest.raises(ValidationError) as error:
        settings_from_environment()

    shown = str(error.value) + repr(error.value.errors())
    assert jwt_secret not in shown
    assert auth_token not in shown


def test_production_refuses_cors_origins() -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        make_settings(**SAFE_PRODUCTION | {"cors_origins": ["http://localhost:3000"]})


@pytest.mark.parametrize("empty", ["", "  "])
def test_an_empty_llm_base_url_or_model_falls_back_to_the_gemini_default(empty: str) -> None:
    settings = make_settings(llm_base_url=empty, llm_model=empty)

    assert settings.llm_base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"
    assert settings.llm_model == "gemini-flash-latest"
