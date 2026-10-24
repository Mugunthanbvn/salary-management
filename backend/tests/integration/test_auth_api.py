"""Auth endpoints (docs/07-api-spec.md section 4, docs/08-security-rbac.md section 5)."""

import hashlib

import pytest
import time_machine
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.deps import get_password_hasher, get_session
from salary_api.core.security import PasswordHasher, decode_access_token
from salary_api.modules.audit.models import AuditEvent
from tests.conftest import FROZEN_NOW, create_test_app, signed_in_client
from tests.factories import DEFAULT_PASSWORD, FAST_ARGON2, make_settings, make_user

LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
PROBLEMS = "https://acme.example/problems/"


def _set_cookie(response_headers: str) -> tuple[str, dict[str, str]]:
    """The session cookie's value and its attributes (lowercased names) from a Set-Cookie."""
    name_value, *attributes = response_headers.split("; ")
    name, _, value = name_value.partition("=")
    assert name == "session"
    parsed = {key.lower(): val for key, _, val in (part.partition("=") for part in attributes)}
    return value, parsed


def test_login_sets_httponly_cookie(
    client: TestClient, db_session: Session, settings: Settings, frozen_time: time_machine.Traveller
) -> None:
    user = make_user(db_session, email="hr@acme.example")

    response = client.post(LOGIN, json={"email": "hr@acme.example", "password": DEFAULT_PASSWORD})

    assert response.status_code == 200
    token, attributes = _set_cookie(response.headers["set-cookie"])
    assert attributes == {"httponly": "", "max-age": "28800", "path": "/", "samesite": "lax"}
    assert decode_access_token(token, settings).user_id == user.id


def test_login_cookie_is_secure_when_cookie_secure_is_true(
    db_session: Session, frozen_time: time_machine.Traveller
) -> None:
    app: FastAPI = create_test_app(make_settings(cookie_secure=True, jwt_ttl_minutes=60))
    app.dependency_overrides[get_session] = lambda: db_session
    make_user(db_session, email="hr@acme.example")

    with TestClient(app) as secure_client:
        response = secure_client.post(
            LOGIN, json={"email": "hr@acme.example", "password": DEFAULT_PASSWORD}
        )

    _token, attributes = _set_cookie(response.headers["set-cookie"])
    assert attributes == {
        "httponly": "",
        "max-age": "3600",
        "path": "/",
        "samesite": "lax",
        "secure": "",
    }


def test_login_returns_the_user_and_the_permissions_of_their_role(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, role="VIEWER", email="vic@acme.example", full_name="Vic Tor")

    response = client.post(LOGIN, json={"email": "vic@acme.example", "password": DEFAULT_PASSWORD})

    assert response.json() == {
        "user": {
            "id": user.id,
            "email": "vic@acme.example",
            "full_name": "Vic Tor",
            "role": "VIEWER",
        },
        "permissions": ["EMPLOYEE_READ", "INSIGHTS_READ", "EXPORT", "ASK"],
    }


def test_login_rejects_unknown_fields(client: TestClient) -> None:
    response = client.post(
        LOGIN, json={"email": "hr@acme.example", "password": "x", "remember_me": True}
    )

    assert response.status_code == 422
    assert response.json()["type"] == f"{PROBLEMS}validation"


@pytest.mark.parametrize("body", [{"email": "hr@acme.example"}, {"password": "x"}])
def test_login_requires_email_and_password(client: TestClient, body: dict[str, str]) -> None:
    response = client.post(LOGIN, json=body)

    assert response.status_code == 422


@pytest.mark.parametrize("reason", ["wrong password", "unknown email", "inactive user"])
def test_login_failure_returns_the_same_401_whatever_the_reason(
    client: TestClient, db_session: Session, reason: str
) -> None:
    make_user(db_session, email="hr@acme.example", is_active=reason != "inactive user")
    email = "nobody@acme.example" if reason == "unknown email" else "hr@acme.example"
    password = "not the password" if reason == "wrong password" else DEFAULT_PASSWORD

    response = client.post(LOGIN, json={"email": email, "password": password})

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert "set-cookie" not in response.headers
    body = response.json()
    assert (body["type"], body["title"], body["detail"]) == (
        f"{PROBLEMS}unauthenticated",
        "Not authenticated",
        "Invalid email or password",
    )


class _CountingHasher(PasswordHasher):
    """The fast test hasher, counting how often a password is checked."""

    def __init__(self) -> None:
        super().__init__(FAST_ARGON2)
        self.verify_calls = 0

    def verify(self, password: str, password_hash: str) -> bool:
        self.verify_calls += 1
        return super().verify(password, password_hash)


def test_login_with_an_unknown_email_still_checks_a_password_hash(
    app: FastAPI, client: TestClient
) -> None:
    hasher = _CountingHasher()
    app.dependency_overrides[get_password_hasher] = lambda: hasher

    client.post(LOGIN, json={"email": "nobody@acme.example", "password": DEFAULT_PASSWORD})

    assert hasher.verify_calls == 1  # against a dummy hash, so it takes as long as a real check


def _committed_events(session: Session) -> list[AuditEvent]:
    """Events the service committed: anything it only added is rolled back first."""
    session.rollback()
    return list(session.scalars(select(AuditEvent).order_by(AuditEvent.id)))


def test_a_successful_login_is_audited_as_auth_login(
    client: TestClient, db_session: Session, frozen_time: time_machine.Traveller
) -> None:
    user = make_user(db_session, email="hr@acme.example")
    db_session.commit()

    client.post(
        LOGIN,
        json={"email": "hr@acme.example", "password": DEFAULT_PASSWORD},
        headers={"X-Request-ID": "req-login"},
    )

    [event] = _committed_events(db_session)
    assert (event.actor_id, event.action, event.entity, event.entity_id, event.diff) == (
        user.id,
        "auth.login",
        "user",
        str(user.id),
        {"result": "success"},
    )
    assert (event.at, event.request_id) == (FROZEN_NOW, "req-login")


