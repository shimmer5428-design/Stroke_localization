"""Initialize the neuro_localization database."""
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy_utils import database_exists, create_database

from .models import Base, get_engine, DATABASE_URL


def ensure_database():
    """Create the database if it doesn't exist."""
    if not database_exists(DATABASE_URL):
        create_database(DATABASE_URL)
        print(f"Created database: neuro_localization")
    else:
        print(f"Database already exists: neuro_localization")


def create_tables(engine=None):
    """Create all tables from ORM models."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    print("All tables created successfully.")


def run_schema_sql(engine=None):
    """Run the raw SQL schema file (for indexes, constraints)."""
    if engine is None:
        engine = get_engine()
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path) as f:
        sql = f.read()
    with engine.begin() as conn:
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(text(stmt))
    print("Schema SQL executed successfully.")


def init():
    """Full database initialization."""
    ensure_database()
    engine = get_engine()
    create_tables(engine)
    print("Database initialization complete.")
    return engine


if __name__ == "__main__":
    init()
