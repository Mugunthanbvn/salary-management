"""Roles and permissions (docs/glossary.md section 1, docs/08-security-rbac.md section 3).

This is the only place that maps roles to permissions. Code checks permissions, never role
names, so adding a role is one entry in ROLE_PERMISSIONS.
"""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "ADMIN"
    HR_MANAGER = "HR_MANAGER"
    VIEWER = "VIEWER"


class Permission(StrEnum):
    EMPLOYEE_READ = "EMPLOYEE_READ"
    EMPLOYEE_WRITE = "EMPLOYEE_WRITE"
    SALARY_READ = "SALARY_READ"
    SALARY_WRITE = "SALARY_WRITE"
    INSIGHTS_READ = "INSIGHTS_READ"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    ASK = "ASK"
    USER_ADMIN = "USER_ADMIN"
    FX_ADMIN = "FX_ADMIN"
    REFERENCE_ADMIN = "REFERENCE_ADMIN"
    AUDIT_READ = "AUDIT_READ"


_ADMIN_ONLY = frozenset(
    {
        Permission.USER_ADMIN,
        Permission.FX_ADMIN,
        Permission.REFERENCE_ADMIN,
        Permission.AUDIT_READ,
    }
)

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.HR_MANAGER: frozenset(Permission) - _ADMIN_ONLY,
    Role.VIEWER: frozenset(
        {Permission.EMPLOYEE_READ, Permission.INSIGHTS_READ, Permission.EXPORT, Permission.ASK}
    ),
}


def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]
