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
from salary_api.domain.constants import MIN_GROUP_SIZE
from salary_api.domain.currency import USD
from salary_api.domain.money import CurrencyMismatchError, FxRate, to_usd
from salary_api.domain.money import Money as DomainMoney
from salary_api.domain.stats import InsufficientData, Summary, summarize
from salary_api.modules.employees.service import can_see_salaries
from salary_api.modules.insights import repository
from salary_api.modules.insights.schemas import (
    ByDepartment,
    CountryStats,
    DepartmentStats,
    InsightQuery,
    Overview,
    Population,
    Stats,
)
from salary_api.modules.reference.schemas import Department


def overview(session: Session, principal: Principal, query: InsightQuery) -> Overview:
    """Headcount, payroll in USD and pay by country (docs/09 section 3.1)."""
    scope = _scope(session, principal, query.country)
    rows = repository.amounts_by_country(session, _where(query), query.comp)
    countries = _groups(rows)
    hidden = scope.audience.hidden_groups([country.count for country in countries])
    by_country = [
        CountryStats(
            country_code=country.key,
            local=scope.stats(country.members, hidden=index in hidden, currency=country.currency),
            usd=scope.stats(country.members, hidden=index in hidden, currency=USD),
        )
        for index, country in enumerate(countries)
    ]
    everyone = [member for country in countries for member in country.members]
    total_hidden = scope.audience.hides(len(everyone))
    payroll = summarize(scope.convert.all(USD, everyone))
    return Overview(
        population=_population(query),
        currency=scope.currency,
        fx_as_of=scope.convert.fx_as_of,
        headcount=None if total_hidden else len(everyone),
        total_payroll_usd=_money(payroll.sum, USD)
        if isinstance(payroll, Summary) and not total_hidden
        else None,
        stats=scope.stats(everyone, hidden=total_hidden),
        by_country=by_country,
    )


def by_department(session: Session, principal: Principal, query: InsightQuery) -> ByDepartment:
    """Pay statistics per department (docs/09 section 3.2)."""
    scope = _scope(session, principal, query.country)
    rows = repository.amounts_by_department(session, _where(query), query.comp)
    departments = _groups(((id_, name), currency, amount) for id_, name, currency, amount in rows)
    hidden = scope.audience.hidden_groups([department.count for department in departments])
    groups = [
        DepartmentStats(
            department=Department(id=department.key[0], name=department.key[1]),
            stats=scope.stats(department.members, hidden=index in hidden),
        )
        for index, department in enumerate(departments)
    ]
    return ByDepartment(
        population=_population(query),
        currency=scope.currency,
        fx_as_of=scope.convert.fx_as_of,
        groups=groups,
    )


@dataclass(frozen=True, slots=True)
class _Audience:
    """Whether the caller may see individual pay (SALARY_READ) or only aggregates."""

    salary_visible: bool

    @classmethod
    def of(cls, principal: Principal) -> "_Audience":
        return cls(salary_visible=can_see_salaries(principal))

    def hides(self, count: int) -> bool:
        """The small-group rule: without SALARY_READ, fewer than MIN_GROUP_SIZE is hidden."""
        return not self.salary_visible and count < MIN_GROUP_SIZE

    def hidden_groups(self, counts: Sequence[int]) -> set[int]:
        """The indexes of the groups of one breakdown that this caller may not see.

        The small-group rule hides groups under MIN_GROUP_SIZE. If that hides exactly one,
        the smallest visible group is hidden too (complementary suppression, docs/09 2.8):
        otherwise the total minus the visible groups would give the hidden one away.
        Ties go to the group listed first.
        """
        hidden = {index for index, count in enumerate(counts) if self.hides(count)}
        visible = [index for index in range(len(counts)) if index not in hidden]
        if len(hidden) == 1 and visible:
            hidden.add(min(visible, key=lambda index: (counts[index], index)))
        return hidden


@dataclass(frozen=True, slots=True)
class _Scope:
    """What one insight request needs: who asks, the response currency, the converter."""

    audience: _Audience
    currency: str  # the population's one currency, else USD
    convert: "_Converter"

    def stats(
        self, members: Iterable[tuple[str, int]], *, hidden: bool, currency: str | None = None
    ) -> Stats:
        """The stats object of members' amounts in `currency` (the response currency if None)."""
        target = currency or self.currency
        amounts = self.convert.all(target, members)
        return _stats(summarize(amounts), target, hidden=hidden, audience=self.audience)


def _scope(session: Session, principal: Principal, countries: Sequence[str]) -> _Scope:
    markets = _markets(session, countries)
    return _Scope(
        audience=_Audience.of(principal),
        currency=markets.currency_of_population(countries),
        convert=_Converter(markets.rates),
    )


@dataclass(frozen=True, slots=True)
class _Group[K]:
    """One group of a breakdown: its key and each member's (currency, amount), sorted."""

    key: K
    members: Sequence[tuple[str, int]]

    @property
    def count(self) -> int:
        return len(self.members)

    @property
    def currency(self) -> str:
        """The currency every member is paid in (one country is always one currency)."""
        return _one_currency(self.members)


def _groups[K](rows: Iterable[tuple[K, str, int]]) -> list[_Group[K]]:
    """(key, currency, amount) rows sorted by key, as one group per key, in the same order."""
    return [
        _Group(key, [(currency, amount) for _key, currency, amount in members])
        for key, members in groupby(rows, key=itemgetter(0))
    ]


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

    def all(self, target: str, members: Iterable[tuple[str, int]]) -> list[int]:
        """Each member's (currency, amount) as an amount in `target`."""
        return [self.to(target, amount, currency) for currency, amount in members]

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


def _stats(
    summary: Summary | InsufficientData, currency: str, *, hidden: bool, audience: "_Audience"
) -> Stats:
    """The stats object of one group; every value and the count are null when it is hidden.

    Without SALARY_READ, min and max are always null: each is one person's exact pay.
    """
    if hidden or isinstance(summary, InsufficientData):
        return Stats(
            count=None if hidden else 0,
            min=None,
            p25=None,
            median=None,
            mean=None,
            p75=None,
            max=None,
            currency=currency,
            suppressed=hidden,
        )
    # The smallest and largest amounts are each one person's exact pay.
    extremes_visible = audience.salary_visible
    return Stats(
        count=summary.count,
        min=summary.min if extremes_visible else None,
        p25=summary.p25,
        median=summary.median,
        mean=summary.mean,
        p75=summary.p75,
        max=summary.max if extremes_visible else None,
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
