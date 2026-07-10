import random
import string
import sys
from datetime import date

import httpx


def print_safe(message: str) -> None:
    """Print message safely handling unicode encoding."""
    try:
        print(message)
    except UnicodeEncodeError:
        print(
            message.encode("utf-8", errors="replace").decode("cp949", errors="replace")
        )


def generate_random_string(length: int = 10) -> str:
    """Generate random alphanumeric string."""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def generate_random_email() -> str:
    """Generate random email address."""
    username = generate_random_string(8)
    domain = random.choice(
        ["gmail.com", "kakao.com", "nate.com", "outlook.com", "naver.com", "daum.net"]
    )
    return f"{username}@{domain}"


def generate_random_nickname() -> str:
    """Generate random nickname."""
    adjectives = [
        "아자",
        "멋진",
        "화난",
        "예쁜",
        "귀여운",
        "멋있는",
        "사랑스러운",
        "활기찬",
    ]
    nouns = [
        "근명",
        "동물",
        "고양이",
        "강아지",
        "사람",
        "여자",
        "남자",
        "여행자",
        "상진",
    ]
    numbers = [str(i) for i in range(100, 999)]
    return (
        f"{random.choice(adjectives)}_{random.choice(nouns)}_{random.choice(numbers)}"
    )


def generate_random_birthdate() -> date:
    """Generate random birthdate with year 2009 or 2010."""
    year = random.choice([2009, 2010])
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # Safe for all months
    return date(year, month, day)


def generate_random_gender() -> str:
    """Generate random gender (M or F)."""
    return random.choice(["M", "F"])


def register_user(
    base_url: str,
    email: str,
    password: str,
    nickname: str,
    birth_date: date,
    gender: str,
) -> bool:
    """Register a single user via API."""
    url = f"{base_url.rstrip('/')}/api/auth/register"

    payload = {
        "email": email,
        "password": password,
        "nickname": nickname,
        "birth_date": birth_date.isoformat(),
        "gender": gender,
        "bio": None,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)

            if response.status_code == 200:
                print_safe(f"  [OK] Successfully registered: {email} ({nickname})")
                return True
            else:
                error_detail = response.json().get("detail", "Unknown error")
                print_safe(
                    f"  [FAIL] Failed to register {email}: {response.status_code} - {error_detail}"
                )
                return False
    except httpx.HTTPStatusError as e:
        print_safe(
            f"  [ERROR] HTTP error for {email}: {e.response.status_code} - {e.response.text}"
        )
        return False
    except httpx.ConnectError:
        print_safe(
            f"  [ERROR] Connection error for {email}: Cannot connect to {base_url}"
        )
        return False
    except Exception as e:
        print_safe(f"  [ERROR] Unexpected error for {email}: {str(e)}")
        return False


def main():
    """Main function to handle command line execution."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/auto_register.py <base_url> [count]")
        print("  base_url: API base URL (e.g., http://localhost:8000)")
        print("  count:    Number of users to create (default: 1)")
        sys.exit(1)

    base_url = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    if count < 1:
        print("Error: Count must be at least 1")
        sys.exit(1)

    print(f"\nRegistering {count} users to {base_url}")
    print("-" * 50)

    password = "test1234!"
    success_count = 0

    for i in range(count):
        print(f"\nUser {i + 1}/{count}:")

        email = generate_random_email()
        nickname = generate_random_nickname()
        birth_date = generate_random_birthdate()
        gender = generate_random_gender()

        print(f"  Email: {email}")
        print(f"  Nickname: {nickname}")
        print(f"  Birthdate: {birth_date}")
        print(f"  Gender: {gender}")

        if register_user(base_url, email, password, nickname, birth_date, gender):
            success_count += 1

    print("\n" + "=" * 50)
    print(f"Registration complete!")
    print(f"  Total attempted: {count}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {count - success_count}")
    print(f"  All users have password: {password}")

    if success_count > 0:
        print(
            "\nNote: Email verification is disabled, so users can log in immediately."
        )


if __name__ == "__main__":
    main()
