"""Reading employees: detail and list (docs/07-api-spec.md sections 6.1 and 6.3)."""

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.modules.reference.models import JobFamily
from tests.factories import make_department, make_employee, make_job_role

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


@pytest.fixture
def population(db_session: Session) -> dict[str, Any]:
    """Four employees, one per country, named after their country."""
    engineer = make_job_role(db_session, "Software Engineer")
    sales = make_department(db_session, "Sales")
    account_executive = make_job_role(
        db_session, "Account Executive", department=sales, family=JobFamily.SALES
    )
    make_employee(db_session, country="DE", job_role=engineer, level="L3", last_name="Germany")
    make_employee(
        db_session,
        country="FR",
        job_role=account_executive,
        level="L2",
        employment_type="PART_TIME",
        last_name="France",
    )
    make_employee(
        db_session,
        country="JP",
        job_role=engineer,
        level="L5",
        employment_type="CONTRACTOR",
        last_name="Japan",
    )
    make_employee(
        db_session, country="US", job_role=account_executive, status="TERMINATED", last_name="Usa"
    )
    return {"engineer": engineer, "sales": sales}


FILTERS = [
    ("countries", lambda _: {"country": ["DE", "JP"]}, ["Germany", "Japan"]),
    ("department", lambda p: {"department_id": [p["sales"].id]}, ["France"]),
    ("job role", lambda p: {"job_role_id": [p["engineer"].id]}, ["Germany", "Japan"]),
    ("levels", lambda _: {"level": ["L2", "L5"]}, ["France", "Japan"]),
    (
        "employment types",
        lambda _: {"employment_type": ["PART_TIME", "CONTRACTOR"]},
        ["France", "Japan"],
    ),
    ("terminated only", lambda _: {"status": ["TERMINATED"]}, ["Usa"]),
    (
        "every status",
        lambda _: {"status": ["ACTIVE", "TERMINATED"]},
        ["France", "Germany", "Japan", "Usa"],
    ),
    ("currency", lambda _: {"currency": ["EUR"]}, ["France", "Germany"]),
    ("filters combine with AND", lambda _: {"country": ["DE"], "level": ["L5"]}, []),
]


@pytest.mark.parametrize(
    ("params", "last_names"),
    [pytest.param(params, names, id=case) for case, params, names in FILTERS],
)
def test_list_filters_combine_values_of_one_key_with_or_and_keys_with_and(
    as_role: Callable[[str], TestClient],
    population: dict[str, Any],
    params: Callable[[dict[str, Any]], dict[str, Any]],
    last_names: list[str],
) -> None:
    response = as_role("HR_MANAGER").get(EMPLOYEES, params=params(population))

    body = response.json()
    assert [item["last_name"] for item in body["items"]] == last_names
    assert body["total"] == len(last_names)


@pytest.mark.parametrize("q", ["müller", "MULLER", "Muller", "lena m"])
def test_search_ignores_accents_and_case(
    as_role: Callable[[str], TestClient], db_session: Session, q: str
) -> None:
    lena = make_employee(db_session, first_name="Lena", last_name="Müller")
    make_employee(db_session, first_name="Max", last_name="Mustermann")

    response = as_role("HR_MANAGER").get(EMPLOYEES, params={"q": q})

    assert [item["id"] for item in response.json()["items"]] == [lena.id]


@pytest.mark.parametrize("q", ["acme-000042", "sato", "@acme"])
def test_search_also_matches_the_employee_code_and_email(
    as_role: Callable[[str], TestClient], db_session: Session, q: str
) -> None:
    sato = make_employee(
        db_session,
        first_name="結衣",
        last_name="佐藤",
        employee_code="ACME-000042",
        email="yui.sato@acme.example",
    )

    response = as_role("HR_MANAGER").get(EMPLOYEES, params={"q": q})

    assert [item["id"] for item in response.json()["items"]] == [sato.id]


def test_search_treats_like_wildcards_as_plain_characters(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_employee(db_session, first_name="Lena", last_name="Becker")

    for q in ("_e", "%e"):
        response = as_role("HR_MANAGER").get(EMPLOYEES, params={"q": q})

        assert response.json()["total"] == 0


def test_search_needs_at_least_two_characters(as_role: Callable[[str], TestClient]) -> None:
    response = as_role("HR_MANAGER").get(EMPLOYEES, params={"q": " m "})

    assert response.status_code == 422
    assert response.json()["errors"][0]["loc"] == ["query", "q"]


@pytest.fixture
def three_people(db_session: Session) -> None:
    make_employee(
        db_session,
        first_name="Zoe",
        last_name="Adams",
        hire_date=date(2022, 5, 1),
        country="FR",
        level="L2",
        employee_code="ACME-000003",
    )
    make_employee(
        db_session,
        first_name="Ana",
        last_name="Becker",
        hire_date=date(2020, 3, 1),
        country="DE",
        level="L4",
        employee_code="ACME-000001",
    )
    make_employee(
        db_session,
        first_name="Ana",
        last_name="Cruz",
        hire_date=date(2022, 5, 1),
        country="BR",
        level="L2",
        employee_code="ACME-000002",
    )


@pytest.mark.parametrize(
    ("sort", "last_names"),
    [
        ("-hire_date", ["Adams", "Cruz", "Becker"]),
        ("hire_date", ["Becker", "Adams", "Cruz"]),
        ("-last_name", ["Cruz", "Becker", "Adams"]),
        ("first_name", ["Becker", "Cruz", "Adams"]),
        ("first_name,-last_name", ["Cruz", "Becker", "Adams"]),
        ("country", ["Cruz", "Becker", "Adams"]),
        ("-level", ["Becker", "Adams", "Cruz"]),
        ("employee_code", ["Becker", "Cruz", "Adams"]),
    ],
)
@pytest.mark.usefixtures("three_people")
def test_list_sorts_by_allowed_fields_then_by_last_name_first_name_and_id(
    as_role: Callable[[str], TestClient], sort: str, last_names: list[str]
) -> None:
    response = as_role("HR_MANAGER").get(EMPLOYEES, params={"sort": sort})

    assert [item["last_name"] for item in response.json()["items"]] == last_names


@pytest.mark.parametrize("sort", ["salary", "-", "last_name,,first_name", "id", "search_text"])
def test_list_refuses_a_sort_field_outside_the_allow_list(
    as_role: Callable[[str], TestClient], sort: str
) -> None:
    response = as_role("HR_MANAGER").get(EMPLOYEES, params={"sort": sort})

    assert response.status_code == 422
    assert response.json()["type"] == f"{PROBLEMS}validation"
    assert response.json()["errors"][0]["loc"] == ["query", "sort"]
