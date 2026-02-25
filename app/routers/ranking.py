from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Movie, MovieGenre, Genre, Review
from app.schemas import MovieRankingItem, MovieRankingResponse

router = APIRouter(prefix="/ranking", tags=["ranking"])


@router.get("/movies", response_model=MovieRankingResponse)
def get_movie_ranking(
    limit: int = Query(10, ge=1, le=100, description="Number of movies to return"),
    db: Session = Depends(get_db),
):
    """
    Returns movie ranking based on average rating.
    """
    # Subquery: count reviews per movie
    review_count_subq = (
        db.query(Review.mid, func.count(Review.rid).label("review_count"))
        .group_by(Review.mid)
        .subquery()
    )

    movies = (
        db.query(Movie, func.coalesce(review_count_subq.c.review_count, 0).label("review_count"))
        .outerjoin(review_count_subq, Movie.mid == review_count_subq.c.mid)
        .order_by(desc(Movie.rat), desc(func.coalesce(review_count_subq.c.review_count, 0)))
        .limit(limit)
        .all()
    )

    result = []
    for rank, (m, review_count) in enumerate(movies, start=1):
        genres = [g.genre.name for g in m.genres]
        result.append(
            MovieRankingItem(
                rank=rank,
                id=m.mid,
                title=m.title,
                posterUrl=m.poster_url,
                genres=genres,
                averageRating=float(m.rat) if m.rat else 0.0,
                releaseDate=m.release_date,
                reviewCount=int(review_count),
            )
        )

    return {"movies": result}
