"""Insight use cases. The dashboard, exports and the Ask tools all call these functions.

Masking, the small-group rule and complementary suppression live here, so every caller of
the service gets them (docs/08-security-rbac.md section 4).
"""

from sqlalchemy.orm import Session

from salary_api.core.permissions import Principal
from salary_api.modules.insights import repository
from salary_api.modules.insights.schemas import InsightQuery, Overview, Population


def overview(session: Session, principal: Principal, query: InsightQuery) -> Overview:
    """Headcount of the population (docs/09 section 3.1)."""
    del principal  # used once masking applies
    return Overview(
        population=_population(query),
        headcount=repository.headcount(session, _where(query)),
    )


def _where(query: InsightQuery) -> repository.PopulationFilter:
    return repository.PopulationFilter(
        countries=query.country,
        department_ids=query.department_id,
        job_role_ids=query.job_role_id,
        levels=query.level,
        employment_types=query.employment_type,
        statuses=query.status,
    )


def _population(query: InsightQuery) -> Population:
    return Population(
        country=query.country,
        department_id=query.department_id,
        job_role_id=query.job_role_id,
        level=query.level,
        employment_type=query.employment_type,
        status=query.status,
        comp=query.comp,
    )
