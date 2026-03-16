import os
import subprocess
import sys
from typing import Optional

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

    make_user(nickname, email, password, gender)


@user_app.command("promote")
def user_promote(
    email: str = typer.Argument(..., help="관리자로 승격할 이메일"),
) -> None:
    """Promote a user to admin."""
    from scripts.make_admin import make_admin

    make_admin(email)


app.add_typer(db_app, name="db")
app.add_typer(user_app, name="user")


if __name__ == "__main__":
    app()
