import sys
import os

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User


def make_admin(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Error: User with email '{email}' not found.")
            return

        if user.is_admin:
            print(f"User '{email}' is already an admin.")
            return

        user.is_admin = True
        db.commit()
        print(f"Success: User '{email}' has been promoted to admin.")

    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/make_admin.py <email>")
        sys.exit(1)

    target_email = sys.argv[1]
    make_admin(target_email)
