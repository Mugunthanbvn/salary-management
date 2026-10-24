"""GET /insights/pay-equity/cohort: one cohort's members against its band (docs/07 8.11).

It lists individuals with their pay, so it needs SALARY_READ and every view is audited.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.core.errors import Forbidden
from salary_api.core.permissions import Principal, Role
from salary_api.domain.enums import Level
from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.insights import service
from salary_api.modules.insights.schemas import CohortQuery
from salary_api.modules.reference.models import JobFamily, JobRole
from tests.factories import make_department, make_employee, make_job_role, make_pay_band

COHORT = "/api/v1/insights/pay-equity/cohort"


def _principal(role: Role) -> Principal:
    return Principal(user_id=1, email="caller@acme.example", full_name="Caller", role=role)


@pytest.fixture
def csm(db_session: Session) -> JobRole:
    return make_job_role(
        db_session,
        "Customer Success Manager",
        department=make_department(db_session, "Customer Success"),
        family=JobFamily.CUSTOMER_SUCCESS,
    )


def _params(role: JobRole, **extra: Any) -> dict[str, Any]:
    return {"job_role_id": role.id, "level": "L2", "country": "DE"} | extra


@pytest.fixture
def cohort(db_session: Session, csm: JobRole) -> None:
    """Three CSMs at L2 in Germany against a EUR 50,000 midpoint, and one elsewhere."""
    make_pay_band(db_session, job_role=csm, level="L2", mid_minor=5_000_000)
    for code, base in (("301", 6_100_000), ("302", 3_999_950), ("303", 4_600_000)):
        make_employee(
            db_session, job_role=csm, level="L2", employee_code=f"ACME-000{code}", base_minor=base
        )
    make_employee(db_session, job_role=csm, level="L3", base_minor=1_000_000)


def _members(body: dict[str, Any]) -> list[tuple[str, str | None, str | None]]:
    return [(m["employee_code"], m["compa_ratio"], m["flag"]) for m in body["members"]]


@pytest.mark.usefixtures("frozen_time", "cohort")
def test_hr_sees_each_cohort_member_against_the_band(
    as_role: Callable[[str], TestClient], csm: JobRole
) -> None:
    response = as_role("HR_MANAGER").get(COHORT, params=_params(csm))

    assert response.status_code == 200
    body = response.json()
    assert body["job_role"] == {"id": csm.id, "title": "Customer Success Manager"}
    assert (body["level"], body["country_code"], body["currency"]) == ("L2", "DE", "EUR")
    assert body["department"] == {"id": csm.department_id, "name": "Customer Success"}
    assert body["band"] == {"min": 4_000_000, "mid": 5_000_000, "max": 6_000_000, "currency": "EUR"}
    # Lowest ratio first. 0.79999 shows as 0.80 but is flagged on the unrounded ratio.
    assert _members(body) == [
        ("ACME-000302", "0.80", "UNDERPAID"),
        ("ACME-000303", "0.92", "IN_BAND"),
        ("ACME-000301", "1.22", "OVERPAID"),
    ]
    first = body["members"][0]
    assert first["base"] == {"amount_minor": 3_999_950, "currency": "EUR"}
    assert (first["first_name"], first["employment_type"]) == ("Test", "FULL_TIME")
    assert first["no_compa_ratio_reason"] is None
    assert isinstance(first["employee_id"], int)


@pytest.mark.usefixtures("frozen_time", "cohort")
def test_a_part_timer_in_the_cohort_gets_no_compa_ratio(
    as_role: Callable[[str], TestClient], db_session: Session, csm: JobRole
) -> None:
    make_employee(
        db_session,
        job_role=csm,
        level="L2",
        employment_type="PART_TIME",
        employee_code="ACME-000390",
        base_minor=2_500_000,
    )

    body = (
        as_role("HR_MANAGER")
        .get(COHORT, params=_params(csm, employment_type=["FULL_TIME", "PART_TIME"]))
        .json()
    )

    [part_timer] = [m for m in body["members"] if m["employee_code"] == "ACME-000390"]
    assert (part_timer["compa_ratio"], part_timer["flag"]) == (None, None)
    assert part_timer["no_compa_ratio_reason"] == "not_full_time"
    assert body["members"][-1] == part_timer  # members without a ratio come last


@pytest.mark.usefixtures("frozen_time")
def test_a_cohort_without_a_band_lists_its_members_without_ratios(
    as_role: Callable[[str], TestClient], db_session: Session, csm: JobRole
) -> None:
    make_employee(db_session, job_role=csm, level="L2", employee_code="ACME-000401")

    body = as_role("HR_MANAGER").get(COHORT, params=_params(csm)).json()

    assert body["band"] is None
    assert _members(body) == [("ACME-000401", None, None)]
    assert body["members"][0]["no_compa_ratio_reason"] == "no_band"


@pytest.mark.parametrize("missing", ["job_role_id", "level", "country"])
def test_the_cohort_needs_a_job_role_a_level_and_a_country(
    as_role: Callable[[str], TestClient], csm: JobRole, missing: str
) -> None:
    params = _params(csm)
    del params[missing]

    response = as_role("HR_MANAGER").get(COHORT, params=params)

    assert response.status_code == 422
    assert response.json()["errors"][0]["loc"] == ["query", missing]


def test_an_unknown_job_role_is_a_validation_error(
    as_role: Callable[[str], TestClient], db_session: Session, csm: JobRole
) -> None:
    make_employee(db_session, country="DE")  # so Germany exists

    response = as_role("HR_MANAGER").get(COHORT, params=_params(csm, job_role_id=csm.id + 99))

    assert response.status_code == 422
    assert response.json()["errors"] == [
        {
            "loc": ["query", "job_role_id"],
            "code": "not_found",
            "message": f"Unknown job role {csm.id + 99}.",
        }
    ]


def test_viewer_cannot_see_cohort_members(
    as_role: Callable[[str], TestClient], csm: JobRole
) -> None:
    response = as_role("VIEWER").get(COHORT, params=_params(csm))

    assert response.status_code == 403
    assert response.json()["type"] == "https://acme.example/problems/forbidden"


def test_the_service_refuses_cohort_members_to_a_caller_without_salary_read(
    db_session: Session, csm: JobRole
) -> None:
    query = CohortQuery(job_role_id=csm.id, level=Level.L2, country="DE")

    with pytest.raises(Forbidden):
        service.pay_equity_cohort(db_session, _principal(Role.VIEWER), query)


@pytest.mark.usefixtures("frozen_time", "cohort")
def test_viewing_a_cohort_writes_one_individuals_view_event_with_the_filters(
    as_role: Callable[[str], TestClient], db_session: Session, csm: JobRole
) -> None:
    as_role("HR_MANAGER").get(COHORT, params=_params(csm))

    query = select(AuditEvent).where(AuditEvent.action == "insights.individuals_view")
    [event] = db_session.scalars(query)
    assert event.diff == {
        "endpoint": "pay-equity/cohort",
        "filters": {
            "job_role_id": csm.id,
            "level": "L2",
            "country": "DE",
            "employment_type": ["FULL_TIME"],
            "status": ["ACTIVE"],
        },
    }
