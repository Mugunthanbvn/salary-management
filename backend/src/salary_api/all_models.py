"""Imports every ORM model, so `Base.metadata` knows every table.

Alembic (`migrations/env.py`) and the migration tests import this module.
Add each new `modules/<feature>/models.py` here.
"""

from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.users.models import User

__all__ = ["AuditEvent", "User"]
