"""Check raw import rows against the template rules (docs/11-import-export.md sections 4-5.4).

Every broken rule of every row becomes a `RowError`; a row without errors becomes an
`ImportRow`, normalized and with its amounts in integer minor units. Pure: the reference
data and today's date come in as values. The field rules are the create-employee API's
own types (one source of truth), applied cell by cell.
"""

import difflib
import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Final

from pydantic import TypeAdapter, ValidationError

from salary_api.domain.compensation import total_compensation
from salary_api.domain.currency import SUPPORTED_CURRENCIES, USD, minor_unit_exponent
from salary_api.domain.enums import ComponentType, EmploymentType, Level
from salary_api.domain.money import InvalidAmountError, Money, TooManyDecimalsError
from salary_api.modules.employees.schemas import EmployeeCode, PersonName, WorkEmail
from salary_api.modules.imports.columns import ALLOWANCE_SLOTS, TEMPLATE_COLUMNS
from salary_api.modules.imports.parsing import RawRow
from salary_api.modules.salaries.schemas import ComponentIn, ComponentName

EARLIEST_HIRE_DATE: Final = date(1970, 1, 1)
BONUS_TARGET_NAME: Final = "Target bonus"

_EMPLOYEE_CODE = TypeAdapter(EmployeeCode)
_PERSON_NAME = TypeAdapter(PersonName)
_WORK_EMAIL = TypeAdapter(WorkEmail)
_COMPONENT_NAME = TypeAdapter(ComponentName)
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_COLUMN_ORDER = {column: position for position, column in enumerate(TEMPLATE_COLUMNS)}


class RowErrorCode(StrEnum):
    """Why a cell is refused (docs/glossary.md section 6). The date and currency codes are the
    ones POST /employees uses for the same rules."""

    REQUIRED = "required"
    INVALID_FORMAT = "invalid_format"
    UNKNOWN_VALUE = "unknown_value"
    TOO_MANY_DECIMALS = "too_many_decimals"
    FUTURE_DATE = "future_date"
    BEFORE_HIRE_DATE = "before_hire_date"
    CURRENCY_MISMATCH = "currency_mismatch"
    DUPLICATE_IN_FILE = "duplicate_in_file"
    DUPLICATE_IN_DB = "duplicate_in_db"


@dataclass(frozen=True, slots=True)
class RowError:
    """One refused cell. `row` is the spreadsheet row (the header is row 1); `value` is the
    trimmed cell text, or None for an empty cell."""

    row: int
    column: str
    code: RowErrorCode
    message: str
    value: str | None


@dataclass(frozen=True, slots=True)
class KnownCountry:
    code: str
    name: str
    currency: str  # every salary there is in this currency
    is_active: bool


@dataclass(frozen=True, slots=True)
class KnownJobRole:
    id: int
    title: str
    department: str  # an import has no department column: it follows the role


@dataclass(frozen=True, slots=True)
class ImportReference:
    """What rows are checked against: loaded once per import, not once per row."""

    countries: Mapping[str, KnownCountry]
    job_roles: Sequence[KnownJobRole]
    today: date


@dataclass(frozen=True, slots=True)
class ImportRow:
    """A valid row, ready to become an employee with a HIRE salary record."""

    row: int
    employee_code: str
    first_name: str
    last_name: str
    email: str  # trimmed and lowercased, as stored
    job_role: KnownJobRole
    level: Level
    employment_type: EmploymentType
    country_code: str
    currency: str  # the country's currency
    hire_date: date
    salary_effective_date: date
    base_minor: int
    components: tuple[ComponentIn, ...]  # allowances in slot order, then the bonus target

    @property
    def total_minor(self) -> int:
        """Base plus every component, all in the row's currency."""
        parts = (Money(c.amount_minor, self.currency) for c in self.components)
        return total_compensation(Money(self.base_minor, self.currency), parts).amount_minor


@dataclass(frozen=True, slots=True)
class RowKey:
    """The unique values of a row, normalized, where they are valid."""

    row: int
    employee_code: str | None
    email: str | None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    row_count: int
    rows: list[ImportRow]  # the rows without any error
    errors: list[RowError]  # in row order, then template column order
    keys: list[RowKey]  # every row's code and email, for the database duplicate check

    @property
    def employee_codes(self) -> list[str]:
        return [key.employee_code for key in self.keys if key.employee_code is not None]

    @property
    def emails(self) -> list[str]:
        return [key.email for key in self.keys if key.email is not None]


