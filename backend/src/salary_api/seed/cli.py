"""`python -m salary_api.seed`: the seed's command line (docs/12-seed-data.md section 14).

Only argument parsing lives here (excluded from coverage, docs/14 section 7); runner.py does
the work.
"""

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from pydantic import ValidationError

from salary_api.core.security import PasswordHasher
from salary_api.seed.errors import SeedRefused
from salary_api.seed.runner import SeedOptions, run_seed
from salary_api.seed.settings import SeedSettings

_MAX_EMPLOYEES = 999_999  # employee codes have six digits


def main(argv: Sequence[str] | None = None) -> int:
    """Seed the database. Exit status 0 when done, 2 when refused or misconfigured."""
    options = parse_args(argv)
    try:
        from_environment: dict[str, Any] = {}  # read from the environment and `.env`
        settings = SeedSettings(**from_environment)
    except ValidationError as error:
        print(f"seed: invalid settings (is APP_ENV set?):\n{error}", file=sys.stderr)
        return 2
    try:
        run_seed(options, settings, hasher=PasswordHasher(), out=sys.stdout)
    except SeedRefused as refused:
        print(f"seed: {refused}", file=sys.stderr)
        return 2
    return 0


def parse_args(argv: Sequence[str] | None = None) -> SeedOptions:
    parser = argparse.ArgumentParser(
        prog="python -m salary_api.seed",
        description="Fill the database with the deterministic demo data (docs/12-seed-data.md).",
    )
    parser.add_argument("--seed", type=int, default=42, help="random seed (default 42)")
    parser.add_argument(
        "--employees", type=_employee_count, default=10_000, help="how many (default 10000)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete all data first (refused with APP_ENV=production unless --force-demo)",
    )
    parser.add_argument(
        "--no-story", dest="story", action="store_false", help="plant no demo story"
    )
    parser.add_argument(
        "--no-history",
        dest="history",
        action="store_false",
        help="one HIRE record per employee",
    )
    parser.add_argument("--db-url", help="target database (default: DATABASE_URL)")
    parser.add_argument(
        "--force-demo",
        action="store_true",
        help="allow --reset with APP_ENV=production (demo data only)",
    )
    arguments = parser.parse_args(argv)
    return SeedOptions(
        seed=arguments.seed,
        employees=arguments.employees,
        reset=arguments.reset,
        story=arguments.story,
        history=arguments.history,
        db_url=arguments.db_url,
        force_demo=arguments.force_demo,
    )


def _employee_count(text: str) -> int:
    count = int(text)
    if not 1 <= count <= _MAX_EMPLOYEES:
        raise argparse.ArgumentTypeError(f"must be between 1 and {_MAX_EMPLOYEES}")
    return count
