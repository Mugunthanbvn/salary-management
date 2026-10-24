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

from salary_api.core.errors import Forbidden, ValidationFailed
from salary_api.core.models import utc_now
from salary_api.core.permissions import Principal
from salary_api.core.schemas import Comp, Money
from salary_api.domain.constants import (
    MIN_GROUP_SIZE,
    PAY_EQUITY_HIGH,
    PAY_EQUITY_LOW,
    ROLLUP_THRESHOLD,
)
from salary_api.domain.currency import USD
from salary_api.domain.enums import Level
from salary_api.domain.money import CurrencyMismatchError, FxRate, to_usd
from salary_api.domain.money import Money as DomainMoney
from salary_api.domain.pay_equity import (
    CohortRollup,
    DepartmentRollup,
    EmployeePay,
    cohort_rollup,
    department_rollup,
    pay_equity_summary,
)
from salary_api.domain.pay_equity import PayEquitySummary as SummaryOfPay
from salary_api.domain.rounding import round_ratio, round_share
from salary_api.domain.stats import InsufficientData, Summary, summarize
from salary_api.modules.audit.service import AuditAction, record_event
from salary_api.modules.employees.models import Employee
from salary_api.modules.employees.service import can_see_salaries
from salary_api.modules.insights import repository
from salary_api.modules.insights.schemas import (
    Band,
    ByDepartment,
    ByJobTitle,
    CohortEquity,
    CountryStats,
    DepartmentCost,
    DepartmentCosts,
    DepartmentEquity,
    DepartmentStats,
    Direction,
    Earner,
    InsightFilters,
    InsightQuery,
    JobTitleQuery,
    JobTitleStats,
    Overview,
    PayEquityCohorts,
    PayEquityDepartments,
    PayEquityQuery,
    PayEquitySummary,
    PayEquityView,
    Population,
    Stats,
    Thresholds,
    TopEarners,
    TopEarnersQuery,
)
from salary_api.modules.reference import service as reference_service
from salary_api.modules.reference.models import PayBand
from salary_api.modules.reference.schemas import Department, JobRoleRef


def overview(session: Session, principal: Principal, query: InsightQuery) -> Overview:
    """Headcount, payroll in USD and pay by country (docs/09 section 3.1)."""
    scope = _scope(session, principal, query.country)
    rows = repository.amounts_by_country(session, _where(query, query.country), query.comp)
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
        population=_population(query, query.country, query.comp),
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
    rows = repository.amounts_by_department(session, _where(query, query.country), query.comp)
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
        population=_population(query, query.country, query.comp),
        currency=scope.currency,
        fx_as_of=scope.convert.fx_as_of,
        groups=groups,
    )


def department_cost(session: Session, principal: Principal, query: InsightQuery) -> DepartmentCosts:
    """What each department's people are paid in total, and its share (docs/09 3.5)."""
    scope = _scope(session, principal, query.country)
    rows = repository.amounts_by_department(session, _where(query, query.country), query.comp)
    departments = _groups(((id_, name), currency, amount) for id_, name, currency, amount in rows)
    hidden = scope.audience.hidden_groups([department.count for department in departments])
    headcount = sum(department.count for department in departments)
    total_hidden = scope.audience.hides(headcount)
    costs = [sum(scope.convert.all(scope.currency, d.members)) for d in departments]
    costs_usd = [sum(scope.convert.all(USD, d.members)) for d in departments]
    total = None if total_hidden or not departments else sum(costs)
    total_usd = None if total_hidden or not departments else sum(costs_usd)
    groups: list[DepartmentCost] = []
    for index, department in enumerate(departments):
        shown = index not in hidden
        cost = costs[index] if shown else None
        groups.append(
            DepartmentCost(
                department=Department(id=department.key[0], name=department.key[1]),
                headcount=department.count if shown else None,
                cost=_money_or_none(cost, scope.currency),
                cost_usd=_money_or_none(costs_usd[index] if shown else None, USD),
                share_of_total=_share(cost, total),
                suppressed=not shown,
            )
        )
    return DepartmentCosts(
        population=_population(query, query.country, query.comp),
        currency=scope.currency,
        fx_as_of=scope.convert.fx_as_of,
        headcount=None if total_hidden else headcount,
        total=_money_or_none(total, scope.currency),
        total_usd=_money_or_none(total_usd, USD),
        suppressed=total_hidden,
        groups=groups,
    )


