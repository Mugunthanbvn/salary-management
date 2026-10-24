"""Auth endpoints (docs/07-api-spec.md section 4, docs/08-security-rbac.md section 5)."""

import pytest
import time_machine
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.deps import get_session
from salary_api.core.security import decode_access_token
from tests.conftest import create_test_app
from tests.factories import DEFAULT_PASSWORD, make_settings, make_user

LOGIN = "/api/v1/auth/login"
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
