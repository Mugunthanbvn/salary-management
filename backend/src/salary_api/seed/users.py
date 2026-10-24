"""The three demo users (docs/12-seed-data.md section 11)."""

from datetime import UTC, datetime, time

from salary_api.core.config import PLACEHOLDER_MARKERS
from salary_api.core.security import PasswordHasher
from salary_api.seed import seed_config as config
from salary_api.seed.errors import SeedRefused
from salary_api.seed.rows import UserRow
from salary_api.seed.seed_config import DemoUserSpec
from salary_api.seed.settings import SeedSettings

_DEV_PASSWORDS = frozenset(user.dev_password for user in config.DEMO_USERS)


def demo_users(settings: SeedSettings, hasher: PasswordHasher) -> list[UserRow]:
    """The demo users, with passwords from SEED_*_PASSWORD hashed by `hasher`.

    Development and tests fall back to the documented defaults (backend/.env.example).
    Production refuses a missing, blank, default or placeholder password (SeedRefused).
    """
    passwords: list[str] = []
    problems: list[str] = []
    for user in config.DEMO_USERS:
        password, problem = _password(settings, user)
        passwords.append(password)
        if problem:
            problems.append(f"{user.password_env} {problem}")
    if problems:
        raise SeedRefused(
            "Refusing to seed demo users with APP_ENV=production: "
            + "; ".join(problems)
            + ". Set real passwords in the environment."
        )
    created = datetime.combine(config.ANCHOR_DATE, time(tzinfo=UTC))
    return [
        UserRow(
            id=user_id,
            email=user.email,
            full_name=user.full_name,
            password_hash=hasher.hash(password),
            role=user.role,
            created_at=created,
            updated_at=created,
        )
        for user_id, (user, password) in enumerate(
            zip(config.DEMO_USERS, passwords, strict=True), start=1
        )
    ]


def _password(settings: SeedSettings, user: DemoUserSpec) -> tuple[str, str | None]:
    """The password to use, and what is wrong with it in production (None if nothing)."""
    password = settings.password_from(user.password_env)
    if password is None or not password.strip():
        if settings.is_production:
            return "", "is not set"
        return user.dev_password, None
    if settings.is_production and _is_placeholder(password):
        return "", "is a default or placeholder password"
    return password, None


def _is_placeholder(password: str) -> bool:
    lowered = password.lower()
    return password in _DEV_PASSWORDS or any(marker in lowered for marker in PLACEHOLDER_MARKERS)