def _share(part: int | None, whole: int | None) -> str | None:
    """`part / whole` to four decimals, from values already suppressed for the caller.

    If either side is hidden (None), so is the share: it would give the hidden value away.
    """
    if part is None or not whole:  # hidden, or nothing to share
        return None
    return str(round_share(Decimal(part) / Decimal(whole)))


def pay_equity(
    session: Session, principal: Principal, query: PayEquityQuery
) -> PayEquityCohorts | PayEquityDepartments:
    """Base pay against pay bands (docs/09 section 3.8): per cohort, or per department.

    Only full-time employees with a band get a ratio; the summary counts the others.
    """
    if query.view == PayEquityView.DEPARTMENTS and len(query.country) != 1:
        message = "The departments view compares departments within one country: "
        raise ValidationFailed(
            [
                {
                    "loc": ["query", "country"],
                    "code": "required",
                    "message": message + "give exactly one country.",
                }
            ]
        )
    audience = _Audience.of(principal)
    _markets(session, query.country)  # refuses an unknown country
    pays, names = _pays(session, query)
    if query.view == PayEquityView.DEPARTMENTS:
        return _department_view(query, pays, names, audience)
    rollups = cohort_rollup(pays)
    hidden = audience.hidden_groups(
        [rollup.base.count for rollup in rollups],
        within=[
            *_partitions([(names.department_of(r), r.cohort.country_code) for r in rollups]),
            *_partitions([rollup.cohort.country_code for rollup in rollups]),
        ],
    )
    return PayEquityCohorts(
        view=PayEquityView.COHORTS,
        population=_population(query, query.country, Comp.BASE),
        thresholds=_THRESHOLDS,
        cohorts=[
            _cohort_equity(rollup, names, hidden=index in hidden, audience=audience)
            for index, rollup in enumerate(rollups)
        ],
        summary=_pay_equity_summary(pay_equity_summary(pays), audience),
    )


def _department_view(
    query: PayEquityQuery, pays: list[EmployeePay], names: "_Names", audience: "_Audience"
) -> PayEquityDepartments:
    """The systemic-gap view: compa-ratios summarised per department of one country."""
    rollups = sorted(
        department_rollup(pays),
        key=lambda rollup: (names.departments[rollup.department_id], rollup.department_id),
    )
    hidden = audience.hidden_groups([rollup.ratios.count for rollup in rollups])
    return PayEquityDepartments(
        view=PayEquityView.DEPARTMENTS,
        population=_population(query, query.country, Comp.BASE),
        country_code=query.country[0],
        thresholds=_THRESHOLDS,
        groups=[
            _department_equity(rollup, names, hidden=index in hidden)
            for index, rollup in enumerate(rollups)
        ],
        summary=_pay_equity_summary(pay_equity_summary(pays), audience),
    )


def _department_equity(
    rollup: DepartmentRollup, names: "_Names", *, hidden: bool
) -> DepartmentEquity:
    department = Department(id=rollup.department_id, name=names.departments[rollup.department_id])
    if hidden:
        return DepartmentEquity(
            department=department,
            count=None,
            median_compa_ratio=None,
            mean_compa_ratio=None,
            pct_below_band=None,
            underpaid_count=None,
            overpaid_count=None,
            below_threshold=None,
            suppressed=True,
        )
    ratios = rollup.ratios
    return DepartmentEquity(
        department=department,
        count=ratios.count,
        median_compa_ratio=str(round_ratio(ratios.median_compa_ratio)),
        mean_compa_ratio=str(round_ratio(ratios.mean_compa_ratio)),
        pct_below_band=str(round_ratio(ratios.pct_below_band)),
        underpaid_count=ratios.underpaid_count,
        overpaid_count=ratios.overpaid_count,
        below_threshold=rollup.below_threshold,  # on the unrounded median
        suppressed=False,
    )


_THRESHOLDS = Thresholds(
    low=str(PAY_EQUITY_LOW), high=str(PAY_EQUITY_HIGH), rollup=str(ROLLUP_THRESHOLD)
)


@dataclass(frozen=True, slots=True)
class _Names:
    """Department and job role names from the pay rows, and the band of each cohort."""

    departments: Mapping[int, str]
    roles: Mapping[int, tuple[str, int]]  # job role id -> (title, department id)
    bands: Mapping[tuple[int, Level, str], PayBand]  # (job role id, level, country) -> band

    def department_of(self, rollup: CohortRollup) -> int:
        return self.roles[rollup.cohort.job_role_id][1]


