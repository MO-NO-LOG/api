# Copilot instructions (MO-NO-LOG / asdasdsad)

## Big picture

- This is a **single FastAPI app** that serves both:
  - a JSON API under `/api/*` (see `app/routers/`)
  - the static frontend from `web/` mounted at `/` (see `app/main.py`)
- Browser JS calls the backend via same-origin fetch to `API_BASE_URL = "/api"` (see `web/js/api.js`).

## Key directories

- `app/main.py`: FastAPI app entrypoint, router registration, static mount.
- `app/routers/`: API surface:
  - `auth.py` → `/api/auth/*`
  - `movies.py` → `/api/movies/*`
  - `reviews.py` → `/api/reviews/*`
- `app/models.py`: SQLAlchemy ORM models (PostgreSQL-oriented).
- `app/schemas.py`: Pydantic request/response shapes consumed by frontend.
- `app/database.py`: SQLAlchemy engine/session + DB connection constants.
- `scripts/init_db.py`: creates DB, drops/creates tables, seeds sample data (destructive).
- `web/`: static HTML/CSS/JS pages; loaded directly from FastAPI StaticFiles.

## API conventions (important for changes)

- Frontend expects **camelCase JSON fields** for movies/reviews (e.g. `posterUrl`, `averageRating`, `createdAt`).
  - Backend manually maps ORM → schema in routers (e.g. `app/routers/movies.py`).
  - Keep response shapes stable; update both `app/schemas.py` and the router mapping if you change a field.
- Several “read” operations are implemented as **POST + JSON body** (match frontend usage):
  - `/api/movies/search` (also uses `page`/`size` query params)
  - `/api/movies/detail`
  - `/api/reviews/by-movie`
- Auth is **JWT Bearer token in Authorization header**:
  - `POST /api/auth/login` returns `access_token` and `refresh_token` in JSON response (see `app/routers/auth.py`).
  - Frontend MUST store tokens (localStorage/sessionStorage/memory) and send `Authorization: Bearer <token>` header.
  - `get_current_user` requires `Authorization` header with Bearer token (see `app/dependencies.py`).
  - `POST /api/auth/refresh` requires refresh token in `Authorization` header to get new access token.
  - Cookie-based auth has been removed for security reasons. See `docs/AUTH_TOKEN_MIGRATION.md`.

## Database workflow

- Default DB is PostgreSQL via SQLAlchemy (see `app/database.py`). Connection info is currently hardcoded.
- Reset/seed workflow (WARNING: drops all tables):
  - `uv run python scripts/init_db.py`
- If you change `app/models.py`, assume you must re-run `scripts/init_db.py` (no migrations present).

## Local dev commands (uv)

- Install deps / create venv:
  - `uv sync`
- Run the server (serves `web/` at `/` and API at `/api/*`):
  - `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Open: `http://localhost:8000/` (do not open `web/*.html` via `file://` if you need API calls).

## Patterns to follow when implementing features

- New endpoints: add a router in `app/routers/` and include it from `app/main.py`.
- DB access: use `db: Session = Depends(get_db)` from `app/database.py`.
- Auth-required endpoints: add `current_user: User = Depends(get_current_user)`.
- Prefer updating Pydantic schemas in `app/schemas.py` first, then align router responses and `web/js/*.js` usage.

## Gotchas

- Secrets/credentials are currently checked into code (`app/database.py`, `app/utils.py`). Do not duplicate them in docs/logs; prefer reading from env vars if you are asked to refactor config.
- `scripts/init_db.py` resets the DB completely; never run it against a shared/prod database.
