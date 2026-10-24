from fastapi import APIRouter, Response

from salary_api.core.config import Settings
from salary_api.core.deps import CurrentUser, PasswordHasherDep, SessionDep, SettingsDep
from salary_api.core.errors import problem_responses
from salary_api.core.security import SESSION_COOKIE
from salary_api.modules.auth import service
from salary_api.modules.auth.schemas import LoginRequest, LoginResponse, MeResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    responses=problem_responses(401, 429),
    summary="Sign in (public)",
)
def login(
    credentials: LoginRequest,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    hasher: PasswordHasherDep,
) -> LoginResponse:
    signed_in = service.login(session, credentials, settings=settings, hasher=hasher)
    _set_session_cookie(response, signed_in.token, settings)
    return signed_in.body


@router.post("/logout", status_code=204, responses=problem_responses(401), summary="Sign out")
def logout(
    principal: CurrentUser, response: Response, session: SessionDep, settings: SettingsDep
) -> None:
    service.logout(session, principal)
    # Same attributes as when it was set, or the browser keeps the cookie.
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.get(
    "/me",
    response_model=MeResponse,
    responses=problem_responses(401),
    summary="The signed-in user and features",
)
def me(principal: CurrentUser, settings: SettingsDep) -> MeResponse:
    return service.me(principal, settings=settings)


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    """HttpOnly, so scripts cannot read it; SameSite=Lax against CSRF (docs/08 section 5.3)."""
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.jwt_ttl_minutes * 60,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
