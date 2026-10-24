"""The users table and its repository (docs/06-data-model.md section 4.1)."""

import pytest
import time_machine
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from salary_api.core.permissions import Role
from salary_api.modules.users import repository
from salary_api.modules.users.models import User
from tests.conftest import FROZEN_NOW


def _add_user(session: Session, email: str = "ana@acme.example") -> User:
    user = User(
        email=email, full_name="Ana Silva", password_hash="not-a-real-hash", role=Role.HR_MANAGER
    )
    session.add(user)
    session.flush()
    return user


def test_a_saved_user_is_found_by_email_and_by_id(
    db_session: Session, frozen_time: time_machine.Traveller
) -> None:
    user_id = _add_user(db_session).id
    db_session.expunge_all()  # read back from the database, not the identity map

    by_email = repository.get_by_email(db_session, "ana@acme.example")
    by_id = repository.get_by_id(db_session, user_id)

    assert by_email is not None
    assert by_email is by_id
    assert (by_email.full_name, by_email.role, by_email.is_active) == (
        "Ana Silva",
        Role.HR_MANAGER,
        True,
    )
    assert (by_email.created_at, by_email.updated_at, by_email.last_login_at) == (
        FROZEN_NOW,
        FROZEN_NOW,
        None,
    )


def test_an_unknown_email_or_id_finds_no_user(db_session: Session) -> None:
    assert repository.get_by_email(db_session, "nobody@acme.example") is None
    assert repository.get_by_id(db_session, 999) is None


def test_two_users_cannot_share_an_email(db_session: Session) -> None:
    _add_user(db_session, email="ana@acme.example")

    with pytest.raises(IntegrityError, match="UNIQUE"):
        _add_user(db_session, email="ana@acme.example")


def test_the_database_rejects_a_role_outside_the_glossary(db_session: Session) -> None:
    row = {
        "email": "root@acme.example",
        "full_name": "Root",
        "password_hash": "not-a-real-hash",
        "role": "ROOT",
        "is_active": True,
        "created_at": FROZEN_NOW,
        "updated_at": FROZEN_NOW,
    }

    with pytest.raises(IntegrityError, match="CHECK"):
        db_session.execute(insert(User).values(**row))


def test_a_user_email_is_stored_trimmed_and_lowercased(db_session: Session) -> None:
    user = _add_user(db_session, email="  Admin@Acme.Example ")

    assert user.email == "admin@acme.example"


def test_emails_that_differ_only_in_case_cannot_both_be_saved(db_session: Session) -> None:
    _add_user(db_session, email="Ana@acme.example")

    with pytest.raises(IntegrityError, match="UNIQUE"):
        _add_user(db_session, email="ana@ACME.example")
