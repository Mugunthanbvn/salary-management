"""The columns of the import template (docs/11-import-export.md section 4), in template order."""

from typing import Final

ALLOWANCE_SLOTS: Final = (1, 2, 3)

TEMPLATE_COLUMNS: Final = (
    "employee_code",
    "first_name",
    "last_name",
    "email",
    "job_role",
    "level",
    "employment_type",
    "country",
    "hire_date",
    "currency",
    "base_salary",
    "bonus_target",
    *(
        column
        for slot in ALLOWANCE_SLOTS
        for column in (f"allowance_{slot}_name", f"allowance_{slot}_amount")
    ),
    "salary_effective_date",
)

REQUIRED_COLUMNS: Final = frozenset(
    {
        "employee_code",
        "first_name",
        "last_name",
        "email",
        "job_role",
        "level",
        "employment_type",
        "country",
        "hire_date",
        "base_salary",
    }
)
