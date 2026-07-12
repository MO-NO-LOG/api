# MO-NO-LOG API

영화 커뮤니티 **MONO-LOG**의 백엔드 API입니다. Fastapi 기반으로 JWT 인증, 영화 정보, 리뷰/댓글, 즐겨찾기, 랭킹, 관리자 기능을 제공합니다.

## 기술 스택

| 계층 | 기술 |
|------|------|
| 런타임 | Python 3.14 |
| 웹 프레임워크 | FastAPI |
| ORM | SQLAlchemy 2.0 |
| 데이터베이스 | PostgreSQL |
| 캐시 / 세션 | Valkey (redis-compatible) |
| 인증 | JWT (python-jose) + HttpOnly 쿠키 |
| 객체 스토리지 | S3 호환 (AWS S3, MinIO, Cloudflare R2) |
| ASGI 서버 | Uvicorn (개발) / Hypercorn (운영) |
| CLI | Typer |
| 패키지 관리 | uv |
| 포매팅/타입 | Ruff / Ty |

## 핵심 기능

- **인증** — 회원가입, 로그인/로그아웃, JWT 액세스/리프레시 토큰 (HttpOnly 쿠키), CSRF 보호 (Double Submit Cookie)
- **이메일 인증** — SMTP 기반 인증 메일 발송, 인증 상태 확인 (선택 사항)
- **영화** — TMDB 연동 영화/TV 가져오기, 검색, 상세 조회, 추천, 트렌드
- **리뷰 & 댓글** — 리뷰 CRUD, 좋아요/싫어요, 댓글/대댓글
- **즐겨찾기** — 영화 즐겨찾기 토글 및 목록 조회
- **랭킹** — 영화 랭킹 조회
- **프로필** — 프로필 조회, S3 호환 스토리지 프로필 이미지 업로드/삭제
- **관리자** — 대시보드, 사용자/영화/리뷰 관리, TMDB 데이터 수동 가져오기
- **보안** — CSRF 토큰 검증, 레이트 리밋 (Valkey 기반), 보안 응답 헤더, 로그아웃 토큰 블랙리스트

## 시작하기

### 사전 요구 사항

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL
- Valkey

### 1. 의존성 설치

```bash
uv sync
```

### 2. 환경 변수 설정

`.env` 파일을 프로젝트 루트에 생성합니다. 자세한 예시는 `.env.example`을 참고하세요.

```env
# Database
DB_USER=postgres
DB_PASS=changeme
DB_HOST=localhost
DB_PORT=5432
DB_NAME=monolog
DB_DATA=./pgdata

# JWT (openssl rand -hex 32)
SECRET_KEY=change-me-to-a-random-secret

# Valkey
VALKEY_HOST=localhost
VALKEY_PORT=6379
VALKEY_DB=0
```

선택 기능별 환경 변수:

| 기능 | 필수 변수 |
|------|-----------|
| TMDB 영화 가져오기 | `TMDB_API_KEY` |
| 이메일 인증 | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` |
| 프로필 이미지 (S3) | `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME` |

### 3. 데이터베이스 초기화

```bash
# 테이블 생성 + 샘플 데이터
uv run mono-log db init --seed --yes

# 샘플 데이터만 추가
uv run mono-log db seed
```

> `db init`은 기존 테이블을 모두 삭제 후 재생성합니다.

### 4. 개발 서버 실행

```bash
uv run mono-log dev
```

| 주소 | 설명 |
|------|------|
| http://localhost:8000 | API 엔드포인트 |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |

### Docker Compose

```bash
docker compose up --build
```

PostgreSQL, Valkey와 함께 API 컨테이너가 실행되며 `localhost:8000`으로 접근 가능합니다.

## CLI 명령어

`mono-log` Typer CLI로 다양한 관리 작업을 수행할 수 있습니다.

```bash
# 도움말
uv run mono-log --help

# 개발 서버 (hot-reload)
uv run mono-log dev

# 운영 서버 (Hypercorn)
uv run mono-log server --host 0.0.0.0 --port 8000

# 코드 포매팅
uv run mono-log format

# 타입 체크
uv run mono-log type

# 데이터베이스 초기화
uv run mono-log db init --seed --yes

# 샘플 데이터 추가
uv run mono-log db seed

# 사용자 생성
uv run mono-log user create

# 관리자 승격
uv run mono-log user promote user@example.com