def _pays(session: Session, query: PayEquityQuery) -> tuple[list[EmployeePay], _Names]:
    """Each employee's pay with their band midpoint (two queries: employees, bands)."""
    rows = repository.pay_rows(session, _where(query, query.country))
    bands = {
        (band.job_role_id, band.level, band.country_code): band
        for band in reference_service.current_pay_bands(
            session,
            today=utc_now().date(),
            countries=query.country,
            job_role_ids=query.job_role_id,
            levels=query.level,
        )
    }
    pays: list[EmployeePay] = []
    departments: dict[int, str] = {}
    roles: dict[int, tuple[str, int]] = {}
    for dept_id, dept_name, role_id, title, level, country, kind, currency, base in rows:
        departments[dept_id] = dept_name
        roles[role_id] = (title, dept_id)
        band = bands.get((role_id, level, country))
        pays.append(
            EmployeePay(
                department_id=dept_id,
                job_role_id=role_id,
                level=level,
                country_code=country,
                employment_type=kind,
                base=DomainMoney(base, currency),
                band_mid=None if band is None else DomainMoney(band.mid_minor, band.currency),
            )
        )
    return pays, _Names(departments, roles, bands)


def _cohort_equity(
    rollup: CohortRollup, names: _Names, *, hidden: bool, audience: "_Audience"
) -> CohortEquity:
    key = rollup.cohort
    title, department_id = names.roles[key.job_role_id]
    band = names.bands[key.job_role_id, key.level, key.country_code]
    ratios = rollup.ratios
    return CohortEquity(
        job_role=JobRoleRef(id=key.job_role_id, title=title),
        level=key.level,
        country_code=key.country_code,
        department=Department(id=department_id, name=names.departments[department_id]),
        stats=_stats(rollup.base, rollup.currency, hidden=hidden, audience=audience),
        band=Band(
            min=band.min_minor, mid=band.mid_minor, max=band.max_minor, currency=band.currency
        ),
        median_compa_ratio=None if hidden else str(round_ratio(ratios.median_compa_ratio)),
        underpaid_count=None if hidden else ratios.underpaid_count,
        overpaid_count=None if hidden else ratios.overpaid_count,
        suppressed=hidden,
    )


def _pay_equity_summary(summary: SummaryOfPay, audience: "_Audience") -> PayEquitySummary:
    if audience.hides(summary.employees_evaluated):
        return PayEquitySummary(
            employees_evaluated=None,
            employees_without_band=None,
            employees_not_full_time=None,
            employees_flagged_underpaid=None,
            employees_flagged_overpaid=None,
            suppressed=True,
        )
    return PayEquitySummary(
        employees_evaluated=summary.employees_evaluated,
        employees_without_band=summary.employees_without_band,
        employees_not_full_time=summary.employees_not_full_time,
        employees_flagged_underpaid=summary.employees_flagged_underpaid,
        employees_flagged_overpaid=summary.employees_flagged_overpaid,
        suppressed=False,
    )


def top_earners(session: Session, principal: Principal, query: TopEarnersQuery) -> TopEarners:
    """The highest or lowest paid people in one country (docs/09 section 3.6).

    Individual pay: SALARY_READ only. The view is audited in the same transaction.
    """
    _require_salary_read(principal, "Top earners")
    countries = [query.country]
    currency = _markets(session, countries).currency_of_population(countries)
    employees = repository.ranked(
        session,
        _where(query, countries),
        query.comp,
        descending=query.direction == Direction.TOP,
        limit=query.n,
    )
    result = TopEarners(
        population=_population(query, countries, query.comp),
        country_code=query.country,
        currency=currency,
        direction=query.direction,
        n=query.n,
        items=[_earner(employee, query.comp) for employee in employees],
    )
    _audit_individuals_view(session, principal, "top-earners", query.model_dump(mode="json"))
    return result


def _earner(employee: Employee, comp: Comp) -> Earner:
    role = employee.job_role
    amount = employee.current_base_minor if comp == Comp.BASE else employee.current_total_minor
    return Earner(
        employee_id=employee.id,
        employee_code=employee.employee_code,
        first_name=employee.first_name,
        last_name=employee.last_name,
        job_role=JobRoleRef(id=role.id, title=role.title),
        level=employee.level,
        department=Department(id=role.department.id, name=role.department.name),
        amount=_money(amount, employee.currency),
    )


