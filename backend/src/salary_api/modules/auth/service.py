from dataclasses import dataclass

from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.errors import Unauthenticated
from salary_api.core.permissions import Permission, permissions_for
from salary_api.core.security import PasswordHasher, create_access_token
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
    user = users.get_by_email(session, credentials.email)
    # Always one password check, so an unknown email takes as long as a known one.
    password_ok = hasher.verify(
        credentials.password, user.password_hash if user else hasher.dummy_hash
    )
    if user is None or not user.is_active or not password_ok:
        raise Unauthenticated(INVALID_CREDENTIALS)  # one message: no user enumeration
    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    return SignedIn(body=_login_response(user), token=token)


def _login_response(user: User) -> LoginResponse:
    granted = permissions_for(user.role)
    return LoginResponse(
        user=SessionUser(id=user.id, email=user.email, full_name=user.full_name, role=user.role),
        permissions=[permission for permission in Permission if permission in granted],
    )
