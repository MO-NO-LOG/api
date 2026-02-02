import re
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Genre, Movie, MovieGenre, Review, User

router = APIRouter(prefix="/admin", tags=["admin"])


# ─────────────────────────────────────────────
# Admin Schemas
# ─────────────────────────────────────────────
class AdminUserResponse(BaseModel):
    uid: int
    name: str
    nickname: str
    email: str
    img: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    createdAt: datetime
    reviewCount: int = 0

    class Config:
        from_attributes = True


class AdminMovieResponse(BaseModel):
    mid: int
    title: str
    director: Optional[str] = None
    posterUrl: Optional[str] = None
    releaseDate: Optional[str] = None
    averageRating: float = 0
    reviewCount: int = 0
    createdAt: datetime

    class Config:
        from_attributes = True


class AdminReviewResponse(BaseModel):
    rid: int
    userId: int
    userNickname: str
    movieId: int
    movieTitle: str
    title: Optional[str] = None
    content: str
    rating: float
    createdAt: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    totalUsers: int
    totalMovies: int
    totalReviews: int
    recentUsers: List[AdminUserResponse]
    recentReviews: List[AdminReviewResponse]


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    nickname: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None


class MovieCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    director: Optional[str] = None
    posterUrl: Optional[str] = None
    releaseDate: Optional[str] = None
    genres: List[str] = []


class MovieUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    director: Optional[str] = None
    posterUrl: Optional[str] = None
    releaseDate: Optional[str] = None


class TMDBMovieRequest(BaseModel):
    tmdbUrl: str


# ─────────────────────────────────────────────
# Admin Check Helper
# ─────────────────────────────────────────────
def require_admin(current_user: User = Depends(get_current_user)):
    # User 모델의 is_admin 필드로 관리자 여부 판단
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────
@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    total_users = db.query(User).count()
    total_movies = db.query(Movie).count()
    total_reviews = db.query(Review).count()

    # Recent users
    recent_users_raw = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    recent_users = []
    for u in recent_users_raw:
        review_count = db.query(Review).filter(Review.uid == u.uid).count()
        recent_users.append(
            AdminUserResponse(
                uid=u.uid,
                name=u.name,
                nickname=u.nickname,
                email=u.email,
                img=u.img,
                bio=u.bio,
                gender=u.gender,
                createdAt=u.created_at,
                reviewCount=review_count,
            )
        )

    # Recent reviews
    recent_reviews_raw = (
        db.query(Review, User, Movie)
        .join(User, Review.uid == User.uid)
        .join(Movie, Review.mid == Movie.mid)
        .order_by(Review.created_at.desc())
        .limit(5)
        .all()
    )
    recent_reviews = []
    for r, u, m in recent_reviews_raw:
        recent_reviews.append(
            AdminReviewResponse(
                rid=r.rid,
                userId=u.uid,
                userNickname=u.nickname,
                movieId=m.mid,
                movieTitle=m.title,
                title=r.title,
                content=r.dec,
                rating=float(r.rat) if r.rat else 0,
                createdAt=r.created_at,
            )
        )

    return DashboardStats(
        totalUsers=total_users,
        totalMovies=total_movies,
        totalReviews=total_reviews,
        recentUsers=recent_users,
        recentReviews=recent_reviews,
    )