# TMDB URL로 영화/TV 가져오기
uv run mono-log movie import-tmdb "https://www.themoviedb.org/movie/27205"
```

## API 개요

모든 API는 `/api` prefix 아래에 위치합니다.

| 그룹 | 라우터 | 주요 엔드포인트 |
|------|--------|----------------|
| Auth | `auth` | 회원가입, 로그인, 로그아웃, 토큰 갱신, 내 정보, 이메일 인증, CSRF 토큰 |
| Movies | `movies` | 검색, 상세, 추천, 트렌드 |
| Reviews | `reviews` | 리뷰 CRUD, 좋아요/싫어요, 댓글/대댓글 |
| Favorites | `favorites` | 즐겨찾기 토글, 상태 확인, 목록 |
| Ranking | `ranking` | 영화 랭킹 |
| User | `user` | 프로필 조회, 프로필 이미지 조회 |
| File | `file` | 프로필 이미지 업로드/삭제 |
| Admin | `admin` | 대시보드, 사용자/영화/리뷰 관리, TMDB 가져오기 |

## 샘플 데이터

`uv run mono-log db init --seed --yes` 또는 `uv run mono-log db seed` 실행 시 다음 데이터가 추가됩니다.

- 사용자 5명
- 장르 15개
- 영화 10편
- 리뷰, 댓글, 좋아요/싫어요 샘플

### 테스트 계정

| 역할 | 이메일 | 비밀번호 |
|------|--------|----------|
| 관리자 | admin@mono-log.com | admin1234 |
| 일반 사용자 | kim@example.com | password123 |

## 프로젝트 구조

```text
mono-log-api/
├── app/
│   ├── main.py              # FastAPI 앱 생성, 미들웨어, 라우터 등록
│   ├── config.py            # Pydantic Settings (환경 변수)
│   ├── database.py          # 데이터베이스 엔진 / 세션
│   ├── models.py            # SQLAlchemy ORM 모델
│   ├── schemas.py           # Pydantic 요청/응답 스키마
│   ├── security.py          # JWT 생성/검증, CSRF 토큰, 비밀번호 해싱
│   ├── utils.py             # 공통 유틸리티 함수
│   ├── valkey_client.py     # Valkey 클라이언트
│   ├── middleware.py        # CSRF, Rate Limit, Security Headers 미들웨어
│   ├── routers/
│   │   ├── auth.py          # 인증 관련 API
│   │   ├── movies.py        # 영화 조회/검색 API
│   │   ├── reviews.py       # 리뷰/댓글 API
│   │   ├── favorites.py     # 즐겨찾기 API
│   │   ├── ranking.py       # 랭킹 API
│   │   ├── user.py          # 프로필 API
│   │   ├── file.py          # 파일 업로드/삭제 API
│   │   └── admin.py         # 관리자 API
│   └── services/
│       ├── token_service.py             # JWT 토큰 발급/검증/블랙리스트
│       ├── email_verification_service.py # 이메일 인증 코드 관리
│       ├── rate_limit_service.py        # 레이트 리밋 로직
│       └── system_settings_service.py   # 시스템 설정 관리
├── scripts/
│   ├── init_db.py           # DB 초기화 (테이블 생성/삭제)
│   ├── seed_data.py         # 샘플 데이터 입력
│   ├── make_user.py         # 사용자 생성 스크립트
│   ├── make_admin.py        # 관리자 승격 스크립트
│   └── auto_register.py     # 자동 회원가입 스크립트
├── main.py                  # Typer CLI 엔트리포인트
├── compose.yml              # Docker Compose (API + PostgreSQL + Valkey)
├── Dockerfile               # 컨테이너 빌드 설정
├── .env.example             # 환경 변수 예시
└── pyproject.toml           # 프로젝트 메타데이터 / 의존성
```

## 보안

- **인증**: JWT 액세스 토큰은 HttpOnly 쿠키로 전송, 리프레시 토큰은 별도 HttpOnly 쿠키 사용
- **CSRF**: Double Submit Cookie 패턴 — 상태 변경 요청 시 쿠키의 서명된 토큰과 `X-CSRF-Token` 헤더 값을 비교 검증
- **Rate Limit**: Valkey 기반 분산 레이트 리밋 (IP + 경로 단위)
- **보안 헤더**: X-Content-Type-Options, X-Frame-Options, CSP, HSTS, Referrer-Policy, Permissions-Policy
- **비밀번호**: bcrypt 해싱 (passlib)
- **토큰 블랙리스트**: 로그아웃 시 리프레시 토큰을 Valkey에 블랙리스트 등록

운영 환경에서는 `COOKIE_SECURE=True`, `REFRESH_TOKEN_COOKIE_SECURE=True`로 설정하고 강력한 `SECRET_KEY`를 사용하세요.

## 라이선스

내부 프로젝트입니다.
