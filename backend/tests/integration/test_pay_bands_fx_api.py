"""GET /pay-bands and GET /fx-rates: read-only reference for insights (docs/07 8.12, 9)."""

from collections.abc import Callable
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.factories import make_fx_rate, make_job_role, make_pay_band

PAY_BANDS = "/api/v1/pay-bands"
FX_RATES = "/api/v1/fx-rates"


@pytest.mark.usefixtures("frozen_time")
def test_pay_bands_lists_the_band_in_force_for_each_role_level_and_country(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    role = make_job_role(db_session)
    make_pay_band(
        db_session,
        job_role=role,
        level="L3",
        country="DE",
        mid_minor=5_000_000,
        effective_from=date(2025, 1, 1),
    )
    make_pay_band(db_session, job_role=role, level="L3", country="DE", mid_minor=6_000_000)
    make_pay_band(
        db_session,
        job_role=role,
        level="L3",
        country="DE",
        mid_minor=9_000_000,
        effective_from=date(2027, 1, 1),
    )  # not started yet
    make_pay_band(db_session, job_role=role, level="L2", country="IN", mid_minor=200_000_000)

    response = as_role("VIEWER").get(PAY_BANDS)

    assert response.status_code == 200
    assert response.json() == {
        "bands": [
            {
                "job_role_id": role.id,
                "level": "L3",
                "country_code": "DE",
                "currency": "EUR",
                "min": 4_800_000,
                "mid": 6_000_000,
                "max": 7_200_000,
                "effective_from": "2026-01-01",
            },
            {
                "job_role_id": role.id,
                "level": "L2",
                "country_code": "IN",
                "currency": "INR",
                "min": 160_000_000,
                "mid": 200_000_000,
                "max": 240_000_000,
                "effective_from": "2026-01-01",
            },
        ]
    }


@pytest.mark.usefixtures("frozen_time")
def test_pay_bands_can_be_filtered_by_country_role_and_level(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    role = make_job_role(db_session)
    other = make_job_role(db_session, "Data Engineer")
    for country, job_role, level in (
        ("DE", role, "L3"),
        ("DE", role, "L2"),
        ("DE", other, "L3"),
        ("FR", role, "L3"),
    ):
        make_pay_band(db_session, job_role=job_role, level=level, country=country)

    body = (
        as_role("HR_MANAGER")
        .get(PAY_BANDS, params={"country": "DE", "job_role_id": role.id, "level": ["L3", "L4"]})
        .json()
    )

    assert [(b["country_code"], b["job_role_id"], b["level"]) for b in body["bands"]] == [
        ("DE", role.id, "L3")
    ]


def test_pay_bands_refuses_an_unknown_parameter(as_role: Callable[[str], TestClient]) -> None:
    response = as_role("HR_MANAGER").get(PAY_BANDS, params={"currency": "EUR"})

    assert response.status_code == 422


def test_fx_rates_lists_each_rate_as_a_decimal_string_with_its_date(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_fx_rate(db_session, "INR", as_of=date(2026, 9, 15))
    make_fx_rate(db_session, "EUR")

    response = as_role("VIEWER").get(FX_RATES)

    assert response.status_code == 200
    assert response.json() == {
        "rates": [
            {
                "currency": "EUR",
                "rate_to_usd": "1.085",
                "as_of": "2026-10-01",
                "source": "Static snapshot (illustrative)",
            },
            {
                "currency": "INR",
                "rate_to_usd": "0.01198",
                "as_of": "2026-09-15",
                "source": "Static snapshot (illustrative)",
            },
        ]
    }
