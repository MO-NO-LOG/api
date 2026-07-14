from datetime import timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

import bcrypt
from app.config import settings
from app.database import get_db
import httpx

from app.models import User
from app.schemas import ProfileCompleteRequest, TokenResponse
from app.security import set_refresh_cookie
from app.services.token_service import RefreshTokenService
from app.utils import (
    create_access_token,
    create_refresh_token,
    create_setup_token,
    decode_setup_token,
)

router = APIRouter(prefix="/oauth", tags=["oauth"])

KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_PROFILE_URL = "https://kapi.kakao.com/v2/user/me"

FRONTEND_URL = "https://mono-log.fun"


@router.get("/kakao/login")
async def kakao_login():
    """Redirect to Kakao OAuth consent screen."""
    if not settings.KAKAO_REST_API_KEY or not settings.KAKAO_REDIRECT_URI:
        raise HTTPException(
            status_code=503,
            detail="Kakao OAuth is not configured on this server.",
        )

    params = {
        "client_id": settings.KAKAO_REST_API_KEY,
        "redirect_uri": settings.KAKAO_REDIRECT_URI,
        "response_type": "code",
    }
    auth_url = f"{KAKAO_AUTH_URL}?{urlencode(params)}"

    return Response(
        status_code=307,
        headers={"Location": auth_url},
    )


@router.get("/kakao/callback")
async def kakao_callback(
    code: str,
    response: Response,
    db: Session = Depends(get_db),
):
    """Handle Kakao OAuth callback."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                KAKAO_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.KAKAO_REST_API_KEY,
                    "redirect_uri": settings.KAKAO_REDIRECT_URI,
                    "code": code,
                },
            )
    except (httpx.HTTPError, Exception) as exc:
        print(f"Kakao token error: {exc}")
        return Response(
            status_code=307,
            headers={"Location": f"{FRONTEND_URL}/login.html?error=kakao_network"},
        )

    if token_resp.status_code != 200:
        return Response(
            status_code=307,
            headers={"Location": f"{FRONTEND_URL}/login.html?error=kakao_auth_failed"},
        )

    kakao_token = token_resp.json()
    access_token = kakao_token["access_token"]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            profile_resp = await client.get(
                KAKAO_PROFILE_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except (httpx.HTTPError, Exception) as exc:
        print(f"Kakao profile error: {exc}")
        return Response(
            status_code=307,
            headers={"Location": f"{FRONTEND_URL}/login.html?error=kakao_profile_failed"},
        )

    if profile_resp.status_code != 200:
        return Response(
            status_code=307,
            headers={"Location": f"{FRONTEND_URL}/login.html?error=kakao_profile_failed"},
        )

    profile = profile_resp.json()
    kakao_id = str(profile["id"])
    kakao_account = profile.get("kakao_account", {})
    properties = profile.get("properties", {})

    email = kakao_account.get("email")
    nickname = properties.get("nickname")
    gender = kakao_account.get("gender")

    if gender == "male":
        gender = "M"
    elif gender == "female":
        gender = "F"
    else:
        gender = None

    user = None
    if email:
        user = db.query(User).filter(User.email == email).first()
        if user and user.oauth_provider is None:
            user.oauth_provider = "kakao"
            user.oauth_id = kakao_id
            db.commit()

    if not user:
        if not email:
            email = f"kakao_{kakao_id}@placeholder.local"

        existing_placeholder = db.query(User).filter(User.email == email).first()
        if existing_placeholder:
            return Response(
                status_code=307,
                headers={"Location": f"{FRONTEND_URL}/login.html?error=kakao_duplicate"},
            )

        random_pw = bcrypt.hashpw(kakao_id.encode(), bcrypt.gensalt(rounds=12)).decode()

        user = User(
            email=email,
            password=random_pw,
            nickname=nickname or f"kakao_{kakao_id}",
            gender=gender,
            oauth_provider="kakao",
            oauth_id=kakao_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    missing = []
    if not user.email or user.email.endswith("@placeholder.local"):
        missing.append("email")
    if not user.nickname:
        missing.append("nickname")
    if not user.gender:
        missing.append("gender")
    if not user.birth_date:
        missing.append("birth_date")

    if missing:
        setup_token = create_setup_token(str(user.email))
        return Response(
            status_code=307,
            headers={
                "Location": f"{FRONTEND_URL}/profile_complete.html?{urlencode({'token': setup_token, 'missing': ','.join(missing)})}"
            },
        )

    access = create_access_token(
        data={"sub": str(user.email)},
        expires_delta=timedelta(minutes=30),
    )
    refresh = create_refresh_token(
        data={"sub": str(user.email)},
        expires_delta=timedelta(days=7),
    )

    await RefreshTokenService.store_refresh_token(
        email=str(user.email),
        refresh_token=refresh,
        expires_delta=timedelta(days=7),
    )

    set_refresh_cookie(
        response,
        refresh,
        max_age=int(timedelta(days=7).total_seconds()),
    )

    response.set_cookie(
        key="oauth_access_token",
        value=access,
        max_age=int(timedelta(minutes=30).total_seconds()),
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN if settings.COOKIE_DOMAIN else None,
    )

    return Response(
        status_code=307,
        headers={"Location": f"{FRONTEND_URL}/"},
    )


@router.post("/kakao/complete-profile", response_model=TokenResponse)
async def complete_profile(
    payload: ProfileCompleteRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Complete missing profile fields after Kakao OAuth signup."""
    try:
        setup_data = decode_setup_token(payload.setup_token)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired setup token")

    email = setup_data["sub"]
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    if payload.email and user.email.endswith("@placeholder.local"):
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing and existing.uid != user.uid:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = payload.email

    if payload.nickname:
        user.nickname = payload.nickname
    if payload.gender:
        user.gender = payload.gender
    if payload.birth_date:
        user.birth_date = payload.birth_date

    db.commit()
    db.refresh(user)

    access = create_access_token(
        data={"sub": str(user.email)},
        expires_delta=timedelta(minutes=30),
    )
    refresh = create_refresh_token(
        data={"sub": str(user.email)},
        expires_delta=timedelta(days=7),
    )

    await RefreshTokenService.store_refresh_token(
        email=str(user.email),
        refresh_token=refresh,
        expires_delta=timedelta(days=7),
    )

    set_refresh_cookie(
        response,
        refresh,
        max_age=int(timedelta(days=7).total_seconds()),
    )

    response.set_cookie(
        key="oauth_access_token",
        value=access,
        max_age=int(timedelta(minutes=30).total_seconds()),
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN if settings.COOKIE_DOMAIN else None,
    )

    return {
        "access_token": access,
        "token_type": "bearer",
    }
