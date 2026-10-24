"""APP_ENV=production refuses unsafe settings (docs/17-deployment.md section 4)."""

from typing import Any

import pytest
from pydantic import ValidationError

from tests.factories import make_settings

SAFE_PRODUCTION: dict[str, Any] = {
    "app_env": "production",
    "jwt_secret": "Zq3vX9kLm2Pt7Rb4Wy8Nc1Hd6Jf5Gs0A",
    "cookie_secure": True,
    "database_url": "sqlite+libsql://salary-prod-acme.turso.io?secure=true",
}


def test_production_accepts_safe_settings() -> None:
    settings = make_settings(**SAFE_PRODUCTION)

    assert settings.app_env == "production"


@pytest.mark.parametrize(
    "jwt_secret",
    [
        "dev-only-change-me",
        "please-change-me-please-change-me-please",
        "short-but-random-Zq3vX9",
    ],
)
def test_production_refuses_a_placeholder_or_short_jwt_secret(jwt_secret: str) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET") as error:
        make_settings(**SAFE_PRODUCTION | {"jwt_secret": jwt_secret})

    assert jwt_secret not in str(error.value)


def test_production_refuses_insecure_cookies() -> None:
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        make_settings(**SAFE_PRODUCTION | {"cookie_secure": False})
