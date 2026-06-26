from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Genre, Movie, MovieGenre
from app.schemas import (
    MovieDetailResponse,
    MovieResponseItem,
    MovieSearchResponse,
)

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/search", response_model=MovieSearchResponse)
def search_movies(
    keyword: str = "",
    searchType: str = "TITLE",
    page: int = 0,
    size: int = 20,
    db: Session = Depends(get_db),
):
    # Base filter query (no joinedload) — used for accurate count
    base_query = db.query(Movie)

    if keyword:
        if searchType == "TITLE":
            base_query = base_query.filter(Movie.title.ilike(f"%{keyword}%"))
        elif searchType == "DIRECTOR":
            base_query = base_query.filter(Movie.director.ilike(f"%{keyword}%"))
        elif searchType == "GENRE":
            base_query = (
                base_query.join(MovieGenre)
                .join(Genre)
                .filter(Genre.name.ilike(f"%{keyword}%"))
            )

    total_count = base_query.count()

    # Data query with eager loading to avoid N+1 on genres
    movies = (
        base_query.options(joinedload(Movie.genres).joinedload(MovieGenre.genre))
        .offset(page * size)
        .limit(size)
        .all()
    )

    total_pages = (total_count + size - 1) // size

    return {
        "movies": [MovieResponseItem.from_movie(m) for m in movies],
        "totalPages": total_pages,
    }


@router.get("/trend", response_model=List[MovieResponseItem])
def get_trend_movies(db: Session = Depends(get_db)):
    # Top 10 by rating
    movies = (
        db.query(Movie)
        .options(joinedload(Movie.genres).joinedload(MovieGenre.genre))
        .order_by(desc(Movie.rat))
        .limit(10)
        .all()
    )

    return [MovieResponseItem.from_movie(m) for m in movies]


@router.get("/detail/{movieId}", response_model=MovieDetailResponse)
def get_movie_detail(movieId: int, db: Session = Depends(get_db)):
    movie = (
        db.query(Movie)
        .filter(Movie.mid == movieId)
        .options(joinedload(Movie.genres).joinedload(MovieGenre.genre))
        .first()
    )
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return MovieDetailResponse(
        **MovieResponseItem.from_movie(movie).model_dump(),
        description=movie.dec,
    )


@router.get("/recommended", response_model=List[MovieResponseItem])
def get_recommended_movies(limit: int = 4, db: Session = Depends(get_db)):
    # Random movies with rating >= 3
    # SQLAlchemy random is tricky across DBs, usually func.random() for PG
    movies = (
        db.query(Movie)
        .filter(Movie.rat >= 3.0)
        .options(joinedload(Movie.genres).joinedload(MovieGenre.genre))
        .order_by(func.random())
        .limit(limit)
        .all()
    )

    # If not enough rated movies, just random movies
    if len(movies) < limit:
        movies = (
            db.query(Movie)
            .options(joinedload(Movie.genres).joinedload(MovieGenre.genre))
            .order_by(func.random())
            .limit(limit)
            .all()
        )

    return [MovieResponseItem.from_movie(m) for m in movies]
