from datetime import timedelta
from typing import cast

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    EmailVerificationConfirmRequest,
    EmailVerificationRequest,
    EmailVerificationStatusResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdateRequest,
)
from app.security import (
    create_csrf_token_with_signature,
    generate_csrf_token,
    set_csrf_cookie,
)
from app.services.email_verification_service import EmailVerificationService
from app.services.rate_limit_service import LoginAttemptService
from app.services.token_service import RefreshTokenService, TokenBlacklistService
from app.utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    if not await EmailVerificationService.is_email_verified(user.email):
        raise HTTPException(status_code=400, detail="Email verification required")

    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_nickname = db.query(User).filter(User.nickname == user.nickname).first()
    if db_nickname:
        raise HTTPException(status_code=400, detail="Nickname already taken")

    # Hash password (bcrypt includes salt automatically)
    hashed_pw = get_password_hash(user.password)

    # Create user
    new_user = User(
        email=user.email,
        password=hashed_pw,
        birth_date=user.birth_date,
        nickname=user.nickname,
        gender=user.gender,
        bio=user.bio,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    await EmailVerificationService.clear_email_verified(user.email)

    return new_user


@router.post("/verify-email/send")
async def send_verification_email(
    payload: EmailVerificationRequest, db: Session = Depends(get_db)
):
    identifier = f"verify-email:{payload.email}"
    if await LoginAttemptService.is_locked(identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later.",
        )
    db_user = db.query(User).filter(User.email == payload.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    code = EmailVerificationService.generate_code()
    ttl_seconds = settings.EMAIL_VERIFICATION_TTL_MINUTES * 60

    stored = await EmailVerificationService.store_verification_code(
        payload.email, code, ttl_seconds
    )
    if not stored:
        raise HTTPException(status_code=500, detail="Failed to store verification code")

    try:
        await EmailVerificationService.send_verification_email(payload.email, code)
    except Exception:
        await LoginAttemptService.register_failure(identifier)
        raise HTTPException(status_code=500, detail="Failed to send verification email")

    await LoginAttemptService.reset(identifier)

    return {"message": "Verification code sent"}


@router.post("/verify-email/confirm")
async def confirm_verification_email(payload: EmailVerificationConfirmRequest):
    identifier = f"verify-confirm:{payload.email}"
    if await LoginAttemptService.is_locked(identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later.",
        )
    ttl_seconds = settings.EMAIL_VERIFICATION_TTL_MINUTES * 60
    verified = await EmailVerificationService.verify_code(
        payload.email, payload.code, ttl_seconds
    )
    if not verified:
        await LoginAttemptService.register_failure(identifier)
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    await LoginAttemptService.reset(identifier)

    await EmailVerificationService.clear_verification_code(payload.email)

    return {"message": "Email verified"}


@router.post("/verify-email/status", response_model=EmailVerificationStatusResponse)
async def get_verification_status(payload: EmailVerificationRequest):
    verified = await EmailVerificationService.is_email_verified(payload.email)
    return {"verified": verified}


@router.post("/login", response_model=TokenResponse)
async def login(user_in: UserLogin, response: Response, db: Session = Depends(get_db)):
    identifier = f"{user_in.email}"
    if await LoginAttemptService.is_locked(identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    user = db.query(User).filter(User.email == user_in.email).first()
    if not user:
        await LoginAttemptService.register_failure(identifier)
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    # Verify password (bcrypt hash includes salt)
    if not verify_password(user_in.password, str(user.password)):
        await LoginAttemptService.register_failure(identifier)
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    await LoginAttemptService.reset(identifier)

    # Set token expiration based on remember_me
    # If remember_me is True, token lasts 7 days; otherwise 30 minutes
    token_expires = timedelta(days=7) if user_in.remember_me else timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(user.email)}, expires_delta=token_expires
    )

    # Create refresh token (always valid for 7 days)
    refresh_token_expires = timedelta(days=7)
    refresh_token = create_refresh_token(
        data={"sub": str(user.email)}, expires_delta=refresh_token_expires
    )

    # Store refresh token in Valkey (async)
    await RefreshTokenService.store_refresh_token(
        email=str(user.email),
        refresh_token=refresh_token,
        expires_delta=refresh_token_expires,
    )

    # Set refresh_token as HttpOnly cookie
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        max_age=int(refresh_token_expires.total_seconds()),
        httponly=settings.REFRESH_TOKEN_COOKIE_HTTPONLY,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,  # type: ignore[arg-type]
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/edit", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check if nickname is being updated and is already taken by another user
    if (
        user_update.nickname is not None
        and user_update.nickname != current_user.nickname
    ):
        existing_user = (
            db.query(User).filter(User.nickname == user_update.nickname).first()
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="Nickname already taken")

    # Update only provided fields
    user_update_data = user_update.model_dump(exclude_unset=True)
    if user_update_data:
        update_values = cast(
            dict,
            {getattr(User, key): value for key, value in user_update_data.items()},
        )
        db.query(User).filter(User.uid == current_user.uid).update(update_values)

    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
):
    # Get access token from Authorization header
    access_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        access_token = auth_header[7:]

    # Add access token to blacklist (async)
    if access_token:
        await TokenBlacklistService.add_to_blacklist(access_token)

    # Delete refresh token from Valkey (async)
    await RefreshTokenService.delete_refresh_token(str(current_user.email))

    # Clear refresh_token cookie
    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
    )

    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(None, alias=settings.REFRESH_TOKEN_COOKIE_NAME),
):
    """
    Refresh access token using refresh token from HttpOnly cookie.
    Fallback to Authorization header if cookie is not present.
    """
    # Try to get refresh token from cookie first
    if not refresh_token:
        # Fallback to Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Refresh token not found in cookie or Authorization header",
            )
        refresh_token = auth_header[7:]

    try:
        # Decode refresh token
        payload = decode_token(refresh_token)
        email = payload.get("sub")
        token_type = payload.get("type")

        if not email or not isinstance(email, str) or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Verify refresh token against stored token in Valkey (async)
        if not await RefreshTokenService.verify_refresh_token(email, refresh_token):
            raise HTTPException(
                status_code=401,
                detail="Refresh token is invalid or has been revoked",
            )

        # Get user from database
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Create new access token
        access_token = create_access_token(
            data={"sub": str(user.email)}, expires_delta=timedelta(minutes=30)
        )

        # Create new refresh token
        new_refresh_token = create_refresh_token(
            data={"sub": str(user.email)}, expires_delta=timedelta(days=7)
        )

        # Update refresh token in Valkey (async)
        await RefreshTokenService.store_refresh_token(
            email=str(user.email),
            refresh_token=new_refresh_token,
            expires_delta=timedelta(days=7),
        )

        # Set new refresh_token as HttpOnly cookie
        response.set_cookie(
            key=settings.REFRESH_TOKEN_COOKIE_NAME,
            value=new_refresh_token,
            max_age=int(timedelta(days=7).total_seconds()),
            httponly=settings.REFRESH_TOKEN_COOKIE_HTTPONLY,
            secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
            samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,  # type: ignore[arg-type]
            path=settings.COOKIE_PATH,
            domain=settings.COOKIE_DOMAIN,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.get("/csrf")
async def get_csrf_token(response: Response, request: Request):
    """
    Get or generate a CSRF token.

    This endpoint returns the current CSRF token from cookie if valid,
    or generates a new one if missing or invalid.
    The token is signed with HMAC for additional security.
    """
    token = request.cookies.get(settings.CSRF_COOKIE_NAME)

    if not token:
        # Generate new signed token
        raw_token = generate_csrf_token()
        signed_token = create_csrf_token_with_signature(raw_token)
        set_csrf_cookie(response, signed_token)
        return {"csrfToken": signed_token}

    # Return existing token
    return {"csrfToken": token}
