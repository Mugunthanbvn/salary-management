"""Insight use cases. The dashboard, exports and the Ask tools all call these functions.

Masking, the small-group rule and complementary suppression live here, so every caller of
the service gets them (docs/08-security-rbac.md section 4).

Currency (docs/09 section 2.5): a population whose countries share one currency is shown in
that currency; any other population is shown in USD, each salary converted before the
statistics are computed (section 2.6).
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from itertools import groupby
from operator import itemgetter

from sqlalchemy.orm import Session

from salary_api.core.errors import ValidationFailed
from salary_api.core.permissions import Principal
from salary_api.core.schemas import Money
from salary_api.domain.currency import USD
from salary_api.domain.money import CurrencyMismatchError, FxRate, to_usd
from salary_api.domain.money import Money as DomainMoney
from salary_api.domain.stats import InsufficientData, Summary, summarize
from salary_api.modules.insights import repository
from salary_api.modules.insights.schemas import (
    CountryStats,
    InsightQuery,
    Overview,
    Population,
    Stats,
)


def overview(session: Session, principal: Principal, query: InsightQuery) -> Overview:
    """Headcount, payroll in USD and pay by country (docs/09 section 3.1)."""
    del principal  # used once masking applies
    markets = _markets(session, query.country)
    currency = markets.currency_of_population(query.country)
    convert = _Converter(markets.rates)
    rows = repository.amounts_by_country(session, _where(query), query.comp)
    by_country: list[CountryStats] = []
    amounts: list[int] = []
    usd_amounts: list[int] = []
    for country_code, group in groupby(rows, key=itemgetter(0)):
        members = [(member_currency, amount) for _, member_currency, amount in group]
        local_currency = _one_currency(members)
        usd = [convert.to(USD, amount, member_currency) for member_currency, amount in members]
        by_country.append(
            CountryStats(
                country_code=country_code,
                local=_stats(summarize(amount for _, amount in members), local_currency),
                usd=_stats(summarize(usd), USD),
            )
        )
        amounts += [
            convert.to(currency, amount, member_currency) for member_currency, amount in members
        ]
        usd_amounts += usd
    payroll = summarize(usd_amounts)
    return Overview(
        population=_population(query),
        currency=currency,
        fx_as_of=convert.fx_as_of,
        headcount=len(rows),
        total_payroll_usd=_money(payroll.sum, USD) if isinstance(payroll, Summary) else None,
        stats=_stats(summarize(amounts), currency),
        by_country=by_country,
    )


@dataclass(frozen=True, slots=True)
class _Markets:
    """Each country's salary currency, and the USD rate of each currency that has one."""

    currency_of: Mapping[str, str]
    rates: Mapping[str, FxRate]

    def currency_of_population(self, countries: Sequence[str]) -> str:
        """The one currency the countries share, else USD (also when no country is named)."""
        currencies = {self.currency_of[code] for code in countries}
        return currencies.pop() if len(currencies) == 1 else USD


def _markets(session: Session, countries: Sequence[str]) -> _Markets:
    """Countries and FX rates in one small query. An unknown country in the filter is a 422."""
    markets = repository.countries_and_rates(session)
    currency_of = {market.code: market.currency for market in markets}
    unknown = [code for code in countries if code not in currency_of]
    if unknown:
        raise ValidationFailed(
            [
                {
                    "loc": ["query", "country"],
                    "code": "not_found",
                    "message": f"Unknown country {code}.",
                }
                for code in unknown
            ]
        )
    rates = {
        market.currency: FxRate(market.currency, Decimal(market.rate_to_usd), market.as_of)
        for market in markets
        if market.rate_to_usd is not None and market.as_of is not None
    }
    return _Markets(currency_of, rates)


class _Converter:
    """Puts amounts in a response currency and remembers the dates of the USD rates used."""

    def __init__(self, rates: Mapping[str, FxRate]) -> None:
        self._rates = rates
        self._dates: set[date] = set()

    def to(self, target: str, amount_minor: int, currency: str) -> int:
        """The amount in `target`: unchanged in its own currency, else converted to USD.

        A missing rate raises FxRateMissingError: never a fallback to 0 or 1.
        """
        if currency == target:
            return amount_minor
        if target != USD:
            raise CurrencyMismatchError(target, currency)
        converted = to_usd(DomainMoney(amount_minor, currency), self._rates)
        self._dates.add(converted.fx_as_of)
        return converted.amount.amount_minor

    @property
    def fx_as_of(self) -> date | None:
        """The oldest `as_of` among the rates used, or None if no amount was converted."""
        return min(self._dates, default=None)


def _one_currency(members: Iterable[tuple[str, int]]) -> str:
    """The currency every member is paid in (one country: always one currency, docs/09 4)."""
    currencies = {currency for currency, _amount in members}
    first = currencies.pop()
    if currencies:
        raise CurrencyMismatchError(first, currencies.pop())
    return first


def _stats(summary: Summary | InsufficientData, currency: str) -> Stats:
    if isinstance(summary, InsufficientData):
        return Stats(
            count=0,
            min=None,
            p25=None,
            median=None,
            mean=None,
            p75=None,
            max=None,
            currency=currency,
            suppressed=False,
        )
    return Stats(
        count=summary.count,
        min=summary.min,
        p25=summary.p25,
        median=summary.median,
        mean=summary.mean,
        p75=summary.p75,
        max=summary.max,
        currency=currency,
        suppressed=False,
    )


def _money(amount_minor: int, currency: str) -> Money:
    return Money(amount_minor=amount_minor, currency=currency)


def _where(query: InsightQuery) -> repository.PopulationFilter:
    return repository.PopulationFilter(
        countries=query.country,
        department_ids=query.department_id,
        job_role_ids=query.job_role_id,
        levels=query.level,
        employment_types=query.employment_type,
        statuses=query.status,
    )


def _population(query: InsightQuery) -> Population:
    return Population(
        country=query.country,
        department_id=query.department_id,
        job_role_id=query.job_role_id,
        level=query.level,
        employment_type=query.employment_type,
        status=query.status,
        comp=query.comp,
    )
