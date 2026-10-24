"""A parallel burst of logins for one email gets at most 5 real answers.

Every attempt in a burst passes the block check before any of them has recorded its
failure. The burst is simulated without threads: while one attempt's password is being
checked, other attempts for the same email fail and commit.
"""

import pytest
import time_machine
from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.core.errors import RateLimited, Unauthenticated
from salary_api.core.security import PasswordHasher
from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.audit.service import AuditAction, record_event
from salary_api.modules.auth import service
from salary_api.modules.auth.schemas import LoginRequest
from tests.factories import DEFAULT_PASSWORD, FAST_ARGON2, make_settings, make_user

EMAIL = "hr@acme.example"
SETTINGS = make_settings()


class _BurstDuringCheck(PasswordHasher):
    """The fast test hasher; during its password check, `parallel` other attempts fail."""

    def __init__(self, session: Session, parallel: int) -> None:
        super().__init__(FAST_ARGON2)
        self._session = session
        self._parallel = parallel

    def verify(self, password: str, password_hash: str) -> bool:
        for _ in range(self._parallel):
            record_event(
                self._session,
                actor_id=None,
                action=AuditAction.AUTH_LOGIN_FAILED,
                entity="auth",
                entity_id=None,
                diff={"email_hash": service.email_hash(EMAIL)},
            )
        self._session.commit()
        self._parallel = 0
        return super().verify(password, password_hash)


def _login(session: Session, password: str, parallel_failures: int) -> service.SignedIn:
    return service.login(
        session,
        LoginRequest(email=EMAIL, password=password),
        settings=SETTINGS,
        hasher=_BurstDuringCheck(session, parallel_failures),
    )


@pytest.fixture(autouse=True)
def _user(db_session: Session, frozen_time: time_machine.Traveller) -> None:
    make_user(db_session, email=EMAIL)
    db_session.commit()


def test_the_right_password_gets_429_when_a_burst_reached_the_limit_during_its_check(
    db_session: Session,
) -> None:
    with pytest.raises(RateLimited):
        _login(db_session, DEFAULT_PASSWORD, parallel_failures=5)

    actions = db_session.scalars(select(AuditEvent.action)).all()
    assert "auth.login" not in actions


def test_a_wrong_password_after_the_fifth_failure_of_a_burst_gets_429(
    db_session: Session,
) -> None:
    with pytest.raises(RateLimited):
        _login(db_session, "not the password", parallel_failures=5)  # this is the 6th


def test_the_failure_that_reaches_the_limit_still_gets_401(db_session: Session) -> None:
    with pytest.raises(Unauthenticated):
        _login(db_session, "not the password", parallel_failures=4)  # this is the 5th
