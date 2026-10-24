"""Login failure limit: 5 failures per email in 15 minutes → 429 (docs/glossary.md section 3).

Failures are counted from `auth.login_failed` audit events, so the limit holds across
serverless instances (docs/08-security-rbac.md section 9).
"""

from datetime import timedelta

import pytest
import time_machine
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from salary_api.modules.audit.models import AuditEvent
from tests.factories import DEFAULT_PASSWORD, make_user

LOGIN = "/api/v1/auth/login"
EMAIL = "hr@acme.example"


def _fail_logins(
    client: TestClient, traveller: time_machine.Traveller, times: int, email: str = EMAIL
) -> None:
    """`times` failed logins, one minute apart; the clock ends one minute after the last."""
    for _ in range(times):
        response = client.post(LOGIN, json={"email": email, "password": "not the password"})
        assert response.status_code == 401
        traveller.shift(timedelta(minutes=1))


def _login(client: TestClient, email: str = EMAIL):
    return client.post(LOGIN, json={"email": email, "password": DEFAULT_PASSWORD})


@pytest.fixture
def user_email(db_session: Session) -> str:
    return make_user(db_session, email=EMAIL).email


@pytest.mark.usefixtures("user_email")
def test_four_failures_still_allow_a_login(
    client: TestClient, frozen_time: time_machine.Traveller
) -> None:
    _fail_logins(client, frozen_time, times=4)

    assert _login(client).status_code == 200


@pytest.mark.usefixtures("user_email")
def test_five_failures_block_even_the_right_password_with_429(
    client: TestClient, frozen_time: time_machine.Traveller
) -> None:
    _fail_logins(client, frozen_time, times=5)

    response = _login(client)

    assert response.status_code == 429
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "https://acme.example/problems/rate-limited"
    assert "set-cookie" not in response.headers


@pytest.mark.usefixtures("user_email")
def test_retry_after_is_the_wait_until_the_oldest_failure_is_15_minutes_old(
    client: TestClient, frozen_time: time_machine.Traveller
) -> None:
    _fail_logins(client, frozen_time, times=5)  # at 0, 1, 2, 3 and 4 minutes; now 5 minutes

    response = _login(client)

    assert response.headers["retry-after"] == str(10 * 60)


@pytest.mark.usefixtures("user_email")
def test_the_limit_holds_until_the_last_second_of_the_window(
    client: TestClient, frozen_time: time_machine.Traveller
) -> None:
    _fail_logins(client, frozen_time, times=5)
    frozen_time.shift(timedelta(minutes=10) - timedelta(seconds=1))  # oldest is 14:59 old

    response = _login(client)

    assert (response.status_code, response.headers["retry-after"]) == (429, "1")


@pytest.mark.usefixtures("user_email")
def test_a_login_is_allowed_again_once_the_oldest_failure_leaves_the_window(
    client: TestClient, frozen_time: time_machine.Traveller
) -> None:
    _fail_logins(client, frozen_time, times=5)
    frozen_time.shift(timedelta(minutes=10))  # the oldest failure is exactly 15 minutes old

    assert _login(client).status_code == 200


@pytest.mark.usefixtures("user_email")
def test_the_limit_counts_failures_per_email(
    client: TestClient, db_session: Session, frozen_time: time_machine.Traveller
) -> None:
    other = make_user(db_session, email="other@acme.example")
    _fail_logins(client, frozen_time, times=5, email=EMAIL)

    assert _login(client, email=other.email).status_code == 200


def test_unknown_emails_are_limited_too(
    client: TestClient, frozen_time: time_machine.Traveller
) -> None:
    _fail_logins(client, frozen_time, times=5, email="nobody@acme.example")

    assert _login(client, email="nobody@acme.example").status_code == 429


@pytest.mark.usefixtures("user_email")
def test_a_blocked_attempt_is_not_counted_as_another_failure(
    client: TestClient, db_session: Session, frozen_time: time_machine.Traveller
) -> None:
    _fail_logins(client, frozen_time, times=5)

    client.post(LOGIN, json={"email": EMAIL, "password": "not the password"})

    db_session.rollback()
    assert db_session.scalar(select(func.count()).select_from(AuditEvent)) == 5
