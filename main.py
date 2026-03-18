import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Optional, cast

import httpx
import typer

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="MONOLOG management CLI",
)


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


db_app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="Database management tasks"
)
user_app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="User management tasks"
)
movie_app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="Movie management tasks"
)


def _run_command(command: list[str]) -> None:
    typer.secho(f"Executing: {' '.join(command)}", fg=typer.colors.BLUE)
    result = subprocess.call(command)
    if result != 0:
        raise typer.Exit(code=result)


def _confirm_destructive(message: str, yes: bool) -> None:
    if yes:
        return
    if not typer.confirm(message, default=False):
        typer.secho("Operation cancelled.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)


@app.command("format")
def format() -> None:
    """Format the code using a code formatter."""
    command = [sys.executable, "-m", "ruff", "format"]

    _run_command(command)


@app.command("type")
def type() -> None:
    """Format the code using a code formatter."""
    command = [sys.executable, "-m", "ty", "check"]

    _run_command(command)


@app.command("dev")
def dev(
    host: str = typer.Option("127.0.0.1", help="바인딩할 호스트"),
    port: int = typer.Option(8000, help="바인딩할 포트"),
    workers: int = typer.Option(1, help="워커 수 (기본 1)"),
) -> None:
    """Run development server."""
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
        "--workers",
        str(workers),
        "--reload",
    ]

    _run_command(command)


@app.command("server")
def serve(
    host: str = typer.Option("0.0.0.0", help="바인딩할 호스트"),
    port: int = typer.Option(8000, help="바인딩할 포트"),
    workers: int = typer.Option(
        _get_int_env("WEB_CONCURRENCY", 1), help="워커 수 (기본 1)"
    ),
) -> None:
    """Run production server."""
    command = [
        sys.executable,
        "-m",
        "hypercorn",
        "app.main:app",
        "--bind",
        f"{host}:{port}",
        "--workers",
        str(workers),
    ]

    _run_command(command)


@db_app.command("init")
def db_init(
    seed: bool = typer.Option(False, help="초기화 후 샘플 데이터 시드"),
    yes: bool = typer.Option(False, "--yes", "-y", help="확인 프롬프트 생략"),
) -> None:
    """Initialize the DB (drops and recreates all tables)."""
    _confirm_destructive("Initialize the database? (This will delete all tables)", yes)

    from scripts.init_db import reset_db

    reset_db(with_seed=seed)
    typer.secho("DB initialization complete", fg=typer.colors.GREEN)


@db_app.command("seed")
def db_seed() -> None:
    """Add sample data to the DB."""
    from scripts.seed_data import seed_all

    seed_all()
    typer.secho("Sample data added successfully", fg=typer.colors.GREEN)


@user_app.command("create")
def user_create(
    nickname: Optional[str] = typer.Argument(None, help="닉네임"),
    email: Optional[str] = typer.Argument(None, help="이메일"),
    password: Optional[str] = typer.Option(None, help="비밀번호"),
    gender: Optional[str] = typer.Option(None, help="성별 (M/F)"),
) -> None:
    """Create a regular user."""
    nickname = nickname or typer.prompt("Nickname")
    email = email or typer.prompt("Email")
    password = password or typer.prompt(
        "Password", hide_input=True, confirmation_prompt=True
    )
    assert nickname is not None
    assert email is not None
    assert password is not None

    if gender is None:
        gender_input = typer.prompt(
            "Gender (M/F, optional)", default="", show_default=False
        )
        gender = gender_input.strip() or None

    if gender:
        gender = gender.upper()
        if gender not in ["M", "F"]:
            raise typer.BadParameter("Gender must be M or F.")

    from scripts.make_user import make_user

    make_user(
        cast(str, nickname),
        cast(str, email),
        cast(str, password),
        gender,
    )


@user_app.command("promote")
def user_promote(
    email: str = typer.Argument(..., help="관리자로 승격할 이메일"),
) -> None:
    """Promote a user to admin."""
    from scripts.make_admin import make_admin

    make_admin(email)


