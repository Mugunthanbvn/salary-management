"""Domain enums use exactly the glossary §2 spellings, in the glossary's order."""

from enum import StrEnum

import pytest

from salary_api.domain.enums import (
    ComponentType,
    EmployeeStatus,
    EmploymentType,
    Level,
    PayEquityFlag,
    SalaryReason,
)


@pytest.mark.parametrize(
    ("enum", "values"),
    [
        (Level, ["L1", "L2", "L3", "L4", "L5", "L6"]),
        (EmploymentType, ["FULL_TIME", "PART_TIME", "CONTRACTOR"]),
        (EmployeeStatus, ["ACTIVE", "TERMINATED"]),
        (SalaryReason, ["HIRE", "PROMOTION", "MERIT", "MARKET_ADJUSTMENT", "CORRECTION"]),
        (ComponentType, ["ALLOWANCE", "BONUS_TARGET"]),
        (PayEquityFlag, ["UNDERPAID", "IN_BAND", "OVERPAID"]),
    ],
)
def test_domain_enums_use_the_glossary_values(enum: type[StrEnum], values: list[str]) -> None:
    assert [member.value for member in enum] == values


def test_enum_members_compare_equal_to_their_stored_strings() -> None:
    assert (Level.L3, EmploymentType.FULL_TIME) == ("L3", "FULL_TIME")


def test_each_level_has_its_glossary_label() -> None:
    assert [(level.value, level.label) for level in Level] == [
        ("L1", "Associate"),
        ("L2", "Mid"),
        ("L3", "Senior"),
        ("L4", "Lead/Staff"),
        ("L5", "Principal"),
        ("L6", "Director"),
    ]
