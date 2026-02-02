import sys
import os
from sqlalchemy import create_engine, text

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import (
    DEFAULT_DATABASE_URL,
    SQLALCHEMY_DATABASE_URL,
)
from app.config import settings
from app.models import Base
from sqlalchemy.orm import sessionmaker


def reset_db(with_seed=False):
    # 1. Create Database if not exists
    engine_default = create_engine(DEFAULT_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with engine_default.connect() as conn:
        result = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{settings.DB_NAME}'")
        )
        if not result.scalar():
            print(f"Creating database {settings.DB_NAME}...")
            conn.execute(text(f"CREATE DATABASE {settings.DB_NAME}"))
        else:
            print(f"Database {settings.DB_NAME} already exists.")

    # 2. Connect to the new database
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # 3. Create Tables
    print("Creating tables...")
    Base.metadata.drop_all(bind=engine)  # Reset for clean state
    Base.metadata.create_all(bind=engine)

    print("Database initialized successfully.")
    session.close()

    # 4. Seed data if requested
    if with_seed:
        print("\nSeeding database with sample data...")
        from scripts.seed_data import seed_all

        seed_all()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize database")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed database with sample data after initialization",
    )
    args = parser.parse_args()

    reset_db(with_seed=args.seed)
