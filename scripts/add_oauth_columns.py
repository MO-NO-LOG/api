"""Add oauth_provider and oauth_id columns to users table.

Safe migration: idempotent, won't fail if columns/constraint already exist.
"""

from app.database import engine
from sqlalchemy import text


def migrate() -> None:
    conn = engine.connect()
    trans = conn.begin()
    try:
        # Check if column exists before adding
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'users' AND column_name = 'oauth_provider'"
        ))
        if result.fetchone() is None:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(20) DEFAULT NULL"
            ))
            print("Added oauth_provider column")

        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'users' AND column_name = 'oauth_id'"
        ))
        if result.fetchone() is None:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN oauth_id VARCHAR(100) DEFAULT NULL"
            ))
            print("Added oauth_id column")

        # Add unique constraint if not exists
        result = conn.execute(text(
            "SELECT constraint_name FROM information_schema.table_constraints "
            "WHERE table_name = 'users' AND constraint_name = 'uq_user_oauth'"
        ))
        if result.fetchone() is None:
            conn.execute(text(
                "ALTER TABLE users ADD CONSTRAINT uq_user_oauth UNIQUE (oauth_provider, oauth_id)"
            ))
            print("Added uq_user_oauth unique constraint")

        trans.commit()
        print("Migration complete: users table now has oauth_provider and oauth_id columns")
    except Exception:
        trans.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
