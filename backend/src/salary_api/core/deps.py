"""FastAPI dependencies shared by routers."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from salary_api.core.config import Settings
from salary_api.core.security import PasswordHasher

_PASSWORD_HASHER = PasswordHasher()


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
SettingsDep = Annotated[Settings, Depends(get_settings)]
PasswordHasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]
