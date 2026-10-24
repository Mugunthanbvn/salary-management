"""Role → permission matrix (docs/08-security-rbac.md section 3.1, docs/glossary.md section 1)."""

import pytest

from salary_api.core.permissions import ROLE_PERMISSIONS, Permission, Role, permissions_for

# The matrix in docs/08-security-rbac.md section 3.1, row by row: (ADMIN, HR_MANAGER, VIEWER).
MATRIX: dict[str, tuple[bool, bool, bool]] = {
    "EMPLOYEE_READ": (True, True, True),
    "EMPLOYEE_WRITE": (True, True, False),
    "SALARY_READ": (True, True, False),
    "SALARY_WRITE": (True, True, False),
    "INSIGHTS_READ": (True, True, True),
    "EXPORT": (True, True, True),
    "IMPORT": (True, True, False),
    "ASK": (True, True, True),
    "USER_ADMIN": (True, False, False),
    "FX_ADMIN": (True, False, False),
    "REFERENCE_ADMIN": (True, False, False),
    "AUDIT_READ": (True, False, False),
}
ROLES_IN_MATRIX_ORDER = ("ADMIN", "HR_MANAGER", "VIEWER")


def test_roles_use_the_glossary_spellings() -> None:
    assert [role.value for role in Role] == ["ADMIN", "HR_MANAGER", "VIEWER"]


def test_permissions_use_the_glossary_spellings_in_glossary_order() -> None:
    assert [permission.value for permission in Permission] == list(MATRIX)


@pytest.mark.parametrize(
    ("role", "permission", "granted"),
    [
        (role, permission, row[column])
        for permission, row in MATRIX.items()
        for column, role in enumerate(ROLES_IN_MATRIX_ORDER)
    ],
)
def test_role_has_exactly_the_permissions_in_the_matrix(
    role: str, permission: str, granted: bool
) -> None:
    assert (Permission(permission) in permissions_for(Role(role))) is granted


def test_every_role_has_an_entry_in_the_mapping() -> None:
    assert set(ROLE_PERMISSIONS) == set(Role)


def test_permissions_for_returns_an_immutable_set() -> None:
    assert isinstance(permissions_for(Role.VIEWER), frozenset)
