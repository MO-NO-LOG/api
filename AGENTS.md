# Developer Guide & Agent Instructions

This document serves as the primary reference for agents and developers working on the `MO-NO-LOG` repository. It consolidates build commands, code style guidelines, and architectural patterns.

## 1. Project Overview & Context

This is a single FastAPI application that serves:

- **JSON API**: Under `/api/*` (defined in `app/routers/`).
- **Frontend**: Static HTML/JS/CSS from `web/` mounted at the root `/`.

### Key Directories

- `app/main.py`: Entrypoint. Mounts static files and includes routers.
- `app/routers/`: API endpoints (`auth.py`, `movies.py`, `reviews.py`).
- `app/models.py`: SQLAlchemy ORM models (PostgreSQL).
- `app/schemas.py`: Pydantic models for request/response validation.
- `app/database.py`: DB connection and session handling.
- `web/`: Static frontend assets.
- `scripts/`: Utility scripts (e.g., DB initialization).

## 2. Environment & Commands

The project uses `uv` for dependency management and task execution.

### Setup & Installation

Ensure `uv` is installed.

```bash
# Sync dependencies and create virtual environment
uv sync
```

### Running the Application

Start the development server with hot-reload:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Open `http://localhost:8000/` for the web interface.
- Open `http://localhost:8000/docs` for the Swagger UI.

### Database Management

**WARNING**: The initialization script drops and recreates all tables.

```bash
# Reset database and seed sample data
uv run python scripts/init_db.py
```

_Note: Connection info is currently hardcoded in `app/database.py`._

### Testing & Linting

_Currently, no test suite or linter configuration is present in the repository._

**Recommended Future Setup:**

- **Test**: `uv add --dev pytest` then run `uv run pytest`
- **Lint**: `uv add --dev ruff` then run `uv run ruff check .`

If adding tests, place them in a `tests/` directory and mirror the `app/` structure.

## 3. Code Style & Conventions

### Formatting & Syntax

- **Indentation**: 4 spaces.
- **Quotes**: Double quotes `"` preferred for strings.
- **Line Length**: Soft limit 88/100 characters (Standard Python).
- **Imports**: Group imports:
  1. Standard Library (`typing`, `os`, `random`)
  2. Third-party (`fastapi`, `sqlalchemy`)
  3. Local Application (`app.models`, `app.schemas`)

### Naming Conventions

- **Python (Backend)**:
  - Variables/Functions: `snake_case` (e.g., `get_current_user`, `search_movies`)
  - Classes/Models: `PascalCase` (e.g., `MovieResponseItem`, `User`)
  - Constants: `UPPER_CASE` (e.g., `API_BASE_URL`)
- **JSON (API Contract)**:
  - Fields: `camelCase` (e.g., `posterUrl`, `createdAt`).
  - **CRITICAL**: The backend manually maps SQLAlchemy models (snake_case) to Pydantic schemas (camelCase) in routers.

### Architectural Patterns

#### 1. API Structure

- **Routers**: Each domain has its own router in `app/routers/`.
- **Dependencies**: Use FastAPI dependency injection for DB sessions and Auth.

  ```python
  def get_data(db: Session = Depends(get_db)):
      ...
  ```

#### 2. Authentication

- **Method**: JWT stored in an **HttpOnly cookie**.
- **Flow**:
  1. `POST /api/auth/login` sets the cookie.
  2. `get_current_user` dependency checks the cookie.
  3. Frontend typically does _not_ send an `Authorization` header.

#### 3. Database Access

- Use SQLAlchemy sessions injected via `get_db`.
- Avoid logic in `app/models.py`; keep models pure.
- **Schema Validation**: Define Pydantic models in `app/schemas.py` for all inputs and outputs.

#### 4. Frontend Integration

- Frontend files in `web/` make fetch calls to `/api/...`.
- `web/js/api.js` defines the `API_BASE_URL`.
- Certain read operations use **POST** to support complex JSON bodies (e.g., `/api/movies/search`).

## 4. Development Rules & Gotchas

### Creating New Endpoints

1. Define the Pydantic schema in `app/schemas.py`.
2. Create the route in the appropriate `app/routers/` file.
3. If it's a new router file, include it in `app/main.py`.

### Error Handling

- Use `fastapi.HTTPException`.
- Provide clear status codes (404 for not found, 401 for auth, 400 for bad input).

```python
if not item:
    raise HTTPException(status_code=404, detail="Item not found")
```

### Security

- **Secrets**: Currently, some credentials might be hardcoded. _Do not expose them further._
- **Auth**: Always use the `get_current_user` dependency for protected routes.

### Common Pitfalls

- **Frontend Fields**: If you change a field name in the backend model, you _must_ update the Pydantic schema alias or the manual mapping in the router to maintain `camelCase` for the frontend.
- **Migrations**: There is no Alembic setup. Changes to `app/models.py` require running `scripts/init_db.py`, which wipes data.

## 5. Reference: Copilot Instructions

_Derived from `.github/copilot-instructions.md`_

- **Read Operations as POST**: Matches frontend usage for:
  - `/api/movies/search`
  - `/api/movies/detail`
  - `/api/reviews/by-movie`
- **Dependency Flow**:
  - `app/main.py` -> `app/routers/*.py` -> `app/schemas.py` & `app/models.py`

---

_This file is auto-generated and maintained to assist coding agents. Always check current file contents for the most up-to-date context._