def _require_salary_read(principal: Principal, what: str) -> None:
    """Endpoints that list individuals' pay refuse callers without SALARY_READ (docs/08 4.1)."""
    if not can_see_salaries(principal):
        raise Forbidden(f"{what} show individual pay: that requires SALARY_READ.")


def _audit_individuals_view(
    session: Session, principal: Principal, endpoint: str, filters: Mapping[str, object]
) -> None:
    """Record who looked at individuals' pay, and with which filters, then commit."""
    record_event(
        session,
        actor_id=principal.user_id,
        action=AuditAction.INSIGHTS_INDIVIDUALS_VIEW,
        entity="insights",
        entity_id=None,
        diff={"endpoint": endpoint, "filters": dict(filters)},
    )
    session.commit()


def by_job_title(session: Session, principal: Principal, query: JobTitleQuery) -> ByJobTitle:
    """Pay statistics per job role in one country, optionally per level (docs/09 3.3)."""
    countries = [query.country]
    scope = _scope(session, principal, countries)
    rows = repository.amounts_by_job_role(session, _where(query, countries), query.comp)
    split = query.split_by_level
    roles = _groups(
        ((role_id, title, level if split else None), currency, amount)
        for role_id, title, level, currency, amount in rows
    )
    # Each role's total is a breakdown of its own: it is visible without the split.
    hidden = scope.audience.hidden_groups(
        [role.count for role in roles], within=_partitions([role.key[0] for role in roles])
    )
    return ByJobTitle(
        population=_population(query, countries, query.comp),
        currency=scope.currency,
        split_by_level=split,
        groups=[
            JobTitleStats(
                job_role=JobRoleRef(id=role.key[0], title=role.key[1]),
                level=role.key[2],
                stats=scope.stats(role.members, hidden=index in hidden),
            )
            for index, role in enumerate(roles)
        ],
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

    def hidden_groups(
        self, counts: Sequence[int], *, within: Iterable[Sequence[int]] = ()
    ) -> set[int]:
        """The indexes of the groups of a breakdown that this caller may not see.

        The small-group rule hides groups under MIN_GROUP_SIZE. Then complementary
        suppression (docs/09 section 2.8): in any breakdown with a visible total (the whole
        list, and each list of indexes in `within`, such as the levels of one job role) where
        exactly one group is hidden, the smallest visible group is hidden too, so the total
        minus the visible groups never gives one hidden group away. Ties go to the group
        listed first. Hiding a group can leave another breakdown with one hidden group, so
        this repeats until nothing changes.
        """
        hidden = {index for index, count in enumerate(counts) if self.hides(count)}
        breakdowns = [range(len(counts)), *within]
        changed = bool(hidden)
        while changed:
            changed = False
            for breakdown in breakdowns:
                visible = [index for index in breakdown if index not in hidden]
                if len(breakdown) - len(visible) == 1 and visible:
                    hidden.add(min(visible, key=lambda index: (counts[index], index)))
                    changed = True
        return hidden


def _partitions[K](parents: Sequence[K]) -> list[list[int]]:
    """The indexes of the groups that share a parent (e.g. one job role's levels)."""
    indexes: dict[K, list[int]] = {}
    for index, parent in enumerate(parents):
        indexes.setdefault(parent, []).append(index)
    return list(indexes.values())


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


def _money_or_none(amount_minor: int | None, currency: str) -> Money | None:
    return None if amount_minor is None else _money(amount_minor, currency)


def _where(query: InsightFilters, countries: Sequence[str]) -> repository.PopulationFilter:
    return repository.PopulationFilter(
        countries=countries,
        department_ids=query.department_id,
        job_role_ids=query.job_role_id,
        levels=query.level,
        employment_types=query.employment_type,
        statuses=query.status,
    )


def _population(query: InsightFilters, countries: Sequence[str], comp: Comp) -> Population:
    """The filters actually applied, as the response echoes them."""
    return Population(
        country=list(countries),
        department_id=query.department_id,
        job_role_id=query.job_role_id,
        level=query.level,
        employment_type=query.employment_type,
        status=query.status,
        comp=comp,
    )
