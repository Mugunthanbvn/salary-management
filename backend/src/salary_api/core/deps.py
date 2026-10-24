"""FastAPI dependencies shared by routers: database session, settings, the caller."""

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, Path, Request
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from salary_api.core.config import Settings
from salary_api.core.errors import Forbidden
from salary_api.core.permissions import Permission, Principal
from salary_api.core.schemas import MAX_ID
from salary_api.core.security import SESSION_COOKIE, PasswordHasher
from salary_api.modules.auth import service as auth_service

_PASSWORD_HASHER = PasswordHasher()

# auto_error=False: a missing token becomes our own 401 problem, not FastAPI's default.
_session_cookie = APIKeyCookie(
    name=SESSION_COOKIE,
    auto_error=False,
    scheme_name="SessionCookie",
    description="The session JWT that POST /auth/login sets (browsers).",
)
_bearer_token = HTTPBearer(
    auto_error=False,
    scheme_name="BearerToken",
    description="The same JWT as `Authorization: Bearer` (server-side fetches).",
)


def get_session(request: Request) -> Iterator[Session]:
    """One database session per request, closed when the response is sent."""
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_password_hasher() -> PasswordHasher:
    """pwdlib's default argon2id parameters. Tests override this with cheaper ones."""
    return _PASSWORD_HASHER


SessionDep = Annotated[Session, Depends(get_session)]
# A row id in a path: 1 to MAX_ID (a 64-bit integer), else 422 like a query or body id.
IdPath = Annotated[int, Path(ge=1, le=MAX_ID)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
PasswordHasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]


def current_user(
    session: SessionDep,
    settings: SettingsDep,
    cookie_token: Annotated[str | None, Depends(_session_cookie)],
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_token)],
) -> Principal:
    """The caller, from `Authorization: Bearer` if sent, else the `session` cookie. 401 if none."""
    token = bearer.credentials if bearer else cookie_token
    return auth_service.authenticate(session, token, settings=settings)


CurrentUser = Annotated[Principal, Depends(current_user)]


def require_permission(*permissions: Permission) -> Callable[[Principal], Principal]:
    """A dependency that lets the caller through only with every listed permission (else 403).

    `Depends(require_permission(Permission.SALARY_READ))`. It returns the Principal, so a
    route can also take it as a parameter.
    """

    def check(principal: CurrentUser) -> Principal:
        missing = [permission for permission in permissions if not principal.has(permission)]
        if missing:
            raise Forbidden(f"Requires {', '.join(missing)}.")
        return principal

    return check