def validate_rows(raw_rows: Sequence[RawRow], reference: ImportReference) -> ValidationReport:
    """Check every row, then codes and emails repeated within the file."""
    checks = [_RowCheck(raw, reference) for raw in raw_rows]
    rows = [check.result() for check in checks]
    keys = [check.key for check in checks]
    errors = [error for check in checks for error in check.errors]
    errors += _repeated_in_file(keys)
    return _report(len(raw_rows), [row for row in rows if row is not None], errors, keys)


def mark_db_duplicates(
    report: ValidationReport, *, taken_codes: Collection[str], taken_emails: Mapping[str, str]
) -> ValidationReport:
    """The report with codes and emails that employees already use as errors.

    `taken_emails` maps each used email to the code of the employee who has it.
    """
    found = db_duplicates(report.keys, taken_codes=taken_codes, taken_emails=taken_emails)
    return _report(report.row_count, report.rows, [*report.errors, *found], report.keys)


def db_duplicates(
    keys: Sequence[RowKey], *, taken_codes: Collection[str], taken_emails: Mapping[str, str]
) -> list[RowError]:
    errors: list[RowError] = []
    for key in keys:
        code, email = key.employee_code, key.email
        if code is not None and code in taken_codes:
            message = f"{code} is already used by an employee."
            errors.append(
                RowError(key.row, "employee_code", RowErrorCode.DUPLICATE_IN_DB, message, code)
            )
        if email is not None and email in taken_emails:
            message = f"This email is already used by {taken_emails[email]}."
            errors.append(RowError(key.row, "email", RowErrorCode.DUPLICATE_IN_DB, message, email))
    return errors


def _report(
    row_count: int, rows: Sequence[ImportRow], errors: Sequence[RowError], keys: list[RowKey]
) -> ValidationReport:
    """A report whose rows are only those without an error."""
    refused = {error.row for error in errors}
    return ValidationReport(
        row_count=row_count,
        rows=[row for row in rows if row.row not in refused],
        errors=sorted(errors, key=lambda error: (error.row, _COLUMN_ORDER[error.column])),
        keys=keys,
    )


def _repeated_in_file(keys: Sequence[RowKey]) -> list[RowError]:
    """An error on each later row with the code or email of an earlier one."""
    errors: list[RowError] = []
    for column in ("employee_code", "email"):
        first_row: dict[str, int] = {}
        for key in keys:
            value: str | None = getattr(key, column)
            if value is None:
                continue
            if value in first_row:
                message = f"Same {column} as row {first_row[value]}."
                errors.append(
                    RowError(key.row, column, RowErrorCode.DUPLICATE_IN_FILE, message, value)
                )
            else:
                first_row[value] = key.row
    return errors


