"""The system prompt (docs/10 section 5): versioned in prompts/system.md, short on purpose.

The reference data block is generated from the database, so tool arguments use real values.
"""

from datetime import date
from functools import cache
from importlib.resources import files

from salary_api.domain.enums import Level
from salary_api.modules.ask.tools import Reference


@cache
def _template() -> str:
    return (files("salary_api.modules.ask") / "prompts" / "system.md").read_text(encoding="utf-8")


def system_prompt(reference: Reference, *, today: date) -> str:
    return (
        _template()
        .replace("{{today}}", today.isoformat())
        .replace("{{reference}}", reference_block(reference))
    )


def reference_block(reference: Reference) -> str:
    countries = "; ".join(f"{code}: {label}" for code, label in reference.country_labels.items())
    levels = "; ".join(f"{level.value} {level.label}" for level in Level)
    return "\n".join(
        [
            f"- Countries: {countries}",
            f"- Departments: {'; '.join(sorted(reference.departments))}",
            f"- Job roles: {'; '.join(sorted(reference.job_roles))}",
            f"- Levels: {levels}",
        ]
    )
