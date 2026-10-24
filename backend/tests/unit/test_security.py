"""Password hashing and session tokens (docs/08-security-rbac.md sections 5.1 and 5.2)."""

import base64
import json
from datetime import timedelta

import jwt
import pytest
import time_machine
from pwdlib.hashers.argon2 import Argon2Hasher

from salary_api.core.deps import get_password_hasher
from salary_api.core.permissions import Role
from salary_api.core.security import (
    InvalidToken,
    PasswordHasher,
    create_access_token,
    decode_access_token,
)
from tests.conftest import FROZEN_NOW
from tests.factories import FAST_PASSWORD_HASHER, TEST_JWT_SECRET, make_settings

SETTINGS = make_settings()


def test_a_password_verifies_against_its_own_hash() -> None:
    password_hash = FAST_PASSWORD_HASHER.hash("correct horse battery")

    assert password_hash.startswith("$argon2id$")
    assert FAST_PASSWORD_HASHER.verify("correct horse battery", password_hash)


def test_a_wrong_password_does_not_verify() -> None:
    password_hash = FAST_PASSWORD_HASHER.hash("correct horse battery")

    assert not FAST_PASSWORD_HASHER.verify("wrong horse battery", password_hash)


def test_a_hash_that_is_not_argon2_does_not_verify() -> None:
    assert not FAST_PASSWORD_HASHER.verify("anything", "not-a-real-hash")


def test_a_hash_needs_rehash_only_when_its_parameters_are_outdated() -> None:
    fast_hash = FAST_PASSWORD_HASHER.hash("correct horse battery")

    assert not FAST_PASSWORD_HASHER.needs_rehash(fast_hash)
    assert PasswordHasher().needs_rehash(fast_hash)  # library defaults are stronger


def test_a_token_carries_the_documented_claims(frozen_time: time_machine.Traveller) -> None:
    token = create_access_token(user_id=42, role=Role.VIEWER, settings=SETTINGS)

    claims = jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])
    assert jwt.get_unverified_header(token)["alg"] == "HS256"
    assert set(claims) == {"sub", "role", "iat", "exp", "jti"}
    assert (claims["sub"], claims["role"]) == ("42", "VIEWER")
    assert claims["iat"] == int(FROZEN_NOW.timestamp())
    assert claims["exp"] - claims["iat"] == 480 * 60


def test_each_token_has_its_own_id(frozen_time: time_machine.Traveller) -> None:
    first = create_access_token(user_id=42, role=Role.VIEWER, settings=SETTINGS)
    second = create_access_token(user_id=42, role=Role.VIEWER, settings=SETTINGS)

    assert decode_access_token(first, SETTINGS).token_id != (
        decode_access_token(second, SETTINGS).token_id
    )


def test_a_valid_token_decodes_to_its_claims(frozen_time: time_machine.Traveller) -> None:
    token = create_access_token(user_id=42, role=Role.HR_MANAGER, settings=SETTINGS)

    claims = decode_access_token(token, SETTINGS)

    assert (claims.user_id, claims.role) == (42, "HR_MANAGER")
    assert (claims.issued_at, claims.expires_at) == (FROZEN_NOW, FROZEN_NOW + timedelta(hours=8))


def test_the_token_lifetime_comes_from_jwt_ttl_minutes(frozen_time: time_machine.Traveller) -> None:
    settings = make_settings(jwt_ttl_minutes=30)

    claims = decode_access_token(
        create_access_token(user_id=1, role=Role.ADMIN, settings=settings), settings
    )

    assert claims.expires_at - claims.issued_at == timedelta(minutes=30)


def test_a_token_is_still_valid_just_before_it_expires(
    frozen_time: time_machine.Traveller,
) -> None:
    token = create_access_token(user_id=42, role=Role.VIEWER, settings=SETTINGS)
    frozen_time.shift(timedelta(hours=8) - timedelta(seconds=1))

    assert decode_access_token(token, SETTINGS).user_id == 42


def test_an_expired_token_is_invalid(frozen_time: time_machine.Traveller) -> None:
    token = create_access_token(user_id=42, role=Role.VIEWER, settings=SETTINGS)
    frozen_time.shift(timedelta(hours=8))

    with pytest.raises(InvalidToken):
        decode_access_token(token, SETTINGS)


def _claims(**overrides: object) -> dict[str, object]:
    issued_at = int(FROZEN_NOW.timestamp())
    claims: dict[str, object] = {
        "sub": "42",
        "role": "VIEWER",
        "iat": issued_at,
        "exp": issued_at + 3600,
        "jti": "token-1",
    }
    return claims | overrides


def _with_payload(token: str, payload: dict[str, object]) -> str:
    """The same header and signature around a different payload."""
    header, _payload, signature = token.split(".")
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{encoded}.{signature}"


TAMPERED = _with_payload(
    jwt.encode(_claims(), TEST_JWT_SECRET, algorithm="HS256"), _claims(sub="1", role="ADMIN")
)
WITHOUT_JTI = {key: value for key, value in _claims().items() if key != "jti"}


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(TAMPERED, id="tampered payload"),
        pytest.param(
            jwt.encode(_claims(), "another-secret-" + "y" * 32, algorithm="HS256"),
            id="wrong secret",
        ),
        pytest.param(jwt.encode(_claims(), key=None, algorithm="none"), id="alg none"),
        pytest.param(jwt.encode(WITHOUT_JTI, TEST_JWT_SECRET, algorithm="HS256"), id="no jti"),
        pytest.param(
            jwt.encode(_claims(sub="ana"), TEST_JWT_SECRET, algorithm="HS256"), id="sub not an id"
        ),
        pytest.param("not-a-jwt", id="garbage"),
    ],
)
def test_a_token_that_was_not_issued_by_us_as_is_invalid(
    token: str, frozen_time: time_machine.Traveller
) -> None:
    with pytest.raises(InvalidToken):
        decode_access_token(token, SETTINGS)


def test_the_app_hashes_with_pwdlib_default_parameters() -> None:
    default_hash = PasswordHasher(Argon2Hasher()).hash("correct horse battery")

    assert not get_password_hasher().needs_rehash(default_hash)


class _CountingArgon2(Argon2Hasher):
    """Cheap argon2 that counts how many hashes it computes."""

    def __init__(self) -> None:
        super().__init__(time_cost=1, memory_cost=8, parallelism=1)
        self.hashes = 0

    def hash(self, password: str | bytes, *, salt: bytes | None = None) -> str:
        self.hashes += 1
        return super().hash(password, salt=salt)


def test_the_dummy_hash_is_ready_before_the_first_unknown_email_login() -> None:
    argon2 = _CountingArgon2()
    hasher = PasswordHasher(argon2)  # built once, at app start-up
    argon2.hashes = 0

    hasher.verify("a guess", hasher.dummy_hash)

    assert argon2.hashes == 0  # one verify only: as long as for a known email, even cold
