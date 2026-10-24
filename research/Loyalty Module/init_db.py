"""
Creates all tables from the SQLAlchemy models, then applies the raw-SQL
migrations in ./migrations (in filename order). Every migration is
idempotent, so this is safe to re-run and also upgrades an existing database.

Usage: python init_db.py
"""
import pathlib

from sqlalchemy import text

from app.database import engine
from app.models import Base

MIGRATIONS_DIR = pathlib.Path(__file__).parent / "migrations"


def create_schema(bind=engine, verbose: bool = True) -> None:
    Base.metadata.create_all(bind)
    if verbose:
        print("Tables created (or already existed).")

    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if verbose:
            print(f"Applying migration: {sql_file.name}")
        with bind.begin() as conn:
            conn.execute(text(sql_file.read_text()))
    if verbose:
        print("Migrations applied.")


def main():
    print(f"Connecting to {engine.url!s}")
    create_schema()


if __name__ == "__main__":
    main()
