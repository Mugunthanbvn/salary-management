from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.modules.users.models import User


def get_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def get_by_email(session: Session, email: str) -> User | None:
    """`email` must already be normalised (trimmed, lowercased), as stored."""
    return session.scalars(select(User).where(User.email == email)).one_or_none()
