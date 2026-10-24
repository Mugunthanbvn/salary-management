"""Demo users and where their passwords come from (docs/12-seed-data.md section 11)."""

from datetime import UTC, datetime
from typing import Any

import pytest

from salary_api.core.permissions import Role
from salary_api.seed.errors import SeedRefused
from salary_api.seed.settings import SeedSettings
from salary_api.seed.users import demo_users
from tests.factories import FAST_PASSWORD_HASHER

# Low entropy on purpose, so secret scanners (gitleaks) do not mistake them for real ones.
REAL = {
    "seed_admin_password": "admin" + "x" * 16,
    "seed_hr_password": "hr" + "y" * 16,
    "seed_viewer_password": "viewer" + "z" * 16,
}


class _SettingsWithoutEnvFile(SeedSettings):
    model_config = SeedSettings.model_config | {"env_file": None}


def _settings(app_env: str, **values: Any) -> SeedSettings:
    return _SettingsWithoutEnvFile(app_env=app_env, **values)


def _passwords_verify(settings: SeedSettings, passwords: list[str]) -> bool:
    users = demo_users(settings, FAST_PASSWORD_HASHER)
    return all(
        FAST_PASSWORD_HASHER.verify(password, user.password_hash)
        for user, password in zip(users, passwords, strict=True)
    )


def test_the_three_demo_users_have_their_documented_emails_names_and_roles() -> None:
    users = demo_users(_settings("development"), FAST_PASSWORD_HASHER)

    assert [(u.id, u.email, u.full_name, u.role, u.is_active) for u in users] == [
        (1, "admin@acme.example", "Arun", Role.ADMIN, True),
        (2, "hr@acme.example", "Hema", Role.HR_MANAGER, True),
        (3, "viewer@acme.example", "Farah", Role.VIEWER, True),
    ]
    assert {u.created_at for u in users} == {datetime(2026, 10, 1, tzinfo=UTC)}


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_without_passwords_development_and_tests_use_the_documented_defaults(app_env: str) -> None:
    settings = _settings(app_env)

    assert _passwords_verify(settings, ["change-me-admin", "change-me-hr", "change-me-viewer"])


def test_passwords_from_the_environment_win() -> None:
    settings = _settings("development", **REAL)

    assert _passwords_verify(settings, list(REAL.values()))


def test_passwords_are_stored_as_argon2_hashes_never_in_clear() -> None:
    users = demo_users(_settings("development", **REAL), FAST_PASSWORD_HASHER)

    assert all(u.password_hash.startswith("$argon2id$") for u in users)
    assert not any(password in u.password_hash for u in users for password in REAL.values())


def test_production_accepts_real_passwords() -> None:
    settings = _settings("production", **REAL)

    assert _passwords_verify(settings, list(REAL.values()))


def test_production_refuses_missing_passwords_and_names_each_variable() -> None:
    settings = _settings("production", seed_admin_password=REAL["seed_admin_password"])

    with pytest.raises(SeedRefused) as refused:
        demo_users(settings, FAST_PASSWORD_HASHER)

    message = str(refused.value)
    assert "SEED_HR_PASSWORD" in message
    assert "SEED_VIEWER_PASSWORD" in message
    assert "SEED_ADMIN_PASSWORD" not in message


@pytest.mark.parametrize(
    "weak",
    ["change-me-hr", "change-me-please-2026", "", "   "],
)
def test_production_refuses_default_placeholder_or_blank_passwords_without_echoing_them(
    weak: str,
) -> None:
    settings = _settings("production", **(REAL | {"seed_hr_password": weak}))

    with pytest.raises(SeedRefused, match="SEED_HR_PASSWORD") as refused:
        demo_users(settings, FAST_PASSWORD_HASHER)

    assert weak.strip() == "" or weak not in str(refused.value)
