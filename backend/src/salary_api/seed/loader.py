"""Write the seed into a database (docs/12-seed-data.md section 13).

Schema first (Alembic `upgrade head`), then SQLAlchemy Core `insert()` executemany in chunks,
with every ID already set by the generator. Everything runs in the caller's transaction, so a
failed seed leaves nothing behind.
"""

import sqlite3
from collections.abc import Sequence
from dataclasses import fields
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Final

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, bindparam, delete, insert, select, update

import salary_api

# Importing the models registers every table on Base.metadata, which clear() relies on.
from salary_api.all_models import (
    Country,
    Department,
    Employee,
    FxRate,
    JobRole,
    PayBand,
    SalaryComponent,
    SalaryRecord,
    User,
)
from salary_api.core.models import Base
from salary_api.seed.errors import SeedRefused
from salary_api.seed.generator import Dataset
from salary_api.seed.rows import UserRow

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

CHUNK_SIZE: Final = 1000
ALEMBIC_INI: Final = Path(salary_api.__file__).resolve().parents[2] / "alembic.ini"


def migrate(engine: Engine) -> None:
    """Bring the schema to the latest Alembic revision (`alembic upgrade head`)."""
    config = Config(ALEMBIC_INI)
    with engine.connect() as connection:  # not begin(): env.py manages the transaction
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def load(
    connection: Connection,
    dataset: Dataset,
    users: Sequence[UserRow],
    *,
    reset: bool = False,
    chunk_size: int = CHUNK_SIZE,
) -> None:
    """Insert the users and the dataset in the caller's transaction (the caller commits).

    Without `reset`, a database that already has data is refused (SeedRefused). With it,
    every row of every table is deleted first.
    """
    if reset:
        clear(connection)
    elif _has_data(connection):
        raise SeedRefused("The database already has data: pass --reset to replace it.")
    for model, rows in (
        (User, users),
        (Country, dataset.countries),
        (Department, dataset.departments),
        (JobRole, dataset.job_roles),
        (PayBand, dataset.pay_bands),
        (FxRate, dataset.fx_rates),
    ):
        _insert(connection, model, rows, chunk_size)
    # employees and salary_records reference each other: employees first, without their
    # current record, then the history, then the link (as the employee service does).
    _insert(connection, Employee, dataset.employees, chunk_size, without="current_salary_record_id")
    _insert(connection, SalaryRecord, dataset.salary_records, chunk_size)
    _insert(connection, SalaryComponent, dataset.salary_components, chunk_size)
    link = (
        update(Employee)
        .where(Employee.id == bindparam("employee_id"))
        # updated_at is set too, or its onupdate default would write the wall-clock time.
        .values(
            current_salary_record_id=bindparam("record_id"),
            updated_at=bindparam("last_change"),
        )
    )
    rows = [
        {
            "employee_id": employee.id,
            "record_id": employee.current_salary_record_id,
            "last_change": employee.updated_at,
        }
        for employee in dataset.employees
    ]
    for start in range(0, len(rows), chunk_size):
        connection.execute(link, rows[start : start + chunk_size])


def clear(connection: Connection) -> None:
    """Delete every row of every table, dependants first (the reset of demo data).

    The one place rows of the append-only tables are deleted: a reset wipes the whole demo
    database, and production refuses it unless explicitly forced (docs/12 section 14).
    """
    connection.execute(update(Employee).values(current_salary_record_id=None))
    for table in reversed(Base.metadata.sorted_tables):
        connection.execute(delete(table))


def checkpoint(engine: Engine) -> None:
    """Fold the WAL into the main file of a local SQLite database, so it is one file.

    Run after the seed's transaction has committed. Other databases need nothing.
    """
    with engine.connect() as connection:
        dbapi_connection = connection.connection.dbapi_connection
        if isinstance(dbapi_connection, sqlite3.Connection):
            # Straight to the driver: inside the BEGIN IMMEDIATE that SQLAlchemy would open,
            # the checkpoint could not complete.
            dbapi_connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def _has_data(connection: Connection) -> bool:
    return any(
        connection.execute(select(table).limit(1)).first() is not None
        for table in Base.metadata.sorted_tables
    )


def _insert(
    connection: Connection,
    model: type[Base],
    rows: "Sequence[DataclassInstance]",
    chunk_size: int,
    *,
    without: str | None = None,
) -> None:
    """Core executemany of `rows` (seed row dataclasses) in chunks of `chunk_size`."""
    if not rows:
        return
    names = [name for name in _field_names(type(rows[0])) if name != without]
    statement = insert(model)
    for start in range(0, len(rows), chunk_size):
        chunk = rows[start : start + chunk_size]
        connection.execute(
            statement, [{name: getattr(row, name) for name in names} for row in chunk]
        )


@cache
def _field_names(row_type: "type[DataclassInstance]") -> tuple[str, ...]:
    return tuple(field.name for field in fields(row_type))
