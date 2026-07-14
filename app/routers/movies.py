from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Genre, Movie, MovieGenre, Review
from app.schemas import (
    MovieDetailResponse,
    MovieResponseItem,
    MovieSearchResponse,
)

router = APIRouter(prefix="/movies", tags=["movies"])


def _avg_rating_subquery(db: Session):
    return (
        db.query(Review.mid, func.avg(Review.rat).label("avg_rating"))
        .group_by(Review.mid)
        .subquery()
    )


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

    avg_sq = _avg_rating_subquery(db)

    # Data query with eager loading to avoid N+1 on genres
    rows = (
        base_query.options(joinedload(Movie.genres).joinedload(MovieGenre.genre))
        .outerjoin(avg_sq, Movie.mid == avg_sq.c.mid)
        .add_columns(func.coalesce(avg_sq.c.avg_rating, 0.0).label("avg_rating"))
        .offset(page * size)
        .limit(size)
        .all()
    )

    total_pages = (total_count + size - 1) // size

    return {
        "movies": [
            MovieResponseItem.from_movie(m, average_rating=float(avg))
            for m, avg in rows
        ],
        "totalPages": total_pages,
    }


@router.get("/trend", response_model=List[MovieResponseItem])
def get_trend_movies(db: Session = Depends(get_db)):
    # Top 10 by average rating from reviews
    avg_sq = _avg_rating_subquery(db)
    rows = (
        db.query(Movie)
        .options(joinedload(Movie.genres).joinedload(MovieGenre.genre))
        .outerjoin(avg_sq, Movie.mid == avg_sq.c.mid)
        .add_columns(func.coalesce(avg_sq.c.avg_rating, 0.0).label("avg_rating"))
        .order_by(desc(func.coalesce(avg_sq.c.avg_rating, 0.0)))
        .limit(10)
        .all()
    )

    return [
        MovieResponseItem.from_movie(m, average_rating=float(avg)) for m, avg in rows
    ]


@router.get("/detail/{movieId}", response_model=MovieDetailResponse)
def get_movie_detail(movieId: int, db: Session = Depends(get_db)):
    avg_sq = _avg_rating_subquery(db)
    row = (
        db.query(Movie)
        .filter(Movie.mid == movieId)
        .options(joinedload(Movie.genres).joinedload(MovieGenre.genre))
        .outerjoin(avg_sq, Movie.mid == avg_sq.c.mid)
        .add_columns(func.coalesce(avg_sq.c.avg_rating, 0.0).label("avg_rating"))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Movie not found")

    movie, avg = row
    return MovieDetailResponse(
        **MovieResponseItem.from_movie(movie, average_rating=float(avg)).model_dump(),
        description=movie.dec,  # ty: ignore[invalid-argument-type]
    )


@router.get("/recommended", response_model=List[MovieResponseItem])
def get_recommended_movies(limit: int = 4, db: Session = Depends(get_db)):
    # Random movies with average rating >= 3
    avg_sq = _avg_rating_subquery(db)
    rows = (
        db.query(Movie)
        .options(joinedload(Movie.genres).joinedload(MovieGenre.genre))
        .outerjoin(avg_sq, Movie.mid == avg_sq.c.mid)
        .add_columns(func.coalesce(avg_sq.c.avg_rating, 0.0).label("avg_rating"))
        .filter(func.coalesce(avg_sq.c.avg_rating, 0.0) >= 3.0)
        .order_by(func.random())
        .limit(limit)
        .all()
    )

    # If not enough rated movies, just random movies
    if len(rows) < limit:
        rows = (
            db.query(Movie)
            .options(joinedload(Movie.genres).joinedload(MovieGenre.genre))
            .outerjoin(avg_sq, Movie.mid == avg_sq.c.mid)
            .add_columns(func.coalesce(avg_sq.c.avg_rating, 0.0).label("avg_rating"))
            .order_by(func.random())
            .limit(limit)
            .all()
        )

    return [
        MovieResponseItem.from_movie(m, average_rating=float(avg)) for m, avg in rows
    ]
