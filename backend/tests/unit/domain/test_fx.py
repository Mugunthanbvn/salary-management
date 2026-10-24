"""FX conversion to USD at read time with dated Decimal rates (ADR 0005, docs/09 §2.6)."""

from datetime import date
from decimal import Decimal

import pytest

from salary_api.domain.money import FxRate

AS_OF = date(2026, 10, 1)


def test_fx_rate_holds_a_decimal_rate_and_its_date() -> None:
    rate = FxRate("EUR", Decimal("1.085"), AS_OF)

    assert (rate.currency, rate.rate_to_usd, rate.as_of) == ("EUR", Decimal("1.085"), AS_OF)


@pytest.mark.parametrize("rate_to_usd", [1.085, 1, "1.085"])
def test_fx_rate_rejects_a_float_rate(rate_to_usd: object) -> None:
    with pytest.raises(TypeError, match="Decimal"):
        FxRate("EUR", rate_to_usd, AS_OF)  # type: ignore[arg-type]
