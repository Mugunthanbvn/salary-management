import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.errors import RateLimited, Unauthenticated
from salary_api.core.models import utc_now
from salary_api.core.permissions import Permission, Principal
from salary_api.core.security import (
    InvalidToken,
    PasswordHasher,
    create_access_token,
    decode_access_token,
)
from salary_api.modules.audit.service import AuditAction, events_since, record_event
from salary_api.modules.auth.schemas import (
    Features,
    LoginRequest,
    LoginResponse,
    MeResponse,
    SessionUser,
)
from salary_api.modules.users import repository as users
from salary_api.modules.users.models import User

INVALID_CREDENTIALS = "Invalid email or password"
SIGN_IN_REQUIRED = "Sign in to continue."
SESSION_NOT_VALID = "Your session has expired or is no longer valid. Sign in again."
# docs/glossary.md section 3: 5 failures per email in 15 minutes → 429 for 15 minutes.
LOGIN_FAILURE_LIMIT = 5
LOGIN_FAILURE_WINDOW = timedelta(minutes=15)
LOGIN_BLOCK = timedelta(minutes=15)


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
    _refuse_while_blocked(session, email_hash(email), now=utc_now())
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
    return SignedIn(body=_login_response(_principal(user)), token=token)


def logout(session: Session, principal: Principal) -> None:
    """Audit the sign-out. The token itself stays valid until it expires (no denylist)."""
    record_event(
        session,
        actor_id=principal.user_id,
        action=AuditAction.AUTH_LOGOUT,
        entity="user",
        entity_id=principal.user_id,
    )
    session.commit()


def me(principal: Principal, *, settings: Settings) -> MeResponse:
    body = _login_response(principal)
    return MeResponse(
        user=body.user,
        permissions=body.permissions,
        features=Features(ask=bool(settings.llm_api_key.get_secret_value())),
    )


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
    return _principal(user)


def email_hash(email: str) -> str:
    """SHA-256 (hex) of the normalised email: failed logins are counted by it, never by email."""
    return hashlib.sha256(email.encode()).hexdigest()


def _refuse_while_blocked(session: Session, hashed_email: str, *, now: datetime) -> None:
    """429 while the email is blocked. Counted from audit events, so the limit holds across
    serverless instances."""
    # A block that is still on started under 15 minutes ago, from a failure whose own
    # 15-minute window started under 30 minutes ago.
    events = events_since(
        session,
        action=AuditAction.AUTH_LOGIN_FAILED,
        since=now - LOGIN_BLOCK - LOGIN_FAILURE_WINDOW,
    )
    failures = [
        event.at
        for event in events
        if event.diff is not None and event.diff.get("email_hash") == hashed_email
    ]
    block_ends_at = _block_ends_at(failures)
    if block_ends_at is not None and block_ends_at > now:
        raise RateLimited(
            "Too many failed sign-in attempts. Try again later.",
            retry_after_seconds=math.ceil((block_ends_at - now).total_seconds()),
        )


def _block_ends_at(failures: Sequence[datetime]) -> datetime | None:
    """When the latest block ends, from failure times oldest first; None if there was none.

    A failure reaches the limit when it is the LOGIN_FAILURE_LIMIT-th (or later) within
    LOGIN_FAILURE_WINDOW. The block lasts LOGIN_BLOCK from the latest such failure.
    """
    reached_at: datetime | None = None
    oldest = 0  # index of the oldest failure inside the window that ends at `at`
    for index, at in enumerate(failures):
        while failures[oldest] <= at - LOGIN_FAILURE_WINDOW:
            oldest += 1
        if index - oldest + 1 >= LOGIN_FAILURE_LIMIT:
            reached_at = at
    return None if reached_at is None else reached_at + LOGIN_BLOCK


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


def _principal(user: User) -> Principal:
    return Principal(user_id=user.id, email=user.email, full_name=user.full_name, role=user.role)


def _login_response(principal: Principal) -> LoginResponse:
    return LoginResponse(
        user=SessionUser(
            id=principal.user_id,
            email=principal.email,
            full_name=principal.full_name,
            role=principal.role,
        ),
        # In glossary order, so the response is stable.
        permissions=[permission for permission in Permission if principal.has(permission)],
    )
