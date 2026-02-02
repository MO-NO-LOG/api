from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt

from app.config import settings

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

    # S3 객체 키 생성
    object_key = f"profile_images/{img_uuid}.avif"

    # 공개 URL 생성
    if settings.S3_PUBLIC_URL:
        # 커스텀 CDN/공개 URL 사용
        return f"{settings.S3_PUBLIC_URL.rstrip('/')}/{object_key}"
    elif settings.S3_ENDPOINT_URL:
        # 커스텀 엔드포인트 사용 (MinIO, R2 등)
        endpoint = settings.S3_ENDPOINT_URL.rstrip("/")
        if settings.S3_USE_PATH_STYLE:
            return f"{endpoint}/{settings.S3_BUCKET_NAME}/{object_key}"
        else:
            return f"{endpoint}/{object_key}"
    else:
        # AWS S3 기본 URL
        return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.S3_REGION}.amazonaws.com/{object_key}"
