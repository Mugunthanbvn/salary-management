"""Every number and list the seed uses (docs/12-seed-data.md). Data only, no logic.

Tuning the seed means changing values here, never the generator. Shares are whole percents,
split exactly by largest remainder. Pay factors and rates are Decimal; probabilities are plain
floats because they are only compared with random draws, never multiplied into money.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final

from salary_api.core.permissions import Role
from salary_api.domain.enums import EmploymentType, Level
from salary_api.modules.reference.models import JobFamily

# --- Dates (section 12): fixed, so a re-run next month gives the same data. -------------------

ANCHOR_DATE: Final = date(2026, 10, 1)
"""'Today' for the seed: every date is relative to it, never to the wall clock."""

EARLIEST_HIRE_DATE: Final = date(2015, 10, 1)
"""Tenure is capped at 11 years before the anchor date (section 7)."""

BAND_EFFECTIVE_FROM: Final = date(2026, 1, 1)

# --- Countries (sections 2 and 5) ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CountrySpec:
    code: str  # ISO 3166-1 alpha-2
    name: str
    currency: str  # ISO 4217; every salary in the country is in it
    share: int  # percent of all employees
    pay_factor: Decimal  # pay level relative to the US, in USD terms
    rounding_major: int  # base pay is rounded to a multiple of this many major units
    faker_locale: str | None  # None: names come from the curated lists below


COUNTRIES: Final = (
    CountrySpec("US", "United States", "USD", 30, Decimal("1.00"), 1000, "en_US"),
    CountrySpec("IN", "India", "INR", 25, Decimal("0.28"), 10000, "en_IN"),
    CountrySpec("GB", "United Kingdom", "GBP", 10, Decimal("0.75"), 1000, "en_GB"),
    CountrySpec("DE", "Germany", "EUR", 8, Decimal("0.75"), 1000, "de_DE"),
    CountrySpec("CA", "Canada", "CAD", 6, Decimal("0.80"), 1000, "en_CA"),
    CountrySpec("FR", "France", "EUR", 5, Decimal("0.68"), 1000, "fr_FR"),
    CountrySpec("SG", "Singapore", "SGD", 5, Decimal("0.80"), 1000, None),
    CountrySpec("AU", "Australia", "AUD", 4, Decimal("0.80"), 1000, "en_AU"),
    CountrySpec("JP", "Japan", "JPY", 4, Decimal("0.62"), 10000, "ja_JP"),
    CountrySpec("BR", "Brazil", "BRL", 3, Decimal("0.30"), 1000, "pt_BR"),
)

# --- Departments and job roles (section 3) ------------------------------------------------------

_LEVELS_IN_ORDER: Final = tuple(Level)


@dataclass(frozen=True, slots=True)
class RoleSpec:
    title: str
    family: JobFamily
    lowest: Level
    highest: Level
    pay_multiplier: Decimal  # the "family multiplier" column of section 3
    weight: int  # percent of its department

    @property
    def levels(self) -> tuple[Level, ...]:
        """The allowed levels, lowest first."""
        start, end = _LEVELS_IN_ORDER.index(self.lowest), _LEVELS_IN_ORDER.index(self.highest)
        return _LEVELS_IN_ORDER[start : end + 1]


@dataclass(frozen=True, slots=True)
class DepartmentSpec:
    name: str
    share: int  # percent of each country's employees
    roles: tuple[RoleSpec, ...]


_F = JobFamily
_L = Level

DEPARTMENTS: Final = (
    DepartmentSpec(
        "Engineering",
        35,
        (
            RoleSpec("Software Engineer", _F.ENGINEERING, _L.L1, _L.L5, Decimal("1.00"), 35),
            RoleSpec("Frontend Engineer", _F.ENGINEERING, _L.L1, _L.L5, Decimal("1.00"), 15),
            RoleSpec("Backend Engineer", _F.ENGINEERING, _L.L1, _L.L5, Decimal("1.00"), 18),
            RoleSpec("Data Engineer", _F.ENGINEERING, _L.L1, _L.L5, Decimal("1.02"), 8),
            RoleSpec("DevOps Engineer", _F.ENGINEERING, _L.L1, _L.L5, Decimal("1.00"), 8),
            RoleSpec("QA Engineer", _F.ENGINEERING, _L.L1, _L.L4, Decimal("0.88"), 8),
            RoleSpec("Engineering Manager", _F.ENGINEERING, _L.L4, _L.L6, Decimal("1.05"), 8),
        ),
    ),
    DepartmentSpec(
        "Sales",
        15,
        (
            RoleSpec(
                "Sales Development Representative", _F.SALES, _L.L1, _L.L2, Decimal("0.70"), 30
            ),
            RoleSpec("Account Executive", _F.SALES, _L.L2, _L.L5, Decimal("0.90"), 40),
            RoleSpec("Sales Engineer", _F.SALES, _L.L2, _L.L5, Decimal("0.95"), 18),
            RoleSpec("Sales Manager", _F.SALES, _L.L4, _L.L6, Decimal("1.00"), 12),
        ),
    ),
    DepartmentSpec(
        "Operations",
        10,
        (
            RoleSpec("Operations Analyst", _F.OPERATIONS, _L.L1, _L.L4, Decimal("0.75"), 35),
            RoleSpec("Project Manager", _F.OPERATIONS, _L.L2, _L.L5, Decimal("0.88"), 30),
            RoleSpec("IT Support Specialist", _F.OPERATIONS, _L.L1, _L.L3, Decimal("0.68"), 25),
            RoleSpec("Facilities Coordinator", _F.OPERATIONS, _L.L1, _L.L3, Decimal("0.60"), 10),
        ),
    ),
    DepartmentSpec(
        "Customer Success",
        10,
        (
            RoleSpec(
                "Customer Success Manager", _F.CUSTOMER_SUCCESS, _L.L1, _L.L5, Decimal("0.78"), 45
            ),
            RoleSpec("Support Specialist", _F.CUSTOMER_SUCCESS, _L.L1, _L.L3, Decimal("0.65"), 40),
            RoleSpec(
                "Implementation Consultant", _F.CUSTOMER_SUCCESS, _L.L2, _L.L4, Decimal("0.85"), 15
            ),
        ),
    ),
    DepartmentSpec(
        "Marketing",
        8,
        (
            RoleSpec("Marketing Manager", _F.MARKETING, _L.L3, _L.L6, Decimal("0.92"), 25),
            RoleSpec("Content Marketer", _F.MARKETING, _L.L1, _L.L4, Decimal("0.75"), 35),
            RoleSpec("Growth Marketer", _F.MARKETING, _L.L1, _L.L4, Decimal("0.82"), 40),
        ),
    ),
    DepartmentSpec(
        "Product",
        6,
        (
            RoleSpec("Product Manager", _F.PRODUCT, _L.L2, _L.L6, Decimal("1.00"), 40),
            RoleSpec("Product Analyst", _F.PRODUCT, _L.L1, _L.L4, Decimal("0.85"), 20),
            RoleSpec("Product Designer", _F.DESIGN, _L.L1, _L.L5, Decimal("0.92"), 30),
            RoleSpec("UX Researcher", _F.DESIGN, _L.L1, _L.L4, Decimal("0.88"), 10),
        ),
    ),
    DepartmentSpec(
        "Finance",
        6,
        (
            RoleSpec("Financial Analyst", _F.FINANCE, _L.L1, _L.L4, Decimal("0.85"), 35),
            RoleSpec("Accountant", _F.FINANCE, _L.L1, _L.L4, Decimal("0.80"), 35),
            RoleSpec("Payroll Specialist", _F.FINANCE, _L.L1, _L.L3, Decimal("0.72"), 18),
            RoleSpec("Finance Manager", _F.FINANCE, _L.L4, _L.L6, Decimal("1.00"), 12),
        ),
    ),
    DepartmentSpec(
        "HR",
        5,
        (
            RoleSpec("HR Business Partner", _F.PEOPLE, _L.L2, _L.L5, Decimal("0.85"), 35),
            RoleSpec("Recruiter", _F.PEOPLE, _L.L1, _L.L4, Decimal("0.75"), 40),
            RoleSpec("People Operations Specialist", _F.PEOPLE, _L.L1, _L.L3, Decimal("0.70"), 25),
        ),
    ),
    DepartmentSpec(
        "Legal",
        5,
        (
            RoleSpec("Legal Counsel", _F.LEGAL, _L.L3, _L.L6, Decimal("1.10"), 45),
            RoleSpec("Paralegal", _F.LEGAL, _L.L1, _L.L3, Decimal("0.70"), 25),
            RoleSpec("Compliance Analyst", _F.LEGAL, _L.L1, _L.L4, Decimal("0.85"), 30),
        ),
    ),
)

# --- Levels and employment type (section 4) -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class LevelSpec:
    level: Level
    share: int  # percent of each country's employees, before clamping to a role's range
    reference_usd: int  # annual base in the US for a pay multiplier of 1.00
    bonus_target_pct: Decimal  # share of base


LEVELS: Final = (
    LevelSpec(Level.L1, 25, 70_000, Decimal("0.05")),
    LevelSpec(Level.L2, 30, 95_000, Decimal("0.08")),
    LevelSpec(Level.L3, 25, 125_000, Decimal("0.10")),
    LevelSpec(Level.L4, 12, 155_000, Decimal("0.15")),
    LevelSpec(Level.L5, 6, 190_000, Decimal("0.20")),
    LevelSpec(Level.L6, 2, 230_000, Decimal("0.25")),
)

EMPLOYMENT_TYPES: Final = (
    (EmploymentType.FULL_TIME, 90),
    (EmploymentType.PART_TIME, 6),
    (EmploymentType.CONTRACTOR, 4),
)

TERMINATED_SHARE: Final = Decimal("0.03")
"""Share of all employees who are TERMINATED, chosen at random."""

# --- Base pay (section 5) -----------------------------------------------------------------------

PAY_NOISE_SIGMA: Final = 0.12
"""Base pay = reference x exp(Normal(0, sigma)): log-normal noise with median 1."""

PART_TIME_FACTOR: Final = (Decimal("0.50"), Decimal("0.80"))
"""A part-timer's base is the full-time base times Uniform(low, high)."""

