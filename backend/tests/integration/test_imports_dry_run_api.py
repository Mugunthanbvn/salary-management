"""POST /imports validates a file and stores a dry-run report (docs/07 section 7.2, docs/11 5)."""

import hashlib
from collections.abc import Callable
from pathlib import Path

import pytest
import time_machine
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.domain.constants import MAX_IMPORT_ROWS, MAX_UPLOAD_BYTES
from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.employees.models import Employee
from salary_api.modules.imports.columns import TEMPLATE_COLUMNS
from salary_api.modules.imports.models import ImportJob
from tests.conftest import signed_in_client
from tests.factories import make_employee, make_job_role, make_user
from tests.spreadsheets import (
    XLSX_TYPE,
    hire,
    import_csv,
    make_import_reference,
    upload,
)

IMPORTS = "/api/v1/imports"
PROBLEMS = "https://acme.example/problems/"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_hr_uploads_a_csv_and_gets_a_201_dry_run_report(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    role = make_import_reference(db_session)
    content = import_csv(
        hire(1, bonus_target="4160.50", allowance_1_name="Transport", allowance_1_amount="1200"),
        hire(2, country="JP", base_salary="6500000"),
    )

    response = as_role("HR_MANAGER").post(IMPORTS, **upload("q4-hires.csv", content))

    assert response.status_code == 201
    body = response.json()
    assert response.headers["location"] == f"{IMPORTS}/{body['id']}"
    assert body == {
        "id": body["id"],
        "status": "DRY_RUN",
        "format": "CSV",
        "filename": "q4-hires.csv",
        "row_count": 2,
        "valid_count": 2,
        "error_count": 0,
        "errors": [],
        "errors_truncated": False,
        "allowed_values": {},
        "preview": [
            {
                "row": 2,
                "employee_code": "ACME-010001",
                "first_name": "Lena",
                "last_name": "Müller 1",
                "email": "lena.1@acme.example",
                "job_role": "Software Engineer",
                "department": role.department.name,
                "level": "L2",
                "employment_type": "FULL_TIME",
                "country_code": "DE",
                "hire_date": "2022-04-01",
                "salary_effective_date": "2022-04-01",
                "base": {"amount_minor": 5_200_000, "currency": "EUR"},
                "total": {"amount_minor": 5_736_050, "currency": "EUR"},
            },
            {
                "row": 3,
                "employee_code": "ACME-010002",
                "first_name": "Lena",
                "last_name": "Müller 2",
                "email": "lena.2@acme.example",
                "job_role": "Software Engineer",
                "department": role.department.name,
                "level": "L2",
                "employment_type": "FULL_TIME",
                "country_code": "JP",
                "hire_date": "2022-04-01",
                "salary_effective_date": "2022-04-01",
                "base": {"amount_minor": 6_500_000, "currency": "JPY"},
                "total": {"amount_minor": 6_500_000, "currency": "JPY"},
            },
        ],
        "created_at": "2026-10-01T09:00:00Z",
        "expires_at": "2026-10-02T09:00:00Z",
        "committed_at": None,
    }


def test_a_dry_run_with_row_errors_is_still_a_201_listing_every_error(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    make_import_reference(db_session)
    content = import_csv(hire(1), hire(2, level="L9", country="JP", base_salary="450000.5"))

    response = as_role("HR_MANAGER").post(IMPORTS, **upload("hires.csv", content))

    assert response.status_code == 201
    body = response.json()
    assert (body["row_count"], body["valid_count"], body["error_count"]) == (2, 1, 2)
    assert body["errors"] == [
        {
            "row": 3,
            "column": "level",
            "code": "unknown_value",
            "message": "'L9' is not a known level.",
            "value": "L9",
        },
        {
            "row": 3,
            "column": "base_salary",
            "code": "too_many_decimals",
            "message": "JPY amounts can't have decimals.",
            "value": "450000.5",
        },
    ]
    assert [row["row"] for row in body["preview"]] == [2]
    assert body["allowed_values"] == {"level": ["L1", "L2", "L3", "L4", "L5", "L6"]}
    assert body["errors_truncated"] is False


def test_a_dry_run_writes_only_the_import_job_and_its_audit_event(
    app: FastAPI,
    client: TestClient,
    db_session: Session,
    settings: Settings,
    frozen_time: time_machine.Traveller,
) -> None:
    make_import_reference(db_session)
    hr = make_user(db_session, role="HR_MANAGER")
    content = import_csv(hire(1), hire(2))

    response = signed_in_client(app, hr, settings).post(IMPORTS, **upload("q4.csv", content))

    assert db_session.scalar(select(func.count(Employee.id))) == 0
    job = db_session.get(ImportJob, response.json()["id"])
    assert job is not None
    assert (job.created_by, job.file_sha256, job.payload is not None) == (
        hr.id,
        hashlib.sha256(content).hexdigest(),
        True,
    )
    event = db_session.scalars(select(AuditEvent)).one()
    assert (event.action, event.actor_id, event.entity, event.entity_id) == (
        "import.dry_run",
        hr.id,
        "import_job",
        str(job.id),
    )
    assert event.diff == {
        "job_id": job.id,
        "filename": "q4.csv",
        "format": "CSV",
        "file_sha256": job.file_sha256,
        "row_count": 2,
        "valid_count": 2,
        "error_count": 0,
    }


def test_a_dry_run_with_errors_keeps_no_payload(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    make_import_reference(db_session)

    response = as_role("HR_MANAGER").post(
        IMPORTS, **upload("q4.csv", import_csv(hire(1), hire(2, level="L9")))
    )

    job = db_session.get(ImportJob, response.json()["id"])
    assert job is not None
    assert job.payload is None  # it can never be committed, so no salary data is kept
    assert [row["row"] for row in job.preview or []] == [2]


def test_the_xlsx_golden_file_gives_the_same_report_as_the_csv_one(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    make_import_reference(db_session)
    make_job_role(db_session, "Customer Success Manager")
    hr = as_role("HR_MANAGER")
    csv_file = (FIXTURES / "import_sample.csv").read_bytes()
    xlsx_file = (FIXTURES / "import_sample.xlsx").read_bytes()

    from_csv = hr.post(IMPORTS, **upload("sample.csv", csv_file)).json()
    from_xlsx = hr.post(IMPORTS, **upload("sample.xlsx", xlsx_file, XLSX_TYPE)).json()

    report = ("row_count", "valid_count", "error_count", "errors", "preview")
    assert {key: from_xlsx[key] for key in report} == {key: from_csv[key] for key in report}
    assert (from_csv["format"], from_xlsx["format"]) == ("CSV", "XLSX")
    assert (from_csv["valid_count"], from_csv["error_count"]) == (3, 2)


def test_codes_and_emails_already_used_by_employees_are_row_errors(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    make_import_reference(db_session)
    make_employee(db_session, employee_code="ACME-010001")
    make_employee(db_session, employee_code="ACME-000042", email="LENA.2@acme.example")

    body = (
        as_role("HR_MANAGER")
        .post(IMPORTS, **upload("q4.csv", import_csv(hire(1), hire(2), hire(3))))
        .json()
    )

    assert [(e["row"], e["column"], e["code"], e["message"]) for e in body["errors"]] == [
        (2, "employee_code", "duplicate_in_db", "ACME-010001 is already used by an employee."),
        (3, "email", "duplicate_in_db", "This email is already used by ACME-000042."),
    ]
    assert body["valid_count"] == 1


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("hires.txt", "text/plain"),
        ("hires.xlsm", XLSX_TYPE),
        ("hires.xls", "application/vnd.ms-excel"),
        ("hires", "text/csv"),
    ],
)
def test_a_file_that_is_not_csv_or_xlsx_is_refused_with_415(
    as_role: Callable[[str], TestClient], filename: str, content_type: str
) -> None:
    response = as_role("HR_MANAGER").post(
        IMPORTS, **upload(filename, import_csv(hire(1)), content_type)
    )

    assert response.status_code == 415
    assert response.json()["type"] == f"{PROBLEMS}unsupported-media-type"


def test_an_upload_over_4_mb_is_refused_with_413(as_role: Callable[[str], TestClient]) -> None:
    content = b"x" * (MAX_UPLOAD_BYTES + 1)

    response = as_role("HR_MANAGER").post(IMPORTS, **upload("big.csv", content))

    assert response.status_code == 413
    assert response.json()["type"] == f"{PROBLEMS}payload-too-large"


@pytest.mark.parametrize(
    ("filename", "content", "detail"),
    [
        ("hires.csv", "M\xfcller".encode("cp1252"), "not UTF-8"),
        ("hires.xlsx", import_csv(hire(1)), "not an Excel workbook"),
        ("hires.csv", b"employee_code,emial\r\nACME-010001,x\r\n", "Unknown column: emial"),
    ],
    ids=["not UTF-8", "a CSV renamed to .xlsx", "a header mismatch"],
)
def test_an_unreadable_file_is_refused_with_400(
    as_role: Callable[[str], TestClient], filename: str, content: bytes, detail: str
) -> None:
    response = as_role("HR_MANAGER").post(IMPORTS, **upload(filename, content))

    assert response.status_code == 400
    body = response.json()
    assert body["type"] == f"{PROBLEMS}bad-request"
    assert detail in body["detail"]


def test_a_header_mismatch_lists_the_expected_headers(
    as_role: Callable[[str], TestClient],
) -> None:
    content = b"employee_code,emial\r\nACME-010001,x\r\n"

    body = as_role("HR_MANAGER").post(IMPORTS, **upload("hires.csv", content)).json()

    assert body["expected_headers"] == list(TEMPLATE_COLUMNS)


def test_more_than_10000_rows_is_refused_with_422(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    content = import_csv(*(hire(1) for _ in range(MAX_IMPORT_ROWS + 1)))

    response = as_role("HR_MANAGER").post(IMPORTS, **upload("all.csv", content))

    assert response.status_code == 422
    body = response.json()
    assert body["type"] == f"{PROBLEMS}validation"
    assert body["errors"] == [
        {
            "loc": ["body", "file"],
            "code": "too_many_rows",
            "message": "The file has more than 10000 employee rows.",
        }
    ]


def test_a_new_upload_expires_the_oldest_of_three_open_dry_runs(
    app: FastAPI,
    client: TestClient,
    db_session: Session,
    settings: Settings,
    frozen_time: time_machine.Traveller,
) -> None:
    make_import_reference(db_session)
    hr = signed_in_client(app, make_user(db_session, role="HR_MANAGER"), settings)
    other = signed_in_client(app, make_user(db_session, role="HR_MANAGER"), settings)
    other_job = other.post(IMPORTS, **upload("theirs.csv", import_csv(hire(9)))).json()["id"]
    ids = [
        hr.post(IMPORTS, **upload(f"{n}.csv", import_csv(hire(n)))).json()["id"]
        for n in (1, 2, 3, 4)
    ]

    jobs = {job.id: job for job in db_session.scalars(select(ImportJob))}
    assert [jobs[job_id].status for job_id in ids] == ["EXPIRED", "DRY_RUN", "DRY_RUN", "DRY_RUN"]
    assert (jobs[ids[0]].payload, jobs[ids[0]].preview) == (None, None)
    assert jobs[other_job].status == "DRY_RUN"  # another user's dry-runs do not count


def test_an_upload_expires_dry_runs_past_their_24_hours(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    make_import_reference(db_session)
    hr = as_role("HR_MANAGER")
    old = hr.post(IMPORTS, **upload("old.csv", import_csv(hire(1)))).json()["id"]
    frozen_time.shift(60 * 60 * 24)

    as_role("HR_MANAGER").post(IMPORTS, **upload("new.csv", import_csv(hire(2))))

    job = db_session.get(ImportJob, old)
    assert job is not None
    assert (job.status, job.payload, job.preview) == ("EXPIRED", None, None)


def test_a_report_keeps_the_first_500_errors_and_counts_them_all(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    make_import_reference(db_session)
    content = import_csv(*(hire(n, level="L9", job_role="Chef") for n in range(1, 401)))

    response = as_role("HR_MANAGER").post(IMPORTS, **upload("bad.csv", content))

    body = response.json()
    assert (body["error_count"], len(body["errors"]), body["errors_truncated"]) == (800, 500, True)
    assert len(response.content) < 200_000  # no allowed values repeated in every message
    assert set(body["allowed_values"]) == {"job_role", "level"}
