from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.domain.enums import Level
from salary_api.modules.reference.models import Country, Department, FxRate, JobRole, PayBand


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


def list_fx_rates(session: Session) -> Sequence[FxRate]:
    return session.scalars(select(FxRate).order_by(FxRate.currency)).all()


def list_pay_bands_started(
    session: Session,
    *,
    on: date,
    countries: Sequence[str] = (),
    job_role_ids: Sequence[int] = (),
    levels: Sequence[Level] = (),
) -> Sequence[PayBand]:
    """Bands that start on or before `on`, by country, role, level, then start date.

    An empty sequence means no condition on that field.
    """
    query = select(PayBand).where(PayBand.effective_from <= on)
    if countries:
        query = query.where(PayBand.country_code.in_(countries))
    if job_role_ids:
        query = query.where(PayBand.job_role_id.in_(job_role_ids))
    if levels:
        query = query.where(PayBand.level.in_(levels))
    order = (PayBand.country_code, PayBand.job_role_id, PayBand.level, PayBand.effective_from)
    return session.scalars(query.order_by(*order)).all()