# --- Components (section 6) ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AllowanceRule:
    """An annual allowance: either a share of base or a fixed amount in the country's currency."""

    name: str
    country_code: str
    employment_types: tuple[EmploymentType, ...]
    percent_of_base: Decimal | None
    fixed_major: Decimal | None


_FULL_TIME: Final = (EmploymentType.FULL_TIME,)
_FULL_AND_PART_TIME: Final = (EmploymentType.FULL_TIME, EmploymentType.PART_TIME)

ALLOWANCES: Final = (
    AllowanceRule("HRA", "IN", _FULL_AND_PART_TIME, Decimal("0.40"), None),
    AllowanceRule("Special allowance", "IN", _FULL_AND_PART_TIME, Decimal("0.10"), None),
    AllowanceRule("Meal", "FR", _FULL_TIME, None, Decimal(1500)),
    AllowanceRule("Transport", "GB", _FULL_TIME, None, Decimal(1200)),
    AllowanceRule("Transport", "DE", _FULL_TIME, None, Decimal(1200)),
)

BONUS_NAME: Final = "Target bonus"
BONUS_EMPLOYMENT_TYPES: Final = _FULL_AND_PART_TIME
SALES_BONUS_EXTRA: Final = Decimal("0.05")
"""Roles in the SALES family get five more percentage points of bonus target."""

