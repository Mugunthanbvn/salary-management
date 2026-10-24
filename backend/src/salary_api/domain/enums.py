"""Domain enums with the exact values of docs/glossary.md §2 (stored as-is in the DB and API)."""

from enum import StrEnum


class Level(StrEnum):
    """Job level: L1 Associate, L2 Mid, L3 Senior, L4 Lead/Staff, L5 Principal, L6 Director."""

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"


class EmploymentType(StrEnum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACTOR = "CONTRACTOR"


class EmployeeStatus(StrEnum):
    ACTIVE = "ACTIVE"
    TERMINATED = "TERMINATED"


class SalaryReason(StrEnum):
    """Why a salary record was written."""

    HIRE = "HIRE"
    PROMOTION = "PROMOTION"
    MERIT = "MERIT"
    MARKET_ADJUSTMENT = "MARKET_ADJUSTMENT"
    CORRECTION = "CORRECTION"


class ComponentType(StrEnum):
    """A salary component on top of base pay (ADR 0010)."""

    ALLOWANCE = "ALLOWANCE"
    BONUS_TARGET = "BONUS_TARGET"


class PayEquityFlag(StrEnum):
    """Compa-ratio against the band: < 0.80, 0.80 to 1.20 inclusive, > 1.20."""

    UNDERPAID = "UNDERPAID"
    IN_BAND = "IN_BAND"
    OVERPAID = "OVERPAID"
