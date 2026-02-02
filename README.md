# MO-NO-LOG - 영화 리뷰 플랫폼

FastAPI 기반의 영화 리뷰 플랫폼입니다.

## 설치 및 실행

### 1. 의존성 설치

```bash
uv sync
```

### 2. 데이터베이스 초기화

**테이블만 생성 (데이터 없음):**

```bash
uv run python scripts/init_db.py
```

**테이블 생성 + 예시 데이터 추가:**

```bash
uv run python scripts/init_db.py --seed
```

**예시 데이터만 추가 (테이블이 이미 존재하는 경우):**

```bash
uv run python scripts/seed_data.py
```

### 3. 서버 실행

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## CLI (Typer)

프로젝트에는 관리용 CLI가 포함되어 있습니다.

```bash
# 도움말
uv run mono-log --help

# 서버 실행
uv run mono-log serve --reload

# DB 초기화 (테이블 삭제 후 재생성)
uv run mono-log db init

# DB 초기화 + 시드
uv run mono-log db init --seed

# 샘플 데이터만 추가
uv run mono-log db seed

# 사용자 생성 (프롬프트)
uv run mono-log user create

# 관리자 승격
uv run mono-log user promote admin@mono-log.com
```

## 예시 데이터

`seed_data.py` 스크립트는 다음 예시 데이터를 추가합니다:

- **사용자 5명** (관리자 1명 포함)
- **장르 15개** (액션, 드라마, SF, 등)
- **영화 10편** (인셉션, 기생충, 인터스텔라, 등)
- **리뷰 12개**
- **댓글 10개**
- **좋아요 데이터**

### 샘플 로그인 정보

- **관리자**: `admin@mono-log.com` / `admin1234`
- **일반 사용자**: `kim@example.com` / `password123`

## API 문서

서버 실행 후 다음 주소에서 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 보안 기능

### CSRF 보호

이 API는 **Double Submit Cookie** 패턴과 HMAC 서명을 사용하여 CSRF 공격을 방지합니다.

#### 주요 특징
- 🔒 HMAC-SHA256 서명으로 토큰 무결성 보장
- 🔄 로그인/로그아웃/토큰 갱신 시 자동 토큰 로테이션
- 🛡️ 인증된 사용자의 상태 변경 요청에 대해 자동 검증
- 📝 안전한 메서드(GET, HEAD, OPTIONS)는 검증 제외

#### 인터랙티브 데모

서버 실행 후 브라우저에서 데모 페이지를 열어보세요:

```bash
# 서버 실행
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 브라우저에서 열기 (파일 경로)
# Windows: file:///D:/your-path/fastapi-api/docs/csrf-demo.html
# Mac/Linux: file:///path/to/fastapi-api/docs/csrf-demo.html
```

또는 Python으로 간단한 서버 실행:
```bash
cd docs
python -m http.server 8080
# 브라우저에서 http://localhost:8080/csrf-demo.html 접속
```

#### 클라이언트 구현

**JavaScript/Fetch 예시:**
```javascript
// 1. 쿠키에서 CSRF 토큰 가져오기
function getCsrfToken() {
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : null;
}

// 2. 요청 시 토큰 포함
const response = await fetch('/api/movies', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': getCsrfToken()  // 헤더에 토큰 추가
  },
  credentials: 'include',  // 쿠키 포함
  body: JSON.stringify({ title: 'Inception', year: 2010 })
});
```

**또는 API 엔드포인트에서 가져오기:**
```javascript
const response = await fetch('/api/auth/csrf', { credentials: 'include' });
const { csrfToken } = await response.json();
```

#### CSRF 검증 제외 엔드포인트
다음 엔드포인트는 CSRF 토큰 없이 호출 가능:
- `POST /api/auth/login` - 초기 로그인
- `POST /api/auth/register` - 회원가입
- `POST /api/auth/verify-email/*` - 이메일 인증
- `GET /api/auth/csrf` - CSRF 토큰 발급

#### 빠른 테스트

**cURL로 테스트:**
```bash
# 1. CSRF 토큰 가져오기
curl -c cookies.txt http://localhost:8000/api/auth/csrf

# 2. 쿠키에서 토큰 추출
CSRF_TOKEN=$(grep csrf_token cookies.txt | awk '{print $7}')

# 3. 로그인
curl -b cookies.txt -c cookies.txt \
  -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@mono-log.com","password":"admin1234"}'

# 4. CSRF 토큰과 함께 요청
curl -b cookies.txt \
  -X POST http://localhost:8000/api/movies/search \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{"query":"inception"}'
```

자세한 내용은 [CSRF Protection Guide](docs/CSRF_PROTECTION.md)를 참조하세요.

