"""Append-only tables: rows are inserted, never changed or deleted through the application.

Audit events and salary history are append-only (docs/06-data-model.md sections 4.6 and 4.9).
A mistake in salary history is fixed by appending a CORRECTION record.
"""

from typing import Any, NoReturn, cast

from sqlalchemy import Connection, Delete, Table, Update, event, inspect
from sqlalchemy.orm import Mapper, ORMExecuteState, Session

_APPEND_ONLY_TABLES: list[Table] = []


class AppendOnlyError(Exception):
    """Rows of an append-only table cannot be changed or deleted."""


def append_only[Model: type[Any]](model: Model) -> Model:
    """Class decorator: refuse ORM updates and deletes of `model`, and bulk statements on it.

    Bulk inserts stay allowed (the seed and imports use them).
    """
    table = cast(Table, model.__table__)

    def refuse_update(mapper: Mapper[Any], _connection: Connection, target: Any) -> None:
        # A row is also "dirty" when only a relationship collection changed; that is fine.
        state = inspect(target)
        if any(state.attrs[attr.key].history.has_changes() for attr in mapper.column_attrs):
            raise AppendOnlyError(f"Rows of {table.name} cannot be changed.")

    def refuse_delete(_mapper: Mapper[Any], _connection: Connection, _target: Any) -> NoReturn:
        raise AppendOnlyError(f"Rows of {table.name} cannot be deleted.")

    event.listen(model, "before_update", refuse_update)
    event.listen(model, "before_delete", refuse_delete)
    _APPEND_ONLY_TABLES.append(table)
    return model


@event.listens_for(Session, "do_orm_execute")
def _refuse_bulk_changes(execute_state: ORMExecuteState) -> None:
    """Also refuse `session.execute(update(...))` and `delete(...)`, ORM or table form."""
    statement = execute_state.statement
    if isinstance(statement, Update | Delete) and any(
        statement.table.compare(table) for table in _APPEND_ONLY_TABLES
    ):
        raise AppendOnlyError(f"Rows of {statement.table} cannot be changed or deleted.")