class _RowCheck:
    """The checks of one row. Each broken rule adds a RowError; the checks go on, so the
    user sees every problem of the row at once."""

    def __init__(self, raw: RawRow, reference: ImportReference) -> None:
        self.raw = raw
        self.reference = reference
        self.errors: list[RowError] = []
        self.employee_code = self._adapted(
            "employee_code",
            _EMPLOYEE_CODE,
            "Employee codes are ACME- and six digits, for example ACME-010001.",
        )
        self.first_name = self._adapted("first_name", _PERSON_NAME, _too_long("first_name", 100))
        self.last_name = self._adapted("last_name", _PERSON_NAME, _too_long("last_name", 100))
        self.email = self._adapted("email", _WORK_EMAIL, "This is not a valid email address.")
        self.key = RowKey(raw.row, self.employee_code, self.email)

    def result(self) -> ImportRow | None:
        """The import row, or None if a rule is broken (self.errors says which)."""
        job_role = self._job_role()
        level = self._choice("level", Level, "level")
        employment_type = self._choice("employment_type", EmploymentType, "employment type")
        country = self._country()
        hire_date = self._hire_date()
        currency = self._currency(country)
        base = self._amount("base_salary", currency, required=True, more_than_zero=True)
        components = self._allowances(currency)
        bonus = self._amount("bonus_target", currency, required=False, more_than_zero=False)
        if bonus is not None:
            components.append(
                ComponentIn(
                    type=ComponentType.BONUS_TARGET, name=BONUS_TARGET_NAME, amount_minor=bonus
                )
            )
        effective_date = self._effective_date(hire_date)
        if (
            self.errors
            or self.employee_code is None
            or self.first_name is None
            or self.last_name is None
            or self.email is None
            or job_role is None
            or level is None
            or employment_type is None
            or country is None
            or currency is None
            or hire_date is None
            or base is None
        ):
            return None
        return ImportRow(
            row=self.raw.row,
            employee_code=self.employee_code,
            first_name=self.first_name,
            last_name=self.last_name,
            email=self.email,
            job_role=job_role,
            level=level,
            employment_type=employment_type,
            country_code=country.code,
            currency=currency,
            hire_date=hire_date,
            salary_effective_date=effective_date or hire_date,
            base_minor=base,
            components=tuple(components),
        )

    def _text(self, column: str) -> str | None:
        value = self.raw.values.get(column)
        return value.strip() or None if value is not None else None

    def _fail(self, column: str, code: RowErrorCode, message: str) -> None:
        self.errors.append(RowError(self.raw.row, column, code, message, self._text(column)))

    def _required(self, column: str) -> str | None:
        value = self._text(column)
        if value is None:
            self._fail(column, RowErrorCode.REQUIRED, f"{column} is required.")
        return value

    def _adapted[T](self, column: str, adapter: TypeAdapter[T], message: str) -> T | None:
        """A required cell checked by an API type (pattern, length, normalization)."""
        value = self._required(column)
        if value is None:
            return None
        try:
            return adapter.validate_python(value)
        except ValidationError:
            self._fail(column, RowErrorCode.INVALID_FORMAT, message)
            return None

    def _choice[E: StrEnum](self, column: str, enum: type[E], label: str) -> E | None:
        value = self._required(column)
        if value is None:
            return None
        try:
            return enum(value.upper())
        except ValueError:
            allowed = ", ".join(enum)
            message = f"'{value}' is not a known {label}. Use one of {allowed}."
            self._fail(column, RowErrorCode.UNKNOWN_VALUE, message)
            return None

    def _job_role(self) -> KnownJobRole | None:
        value = self._required("job_role")
        if value is None:
            return None
        by_title = {role.title.casefold(): role for role in self.reference.job_roles}
        role = by_title.get(" ".join(value.split()).casefold())
        if role is None:
            guess = difflib.get_close_matches(value.casefold(), list(by_title), n=1, cutoff=0.6)
            hint = f" Did you mean '{by_title[guess[0]].title}'?" if guess else ""
            titles = ", ".join(sorted(role.title for role in self.reference.job_roles))
            message = f"'{value}' is not a known job role.{hint} Job roles: {titles}."
            self._fail("job_role", RowErrorCode.UNKNOWN_VALUE, message)
        return role

    def _country(self) -> KnownCountry | None:
        value = self._required("country")
        if value is None:
            return None
        country = self.reference.countries.get(value.upper())
        if country is None or not country.is_active:
            active = sorted(c.code for c in self.reference.countries.values() if c.is_active)
            countries = ", ".join(active)
            message = f"'{value}' is not a country ACME employs people in. Countries: {countries}."
            self._fail("country", RowErrorCode.UNKNOWN_VALUE, message)
            return None
        return country

    def _currency(self, country: KnownCountry | None) -> str | None:
        """The salary currency: always the country's. A given currency must equal it."""
        given = self._text("currency")
        if country is not None:
            if given is not None and given.upper() != country.currency:
                message = f"Salaries in {country.name} are paid in {country.currency}."
                self._fail("currency", RowErrorCode.CURRENCY_MISMATCH, message)
            return country.currency
        if given is not None and given.upper() not in SUPPORTED_CURRENCIES:
            currencies = ", ".join(sorted(SUPPORTED_CURRENCIES))
            message = f"'{given}' is not a known currency. Use one of {currencies}."
            self._fail("currency", RowErrorCode.UNKNOWN_VALUE, message)
        return None

    def _date(self, column: str, label: str, *, required: bool) -> date | None:
        value = self._required(column) if required else self._text(column)
        if value is None:
            return None
        parsed = _iso_date(value)
        if parsed is None:
            message = f"Write the {label} as YYYY-MM-DD, for example 2022-04-01."
            self._fail(column, RowErrorCode.INVALID_FORMAT, message)
        elif parsed > self.reference.today:
            message = f"The {label} cannot be in the future."
            self._fail(column, RowErrorCode.FUTURE_DATE, message)
            return None
        return parsed

    def _hire_date(self) -> date | None:
        hire_date = self._date("hire_date", "hire date", required=True)
        if hire_date is not None and hire_date < EARLIEST_HIRE_DATE:
            message = f"Hire dates before {EARLIEST_HIRE_DATE} are not accepted."
            self._fail("hire_date", RowErrorCode.INVALID_FORMAT, message)
            return None
        return hire_date

    def _effective_date(self, hire_date: date | None) -> date | None:
        column = "salary_effective_date"
        effective_date = self._date(column, "salary effective date", required=False)
        if effective_date is not None and hire_date is not None and effective_date < hire_date:
            message = "The salary effective date cannot be before the hire date."
            self._fail(column, RowErrorCode.BEFORE_HIRE_DATE, message)
            return None
        return effective_date

    def _amount(
        self, column: str, currency: str | None, *, required: bool, more_than_zero: bool
    ) -> int | None:
        """Major units as written, in minor units of `currency` (None when the currency is
        unknown: then only how the amount is written can be checked)."""
        value = self._required(column) if required else self._text(column)
        if value is None:
            return None
        try:
            money = Money.from_major(value, currency or USD)
        except TooManyDecimalsError:
            if currency is not None:
                self._fail(column, RowErrorCode.TOO_MANY_DECIMALS, _decimals_message(currency))
            return None
        except InvalidAmountError:
            message = (
                f"Write {column} as a plain number like 52000.00, "
                "with no currency symbol or thousands separator."
            )
            self._fail(column, RowErrorCode.INVALID_FORMAT, message)
            return None
        if money.amount_minor < 0 or (more_than_zero and money.amount_minor == 0):
            message = (
                f"{column} must be more than 0."
                if more_than_zero
                else f"{column} cannot be negative."
            )
            self._fail(column, RowErrorCode.INVALID_FORMAT, message)
            return None
        return money.amount_minor if currency is not None else None

    def _allowances(self, currency: str | None) -> list[ComponentIn]:
        """Up to three allowances; a name needs an amount and an amount needs a name."""
        components: list[ComponentIn] = []
        slot_of_name: dict[str, int] = {}
        for slot in ALLOWANCE_SLOTS:
            name_column, amount_column = f"allowance_{slot}_name", f"allowance_{slot}_amount"
            name, amount_text = self._text(name_column), self._text(amount_column)
            if name is None and amount_text is None:
                continue
            if amount_text is None:
                self._fail(
                    amount_column, RowErrorCode.REQUIRED, f"Allowance {slot} needs an amount."
                )
            if name is None:
                self._fail(name_column, RowErrorCode.REQUIRED, f"Allowance {slot} needs a name.")
            amount = self._amount(amount_column, currency, required=False, more_than_zero=True)
            name = self._allowance_name(name_column, name, slot, slot_of_name)
            if name is not None and amount is not None:
                components.append(
                    ComponentIn(type=ComponentType.ALLOWANCE, name=name, amount_minor=amount)
                )
        return components

    def _allowance_name(
        self, column: str, name: str | None, slot: int, slot_of_name: dict[str, int]
    ) -> str | None:
        if name is None:
            return None
        try:
            name = _COMPONENT_NAME.validate_python(name)
        except ValidationError:
            self._fail(column, RowErrorCode.INVALID_FORMAT, _too_long("Allowance names", 60))
            return None
        earlier = slot_of_name.setdefault(name.casefold(), slot)
        if earlier != slot:
            message = f"Allowance {slot} has the same name as allowance {earlier}."
            self._fail(column, RowErrorCode.INVALID_FORMAT, message)
            return None
        return name


def _iso_date(value: str) -> date | None:
    """A YYYY-MM-DD date, or None. Other forms (03/04/2022: March or April?) are refused."""
    if _ISO_DATE.fullmatch(value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:  # e.g. 2022-02-30
        return None


def _decimals_message(currency: str) -> str:
    exponent = minor_unit_exponent(currency)
    if exponent == 0:
        return f"{currency} amounts can't have decimals."
    return f"{currency} amounts have at most {exponent} decimals."


def _too_long(field: str, limit: int) -> str:
    return f"{field} can be at most {limit} characters."
