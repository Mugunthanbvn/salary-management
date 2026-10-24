"""Copy the seed file into an empty, migrated Turso database in large batches.

Use it when the database was created in the Turso web dashboard (so `turso db create
--from-file` is not an option). Inserting row by row over the network takes about an hour;
batches of a few hundred rows take about 80 s for the 10k seed.

    make seed-turso                                   # builds build/seed.db
    DATABASE_URL="sqlite+libsql://<db>-<org>.<region>.turso.io?secure=true" \\
    DATABASE_AUTH_TOKEN=... uv run alembic upgrade head   # creates the tables
    DATABASE_URL=... DATABASE_AUTH_TOKEN=... \\
    uv run python scripts/copy_seed_to_turso.py ../build/seed.db

It refuses to run if the two databases are at different migrations or a table is not empty.
"""

import os
import sys
import time

import sqlalchemy as sa

MAX_PARAMS_PER_STATEMENT = 30_000  # SQLite allows 32,766 bound parameters


def main(seed_file: str) -> None:
    src = sa.create_engine(f"sqlite:///{seed_file}")
    dst = sa.create_engine(
        os.environ["DATABASE_URL"],
        connect_args={"auth_token": os.environ["DATABASE_AUTH_TOKEN"]},
    )
    meta = sa.MetaData()
    meta.reflect(src)
    with src.connect() as s:
        src_rev = s.execute(sa.text("select version_num from alembic_version")).scalar()
    start = time.monotonic()
    with dst.begin() as d:
        d.execute(sa.text("PRAGMA foreign_keys=OFF"))
        dst_rev = d.execute(sa.text("select version_num from alembic_version")).scalar()
        if dst_rev != src_rev:
            sys.exit(f"Migration mismatch: target {dst_rev}, seed file {src_rev}")
        for table in meta.tables.values():
            if table.name == "alembic_version":
                continue
            count = d.execute(sa.select(sa.func.count()).select_from(table)).scalar()
            if count:
                sys.exit(f"Table {table.name} is not empty ({count} rows); nothing copied")
            with src.connect() as s:
                rows = [dict(r._mapping) for r in s.execute(sa.select(table))]
            size = max(1, MAX_PARAMS_PER_STATEMENT // len(table.columns))
            for i in range(0, len(rows), size):
                d.execute(table.insert().values(rows[i : i + size]))
            print(f"{table.name}: {len(rows)} rows ({time.monotonic() - start:.1f} s)")
    print(f"Committed in {time.monotonic() - start:.1f} s")


if __name__ == "__main__":
    main(sys.argv[1])
