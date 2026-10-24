"""Imports every ORM model, so `Base.metadata` knows every table.

Alembic (`migrations/env.py`) and the migration tests import this module.
Add each new `modules/<feature>/models.py` here.
"""

from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.employees.models import Employee
from salary_api.modules.imports.models import ImportJob
from salary_api.modules.reference.models import Country, Department, FxRate, JobRole, PayBand
from salary_api.modules.salaries.models import SalaryComponent, SalaryRecord
from salary_api.modules.users.models import User

__all__ = [
    "AuditEvent",
    "Country",
    "Department",
    "Employee",
    "FxRate",
    "ImportJob",
    "JobRole",
    "PayBand",
    "SalaryComponent",
    "SalaryRecord",
    "User",
]
