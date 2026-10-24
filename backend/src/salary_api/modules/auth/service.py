import hashlib
from dataclasses import dataclass

from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.errors import Unauthenticated
from salary_api.core.models import utc_now
from salary_api.core.permissions import Permission, permissions_for
from salary_api.core.security import PasswordHasher, create_access_token
from salary_api.modules.audit.service import AuditAction, record_event
from salary_api.modules.auth.schemas import LoginRequest, LoginResponse, SessionUser
from salary_api.modules.users import repository as users
from salary_api.modules.users.models import User

INVALID_CREDENTIALS = "Invalid email or password"


@dataclass(frozen=True, slots=True)
class SignedIn:
    body: LoginResponse
    token: str


def login(
    session: Session, credentials: LoginRequest, *, settings: Settings, hasher: PasswordHasher
) -> SignedIn:
    """Check the credentials and audit the attempt; commits either way."""
    email = credentials.email
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


def email_hash(email: str) -> str:
    """SHA-256 (hex) of the normalised email: failed logins are counted by it, never by email."""
    return hashlib.sha256(email.encode()).hexdigest()


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