# --- Salary history (section 7) -----------------------------------------------------------------

MEAN_TENURE_YEARS: Final = 3.5
"""Tenure ~ Exponential(mean), capped at EARLIEST_HIRE_DATE."""

MERIT_PROBABILITY: Final = 0.55  # per work anniversary
MERIT_RAISE: Final = (Decimal("0.02"), Decimal("0.06"))
PROMOTION_PROBABILITY: Final = 0.15  # once per employee, on one anniversary
PROMOTION_RAISE: Final = (Decimal("0.10"), Decimal("0.15"))
MARKET_ADJUSTMENT_PROBABILITY: Final = 0.01  # per employee
MARKET_ADJUSTMENT_RAISE: Final = (Decimal("0.05"), Decimal("0.10"))
CORRECTION_PROBABILITY: Final = 0.005  # per employee
CORRECTION_CHANGE: Final = (Decimal("-0.03"), Decimal("0.03"))

# --- Demo story (section 8) ---------------------------------------------------------------------

OUTLIER_SHARE: Final = Decimal("0.02")
"""Share of active full-time employees made individual outliers."""

UNDERPAID_SHARE_OF_OUTLIERS: Final = Decimal("0.60")
UNDERPAID_FACTOR: Final = (Decimal("0.65"), Decimal("0.75"))  # times the band midpoint
OVERPAID_FACTOR: Final = (Decimal("1.30"), Decimal("1.45"))  # times the band midpoint

