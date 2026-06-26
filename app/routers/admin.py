import re
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Genre, Movie, MovieGenre, Review, User
from app.schemas import (
    AdminMovieCreateRequest,
    AdminMovieResponse,
    AdminMovieUpdateRequest,
    AdminReviewResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
    DashboardStats,
    EmailVerificationSettingsResponse,
    EmailVerificationSettingsUpdateRequest,
    TMDBImportRequest,
)
from app.services.system_settings_service import SystemSettingsService
from app.utils import parse_release_date, review_count_subquery

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


def _get_or_create_genre(db: Session, name: str) -> Genre:
    genre = db.query(Genre).filter(Genre.name == name).first()
    if not genre:
        genre = Genre(name=name)
        db.add(genre)
    return genre


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    total_users = db.query(User).count()
    total_movies = db.query(Movie).count()
    total_reviews = db.query(Review).count()

    review_count_sq = review_count_subquery(db)
    recent_users_raw = (
        db.query(User, func.coalesce(review_count_sq.c.cnt, 0).label("review_count"))
        .outerjoin(review_count_sq, User.uid == review_count_sq.c.uid)
        .order_by(User.created_at.desc())
        .limit(5)
        .all()
    )
    recent_users = [
        AdminUserResponse.from_user(u, int(review_count))
        for u, review_count in recent_users_raw
    ]

    recent_reviews_raw = (
        db.query(Review, User, Movie)
        .join(User, Review.uid == User.uid)
        .join(Movie, Review.mid == Movie.mid)
        .order_by(Review.created_at.desc())
        .limit(5)
        .all()
    )
    recent_reviews = [
        AdminReviewResponse.from_review(r, u, m) for r, u, m in recent_reviews_raw
    ]

    return DashboardStats(
        totalUsers=total_users,
        totalMovies=total_movies,
        totalReviews=total_reviews,
        recentUsers=recent_users,
        recentReviews=recent_reviews,
    )


