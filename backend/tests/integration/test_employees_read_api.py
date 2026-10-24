"""Reading employees: detail and list (docs/07-api-spec.md sections 6.1 and 6.3)."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.factories import make_employee, make_job_role

EMPLOYEES = "/api/v1/employees"
PROBLEMS = "https://acme.example/problems/"


def test_hr_sees_an_employee_with_their_current_salary_and_components(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    role = make_job_role(db_session, "Software Engineer")
    employee = make_employee(
        db_session,
        country="IN",
        job_role=role,
        level="L3",
        first_name="Priya",
        last_name="Sharma",
        email="priya.sharma@acme.example",
        employee_code="ACME-004217",
        base_minor=240_000_000,
        components=[("ALLOWANCE", "HRA", 96_000_000), ("BONUS_TARGET", "Target bonus", 26_400_000)],
    )

    response = as_role("HR_MANAGER").get(f"{EMPLOYEES}/{employee.id}")

    assert response.status_code == 200
    inr = "INR"
    assert response.json() == {
        "id": employee.id,
        "employee_code": "ACME-004217",
        "first_name": "Priya",
        "last_name": "Sharma",
        "email": "priya.sharma@acme.example",
        "job_role": {"id": role.id, "title": "Software Engineer"},
        "department": {"id": role.department_id, "name": "Engineering"},
        "level": "L3",
        "employment_type": "FULL_TIME",
        "country_code": "IN",
        "status": "ACTIVE",
        "hire_date": "2024-01-15",
        "termination_date": None,
        "current_base": {"amount_minor": 240_000_000, "currency": inr},
        "current_total": {"amount_minor": 362_400_000, "currency": inr},
        "current_salary": {
            "id": employee.current_salary_record_id,
            "effective_date": "2024-01-15",
            "reason": "HIRE",
            "components": [
                {
                    "type": "ALLOWANCE",
                    "name": "HRA",
                    "amount": {"amount_minor": 96_000_000, "currency": inr},
                },
                {
                    "type": "BONUS_TARGET",
                    "name": "Target bonus",
                    "amount": {"amount_minor": 26_400_000, "currency": inr},
                },
            ],
        },
        "salary_masked": False,
        "version": 1,
    }


def test_an_unknown_employee_is_404_not_found(as_role: Callable[[str], TestClient]) -> None:
    response = as_role("HR_MANAGER").get(f"{EMPLOYEES}/999")

    assert response.status_code == 404
    assert response.json()["type"] == f"{PROBLEMS}not-found"


def test_a_path_that_is_not_an_integer_id_is_not_an_employee(
    as_role: Callable[[str], TestClient],
) -> None:
    response = as_role("HR_MANAGER").get(f"{EMPLOYEES}/export")

    assert response.status_code in {404, 405}  # never a 422 from the id route


def test_list_shows_active_employees_by_last_name_first_name_then_id(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    becker = make_employee(db_session, first_name="Ana", last_name="Becker")
    zoe_adams = make_employee(db_session, first_name="Zoe", last_name="Adams")
    ben_adams = make_employee(db_session, first_name="Ben", last_name="Adams")
    another_ben_adams = make_employee(db_session, first_name="Ben", last_name="Adams")
    make_employee(db_session, last_name="Aaron", status="TERMINATED")

    response = as_role("HR_MANAGER").get(EMPLOYEES)

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [
        ben_adams.id,
        another_ben_adams.id,
        zoe_adams.id,
        becker.id,
    ]
    assert (body["page"], body["page_size"], body["total"]) == (1, 25, 4)


def test_a_list_item_has_the_list_fields_and_the_current_salary(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    role = make_job_role(db_session, "Software Engineer")
    employee = make_employee(
        db_session,
        country="JP",
        job_role=role,
        first_name="Yui",
        last_name="Sato",
        email="yui.sato@acme.example",
        employee_code="ACME-000310",
        base_minor=6_000_000,
        components=[("ALLOWANCE", "Commuting", 120_000)],
    )

    item = as_role("HR_MANAGER").get(EMPLOYEES).json()["items"][0]

    assert item == {
        "id": employee.id,
        "employee_code": "ACME-000310",
        "first_name": "Yui",
        "last_name": "Sato",
        "email": "yui.sato@acme.example",
        "job_role": {"id": role.id, "title": "Software Engineer"},
        "department": {"id": role.department_id, "name": "Engineering"},
        "level": "L3",
        "employment_type": "FULL_TIME",
        "country_code": "JP",
        "status": "ACTIVE",
        "hire_date": "2024-01-15",
        "current_base": {"amount_minor": 6_000_000, "currency": "JPY"},
        "current_total": {"amount_minor": 6_120_000, "currency": "JPY"},
        "salary_masked": False,
        "version": 1,
    }


def test_list_pages_through_the_employees(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    ids = [make_employee(db_session, last_name=f"Name {n:02d}").id for n in range(5)]

    response = as_role("HR_MANAGER").get(EMPLOYEES, params={"page": 2, "page_size": 2})

    body = response.json()
    assert [item["id"] for item in body["items"]] == ids[2:4]
    assert (body["page"], body["page_size"], body["total"]) == (2, 2, 5)


@pytest.mark.parametrize(
    "params",
    [{"page": 0}, {"page_size": 0}, {"page_size": 101}, {"departmentId": 1}],
    ids=["page 0", "page size 0", "page size over 100", "unknown parameter"],
)
def test_list_refuses_a_page_outside_the_limits_or_an_unknown_parameter(
    as_role: Callable[[str], TestClient], params: dict[str, int]
) -> None:
    response = as_role("HR_MANAGER").get(EMPLOYEES, params=params)

    assert response.status_code == 422
    assert response.json()["type"] == f"{PROBLEMS}validation"
