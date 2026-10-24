from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from salary_api.core.models import utc_now
from salary_api.domain import money
from salary_api.domain.currency import SUPPORTED_CURRENCIES, minor_unit_exponent
from salary_api.domain.enums import EmploymentType, Level, SalaryReason
from salary_api.modules.reference import repository, schemas
from salary_api.modules.reference.models import Country, PayBand


def reference_data(session: Session) -> schemas.ReferenceData:
    """Countries by name, departments by name, job roles by title; enums in glossary order."""
    return schemas.ReferenceData(
        countries=countries(session),
        departments=[
            schemas.Department(id=department.id, name=department.name)
            for department in repository.list_departments(session)
        ],
        job_roles=[
            schemas.JobRole(
                id=role.id, title=role.title, department_id=role.department_id, family=role.family
            )
            for role in repository.list_job_roles(session)
        ],
        levels=[schemas.LevelOption(code=level, label=level.label) for level in Level],
        employment_types=list(EmploymentType),
        currencies=[
            schemas.CurrencyOption(code=code, exponent=minor_unit_exponent(code))
            for code in sorted(SUPPORTED_CURRENCIES)
        ],
        salary_change_reasons=list(SalaryReason),
    )


def countries(session: Session) -> list[schemas.Country]:
    """Every country, active or not, by name."""
    return [_country(country) for country in repository.list_countries(session)]


def _country(country: Country) -> schemas.Country:
    return schemas.Country(
        code=country.code,
        name=country.name,
        default_currency=country.default_currency,
        is_active=country.is_active,
    )


def usd_rates(session: Session) -> dict[str, money.FxRate]:
    """The current USD rate of each currency that has one, as dated Decimal rates (ADR 0005)."""
    return {
        row.currency: money.FxRate(row.currency, Decimal(row.rate_to_usd), row.as_of)
        for row in repository.list_fx_rates(session)
    }


def current_pay_bands(
    session: Session,
    *,
    today: date,
    countries: Sequence[str] = (),
    job_role_ids: Sequence[int] = (),
    levels: Sequence[Level] = (),
) -> list[PayBand]:
    """The band in force per role + level + country: the latest one started by `today`."""
    current: dict[tuple[int, Level, str], PayBand] = {}
    for band in repository.list_pay_bands_started(
        session, on=today, countries=countries, job_role_ids=job_role_ids, levels=levels
    ):  # oldest first within a key, so the latest one stays
        current[band.job_role_id, band.level, band.country_code] = band
    return list(current.values())


def pay_bands(session: Session, query: schemas.PayBandQuery) -> schemas.PayBands:
    """The bands in force today, filtered (docs/07 section 8.12). Read-only in v1."""
    bands = current_pay_bands(
        session,
        today=utc_now().date(),
        countries=query.country,
        job_role_ids=query.job_role_id,
        levels=query.level,
    )
    return schemas.PayBands(
        bands=[
            schemas.PayBandItem(
                job_role_id=band.job_role_id,
                level=band.level,
                country_code=band.country_code,
                currency=band.currency,
                min=band.min_minor,
                mid=band.mid_minor,
                max=band.max_minor,
                effective_from=band.effective_from,
            )
            for band in bands
        ]
    )


def fx_rates(session: Session) -> schemas.FxRates:
    """The current USD rate of each currency, with its date and source (docs/07 section 9)."""
    return schemas.FxRates(
        rates=[
            schemas.FxRateItem(
                currency=rate.currency,
                rate_to_usd=rate.rate_to_usd,
                as_of=rate.as_of,
                source=rate.source,
            )
            for rate in repository.list_fx_rates(session)
        ]
    )