@movie_app.command("import-tmdb")
def movie_import_tmdb(
    tmdb_url: str = typer.Argument(..., help="TMDB 영화/TV URL"),
) -> None:
    """Import a movie or TV series from a TMDB URL."""
    from app.config import settings
    from app.database import SessionLocal
    from app.models import Genre, Movie, MovieGenre

    if not settings.TMDB_API_KEY:
        raise typer.BadParameter(
            "TMDB_API_KEY is not configured. Please set it in .env."
        )

    movie_match = re.search(r"/movie/(\d+)", tmdb_url)
    tv_match = re.search(r"/tv/(\d+)", tmdb_url)

    if movie_match:
        content_type = "movie"
        content_id = movie_match.group(1)
    elif tv_match:
        content_type = "tv"
        content_id = tv_match.group(1)
    else:
        raise typer.BadParameter(
            "Invalid TMDB URL. Use https://www.themoviedb.org/movie/{id} or https://www.themoviedb.org/tv/{id}."
        )

    try:
        with httpx.Client(timeout=30.0) as client:
            if content_type == "movie":
                content_response = client.get(
                    f"https://api.themoviedb.org/3/movie/{content_id}",
                    params={"api_key": settings.TMDB_API_KEY, "language": "ko-KR"},
                )
                content_response.raise_for_status()
                content_data = content_response.json()

                credits_response = client.get(
                    f"https://api.themoviedb.org/3/movie/{content_id}/credits",
                    params={"api_key": settings.TMDB_API_KEY},
                )
                credits_response.raise_for_status()
                credits_data = credits_response.json()

                director = None
                for crew in credits_data.get("crew", []):
                    if crew.get("job") == "Director":
                        director = crew.get("name")
                        break

                title = content_data.get("title", "")
                release_date_str = content_data.get("release_date")
            else:
                content_response = client.get(
                    f"https://api.themoviedb.org/3/tv/{content_id}",
                    params={"api_key": settings.TMDB_API_KEY, "language": "ko-KR"},
                )
                content_response.raise_for_status()
                content_data = content_response.json()

                credits_response = client.get(
                    f"https://api.themoviedb.org/3/tv/{content_id}/credits",
                    params={"api_key": settings.TMDB_API_KEY},
                )
                credits_response.raise_for_status()
                credits_data = credits_response.json()

                director = None
                creators = content_data.get("created_by", [])
                if creators:
                    director = creators[0].get("name")

                if not director:
                    for crew in credits_data.get("crew", []):
                        if crew.get("job") in ["Executive Producer", "Producer"]:
                            director = crew.get("name")
                            break

                title = content_data.get("name", "")
                release_date_str = content_data.get("first_air_date")
    except httpx.HTTPStatusError as exc:
        typer.secho(f"TMDB API error: {exc.response.text}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    poster_url = None
    if content_data.get("poster_path"):
        poster_url = (
            f"https://media.themoviedb.org/t/p/original{content_data['poster_path']}"
        )

    genre_names = [genre["name"] for genre in content_data.get("genres", [])]

    db = SessionLocal()
    try:
        new_movie = Movie(
            title=title,
            dec=content_data.get("overview", ""),
            director=director,
            poster_url=poster_url,
            release_date=(
                datetime.strptime(release_date_str, "%Y-%m-%d").date()
                if release_date_str
                else None
            ),
            rat=0,
        )

        db.add(new_movie)
        db.flush()

        for genre_name in genre_names:
            genre = db.query(Genre).filter(Genre.name == genre_name).first()
            if not genre:
                genre = Genre(name=genre_name)
                db.add(genre)
                db.flush()

            db.add(MovieGenre(mid=new_movie.mid, gid=genre.gid))

        db.commit()
        typer.secho(
            f"Imported: {new_movie.title} (ID: {new_movie.mid})", fg=typer.colors.GREEN
        )
    except Exception as exc:
        db.rollback()
        typer.secho(f"Import failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    finally:
        db.close()


app.add_typer(db_app, name="db")
app.add_typer(user_app, name="user")
app.add_typer(movie_app, name="movie")


if __name__ == "__main__":
    app()
