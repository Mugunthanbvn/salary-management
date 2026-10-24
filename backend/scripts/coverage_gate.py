"""Coverage gate: at least 90 % (branch) on domain/ and modules/*/service.py.

Run after `pytest --cov` (make test-backend, CI). Overall coverage is reported by pytest-cov;
this gate covers only the business logic (docs/14-testing-strategy.md section 7). While no
gated file exists yet, it passes; it starts gating as soon as one appears.
"""

import sys

from coverage import Coverage
from coverage.exceptions import NoDataError
from coverage.files import GlobMatcher

GATED_FILES = ["*/salary_api/domain/*.py", "*/salary_api/modules/*/service.py"]
FAIL_UNDER = 90.0


def is_gated(path: str) -> bool:
    """Whether a source file counts towards the gate (the matcher coverage uses for include)."""
    return GlobMatcher(GATED_FILES).match(path)


def main() -> int:
    coverage = Coverage()
    coverage.load()
    print("Coverage gate: domain/ and modules/*/service.py")
    try:
        total = coverage.report(include=GATED_FILES, show_missing=True, skip_covered=False)
    except NoDataError:
        print("No domain or service files yet: nothing to gate.")
        return 0
    if total < FAIL_UNDER:
        print(f"FAILED: {total:.1f} % is below {FAIL_UNDER:.0f} %.")
        return 1
    print(f"Passed: {total:.1f} % >= {FAIL_UNDER:.0f} %.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
