from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.modules.reference.models import Country, Department, JobRole


def list_countries(session: Session) -> Sequence[Country]:
    return session.scalars(select(Country).order_by(Country.name, Country.code)).all()


def list_departments(session: Session) -> Sequence[Department]:
    return session.scalars(select(Department).order_by(Department.name)).all()


def list_job_roles(session: Session) -> Sequence[JobRole]:
    return session.scalars(select(JobRole).order_by(JobRole.title)).all()


def get_country(session: Session, code: str) -> Country | None:
    return session.get(Country, code)


def get_job_role(session: Session, job_role_id: int) -> JobRole | None:
    return session.get(JobRole, job_role_id)
