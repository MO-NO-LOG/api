# MO-NO-LOG API - 백엔드 발표 자료

> 영화 커뮤니티 **MONO-LOG**의 백엔드 API
> 발표자: 백엔드 담당

---

## 📋 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [기술 스택](#2-기술-스택)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [핵심 기능](#4-핵심-기능)
5. [보안 설계](#5-보안-설계)
6. [인증/인가 시스템](#6-인증인가-시스템)
7. [데이터베이스 설계](#7-데이터베이스-설계)
8. [주요 구현 포인트](#8-주요-구현-포인트)
9. [API 구조](#9-api-구조)
10. [배포 및 운영](#10-배포-및-운영)

---

## 1. 프로젝트 개요

### MONO-LOG이란?
- 영화에 대한 리뷰와 토론을 위한 커뮤니티 플랫폼
- 사용자가 영화를 검색하고, 리뷰를 작성하고, 다른 사용자와 소통

### 백엔드 목표
- **보안 우선**: JWT, CSRF, Rate Limit 등 다층 보안 적용
- **확장성**: Valkey 기반 분산 캐싱/세션 관리
- **유연성**: S3 호환 스토리지, 선택적 이메일 인증
- **관리 편의성**: 관리자 대시보드 및 CLI 도구 제공

---

## 2. 기술 스택

| 계층 | 기술 | 비고 |
|------|------|------|
| **런타임** | Python 3.14 | 최신 Python 버전 |
| **웹 프레임워크** | FastAPI | 비동기 지원, 자동 문서화 |
| **ORM** | SQLAlchemy 2.0 | 타입 안전, 최신 ORM 패턴 |
| **데이터베이스** | PostgreSQL | 관계형 DB, JSON 지원 |
| **캐시/세션** | Valkey (Redis 호환) | 분산 세션, Rate Limit |
| **인증** | JWT (python-jose) | Access + Refresh 토큰 |
| **객체 스토리지** | S3 호환 | AWS S3, MinIO, Cloudflare R2 |
| **ASGI 서버** | Uvicorn (개발) / Hypercorn (운영) | 프로덕션 환경 분리 |
| **CLI** | Typer | 관리 작업 자동화 |
| **패키지 관리** | uv | 빠른 의존성 관리 |
| **포매팅/타입** | Ruff / Ty | 코드 품질 유지 |

---

## 3. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Client (Frontend)                     │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────┐
│                     FastAPI Application                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Routers    │  │  Middleware  │  │    Services      │  │
│  │  (API Endpts)│  │ CSRF/RateLim │  │ Token/Email/Rate │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │            │
│  ┌──────▼─────────────────▼────────────────────▼─────────┐ │
│  │              SQLAlchemy ORM Layer                      │ │
│  └─────────────────────────┬──────────────────────────────┘ │
└────────────────────────────┼────────────────────────────────┘
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│   PostgreSQL   │  │     Valkey     │  │  S3-Compatible │
│   (RDBMS)      │  │  (Cache/Session)│  │  (Profile Img) │
└────────────────┘  └────────────────┘  └────────────────┘
```

### 미들웨어 스택 (요청 처리 순서)
1. **SecurityHeadersMiddleware** - 보안 헤더 추가
2. **RateLimitMiddleware** - IP+경로 기반 레이트 리밋
3. **CsrfMiddleware** - CSRF 토큰 검증 (Double Submit Cookie)
4. **CORS** - Cross-Origin 요청 허용

---

## 4. 핵심 기능

### 4.1 인증 (Auth)
| 기능 | 설명 |
|------|------|
| 회원가입 | 이메일/닉네임 중복 검사, 선택적 이메일 인증 |
| 로그인 | Access Token (30분/7일) + Refresh Token (7일) |
| 토큰 갱신 | Refresh Token Rotation (재발급 시 기존 토큰 무효화) |
| 로그아웃 | Refresh Token Valkey 블랙리스트 등록 |
| 이메일 인증 | SMTP 기반 6자리 코드 발송 (설정으로 ON/OFF) |

### 4.2 영화 (Movies)
| 기능 | 설명 |
|------|------|
| 검색 | 제목/감독/장르 검색 + 페이지네이션 |
| 상세 조회 | 영화 정보 + 장르 + 설명 |
| 트렌드 | 평점 순 TOP 10 |
| 추천 | 평점 3.0 이상 랜덤 추천 (부족 시 전체 랜덤) |

### 4.3 리뷰 & 댓글 (Reviews)
| 기능 | 설명 |
|------|------|
| 리뷰 CRUD | 작성/조회/삭제 (본인 또는 관리자) |
| 좋아요/싫어요 | 한 리뷰당 한 번만 (L/D 토글) |
| 댓글 | 리뷰당 댓글 작성 |
| 대댓글 | 1단계 깊이 제한 (댓글 → 답글) |
| 삭제 | 소유자 또는 관리자만 가능 |

### 4.4 기타 기능
- **즐겨찾기**: 영화 즐겨찾기 토글, 목록 조회, 상태 확인
- **랭킹**: 평점 + 리뷰 수 기준 영화 랭킹
- **프로필**: 사용자 정보 조회, S3 이미지 업로드/삭제
- **관리자**: 대시보드, 사용자/영화/리뷰 관리, TMDB 수동 가져오기

---

## 5. 보안 설계

### 5.1 다층 보안 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 1: Transport Security                                  │
│  - HTTPS (COOKIE_SECURE=True in production)                  │
│  - HSTS Header (max-age=31536000)                            │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│  Layer 2: Authentication                                     │
│  - JWT Access Token (HttpOnly 쿠키 또는 Bearer 헤더)        │
│  - JWT Refresh Token (HttpOnly 전용 쿠키)                    │
│  - Token Blacklist (Valkey, 로그아웃 시 등록)                │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│  Layer 3: CSRF Protection                                    │
│  - Double Submit Cookie 패턴                                 │
│  - HMAC 서명 (secrets + SHA256)                              │
│  - 상수 시간 비교 (hmac.compare_digest)                      │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│  Layer 4: Rate Limiting                                      │
│  - Valkey 기반 분산 카운터                                   │
│  - IP + 경로 단위 제한 (기본: 120 req / 60s)                 │
│  - 로그인 시도 제한 (5회 / 15분)                             │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│  Layer 5: Security Headers                                   │
│  - X-Content-Type-Options: nosniff                           │
│  - X-Frame-Options: DENY                                     │
│  - X-XSS-Protection: 1; mode=block                           │
│  - CSP / Referrer-Policy / Permissions-Policy                │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 CSRF 보호 상세

**Double Submit Cookie 패턴 + HMAC 서명**

```python
# 1. 토큰 생성
raw_token = secrets.token_urlsafe(32)  # 암호학적으로 안전한 랜덤
signed_token = f"{raw_token}.{hmac_signature}"

# 2. 응답에 쿠키 설정 (JS에서 읽을 수 있도록 HttpOnly=False)
response.set_cookie("csrf_token", signed_token, httponly=False)

# 3. 상태 변경 요청 시 검증
cookie_token = request.cookies.get("csrf_token")
header_token = request.headers.get("X-CSRF-Token")

# 4. 서명 검증 + 상수 시간 비교
if hmac.compare_digest(cookie_raw, header_raw):
    # 유효
```

**CSRF 예외 경로** (인증 전 토큰이 없을 수 있는 경로):
- `/api/auth/login`
- `/api/auth/register`
- `/api/auth/verify-email/*`
- `/api/auth/csrf`

### 5.3 Rate Limiting

```python
# Valkey 기반 원자적 카운터
count = await client.incr(key)  # 원자적 증가
if count == 1:
    await client.expire(key, window_seconds)  # 첫 요청 시 만료 설정
return count <= max_requests
```

**로그인 시도 제한**:
- 식별자: `login_attempts:{email}`
- 임계값: 5회 실패 → 15분 잠금
- 실패 시: `register_failure()` 호출
- 성공 시: `reset()` 호출

### 5.4 토큰 생명주기

| 토큰 타입 | 만료 시간 | 저장 위치 | 특징 |
|-----------|-----------|-----------|------|
| **Access Token** | 30분 (기본) / 7일 (remember_me) | 클라이언트 메모리 또는 쿠키 | 매 요청마다 사용 |
| **Refresh Token** | 7일 | Valkey (key: `refresh_token:{email}`) | 토큰 갱신용, Rotation 적용 |
| **Blacklisted Token** | 원본 토큰 만료까지 | Valkey (key: `blacklist:{token}`) | 로그아웃 시 등록 |

**Refresh Token Rotation**:
```python
# /auth/refresh 엔드포인트
1. 기존 refresh_token 검증 (Valkey 저장값과 일치 여부)
2. 새 access_token 발급 (30분)
3. 새 refresh_token 발급 (7일)
4. Valkey에 새 refresh_token 저장 (기존 값 덮어쓰기)
5. 새 refresh_token을 HttpOnly 쿠키로 설정
```

---

## 6. 인증/인가 시스템

### 6.1 로그인 플로우

```
Client                    Backend                      Valkey
  │                           │                           │
  ├─ POST /auth/login ───────>│                           │
  │   {email, password}       │                           │
  │                           ├─ PW 검증 (bcrypt) ───────>│
  │                           │                           │
  │                           ├─ LoginAttemptService      │
  │                           │   .reset(email)           │
  │                           │                           │
  │                           ├─ Access Token 생성        │
  │                           ├─ Refresh Token 생성       │
  │                           ├─ RefreshTokenService      │
  │                           │   .store(email, token) ──>│
  │                           │                           │
  │<─ {access_token} ─────────┤                           │
  │   Set-Cookie:             │                           │
  │   refresh_token=xxx       │                           │
```

### 6.2 요청 인증 플로우

```
Client                    Backend                      Valkey
  │                           │                           │
  ├─ GET /api/...             │                           │
  │   Authorization: Bearer   │                           │
  │   또는 Cookie: access_token│                          │
  │                           │                           │
  │                           ├─ TokenBlacklistService    │
  │                           │   .is_blacklisted(token) >│
  │                           │   ← false                 │
  │                           │                           │
  │                           ├─ JWT 디코드 및 검증       │
  │                           ├─ DB에서 User 조회         │
  │                           │                           │
  │<─ 200 OK + User Data ─────┤                           │
```

### 6.3 이메일 인증 (선택적)

**설정으로 제어 가능** (`SystemSettingsService`):

```python
# 회원가입 시
if email_verification_enabled:
    if not await EmailVerificationService.is_email_verified(email):
        raise HTTPException(400, "Email verification required")

# 인증 코드 플로우
1. POST /auth/verify-email/send → 6자리 코드 생성 → SMTP 발송
2. POST /auth/verify-email/confirm → 코드 검증 → Valkey에 "verified" 플래그 저장
3. 회원가입 시 is_email_verified() 확인
```

**Valkey 키 구조**:
- `email_verification:{email}` → "123456" (TTL: 10분)
- `email_verified:{email}` → "verified" (TTL: 10분)

---

## 7. 데이터베이스 설계

### 7.1 ERD (Entity Relationship Diagram)

```
┌─────────────┐       ┌──────────────┐       ┌─────────────┐
│   users     │       │    movie     │       │    genre    │
├─────────────┤       ├──────────────┤       ├─────────────┤
│ uid (PK)    │◄──────│ mid (PK)     │──────►│ gid (PK)    │
│ nickname    │       │ title        │       │ name        │
│ email       │       │ dec          │       └─────────────┘
│ password    │       │ rat          │              ▲
│ img         │       │ director     │              │
│ bio         │       │ poster_url   │       ┌──────┴──────┐
│ gender      │       │ release_date │       │ movie_genre │
│ is_admin    │       └──────┬───────┘       ├─────────────┤
│ created_at  │              │               │ mid (FK,PK) │
└──────┬──────┘              │               │ gid (FK,PK) │
       │                     │               └─────────────┘
       │                     │
       ▼                     ▼
┌──────────────┐      ┌──────────────┐
│   review     │      │  favorite    │
├──────────────┤      ├──────────────┤
│ rid (PK)     │      │ fid (PK)     │
│ uid (FK)     │◄─────│ uid (FK)     │
│ mid (FK)     │      │ mid (FK)     │
│ title        │      │ created_at   │
│ dec          │      └──────────────┘
│ rat          │             │
│ created_at   │             │
└──────┬───────┘             │
       │                     │
       ▼                     │
┌──────────────┐             │
│   comment    │             │
├──────────────┤             │
│ cid (PK)     │             │
│ rid (FK)     │◄────────────┘
│ uid (FK)     │
│ dec          │
│ parent_cid   │──┐ (대댓글, NULL=최상위)
│ created_at   │  │
└──────┬───────┘  │
       │          │
       ▼          │
┌──────────────┐  │
│ review_like  │  │
│ comment_like │  │
├──────────────┤  │
│ lid (PK)     │  │
│ rid/cid (FK) │  │
│ uid (FK)     │  │
│ type (L/D)   │  │
│ created_at   │  │
└──────────────┘  │
                  │
                  └─ (replies 관계)
```

### 7.2 주요 설계 결정

| 결정 | 이유 |
|------|------|
| **Soft Delete 미사용** | `CASCADE` 삭제로 데이터 일관성 유지, 실제 삭제로 용량 관리 |
| **Comment 계층 구조** | `parent_cid` Self-Reference, 깊이 1로 제한 (복잡도 방지) |
| **Like/Dislike 분리** | `review_like`, `comment_like` 테이블 (확장성 고려) |
| **평점 `Numeric(2,1)`** | 0.0 ~ 9.9 범위, 소수점 1자리 정밀도 |
| **UUIDv7 for 이미지** | 시간 순서 보장 + 충돌 방지 (UUIDv4 대비) |
| **UniqueConstraint (uid, mid)** | 한 사용자가 같은 영화를 중복 즐겨찾기 방지 |

### 7.3 인덱스 전략
- `uid`, `email`, `nickname` (User) - 조회 최적화
- `mid` (Movie) - PK + 조회
- `rid`, `cid` (Review, Comment) - PK + 조회
- 복합 인덱스 미사용 (현재 데이터 규모 고려)

---

## 8. 주요 구현 포인트

### 8.1 N+1 문제 방지

```python
# ❌ N+1 발생 (각 영화마다 장르 쿼리)
movies = db.query(Movie).all()
for m in movies:
    genres = m.genres  # 추가 쿼리

# ✅ Eager Loading
movies = (
    db.query(Movie)
    .options(joinedload(Movie.genres).joinedload(MovieGenre.genre))
    .all()
)
```

### 8.2 서브쿼리를 활용한 집계

```python
# 리뷰 수를 서브쿼리로 계산 (N+1 방지)
review_count_sq = (
    db.query(Review.mid, func.count(Review.rid).label("review_count"))
    .group_by(Review.mid)
    .subquery()
)

movies = (
    db.query(Movie, review_count_sq.c.review_count)
    .outerjoin(review_count_sq, Movie.mid == review_count_sq.c.mid)
    .all()
)
```

### 8.3 파일 업로드 파이프라인

```
1. 파일 수신 (FastAPI UploadFile)
   ↓
2. 확장자 검증 (.jpg, .png, .avif 등 9종)
   ↓
3. 크기 검증 (최대 1MiB)
   ↓
4. AVIF 변환 (Pillow + pillow-avif-plugin)
   ↓
5. UUIDv7 생성 (시간 순서 + 충돌 방지)
   ↓
6. S3 업로드 (boto3, public-read)
   ↓
7. DB 업데이트 (img 컬럼에 UUID만 저장)
   ↓
8. 이전 이미지 삭제 (S3 + DB)
```

**S3 호환성**:
- AWS S3: Virtual-hosted style (기본)
- MinIO: Path-style (`S3_USE_PATH_STYLE=True`)
- Cloudflare R2: Custom endpoint + public URL

### 8.4 TMDB 데이터 가져오기

```python
# CLI: uv run mono-log movie import-tmdb "https://www.themoviedb.org/movie/27205"
# API: POST /api/admin/movies/import

1. URL 파싱 → content_type (movie/tv), content_id
2. TMDB API 호출 (한국어 메타데이터)
   - /movie/{id} 또는 /tv/{id}
   - /movie/{id}/credits 또는 /tv/{id}/credits
3. 감독 추출 (영화: job="Director", TV: created_by[0])
4. 장르 매핑 (TMDB 장르 → 내부 Genre 테이블)
5. Movie + MovieGenre 레코드 생성
```

### 8.5 관리자 권한 체크

```python
def require_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(403, "Admin access required")
    return current_user

# 사용 예
@router.get("/admin/dashboard")
def get_dashboard(..., admin: User = Depends(require_admin)):
    ...
```

---

## 9. API 구조

### 9.1 엔드포인트 요약

| Prefix | 라우터 | 주요 엔드포인트 | 인증 |
|--------|--------|-----------------|------|
| `/api/auth` | auth | `POST /register`, `POST /login`, `POST /refresh`, `GET /me`, `POST /verify-email/*` | 선택적 |
| `/api/movies` | movies | `GET /search`, `GET /detail/{id}`, `GET /trend`, `GET /recommended` | ❌ |
| `/api/reviews` | reviews | `GET /by-movie/{id}`, `POST /create`, `POST /like`, `POST /comment/create` | ✅ |
| `/api/favorites` | favorites | `POST /toggle`, `GET /list`, `POST /status` | ✅ |
| `/api/ranking` | ranking | `GET /movies` | ❌ |
| `/api/user` | user | `GET /profile/{id}` | ❌ |
| `/api/file` | file | `POST /profile-image`, `DELETE /profile-image` | ✅ |
| `/api/admin` | admin | `GET /dashboard`, `GET /users`, `GET /movies`, `POST /movies/import` | ✅ + Admin |

### 9.2 응답 형식

**성공 응답**:
```json
{
  "message": "Review created successfully"
}
```

**에러 응답**:
```json
{
  "code": "CSRF_INVALID",
  "message": "CSRF token validation failed",
  "details": {
    "has_cookie": false,
    "has_header": true
  }
}
```

**페이지네이션**:
```json
{
  "movies": [...],
  "totalPages": 5
}
```

### 9.3 Swagger 문서
- **URL**: `http://localhost:8000/docs` (Swagger UI)
- **URL**: `http://localhost:8000/redoc` (ReDoc)
- FastAPI 자동 생성, 타입 기반 문서화

---

## 10. 배포 및 운영

### 10.1 환경 변수

| 카테고리 | 필수 변수 | 설명 |
|----------|-----------|------|
| **Database** | `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_NAME` | PostgreSQL 연결 |
| **JWT** | `SECRET_KEY` | 최소 32바이트 랜덤 문자열 |
| **Valkey** | `VALKEY_HOST`, `VALKEY_PORT` | Redis 호환 캐시 |
| **TMDB** | `TMDB_API_KEY` | 영화 데이터 가져오기 |
| **SMTP** | `SMTP_HOST`, `SMTP_FROM` | 이메일 인증 (선택) |
| **S3** | `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME` | 프로필 이미지 (선택) |

### 10.2 Docker Compose

```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    depends_on: [postgres, valkey]
  postgres:
    image: postgres:16
  valkey:
    image: valkey/valkey:8
```

### 10.3 CLI 명령어

```bash
# 개발 서버 (hot-reload)
uv run mono-log dev

# 운영 서버
uv run mono-log server --host 0.0.0.0 --port 8000

# DB 초기화 + 샘플 데이터
uv run mono-log db init --seed --yes

# TMDB에서 영화 가져오기
uv run mono-log movie import-tmdb "https://www.themoviedb.org/movie/27205"

# 관리자 승격
uv run mono-log user promote admin@example.com
```

### 10.4 운영 고려사항

| 항목 | 권장 설정 |
|------|-----------|
| `COOKIE_SECURE` | `True` (HTTPS 필수) |
| `REFRESH_TOKEN_COOKIE_SECURE` | `True` |
| `SECRET_KEY` | `openssl rand -hex 32` |
| Rate Limit | 트래픽에 맞게 조정 (기본 120/60s) |
| Valkey TTL | 메모리 사용량 모니터링 |
| S3 버킷 정책 | Public Read (이미지 다운로드용) |

---

## 11. 트러블슈팅 및 개선 포인트

### 11.1 현재 구현의 강점

| 강점 | 설명 |
|------|------|
| **보안 다층화** | CSRF + Rate Limit + JWT + Blacklist |
| **확장 가능한 스토리지** | S3 호환으로 벤더 독립성 확보 |
| **유연한 인증** | 이메일 인증 ON/OFF 설정 가능 |
| **관리 도구** | Typer CLI로 운영 작업 자동화 |
| **타입 안전성** | SQLAlchemy 2.0 + Pydantic + Ty |

### 11.2 개선 여지

| 영역 | 현재 | 개선 방향 |
|------|------|-----------|
| **비밀번호 재설정** | 미구현 | Forgot Password 플로우 |
| **소셜 로그인** | 미구현 | OAuth2 (Google, Kakao) |
| **알림** | 미구현 | 댓글/좋아요 알림 |
| **검색 최적화** | ILIKE | Full-text Search (PostgreSQL) |
| **이미지 리사이징** | 클라이언트 원본 | 서버 측 썸네일 생성 |
| **테스트** | 미구현 | pytest + TestContainers |

---

## 12. Q&A

### 자주 묻는 질문

**Q: 왜 Refresh Token을 Valkey에 저장하나요?**
A: 단일 로그아웃 및 강제 로그아웃(관리자 기능)을 지원하기 위함. JWT만으로는 서버 측 무효화가 불가능.

**Q: CSRF 토큰을 HttpOnly로 설정하지 않은 이유는?**
A: Double Submit Cookie 패턴에서 JavaScript가 쿠키를 읽어서 `X-CSRF-Token` 헤더에 넣어야 하기 때문.

**Q: 왜 AVIF 포맷을 사용하나요?**
A: WebP보다 압축률이 높고, 최신 브라우저에서 지원. 프로필 이미지 크기 최적화.

**Q: TMDB API를 실시간으로 호출하지 않는 이유는?**
A: 레이트 리밋, 비용, 데이터 일관성. 필요 시 수동으로 가져오는 방식 채택.

---

## 부록: 주요 파일 위치

```
app/
├── main.py                    # FastAPI 앱, 미들웨어, 라우터 등록
├── config.py                  # Pydantic Settings (환경 변수)
├── database.py                # SQLAlchemy 엔진/세션
├── models.py                  # ORM 모델 정의
├── schemas.py                 # Pydantic 요청/응답 스키마
├── security.py                # CSRF, 쿠키 헬퍼
├── utils.py                   # JWT, 비밀번호, S3 URL 유틸
├── middleware.py              # CSRF, Rate Limit, Security Headers
├── dependencies.py            # get_current_user 의존성
├── routers/                   # API 엔드포인트
│   ├── auth.py
│   ├── movies.py
│   ├── reviews.py
│   ├── admin.py
│   └── ...
└── services/                  # 비즈니스 로직
    ├── token_service.py       # Refresh Token, Blacklist
    ├── email_verification_service.py
    ├── rate_limit_service.py
    └── system_settings_service.py
```

---

*최종 수정: 2026-07-12*
