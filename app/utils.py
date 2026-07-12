from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

import bcrypt
from jose import jwt
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings

if TYPE_CHECKING:
    from app.models import User

# Secret key for JWT (should be in env var, but hardcoded for now)
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    bcrypt includes salt in the hash, so no separate salt is needed.

    Args:
        plain_password: The plain text password
        hashed_password: The hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    bcrypt automatically generates and includes salt in the hash.

    Args:
        password: The plain text password

    Returns:
        The hashed password as a string
    """
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a refresh token with longer expiration time.

    Args:
        data: Dictionary containing user data (e.g., {"sub": email})
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        from app.config import settings

        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid or expired
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def build_s3_url(object_key: str) -> str:
    """
    Build a public S3 URL for the given object key.

    Supports custom CDN URLs, custom endpoints (MinIO/R2), and AWS S3.
    """
    if settings.S3_PUBLIC_URL:
        return f"{settings.S3_PUBLIC_URL.rstrip('/')}/{object_key}"
    if settings.S3_ENDPOINT_URL:
        endpoint = settings.S3_ENDPOINT_URL.rstrip("/")
        if settings.S3_USE_PATH_STYLE:
            return f"{endpoint}/{settings.S3_BUCKET_NAME}/{object_key}"
        return f"{endpoint}/{object_key}"
    return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.S3_REGION}.amazonaws.com/{object_key}"


def get_profile_image_url(img_uuid: Optional[str]) -> Optional[str]:
    """
    Convert profile image UUID to full S3 URL.

    Args:
        img_uuid: UUID of the profile image (without path or extension)

    Returns:
        Full S3 URL or None if img_uuid is empty/None
    """
    if not img_uuid:
        return None
    return build_s3_url(f"profile_images/{img_uuid}.avif")


def review_count_subquery(db: Session):
    """Return a subquery that counts reviews per movie."""
    from app.models import Review

    return (
        db.query(Review.mid, func.count(Review.rid).label("review_count"))
        .group_by(Review.mid)
        .subquery()
    )


def user_review_count_subquery(db: Session):
    """Return a subquery that counts reviews per user."""
    from app.models import Review

    return (
        db.query(Review.uid, func.count(Review.rid).label("review_count"))
        .group_by(Review.uid)
        .subquery()
    )


def is_owner_or_admin(obj, user: "User") -> bool:
    """Check whether the user owns the object or is an admin."""
    return bool(obj.uid == user.uid or user.is_admin)


def parse_release_date(date_str: Optional[str]) -> Optional[date]:
    """Parse an ISO date string (YYYY-MM-DD) or return None."""
    if not date_str:
        return None
    return date.fromisoformat(date_str)