def test_a_successful_login_stamps_last_login_at(
    client: TestClient, db_session: Session, frozen_time: time_machine.Traveller
) -> None:
    user = make_user(db_session, email="hr@acme.example")
    db_session.commit()

    client.post(LOGIN, json={"email": "hr@acme.example", "password": DEFAULT_PASSWORD})

    db_session.rollback()
    db_session.refresh(user)
    assert user.last_login_at == FROZEN_NOW


@pytest.mark.parametrize("email_is_known", [True, False])
def test_a_failed_login_is_audited_with_the_email_hash_never_the_email(
    client: TestClient,
    db_session: Session,
    frozen_time: time_machine.Traveller,
    email_is_known: bool,
) -> None:
    user = make_user(db_session, email="hr@acme.example")
    db_session.commit()
    email = "hr@acme.example" if email_is_known else "nobody@acme.example"

    client.post(LOGIN, json={"email": email, "password": "not the password"})

    [event] = _committed_events(db_session)
    assert (event.actor_id, event.action, event.entity) == (None, "auth.login_failed", "auth")
    assert event.entity_id == (str(user.id) if email_is_known else None)
    assert event.diff == {"email_hash": hashlib.sha256(email.encode()).hexdigest()}
    assert email not in str(event.diff)


def test_login_email_is_trimmed_and_case_insensitive(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, email="hr@acme.example")

    response = client.post(
        LOGIN, json={"email": "  HR@Acme.Example ", "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 200


def test_failed_logins_hash_the_normalised_email(client: TestClient, db_session: Session) -> None:
    client.post(LOGIN, json={"email": "  Nobody@ACME.example ", "password": "x"})

    [event] = _committed_events(db_session)
    assert event.diff == {"email_hash": hashlib.sha256(b"nobody@acme.example").hexdigest()}


def test_login_upgrades_a_hash_made_with_outdated_parameters(
    app: FastAPI, client: TestClient, db_session: Session
) -> None:
    stronger = PasswordHasher(Argon2Hasher(time_cost=2, memory_cost=8, parallelism=1))
    app.dependency_overrides[get_password_hasher] = lambda: stronger
    user = make_user(db_session, email="hr@acme.example")  # hashed with time_cost=1
    db_session.commit()
    outdated_hash = user.password_hash

    client.post(LOGIN, json={"email": "hr@acme.example", "password": DEFAULT_PASSWORD})

    db_session.rollback()
    db_session.refresh(user)
    assert user.password_hash != outdated_hash
    assert not stronger.needs_rehash(user.password_hash)
    assert stronger.verify(DEFAULT_PASSWORD, user.password_hash)


def test_login_keeps_an_up_to_date_hash(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, email="hr@acme.example")
    db_session.commit()
    current_hash = user.password_hash

    client.post(LOGIN, json={"email": "hr@acme.example", "password": DEFAULT_PASSWORD})

    db_session.rollback()
    db_session.refresh(user)
    assert user.password_hash == current_hash


def test_logout_clears_the_cookie_with_the_same_attributes(
    app: FastAPI, client: TestClient, db_session: Session, settings: Settings
) -> None:
    signed_in = signed_in_client(app, make_user(db_session), settings)

    response = signed_in.post(LOGOUT)

    assert response.status_code == 204
    value, attributes = _set_cookie(response.headers["set-cookie"])
    attributes.pop("expires")  # a date in the past
    assert (value, attributes) == (
        '""',
        {"httponly": "", "max-age": "0", "path": "/", "samesite": "lax"},
    )


def test_logout_is_audited_as_auth_logout(
    app: FastAPI,
    client: TestClient,
    db_session: Session,
    settings: Settings,
    frozen_time: time_machine.Traveller,
) -> None:
    user = make_user(db_session)
    db_session.commit()

    signed_in_client(app, user, settings).post(LOGOUT)

    [event] = _committed_events(db_session)
    assert (event.actor_id, event.action, event.entity, event.entity_id, event.diff) == (
        user.id,
        "auth.logout",
        "user",
        str(user.id),
        None,
    )


def test_me_returns_the_login_body_and_the_feature_flags(
    app: FastAPI, client: TestClient, db_session: Session, settings: Settings
) -> None:
    user = make_user(db_session, role="HR_MANAGER", email="hr@acme.example", full_name="Hal")

    response = signed_in_client(app, user, settings).get(ME)

    assert response.status_code == 200
    assert response.json() == {
        "user": {
            "id": user.id,
            "email": "hr@acme.example",
            "full_name": "Hal",
            "role": "HR_MANAGER",
        },
        "permissions": [
            "EMPLOYEE_READ",
            "EMPLOYEE_WRITE",
            "SALARY_READ",
            "SALARY_WRITE",
            "INSIGHTS_READ",
            "EXPORT",
            "IMPORT",
            "ASK",
        ],
        "features": {"ask": False},
    }


def test_me_reports_ask_enabled_when_an_llm_api_key_is_set(db_session: Session) -> None:
    settings = make_settings(llm_api_key="test-llm-key")
    app = create_test_app(settings)
    app.dependency_overrides[get_session] = lambda: db_session

    response = signed_in_client(app, make_user(db_session), settings).get(ME)

    assert response.json()["features"] == {"ask": True}


def test_me_writes_no_audit_event(
    app: FastAPI, client: TestClient, db_session: Session, settings: Settings
) -> None:
    user = make_user(db_session)
    db_session.commit()

    signed_in_client(app, user, settings).get(ME)

    assert _committed_events(db_session) == []
