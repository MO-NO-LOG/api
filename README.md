# MO-NO-LOG API

MO-NO-LOG API는 FastAPI 기반 영화 커뮤니티 백엔드입니다. 회원 인증, 영화 조회, 리뷰/댓글, 즐겨찾기, 랭킹, 관리자 기능, 프로필 이미지 업로드를 제공합니다.

## 핵심 기능

- JWT + HttpOnly 쿠키 기반 인증
- 이메일 인증, 토큰 갱신, 로그아웃 블랙리스트 처리
- 영화 검색, 상세 조회, 추천/트렌드, 랭킹 조회
- 리뷰 작성, 좋아요/싫어요, 댓글/대댓글
- 즐겨찾기 토글 및 목록 조회
- 관리자 대시보드, 사용자/영화/리뷰 관리, TMDB 가져오기
- S3 호환 스토리지 프로필 이미지 업로드
- CSRF 보호, 보안 헤더, Valkey 기반 레이트 리밋

## 기술 스택

- Python 3.14
- FastAPI
- SQLAlchemy
- PostgreSQL
- Valkey
- Typer CLI
- boto3 / S3 compatible storage

## 빠른 시작

### 1. 의존성 설치

```bash
uv sync
```

### 2. 환경 변수 준비

프로젝트 루트의 `.env`에 최소한 아래 항목을 설정하세요.

```env
DB_USER=postgres
DB_PASS=change-me
DB_HOST=localhost
DB_PORT=5432
DB_NAME=monolog
DB_DATA=/path/to/postgres/data

SECRET_KEY=change-this-in-production

VALKEY_HOST=localhost
VALKEY_PORT=6379
VALKEY_DB=0
VALKEY_PASSWORD=
```

선택 기능을 사용하려면 아래 값도 추가합니다.

- `TMDB_API_KEY`: TMDB 영화/TV 정보 가져오기
- `SMTP_*`: 이메일 인증 메일 발송
- `S3_*`: 프로필 이미지 저장

### 3. 데이터베이스 초기화

주의: 초기화 명령은 테이블을 삭제 후 재생성합니다.

```bash
uv run mono-log db init --seed --yes
```

샘플 데이터만 다시 넣고 싶다면:

```bash
uv run mono-log db seed
```

### 4. 개발 서버 실행

```bash
uv run mono-log dev
```

실행 후 확인할 주소:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker Compose

컨테이너로 API, PostgreSQL, Valkey를 함께 실행할 수 있습니다.

```bash
docker compose up --build
```

기본 매핑 포트는 `8000:80`입니다.

## CLI 사용법

이 프로젝트는 `mono-log` 관리 CLI를 제공합니다.

```bash
# 도움말
uv run mono-log --help

# 개발 서버
uv run mono-log dev

# 운영용 서버
uv run mono-log server --host 0.0.0.0 --port 8000

# DB 초기화 + 샘플 데이터
uv run mono-log db init --seed --yes

# 샘플 데이터만 추가
uv run mono-log db seed

# 사용자 생성
uv run mono-log user create

# 관리자 승격
uv run mono-log user promote user@example.com

# TMDB URL로 영화/TV 가져오기
uv run mono-log movie import-tmdb "https://www.themoviedb.org/movie/27205"
```

## 샘플 데이터

`uv run mono-log db init --seed --yes` 또는 `uv run mono-log db seed` 실행 시 예시 데이터가 들어갑니다.

- 사용자 5명
- 장르 15개
- 영화 10편
- 리뷰, 댓글, 좋아요 데이터

샘플 계정:

- 관리자: `admin@mono-log.com` / `admin1234`
- 일반 사용자: `kim@example.com` / `password123`

## 주요 API 그룹

- `auth`: 회원가입, 로그인, 로그아웃, 내 정보, 이메일 인증, CSRF 토큰
- `movies`: 검색, 상세, 추천, 트렌드
- `reviews`: 리뷰 작성, 반응, 댓글/대댓글
- `favorites`: 즐겨찾기 토글, 상태, 목록
- `ranking`: 영화 랭킹
- `user`: 프로필 조회, 프로필 이미지 조회
- `file`: 프로필 이미지 업로드/삭제
- `admin`: 대시보드와 관리자 CRUD

## 보안 메모

- 인증은 `Authorization` 헤더보다 쿠키 기반 흐름을 우선 사용합니다.
- 상태 변경 요청은 CSRF 보호를 거칩니다.
- 로그인/인증 관련 기능은 Valkey를 사용해 토큰 블랙리스트 및 요청 제한을 처리합니다.
- 운영 환경에서는 반드시 `SECRET_KEY`를 교체하고 secure cookie 설정을 활성화하세요.

## 프로젝트 구조

```text
app/
  main.py            # FastAPI 앱과 미들웨어 등록
  config.py          # 환경 변수 설정
  database.py        # DB 엔진과 세션
  models.py          # SQLAlchemy 모델
  schemas.py         # Pydantic 스키마
  middleware.py      # CSRF, rate limit, security headers
  routers/           # API 라우터
  services/          # 토큰, 이메일, 레이트 리밋 서비스

scripts/
  init_db.py         # DB 초기화
  seed_data.py       # 샘플 데이터 입력
  make_user.py       # 사용자 생성
  make_admin.py      # 관리자 승격

main.py              # Typer CLI 엔트리포인트
compose.yml          # Docker Compose 설정
Dockerfile           # 컨테이너 빌드 설정
```

## 개발 시 참고

- 포맷팅: `uv run mono-log format`
- 타입 체크: `uv run mono-log type`
- 현재 저장소에는 별도 테스트 스위트가 포함되어 있지 않습니다.

## 주의사항

- `uv run mono-log db init`은 기존 테이블을 모두 제거합니다.
- README 예시의 환경 변수 값은 자리표시자입니다. 실제 비밀 값은 별도로 관리하세요.
- S3, SMTP, TMDB 기능은 관련 환경 변수가 없으면 동작하지 않습니다.
