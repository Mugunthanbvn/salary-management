"""Reference data for forms and filters (docs/07-api-spec.md section 5)."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.modules.reference.models import JobFamily
from tests.factories import make_country, make_department, make_job_role

REFERENCE = "/api/v1/reference"


def test_reference_lists_every_dropdown_value_in_display_order(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_country(db_session, "JP")
    make_country(db_session, "DE", is_active=False)
    customer_success = make_department(db_session, "Customer Success")
    engineering = make_department(db_session, "Engineering")
    manager = make_job_role(
        db_session,
        "Customer Success Manager",
        department=customer_success,
        family=JobFamily.CUSTOMER_SUCCESS,
    )
    engineer = make_job_role(db_session, "Backend Engineer", department=engineering)

    response = as_role("VIEWER").get(REFERENCE)

    assert response.status_code == 200
    assert response.json() == {
        "countries": [
            {"code": "DE", "name": "Germany", "default_currency": "EUR", "is_active": False},
            {"code": "JP", "name": "Japan", "default_currency": "JPY", "is_active": True},
        ],
        "departments": [
            {"id": customer_success.id, "name": "Customer Success"},
            {"id": engineering.id, "name": "Engineering"},
        ],
        "job_roles": [
            {
                "id": engineer.id,
                "title": "Backend Engineer",
                "department_id": engineering.id,
                "family": "ENGINEERING",
            },
            {
                "id": manager.id,
                "title": "Customer Success Manager",
                "department_id": customer_success.id,
                "family": "CUSTOMER_SUCCESS",
            },
        ],
        "levels": [
            {"code": "L1", "label": "Associate"},
            {"code": "L2", "label": "Mid"},
            {"code": "L3", "label": "Senior"},
            {"code": "L4", "label": "Lead/Staff"},
            {"code": "L5", "label": "Principal"},
            {"code": "L6", "label": "Director"},
        ],
        "employment_types": ["FULL_TIME", "PART_TIME", "CONTRACTOR"],
        "currencies": [
            {"code": "AUD", "exponent": 2},
            {"code": "BRL", "exponent": 2},
            {"code": "CAD", "exponent": 2},
            {"code": "EUR", "exponent": 2},
            {"code": "GBP", "exponent": 2},
            {"code": "INR", "exponent": 2},
            {"code": "JPY", "exponent": 0},
            {"code": "SGD", "exponent": 2},
            {"code": "USD", "exponent": 2},
        ],
        "salary_change_reasons": ["HIRE", "PROMOTION", "MERIT", "MARKET_ADJUSTMENT", "CORRECTION"],
    }