### 기타 보안 기능
- ✅ JWT 기반 인증 (HttpOnly 쿠키)
- ✅ 비밀번호 해싱 (bcrypt)
- ✅ Rate Limiting (Redis 기반)
- ✅ 토큰 블랙리스트 (로그아웃 시)
- ✅ 이메일 인증
- ✅ 보안 헤더 자동 추가 (CSP, X-Frame-Options, 등)

## S3 파일 스토리지

프로필 이미지는 S3 호환 스토리지에 저장됩니다.

### 지원 스토리지
- ✅ AWS S3
- ✅ MinIO (Self-hosted)
- ✅ Cloudflare R2
- ✅ DigitalOcean Spaces
- ✅ Backblaze B2
- ✅ 기타 S3 호환 API

### 주요 특징
- 📤 **업로드**: JWT 인증 필요
- 📥 **다운로드**: 인증 불필요 (공개 URL)
- 🔄 **자동 중복 제거**: BLAKE3 해시 기반
- 🖼️ **자동 변환**: 모든 이미지를 AVIF 포맷으로 변환
- ⚡ **캐싱**: 1년 Cache-Control 헤더 자동 설정

### 빠른 시작

`.env` 파일에 S3 설정 추가:

```env
# AWS S3 예시
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=profile-images
S3_REGION=us-east-1
S3_PUBLIC_URL=
S3_USE_PATH_STYLE=false

# MinIO 예시 (로컬 개발)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=profile-images
S3_REGION=us-east-1
S3_USE_PATH_STYLE=true
```

### 연결 테스트

```bash
uv run python scripts/test_s3_connection.py
```

### API 사용 예시

**프로필 이미지 업로드:**
```bash
curl -X POST "http://localhost:8000/api/file/profile-image" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/image.jpg"
```

**프로필 이미지 삭제:**
```bash
curl -X DELETE "http://localhost:8000/api/file/profile-image" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

자세한 설정 가이드는 [S3 Storage Setup Guide](docs/S3_STORAGE_SETUP.md)를 참조하세요.

## 프로젝트 구조

```
app/
├── routers/         # API 라우터
│   ├── auth.py      # 인증 관련
│   ├── movies.py    # 영화 관련
│   ├── reviews.py   # 리뷰 관련
│   ├── user.py      # 사용자 관련
│   ├── admin.py     # 관리자 관련
│   └── file.py      # 파일 업로드 (S3)
├── models.py        # SQLAlchemy ORM 모델
├── schemas.py       # Pydantic 스키마
├── database.py      # DB 연결 설정
├── dependencies.py  # FastAPI 의존성
├── config.py        # 설정 관리
└── utils.py         # 유틸리티 함수

scripts/
├── init_db.py            # DB 초기화 스크립트
├── seed_data.py          # 예시 데이터 추가 스크립트
└── test_s3_connection.py # S3 연결 테스트

web/                 # 프론트엔드 정적 파일
```

## 환경 변수 설정

주요 환경 변수는 `.env` 파일에 설정합니다:

```env
# Database
DB_USER=postgres
DB_PASS=your-password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=monolog

# Security
SECRET_KEY=your-super-secret-key-change-in-production
COOKIE_SECURE=false  # 프로덕션에서는 true (HTTPS 필수)
COOKIE_SAMESITE=lax

# CSRF
CSRF_COOKIE_NAME=csrf_token
CSRF_HEADER_NAME=X-CSRF-Token
CSRF_TOKEN_BYTES=32

# Redis (Rate limiting, Token blacklist)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# SMTP (Email verification)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# S3 Storage (Profile images)
S3_ENDPOINT_URL=          # AWS S3는 비워두기, MinIO/R2는 URL 입력
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=profile-images
S3_REGION=us-east-1
S3_PUBLIC_URL=            # 선택사항: CDN URL
S3_USE_PATH_STYLE=false   # MinIO는 true, AWS S3는 false
```

## 주의사항

⚠️ **보안 경고**
- `init_db.py` 스크립트는 기존 테이블을 모두 삭제하고 재생성합니다. 운영 환경에서는 사용하지 마세요!
- 프로덕션 환경에서는 반드시 `SECRET_KEY`를 변경하고, `COOKIE_SECURE=true`로 설정하세요.
- HTTPS를 사용하지 않으면 쿠키가 탈취될 수 있습니다.

## 문서

- [S3 Storage Setup Guide](docs/S3_STORAGE_SETUP.md) - S3 스토리지 설정 가이드 (AWS S3, MinIO, R2 등)
- [CSRF Protection Guide](docs/CSRF_PROTECTION.md) - CSRF 보호 상세 가이드
- [CSRF Demo](docs/csrf-demo.html) - 인터랙티브 CSRF 데모 (브라우저에서 열기)
- [API Documentation](http://localhost:8000/docs) - Swagger UI
- [ReDoc](http://localhost:8000/redoc) - Alternative API docs
- [Changelog](CHANGELOG.md) - 프로젝트 변경 이력
