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

    @property
    def label(self) -> str:
        """The display name from docs/glossary.md §2, e.g. `Lead/Staff` for L4."""
        return _LEVEL_LABELS[self]


_LEVEL_LABELS = {
    Level.L1: "Associate",
    Level.L2: "Mid",
    Level.L3: "Senior",
    Level.L4: "Lead/Staff",
    Level.L5: "Principal",
    Level.L6: "Director",
}


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
