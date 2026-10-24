"""GET /imports/{id}: the job's creator or an administrator sees it (docs/07 section 7.3)."""

from collections.abc import Callable

import time_machine
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.modules.audit.models import AuditEvent
from tests.conftest import signed_in_client
from tests.factories import make_user
from tests.spreadsheets import hire, import_csv, make_dry_run, make_import_reference, upload

IMPORTS = "/api/v1/imports"
PROBLEMS = "https://acme.example/problems/"


def test_the_creator_reads_the_report_the_upload_returned(
    app: FastAPI,
    client: TestClient,
    db_session: Session,
    settings: Settings,
    frozen_time: time_machine.Traveller,
) -> None:
    make_import_reference(db_session)
    hr = signed_in_client(app, make_user(db_session, role="HR_MANAGER"), settings)
    uploaded = hr.post(IMPORTS, **upload("q4.csv", import_csv(hire(1), hire(2, level="L9"))))

    response = hr.get(f"{IMPORTS}/{uploaded.json()['id']}")

    assert response.status_code == 200
    assert response.json() == uploaded.json()


def test_an_administrator_reads_another_users_job(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    job = make_dry_run(db_session)

    response = as_role("ADMIN").get(f"{IMPORTS}/{job.id}")

    assert (response.status_code, response.json()["id"]) == (200, job.id)


def test_another_hr_manager_gets_404_for_a_job_they_did_not_upload(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    job = make_dry_run(db_session)

    response = as_role("HR_MANAGER").get(f"{IMPORTS}/{job.id}")

    assert response.status_code == 404
    assert response.json()["type"] == f"{PROBLEMS}not-found"


def test_an_unknown_job_is_404_and_an_id_beyond_64_bits_is_422(
    as_role: Callable[[str], TestClient],
) -> None:
    hr = as_role("HR_MANAGER")

    assert hr.get(f"{IMPORTS}/999999").status_code == 404
    assert hr.get(f"{IMPORTS}/{10**20}").status_code == 422


def test_a_dry_run_past_its_24_hours_reads_as_expired_without_a_write(
    app: FastAPI,
    client: TestClient,
    db_session: Session,
    settings: Settings,
    frozen_time: time_machine.Traveller,
) -> None:
    user = make_user(db_session, role="HR_MANAGER")
    job = make_dry_run(db_session, user=user)
    frozen_time.shift(60 * 60 * 24)
    events_before = len(db_session.scalars(select(AuditEvent)).all())

    body = signed_in_client(app, user, settings).get(f"{IMPORTS}/{job.id}").json()

    assert body["status"] == "EXPIRED"
    db_session.refresh(job)
    assert job.status == "DRY_RUN"
    assert len(db_session.scalars(select(AuditEvent)).all()) == events_before


def test_an_expired_dry_run_shows_no_preview_salaries(
    app: FastAPI,
    client: TestClient,
    db_session: Session,
    settings: Settings,
    frozen_time: time_machine.Traveller,
) -> None:
    user = make_user(db_session, role="HR_MANAGER")
    job = make_dry_run(db_session, user=user)
    frozen_time.shift(60 * 60 * 24)

    body = signed_in_client(app, user, settings).get(f"{IMPORTS}/{job.id}").json()

    assert (body["status"], body["preview"]) == ("EXPIRED", [])
