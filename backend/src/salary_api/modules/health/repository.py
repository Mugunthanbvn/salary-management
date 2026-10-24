from sqlalchemy import select
from sqlalchemy.orm import Session


def ping(session: Session) -> None:
    """Run `SELECT 1`: a read-only round trip to the database."""
    session.execute(select(1))