# ─────────────────────────────────────────────
# User Management
# ─────────────────────────────────────────────
@router.get("/users", response_model=List[AdminUserResponse])
def get_all_users(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    offset = (page - 1) * size
    users = (
        db.query(User).order_by(User.created_at.desc()).offset(offset).limit(size).all()
    )

    result = []
    for u in users:
        review_count = db.query(Review).filter(Review.uid == u.uid).count()
        result.append(
            AdminUserResponse(
                uid=u.uid,
                name=u.name,
                nickname=u.nickname,
                email=u.email,
                img=u.img,
                bio=u.bio,
                gender=u.gender,
                createdAt=u.created_at,
                reviewCount=review_count,
            )
        )
    return result


@router.get("/users/{user_id}", response_model=AdminUserResponse)
def get_user_detail(
    user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.uid == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    review_count = db.query(Review).filter(Review.uid == user.uid).count()
    return AdminUserResponse(
        uid=user.uid,
        name=user.name,
        nickname=user.nickname,
        email=user.email,
        img=user.img,
        bio=user.bio,
        gender=user.gender,
        createdAt=user.created_at,
        reviewCount=review_count,
    )


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.uid == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.name is not None:
        user.name = data.name
    if data.nickname is not None:
        user.nickname = data.nickname
    if data.email is not None:
        user.email = data.email
    if data.bio is not None:
        user.bio = data.bio
    if data.gender is not None:
        user.gender = data.gender

    db.commit()
    return {"message": "User updated successfully"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.uid == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 관리자 자기 자신은 삭제 불가
    if user.uid == admin.uid:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


# ─────────────────────────────────────────────
# Movie Management
# ─────────────────────────────────────────────
@router.get("/movies", response_model=List[AdminMovieResponse])
def get_all_movies(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    offset = (page - 1) * size
    movies = (
        db.query(Movie)
        .order_by(Movie.created_at.desc())
        .offset(offset)
        .limit(size)
        .all()
    )

    result = []
    for m in movies:
        review_count = db.query(Review).filter(Review.mid == m.mid).count()
        result.append(
            AdminMovieResponse(
                mid=m.mid,
                title=m.title,
                director=m.director,
                posterUrl=m.poster_url,
                releaseDate=str(m.release_date) if m.release_date else None,
                averageRating=float(m.rat) if m.rat else 0,
                reviewCount=review_count,
                createdAt=m.created_at,
            )
        )
    return result


@router.post("/movies")
def create_movie(
    data: MovieCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    from datetime import date as date_type

    release_date = None
    if data.releaseDate:
        try:
            release_date = date_type.fromisoformat(data.releaseDate)
        except ValueError:
            pass

    movie = Movie(
        title=data.title,
        dec=data.description,
        director=data.director,
        poster_url=data.posterUrl,
        release_date=release_date,
    )
    db.add(movie)
    db.commit()
    db.refresh(movie)

    # Add genres
    for genre_name in data.genres:
        genre = db.query(Genre).filter(Genre.name == genre_name).first()
        if not genre:
            genre = Genre(name=genre_name)
            db.add(genre)
            db.commit()
            db.refresh(genre)

        movie_genre = MovieGenre(mid=movie.mid, gid=genre.gid)
        db.add(movie_genre)

    db.commit()
    return {"message": "Movie created successfully", "movieId": movie.mid}


@router.put("/movies/{movie_id}")
def update_movie(
    movie_id: int,
    data: MovieUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    movie = db.query(Movie).filter(Movie.mid == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    if data.title is not None:
        movie.title = data.title
    if data.description is not None:
        movie.dec = data.description
    if data.director is not None:
        movie.director = data.director
    if data.posterUrl is not None:
        movie.poster_url = data.posterUrl
    if data.releaseDate is not None:
        from datetime import date as date_type

        try:
            movie.release_date = date_type.fromisoformat(data.releaseDate)
        except ValueError:
            pass

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


# ─────────────────────────────────────────────
# Review Management
# ─────────────────────────────────────────────
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

    result = []
    for r, u, m in reviews:
        result.append(
            AdminReviewResponse(
                rid=r.rid,
                userId=u.uid,
                userNickname=u.nickname,
                movieId=m.mid,
                movieTitle=m.title,
                title=r.title,
                content=r.dec,
                rating=float(r.rat) if r.rat else 0,
                createdAt=r.created_at,
            )
        )
    return result


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


# ─────────────────────────────────────────────
# TMDB Movie Import
# ─────────────────────────────────────────────
@router.post("/movies/import-tmdb")
async def import_movie_from_tmdb(
    request: TMDBMovieRequest,
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

    # Extract movie or TV ID from TMDB URL
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
        # Fetch content details from TMDB API
        async with httpx.AsyncClient() as client:
            if content_type == "movie":
                # Get movie details
                content_response = await client.get(
                    f"https://api.themoviedb.org/3/movie/{content_id}",
                    params={"api_key": settings.TMDB_API_KEY, "language": "ko-KR"},
                )
                content_response.raise_for_status()
                content_data = content_response.json()

                # Get movie credits for director
                credits_response = await client.get(
                    f"https://api.themoviedb.org/3/movie/{content_id}/credits",
                    params={"api_key": settings.TMDB_API_KEY},
                )
                credits_response.raise_for_status()
                credits_data = credits_response.json()

                # Extract director
                director = None
                for crew in credits_data.get("crew", []):
                    if crew.get("job") == "Director":
                        director = crew.get("name")
                        break

                title = content_data.get("title", "")
                release_date_str = content_data.get("release_date")

            else:  # TV series
                # Get TV series details
                content_response = await client.get(
                    f"https://api.themoviedb.org/3/tv/{content_id}",
                    params={"api_key": settings.TMDB_API_KEY, "language": "ko-KR"},
                )
                content_response.raise_for_status()
                content_data = content_response.json()

                # Get TV series credits for creator
                credits_response = await client.get(
                    f"https://api.themoviedb.org/3/tv/{content_id}/credits",
                    params={"api_key": settings.TMDB_API_KEY},
                )
                credits_response.raise_for_status()
                credits_data = credits_response.json()

                # Extract creator (use first creator as director)
                director = None
                creators = content_data.get("created_by", [])
                if creators:
                    director = creators[0].get("name")

                # If no creator, try to get executive producer
                if not director:
                    for crew in credits_data.get("crew", []):
                        if crew.get("job") in ["Executive Producer", "Producer"]:
                            director = crew.get("name")
                            break

                title = content_data.get(
                    "name", ""
                )  # TV uses 'name' instead of 'title'
                release_date_str = content_data.get("first_air_date")

        # Build poster URL
        poster_url = None
        if content_data.get("poster_path"):
            poster_url = f"https://media.themoviedb.org/t/p/original{content_data['poster_path']}"

        # Extract genres
        genre_names = [genre["name"] for genre in content_data.get("genres", [])]

        # Create movie/TV entry in database
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
        db.flush()  # Get the movie ID

        # Add genres
        for genre_name in genre_names:
            # Find or create genre
            genre = db.query(Genre).filter(Genre.name == genre_name).first()
            if not genre:
                genre = Genre(name=genre_name)
                db.add(genre)
                db.flush()

            # Link movie and genre
            movie_genre = MovieGenre(mid=new_movie.mid, gid=genre.gid)
            db.add(movie_genre)

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
