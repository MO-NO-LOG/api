from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Movie, MovieGenre
from app.schemas import MovieRankingItem, MovieRankingResponse
from app.utils import review_count_subquery

router = APIRouter(prefix="/ranking", tags=["ranking"])


@router.get("/movies", response_model=MovieRankingResponse)
def get_movie_ranking(
    limit: int = Query(10, ge=1, le=100, description="Number of movies to return"),
    db: Session = Depends(get_db),
):
    """
    Returns movie ranking based on average rating.
    """
    review_count_subq = review_count_subquery(db)

    movies = (
        db.query(
            Movie,
            func.coalesce(review_count_subq.c.review_count, 0).label("review_count"),
            func.coalesce(review_count_subq.c.avg_rating, 0.0).label("avg_rating"),
        )
        .outerjoin(review_count_subq, Movie.mid == review_count_subq.c.mid)
        .options(joinedload(Movie.genres).joinedload(MovieGenre.genre))
        .order_by(
            desc(func.coalesce(review_count_subq.c.avg_rating, 0.0)),
            desc(func.coalesce(review_count_subq.c.review_count, 0)),
        )
        .limit(limit)
        .all()
    )

    return {
        "movies": [
            MovieRankingItem.from_movie(
                rank, m, int(review_count), average_rating=float(avg_rating)
            )
            for rank, (m, review_count, avg_rating) in enumerate(movies, start=1)
        ]
    }
