import sys
import os
from datetime import date as date_type

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User
from app.utils import get_password_hash


def make_user(
    nickname: str, email: str, password: str, gender: str | None = None, birth_date: str | None = None
):
    """
    Create a new regular user.

    Args:
        nickname: User's unique nickname
        email: User's unique email
        password: User's password (will be hashed)
        gender: User's gender (optional, 'M' or 'F')
        birth_date: User's birth date in YYYY-MM-DD format (optional)
    """
    db = SessionLocal()
    try:
        # Check if email already exists
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            print(f"Error: User with email '{email}' already exists.")
            return

        # Check if nickname already exists
        existing_nickname = db.query(User).filter(User.nickname == nickname).first()
        if existing_nickname:
            print(f"Error: User with nickname '{nickname}' already exists.")
            return

        # Hash password (bcrypt includes salt automatically)
        hashed_password = get_password_hash(password)

        parsed_birth_date = None
        if birth_date:
            parsed_birth_date = date_type.fromisoformat(birth_date)

        # Create new user
        new_user = User(
            nickname=nickname,
            email=email,
            password=hashed_password,
            gender=gender,
            birth_date=parsed_birth_date,
            is_admin=False,
        )
        db.add(new_user)
        db.commit()

        print(f"Success: User '{nickname}' ({email}) has been created.")
        print(f"User ID: {new_user.uid}")

    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: uv run python scripts/make_user.py <nickname> <email> <password> [gender] [birth_date]"
        )
        print(
            "Example: uv run python scripts/make_user.py johndoe john@example.com mypassword123 M 1990-01-01"
        )
        print("Gender is optional (M or F)")
        print("Birth date is optional (YYYY-MM-DD)")
        sys.exit(1)

    user_nickname = sys.argv[1]
    user_email = sys.argv[2]
    user_password = sys.argv[3]
    user_gender = sys.argv[4] if len(sys.argv) > 4 else None
    user_birth_date = sys.argv[5] if len(sys.argv) > 5 else None

    # Validate gender if provided
    if user_gender and user_gender not in ["M", "F", "m", "f"]:
        print("Error: Gender must be 'M' or 'F'")
        sys.exit(1)

    if user_gender:
        user_gender = user_gender.upper()

    make_user(user_nickname, user_email, user_password, user_gender, user_birth_date)
