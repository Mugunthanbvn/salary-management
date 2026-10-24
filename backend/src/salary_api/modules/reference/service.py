from sqlalchemy.orm import Session

from salary_api.domain.currency import SUPPORTED_CURRENCIES, minor_unit_exponent
from salary_api.domain.enums import EmploymentType, Level, SalaryReason
from salary_api.modules.reference import repository, schemas
from salary_api.modules.reference.models import Country


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
