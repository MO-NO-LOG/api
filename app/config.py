from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_USER: str
    DB_PASS: str
    DB_HOST: str
    DB_PORT: str = "5432"
    DB_NAME: str
    DB_DATA: str

    SECRET_KEY: str  # Must be set via environment variable; no default allowed
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    COOKIE_SECURE: bool = False  # Set True in production (HTTPS required)
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: Optional[str] = None
    COOKIE_PATH: str = "/"
    COOKIE_MAX_AGE_DAYS: int = 7

    REFRESH_TOKEN_COOKIE_NAME: str = "refresh_token"
    REFRESH_TOKEN_COOKIE_HTTPONLY: bool = True
    REFRESH_TOKEN_COOKIE_SECURE: bool = False  # Set True in production (HTTPS required)
    REFRESH_TOKEN_COOKIE_SAMESITE: str = "lax"

    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    CSRF_TOKEN_BYTES: int = 32

    RATE_LIMIT_MAX_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_ATTEMPT_WINDOW_SECONDS: int = 900

    VALKEY_HOST: str = "localhost"
    VALKEY_PORT: int = 6379
    VALKEY_DB: int = 0
    VALKEY_PASSWORD: str = ""

    TMDB_API_KEY: str = ""  # TMDB API key for fetching movie data

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    EMAIL_VERIFICATION_TTL_MINUTES: int = 10

    # S3 Storage Configuration (compatible with AWS S3, MinIO, Cloudflare R2, etc.)
    S3_ENDPOINT_URL: Optional[str] = (
        None  # e.g., "https://s3.amazonaws.com" or "http://localhost:9000"
    )
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = "profile-images"
    S3_REGION: str = "us-east-1"
    S3_PUBLIC_URL: Optional[str] = None  # Custom CDN/public URL (optional)
    S3_USE_PATH_STYLE: bool = False  # True for MinIO, False for AWS S3

    class Config:
        env_file = ".env"


settings = Settings()  # ty:ignore[missing-argument]
