import hashlib
import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.errors import RateLimited, Unauthenticated
from salary_api.core.models import utc_now
from salary_api.core.permissions import Permission, Principal, permissions_for
from salary_api.core.security import (
    InvalidToken,
    PasswordHasher,
    create_access_token,
    decode_access_token,
)
from salary_api.modules.audit.service import AuditAction, events_since, record_event
from salary_api.modules.auth.schemas import LoginRequest, LoginResponse, SessionUser
from salary_api.modules.users import repository as users
from salary_api.modules.users.models import User

INVALID_CREDENTIALS = "Invalid email or password"
SIGN_IN_REQUIRED = "Sign in to continue."
SESSION_NOT_VALID = "Your session has expired or is no longer valid. Sign in again."
# docs/glossary.md section 3: 5 failures per email in 15 minutes → 429.
LOGIN_FAILURE_LIMIT = 5
LOGIN_FAILURE_WINDOW = timedelta(minutes=15)


@dataclass(frozen=True, slots=True)
class SignedIn:
    body: LoginResponse
    token: str


def login(
    session: Session, credentials: LoginRequest, *, settings: Settings, hasher: PasswordHasher
) -> SignedIn:
    """Check the credentials and audit the attempt; commits either way.

    Refused with 429, before any password check, while the email is over the failure limit.
    """
    email = credentials.email
    _refuse_while_over_failure_limit(session, email_hash(email), now=utc_now())
    user = users.get_by_email(session, email)
    # Always one password check, so an unknown email takes as long as a known one.
    password_ok = hasher.verify(
        credentials.password, user.password_hash if user else hasher.dummy_hash
    )
    if user is None or not user.is_active or not password_ok:
        _record_failed_login(session, email=email, user=user)
        session.commit()  # the failure stays recorded: the login failure limit counts it
        raise Unauthenticated(INVALID_CREDENTIALS)  # one message: no user enumeration

    if hasher.needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(credentials.password)  # upgrade outdated parameters
    user.last_login_at = utc_now()
    record_event(
        session,
        actor_id=user.id,
        action=AuditAction.AUTH_LOGIN,
        entity="user",
        entity_id=user.id,
        diff={"result": "success"},
    )
    session.commit()
    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    return SignedIn(body=_login_response(user), token=token)


def authenticate(session: Session, token: str | None, *, settings: Settings) -> Principal:
    """The caller behind a session token. The user is loaded on every request, so a
    deactivated user or a changed role takes effect at once."""
    if not token:
        raise Unauthenticated(SIGN_IN_REQUIRED)
    try:
        claims = decode_access_token(token, settings)
    except InvalidToken:
        raise Unauthenticated(SESSION_NOT_VALID) from None
    user = users.get_by_id(session, claims.user_id)
    if user is None or not user.is_active:
        raise Unauthenticated(SESSION_NOT_VALID)
    return Principal(user_id=user.id, email=user.email, full_name=user.full_name, role=user.role)


def email_hash(email: str) -> str:
    """SHA-256 (hex) of the normalised email: failed logins are counted by it, never by email."""
    return hashlib.sha256(email.encode()).hexdigest()


def _refuse_while_over_failure_limit(session: Session, hashed_email: str, *, now: datetime) -> None:
    """Counted from audit events, so the limit holds across serverless instances."""
    failures = [
        event.at
        for event in events_since(
            session, action=AuditAction.AUTH_LOGIN_FAILED, since=now - LOGIN_FAILURE_WINDOW
        )
        if event.diff is not None and event.diff.get("email_hash") == hashed_email
    ]
    if len(failures) < LOGIN_FAILURE_LIMIT:
        return
    # The limit lifts when the oldest of the last LOGIN_FAILURE_LIMIT failures leaves the window.
    lifts_at = failures[-LOGIN_FAILURE_LIMIT] + LOGIN_FAILURE_WINDOW
    raise RateLimited(
        "Too many failed sign-in attempts. Try again later.",
        retry_after_seconds=math.ceil((lifts_at - now).total_seconds()),
    )


def _record_failed_login(session: Session, *, email: str, user: User | None) -> None:
    # No actor: the caller is not authenticated. The targeted user, if known, is the entity.
    record_event(
        session,
        actor_id=None,
        action=AuditAction.AUTH_LOGIN_FAILED,
        entity="auth",
        entity_id=user.id if user else None,
        diff={"email_hash": email_hash(email)},
    )


def _login_response(user: User) -> LoginResponse:
    granted = permissions_for(user.role)
    return LoginResponse(
        user=SessionUser(id=user.id, email=user.email, full_name=user.full_name, role=user.role),
        permissions=[permission for permission in Permission if permission in granted],
    )
