"""Who is calling and what may they do (docs/08-security-rbac.md sections 3.3 and 5.2).

The routes under /api/v1/_test exist only in these tests.
"""

from collections.abc import Callable
from datetime import timedelta

import pytest
import time_machine
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.deps import CurrentUser, require_permission
from salary_api.core.permissions import Permission, Role
from salary_api.core.security import create_access_token
from tests.conftest import signed_in_client
from tests.factories import make_user

PROBLEMS = "https://acme.example/problems/"
WHOAMI = "/api/v1/_test/whoami"
SALARIES = "/api/v1/_test/salaries"
AUDIT_SALARIES = "/api/v1/_test/audit-salaries"


@pytest.fixture(autouse=True)
def protected_routes(app: FastAPI) -> None:
    @app.get(WHOAMI)
    def whoami(principal: CurrentUser) -> dict[str, object]:
        return {"user_id": principal.user_id, "role": principal.role}

    @app.get(SALARIES, dependencies=[Depends(require_permission(Permission.SALARY_READ))])
    def salaries() -> dict[str, bool]:
        return {"ok": True}

    @app.get(
        AUDIT_SALARIES,
        dependencies=[Depends(require_permission(Permission.SALARY_READ, Permission.AUDIT_READ))],
    )
    def audit_salaries() -> dict[str, bool]:
        return {"ok": True}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _assert_unauthenticated(response_status: int, body: dict[str, object]) -> None:
    assert (response_status, body["type"]) == (401, f"{PROBLEMS}unauthenticated")


def test_a_request_without_a_token_is_unauthenticated(client: TestClient) -> None:
    response = client.get(WHOAMI)

    _assert_unauthenticated(response.status_code, response.json())
    assert response.headers["content-type"] == "application/problem+json"


def test_a_session_cookie_identifies_the_caller(
    app: FastAPI, db_session: Session, settings: Settings, client: TestClient
) -> None:
    user = make_user(db_session, role="VIEWER")

    response = signed_in_client(app, user, settings).get(WHOAMI)

    assert response.json() == {"user_id": user.id, "role": "VIEWER"}


def test_a_bearer_token_identifies_the_caller(
    client: TestClient, db_session: Session, settings: Settings
) -> None:
    user = make_user(db_session, role="ADMIN")
    token = create_access_token(user_id=user.id, role=user.role, settings=settings)

    response = client.get(WHOAMI, headers=_bearer(token))

    assert response.json() == {"user_id": user.id, "role": "ADMIN"}


def test_a_bearer_token_wins_over_a_session_cookie(
    client: TestClient, db_session: Session, settings: Settings
) -> None:
    user = make_user(db_session)
    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    client.cookies.set("session", "not-a-jwt")

    response = client.get(WHOAMI, headers=_bearer(token))

    assert response.status_code == 200


@pytest.mark.parametrize(
    "authorization", ["Bearer not-a-jwt", "Bearer ", "Basic dXNlcjpwYXNz", "not-a-jwt"]
)
def test_a_malformed_authorization_header_is_unauthenticated(
    client: TestClient, authorization: str
) -> None:
    response = client.get(WHOAMI, headers={"Authorization": authorization})

    _assert_unauthenticated(response.status_code, response.json())


def test_an_invalid_session_cookie_is_unauthenticated(client: TestClient) -> None:
    client.cookies.set("session", "not-a-jwt")

    response = client.get(WHOAMI)

    _assert_unauthenticated(response.status_code, response.json())


def test_an_expired_token_is_unauthenticated(
    app: FastAPI,
    client: TestClient,
    db_session: Session,
    settings: Settings,
    frozen_time: time_machine.Traveller,
) -> None:
    viewer = signed_in_client(app, make_user(db_session), settings)
    frozen_time.shift(timedelta(minutes=settings.jwt_ttl_minutes))

    response = viewer.get(WHOAMI)

    _assert_unauthenticated(response.status_code, response.json())


def test_a_token_of_a_user_deactivated_since_is_unauthenticated(
    app: FastAPI, client: TestClient, db_session: Session, settings: Settings
) -> None:
    user = make_user(db_session)
    signed_in = signed_in_client(app, user, settings)
    user.is_active = False
    db_session.flush()

    response = signed_in.get(WHOAMI)

    _assert_unauthenticated(response.status_code, response.json())


def test_a_token_of_an_unknown_user_is_unauthenticated(
    client: TestClient, settings: Settings
) -> None:
    token = create_access_token(user_id=999, role=Role.ADMIN, settings=settings)

    response = client.get(WHOAMI, headers=_bearer(token))

    _assert_unauthenticated(response.status_code, response.json())


def test_a_role_change_in_the_database_applies_to_the_next_request(
    app: FastAPI, client: TestClient, db_session: Session, settings: Settings
) -> None:
    user = make_user(db_session, role="HR_MANAGER")
    signed_in = signed_in_client(app, user, settings)  # the token's role claim says HR_MANAGER
    assert signed_in.get(SALARIES).status_code == 200
    user.role = Role.VIEWER
    db_session.flush()

    response = signed_in.get(SALARIES)

    assert response.status_code == 403


def test_a_missing_permission_is_forbidden(as_role: Callable[[str], TestClient]) -> None:
    response = as_role("VIEWER").get(SALARIES)

    assert response.status_code == 403
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert (body["type"], body["detail"]) == (f"{PROBLEMS}forbidden", "Requires SALARY_READ.")


def test_every_listed_permission_is_required(as_role: Callable[[str], TestClient]) -> None:
    hr_response = as_role("HR_MANAGER").get(AUDIT_SALARIES)
    admin_response = as_role("ADMIN").get(AUDIT_SALARIES)

    assert (hr_response.status_code, hr_response.json()["detail"]) == (
        403,
        "Requires AUDIT_READ.",
    )
    assert admin_response.status_code == 200


def test_an_anonymous_caller_gets_401_not_403_on_a_protected_route(client: TestClient) -> None:
    response = client.get(SALARIES)

    assert response.status_code == 401
