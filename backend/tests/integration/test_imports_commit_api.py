"""POST /imports/{id}/commit writes every row in one transaction, or nothing (docs/11 5.6)."""

from collections.abc import Callable
from datetime import date

import pytest
import time_machine
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.employees.models import Employee
from salary_api.modules.imports.models import ImportJob
from salary_api.modules.salaries import repository as salary_repository
from salary_api.modules.salaries.models import SalaryComponent, SalaryRecord
from salary_api.modules.users.models import User
from tests.conftest import FROZEN_NOW, signed_in_client
from tests.factories import make_employee, make_user
from tests.spreadsheets import hire, make_dry_run

IMPORTS = "/api/v1/imports"
PROBLEMS = "https://acme.example/problems/"


def _count(session: Session, model: type[Employee | SalaryRecord | SalaryComponent]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _commit(http: TestClient, job: ImportJob) -> dict[str, object]:
    response = http.post(f"{IMPORTS}/{job.id}/commit")
    return {"http_status": response.status_code, **response.json()}


@pytest.fixture
def hr_user(db_session: Session) -> User:
    return make_user(db_session, role="HR_MANAGER", full_name="Harriet Rao")


@pytest.fixture
def hr(
    app: FastAPI,
    client: TestClient,
    hr_user: User,
    settings: Settings,
    frozen_time: time_machine.Traveller,
) -> TestClient:
    """HR_MANAGER `hr_user`, signed in once time is frozen (a token from later is refused)."""
    return signed_in_client(app, hr_user, settings)


def test_commit_creates_each_employee_with_a_hire_record_and_returns_the_count(
    hr: TestClient,
    hr_user: User,
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    job = make_dry_run(
        db_session,
        hire(
            1,
            first_name="Jürgen",
            last_name="Müller",
            email="Jurgen.Muller@acme.example",
            level="L3",
            bonus_target="4160.50",
            allowance_1_name="Transport",
            allowance_1_amount="1200",
            salary_effective_date="2022-05-01",
        ),
        hire(2, country="JP", base_salary="6500000"),
        user=hr_user,
    )

    response = hr.post(f"{IMPORTS}/{job.id}/commit")

    assert response.status_code == 200
    assert response.json() == {"id": job.id, "status": "COMMITTED", "inserted": 2}
    jurgen = db_session.scalars(
        select(Employee).where(Employee.employee_code == "ACME-010001")
    ).one()
    record = db_session.scalars(
        select(SalaryRecord).where(SalaryRecord.employee_id == jurgen.id)
    ).one()
    assert (jurgen.first_name, jurgen.email, jurgen.level, jurgen.status) == (
        "Jürgen",
        "jurgen.muller@acme.example",
        "L3",
        "ACTIVE",
    )
    assert (jurgen.country_code, jurgen.hire_date, jurgen.version) == ("DE", date(2022, 4, 1), 1)
    assert jurgen.search_text == "jurgen muller acme-010001 jurgen.muller@acme.example"
    assert (record.reason, record.effective_date, record.changed_by) == (
        "HIRE",
        date(2022, 5, 1),
        hr_user.id,
    )
    assert (record.job_role_id, record.level) == (jurgen.job_role_id, "L3")
    assert (record.currency, record.base_minor, record.total_minor) == ("EUR", 5_200_000, 5_736_050)
    assert [(c.type, c.name, c.amount_minor) for c in record.components] == [
        ("ALLOWANCE", "Transport", 120_000),
        ("BONUS_TARGET", "Target bonus", 416_050),
    ]
    assert jurgen.current_salary_record_id == record.id
    assert (jurgen.currency, jurgen.current_base_minor, jurgen.current_total_minor) == (
        "EUR",
        5_200_000,
        5_736_050,
    )


def test_committed_employees_are_listed_like_any_other(
    hr: TestClient,
    hr_user: User,
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    job = make_dry_run(
        db_session, hire(1), hire(2, country="JP", base_salary="6500000"), user=hr_user
    )
    hr.post(f"{IMPORTS}/{job.id}/commit")

    items = hr.get("/api/v1/employees", params={"q": "müller"}).json()["items"]

    assert [(item["employee_code"], item["current_base"]) for item in items] == [
        ("ACME-010001", {"amount_minor": 5_200_000, "currency": "EUR"}),
        ("ACME-010002", {"amount_minor": 6_500_000, "currency": "JPY"}),
    ]
    detail = hr.get(f"/api/v1/employees/{items[1]['id']}").json()
    assert detail["current_salary"]["reason"] == "HIRE"


def test_commit_writes_one_import_commit_event_and_ends_the_job(
    hr: TestClient,
    hr_user: User,
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    job = make_dry_run(db_session, hire(1), hire(3), hire(2), user=hr_user)

    hr.post(f"{IMPORTS}/{job.id}/commit")

    event = db_session.scalars(select(AuditEvent).where(AuditEvent.action == "import.commit")).one()
    assert (event.actor_id, event.entity, event.entity_id) == (
        hr_user.id,
        "import_job",
        str(job.id),
    )
    assert event.diff == {
        "job_id": job.id,
        "inserted": 3,
        "employee_code_range": ["ACME-010001", "ACME-010003"],
    }
    db_session.refresh(job)
    assert (job.status, job.payload, job.preview) == ("COMMITTED", None, None)
    assert job.committed_at == FROZEN_NOW


def test_an_administrator_may_commit_another_users_dry_run(
    as_role: Callable[[str], TestClient], db_session: Session, frozen_time: time_machine.Traveller
) -> None:
    job = make_dry_run(db_session)

    result = _commit(as_role("ADMIN"), job)

    assert (result["http_status"], result["inserted"]) == (200, 1)


def test_another_hr_manager_gets_404_and_nothing_is_written(
    as_role: Callable[[str], TestClient], db_session: Session, frozen_time: time_machine.Traveller
) -> None:
    job = make_dry_run(db_session)

    result = _commit(as_role("HR_MANAGER"), job)

    assert (result["http_status"], result["type"]) == (404, f"{PROBLEMS}not-found")
    assert _count(db_session, Employee) == 0


def test_a_dry_run_with_errors_cannot_be_committed(
    hr: TestClient,
    hr_user: User,
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    job = make_dry_run(db_session, hire(1), hire(2, level="L9"), user=hr_user)

    result = _commit(hr, job)

    assert (result["http_status"], result["type"]) == (409, f"{PROBLEMS}invalid-state")
    assert "errors" in str(result["detail"])
    assert _count(db_session, Employee) == 0


def test_committing_twice_is_refused_the_second_time(
    hr: TestClient,
    hr_user: User,
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    job = make_dry_run(db_session, hire(1), user=hr_user)
    _commit(hr, job)

    result = _commit(hr, job)

    assert (result["http_status"], result["type"]) == (409, f"{PROBLEMS}invalid-state")
    assert _count(db_session, Employee) == 1


def test_a_dry_run_past_its_24_hours_is_refused_and_becomes_expired(
    app: FastAPI,
    client: TestClient,
    db_session: Session,
    settings: Settings,
    frozen_time: time_machine.Traveller,
) -> None:
    user = make_user(db_session, role="HR_MANAGER")
    job = make_dry_run(db_session, hire(1), user=user)
    frozen_time.shift(60 * 60 * 24)

    result = _commit(signed_in_client(app, user, settings), job)  # a new session: 8 h TTL

    assert (result["http_status"], result["type"]) == (409, f"{PROBLEMS}invalid-state")
    db_session.refresh(job)
    assert (job.status, job.payload) == ("EXPIRED", None)
    assert _count(db_session, Employee) == 0


def test_a_duplicate_created_after_the_dry_run_is_a_409_listing_the_rows(
    hr: TestClient,
    hr_user: User,
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    job = make_dry_run(db_session, hire(1), hire(2), user=hr_user)
    make_employee(db_session, employee_code="ACME-000042", email="lena.2@acme.example")

    result = _commit(hr, job)

    assert (result["http_status"], result["type"]) == (409, f"{PROBLEMS}duplicate")
    assert result["conflicts"] == [
        {
            "row": 3,
            "column": "email",
            "code": "duplicate_in_db",
            "message": "This email is already used by ACME-000042.",
            "value": "lena.2@acme.example",
        }
    ]
    assert _count(db_session, Employee) == 1  # only the one made above
    db_session.refresh(job)
    assert job.status == "DRY_RUN"


def test_a_failure_mid_commit_writes_nothing_and_marks_the_job_failed(
    hr: TestClient,
    hr_user: User,
    db_session: Session,
    frozen_time: time_machine.Traveller,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = make_dry_run(
        db_session,
        hire(1, allowance_1_name="Meals", allowance_1_amount="100"),
        hire(2),
        user=hr_user,
    )

    def disk_full(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk I/O error")

    # Employees and salary records are written by then; the components fail.
    monkeypatch.setattr(salary_repository, "insert_components", disk_full)

    result = _commit(hr, job)

    assert (result["http_status"], result["type"]) == (500, f"{PROBLEMS}import-failed")
    assert (_count(db_session, Employee), _count(db_session, SalaryRecord)) == (0, 0)
    db_session.refresh(job)
    assert (job.status, job.failure_reason, job.payload) == ("FAILED", "OSError", None)
    actions = db_session.scalars(select(AuditEvent.action).order_by(AuditEvent.id)).all()
    assert actions == ["import.dry_run", "import.fail"]
    event = db_session.scalars(select(AuditEvent).where(AuditEvent.action == "import.fail")).one()
    assert event.diff == {"job_id": job.id, "failure_reason": "OSError"}
