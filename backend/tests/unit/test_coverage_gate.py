"""The 90 % gate covers domain/ and every service, at any depth (scripts/coverage_gate.py)."""

import pytest

from scripts.coverage_gate import is_gated

SRC = "/repo/backend/src/salary_api"


@pytest.mark.parametrize(
    ("path", "gated"),
    [
        (f"{SRC}/domain/money.py", True),
        (f"{SRC}/domain/fx/rates.py", True),
        (f"{SRC}/modules/employees/service.py", True),
        (f"{SRC}/modules/insights/service/pay_equity.py", True),
        (f"{SRC}/modules/employees/router.py", False),
        (f"{SRC}/core/db.py", False),
    ],
)
def test_gate_covers_domain_and_service_files_at_any_depth(path: str, gated: bool) -> None:
    assert is_gated(path) is gated