PAY_GAP_COUNTRY: Final = "DE"
PAY_GAP_DEPARTMENT: Final = "Customer Success"
PAY_GAP_FACTOR: Final = Decimal("0.92")
"""Every DE Customer Success employee's base is multiplied by this."""

# --- Pay bands (section 8) ----------------------------------------------------------------------

BAND_MIN_FACTOR: Final = Decimal("0.8")  # min = 0.8 x mid (glossary section 3)
BAND_MAX_FACTOR: Final = Decimal("1.2")  # max = 1.2 x mid

# --- Names and emails (section 9) ---------------------------------------------------------------

EMPLOYEE_CODE_PREFIX: Final = "ACME-"
EMAIL_DOMAIN: Final = "acme.example"  # reserved by RFC 2606: no real person is emailed


@dataclass(frozen=True, slots=True)
class NameGroup:
    """Names of one origin. A Singapore name takes its first and last name from one group."""

    origin: str
    weight: int  # percent of Singapore employees
    first_names: tuple[str, ...]
    last_names: tuple[str, ...]


SINGAPORE_NAME_GROUPS: Final = (
    NameGroup(
        "Chinese",
        75,
        (
            "Wei Ling",
            "Jia Hui",
            "Xin Yi",
            "Hui Min",
            "Mei Ling",
            "Li Ting",
            "Shu Fen",
            "Kai Wen",
            "Jun Jie",
            "Wei Jie",
            "Zhi Hao",
            "Jia Wei",
            "Yong Sheng",
            "Boon Keng",
            "Siew Lan",
        ),
        (
            "Tan",
            "Lim",
            "Lee",
            "Ng",
            "Ong",
            "Wong",
            "Goh",
            "Chua",
            "Chan",
            "Koh",
            "Teo",
            "Ang",
            "Yeo",
            "Tay",
            "Ho",
            "Low",
            "Toh",
            "Sim",
        ),
    ),
    NameGroup(
        "Malay",
        15,
        (
            "Nur Aisyah",
            "Siti",
            "Nurul Huda",
            "Farah Nadia",
            "Aisyah",
            "Hafizah",
            "Amirah",
            "Muhammad Hafiz",
            "Ahmad Faizal",
            "Muhammad Irfan",
            "Zulkifli",
            "Syafiq",
            "Haziq",
        ),
        ("Abdullah", "Rahman", "Ismail", "Hassan", "Osman", "Yusof"),
    ),
    NameGroup(
        "Indian",
        10,
        (
            "Priya",
            "Kavitha",
            "Lakshmi",
            "Divya",
            "Anitha",
            "Meena",
            "Arjun",
            "Ravi",
            "Suresh",
            "Vikram",
            "Karthik",
            "Ganesh",
        ),
        ("Ramasamy", "Krishnan", "Pillai", "Nair", "Subramaniam", "Rajendran", "Muthu"),
    ),
)

SINGAPORE_FIRST_NAMES: Final = tuple(
    name for group in SINGAPORE_NAME_GROUPS for name in group.first_names
)
SINGAPORE_LAST_NAMES: Final = tuple(
    name for group in SINGAPORE_NAME_GROUPS for name in group.last_names
)

# --- FX snapshot (section 10): illustrative, not market data. ------------------------------------

FX_AS_OF: Final = date(2026, 10, 1)
FX_SOURCE: Final = "illustrative static snapshot"
FX_RATES: Final = {  # USD per one major unit, as decimal strings (ADR 0005)
    "USD": "1.0000",
    "EUR": "1.0800",
    "GBP": "1.2700",
    "INR": "0.0120",
    "JPY": "0.0067",
    "CAD": "0.7300",
    "SGD": "0.7400",
    "AUD": "0.6600",
    "BRL": "0.1800",
}

# --- Demo users (section 11) --------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DemoUserSpec:
    email: str
    full_name: str
    role: Role
    password_env: str  # the environment variable that holds the password
    dev_password: str  # the documented default (backend/.env.example); refused in production


DEMO_USERS: Final = (
    DemoUserSpec(
        "admin@acme.example", "Arun", Role.ADMIN, "SEED_ADMIN_PASSWORD", "change-me-admin"
    ),
    DemoUserSpec("hr@acme.example", "Hema", Role.HR_MANAGER, "SEED_HR_PASSWORD", "change-me-hr"),
    DemoUserSpec(
        "viewer@acme.example", "Farah", Role.VIEWER, "SEED_VIEWER_PASSWORD", "change-me-viewer"
    ),
)
