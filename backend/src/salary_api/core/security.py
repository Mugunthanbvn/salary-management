"""Password hashing (pwdlib argon2) and session tokens (PyJWT HS256).

docs/08-security-rbac.md sections 5.1 and 5.2. Tokens carry `sub` (user id as a string),
`role`, `iat`, `exp` and `jti`. The `role` claim is informational only: permissions come
from the user's role in the database on every request.
"""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher

from salary_api.core.config import Settings
from salary_api.core.permissions import Role

SESSION_COOKIE = "session"
JWT_ALGORITHM = "HS256"
_REQUIRED_CLAIMS = ["sub", "role", "iat", "exp", "jti"]


class PasswordHasher:
    """Argon2id hashing. The default uses pwdlib's parameters; tests pass cheaper ones."""

    def __init__(self, argon2: Argon2Hasher | None = None) -> None:
        self._argon2 = argon2 or Argon2Hasher()
        self._password_hash = PasswordHash((self._argon2,))
        # A hash of a random password, checked when the email is unknown, so that login
        # costs one verify like a real one. Made now, not on first use: a cold instance's
        # first unknown-email login would otherwise also pay for a hash.
        self.dummy_hash = self.hash(secrets.token_urlsafe(16))

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        """Constant-time check. A hash in an unknown format never verifies."""
        try:
            return self._password_hash.verify(password, password_hash)
        except UnknownHashError:
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        """Whether the hash was made with other parameters than this hasher's."""
        return self._argon2.check_needs_rehash(password_hash)


class InvalidToken(Exception):
    """The token is expired, tampered with, signed with another secret, or malformed."""


@dataclass(frozen=True, slots=True)
class TokenClaims:
    user_id: int
    role: str
    issued_at: datetime
    expires_at: datetime
    token_id: str


def create_access_token(*, user_id: int, role: Role, settings: Settings) -> str:
    issued_at = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "role": role.value,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.jwt_ttl_minutes),
        "jti": uuid4().hex,
    }
    secret = settings.jwt_secret.get_secret_value()
    # PyJWT's key type names `cryptography` classes (RSA/EC keys), not installed for HS256.
    return jwt.encode(claims, secret, algorithm=JWT_ALGORITHM)  # pyright: ignore[reportUnknownMemberType]


def decode_access_token(token: str, settings: Settings) -> TokenClaims:
    """The token's claims, or InvalidToken. Only HS256 with our secret is accepted."""
    try:
        claims = jwt.decode(  # pyright: ignore[reportUnknownMemberType] (see create_access_token)
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            options={"require": _REQUIRED_CLAIMS},
        )
        return TokenClaims(
            user_id=int(claims["sub"]),
            role=str(claims["role"]),
            issued_at=datetime.fromtimestamp(claims["iat"], UTC),
            expires_at=datetime.fromtimestamp(claims["exp"], UTC),
            token_id=str(claims["jti"]),
        )
    except (jwt.InvalidTokenError, ValueError) as error:
        raise InvalidToken(str(error)) from None