@router.get("/users", response_model=List[AdminUserResponse])
def get_all_users(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    offset = (page - 1) * size
    review_count_sq = review_count_subquery(db)
    rows = (
        db.query(User, func.coalesce(review_count_sq.c.cnt, 0).label("review_count"))
        .outerjoin(review_count_sq, User.uid == review_count_sq.c.uid)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(size)
        .all()
    )

    return [
        AdminUserResponse.from_user(u, int(review_count))
        for u, review_count in rows
    ]


@router.get("/users/{user_id}", response_model=AdminUserResponse)
def get_user_detail(
    user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.uid == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    review_count = db.query(Review).filter(Review.uid == user.uid).count()
    return AdminUserResponse.from_user(user, review_count)


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    data: AdminUserUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.uid == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)

    db.commit()
    return {"message": "User updated successfully"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.uid == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.uid == admin.uid:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.get("/movies", response_model=List[AdminMovieResponse])
def get_all_movies(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    offset = (page - 1) * size
    review_count_sq = review_count_subquery(db)
    rows = (
        db.query(Movie, func.coalesce(review_count_sq.c.cnt, 0).label("review_count"))
        .outerjoin(review_count_sq, Movie.mid == review_count_sq.c.mid)
        .order_by(Movie.created_at.desc())
        .offset(offset)
        .limit(size)
        .all()
    )

    return [
        AdminMovieResponse.from_movie(m, int(review_count))
        for m, review_count in rows
    ]


@router.post("/movies")
def create_movie(
    data: AdminMovieCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    movie = Movie(
        title=data.title,
        dec=data.description,
        director=data.director,
        poster_url=data.posterUrl,
        release_date=parse_release_date(data.releaseDate),
    )
    db.add(movie)
    db.flush()

    for genre_name in data.genres:
        genre = _get_or_create_genre(db, genre_name)
        db.add(MovieGenre(mid=movie.mid, gid=genre.gid))

    db.commit()
    db.refresh(movie)
    return {"message": "Movie created successfully", "movieId": movie.mid}


@router.put("/movies/{movie_id}")
def update_movie(
    movie_id: int,
    data: AdminMovieUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    movie = db.query(Movie).filter(Movie.mid == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    updates = data.model_dump(exclude_unset=True)
    field_map = {
        "title": "title",
        "description": "dec",
        "director": "director",
        "posterUrl": "poster_url",
    }
    for schema_key, model_attr in field_map.items():
        if schema_key in updates:
            setattr(movie, model_attr, updates[schema_key])

    if "releaseDate" in updates:
        movie.release_date = parse_release_date(updates["releaseDate"])

    db.commit()
    return {"message": "Movie updated successfully"}


@router.delete("/movies/{movie_id}")
def delete_movie(
    movie_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    movie = db.query(Movie).filter(Movie.mid == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    db.delete(movie)
    db.commit()
    return {"message": "Movie deleted successfully"}


@router.get("/reviews", response_model=List[AdminReviewResponse])
def get_all_reviews(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    offset = (page - 1) * size
    reviews = (
        db.query(Review, User, Movie)
        .join(User, Review.uid == User.uid)
        .join(Movie, Review.mid == Movie.mid)
        .order_by(Review.created_at.desc())
        .offset(offset)
        .limit(size)
        .all()
    )

    return [AdminReviewResponse.from_review(r, u, m) for r, u, m in reviews]


@router.delete("/reviews/{review_id}")
def delete_review(
    review_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    review = db.query(Review).filter(Review.rid == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    db.delete(review)
    db.commit()
    return {"message": "Review deleted successfully"}


@router.post("/movies/import-tmdb")
async def import_movie_from_tmdb(
    request: TMDBImportRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    TMDB URL에서 영화/TV 시리즈 정보를 가져와 DB에 추가합니다.
    URL 형식:
    - 영화: https://www.themoviedb.org/movie/{movie_id}
    - TV: https://www.themoviedb.org/tv/{tv_id}
    """
    if not settings.TMDB_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="TMDB API key not configured. Please set TMDB_API_KEY in .env file.",
        )

    movie_match = re.search(r"/movie/(\d+)", request.tmdbUrl)
    tv_match = re.search(r"/tv/(\d+)", request.tmdbUrl)

    if movie_match:
        content_type = "movie"
        content_id = movie_match.group(1)
    elif tv_match:
        content_type = "tv"
        content_id = tv_match.group(1)
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid TMDB URL. Expected format: https://www.themoviedb.org/movie/{id} or https://www.themoviedb.org/tv/{id}",
        )

    try:
        async with httpx.AsyncClient() as client:
            if content_type == "movie":
                content_response = await client.get(
                    f"https://api.themoviedb.org/3/movie/{content_id}",
                    params={"api_key": settings.TMDB_API_KEY, "language": "ko-KR"},
                )
                content_response.raise_for_status()
                content_data = content_response.json()

                credits_response = await client.get(
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
                content_response = await client.get(
                    f"https://api.themoviedb.org/3/tv/{content_id}",
                    params={"api_key": settings.TMDB_API_KEY, "language": "ko-KR"},
                )
                content_response.raise_for_status()
                content_data = content_response.json()

                credits_response = await client.get(
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

        poster_url = None
        if content_data.get("poster_path"):
            poster_url = f"https://media.themoviedb.org/t/p/original{content_data['poster_path']}"

        genre_names = [genre["name"] for genre in content_data.get("genres", [])]

        new_movie = Movie(
            title=title,
            dec=content_data.get("overview", ""),
            director=director,
            poster_url=poster_url,
            release_date=parse_release_date(release_date_str),
            rat=0,
        )

        db.add(new_movie)
        db.flush()

        for genre_name in genre_names:
            genre = _get_or_create_genre(db, genre_name)
            db.add(MovieGenre(mid=new_movie.mid, gid=genre.gid))

        db.commit()

        return {
            "message": "Content imported successfully",
            "movie": {
                "mid": new_movie.mid,
                "title": new_movie.title,
                "director": new_movie.director,
                "posterUrl": new_movie.poster_url,
                "releaseDate": (
                    new_movie.release_date.isoformat()
                    if new_movie.release_date
                    else None
                ),
                "genres": genre_names,
                "type": content_type,
            },
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"TMDB API error: {e.response.text}",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to import content: {str(e)}"
        )


@router.get("/settings/email-verification", response_model=EmailVerificationSettingsResponse)
async def get_email_verification_setting(
    admin: User = Depends(require_admin),
):
    enabled = await SystemSettingsService.is_email_verification_enabled()
    return EmailVerificationSettingsResponse(enabled=enabled)


@router.put("/settings/email-verification")
async def update_email_verification_setting(
    data: EmailVerificationSettingsUpdateRequest,
    admin: User = Depends(require_admin),
):
    success = await SystemSettingsService.set_email_verification_enabled(data.enabled)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update setting")
    return {"message": "Email verification setting updated", "enabled": data.enabled}
