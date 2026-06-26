from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Favorite, Movie, User
from app.schemas import FavoriteItem, FavoriteListResponse, FavoriteToggleRequest

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("/toggle")
def toggle_favorite(
    req: FavoriteToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movie = db.query(Movie).filter(Movie.mid == req.movieId).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    existing = (
        db.query(Favorite)
        .filter(Favorite.uid == current_user.uid, Favorite.mid == req.movieId)
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()
        return {"favorited": False, "movieId": req.movieId}

    db.add(Favorite(uid=current_user.uid, mid=req.movieId))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Another concurrent request already created the favorite.
        return {"favorited": True, "movieId": req.movieId}

    return {"favorited": True, "movieId": req.movieId}


@router.get("/list", response_model=FavoriteListResponse)
def list_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    favorites = (
        db.query(Favorite)
        .filter(Favorite.uid == current_user.uid)
        .order_by(Favorite.created_at.desc())
        .all()
    )

    return {"favorites": [FavoriteItem.from_favorite(f) for f in favorites]}


@router.post("/status")
def get_favorite_status(
    req: FavoriteToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = (
        db.query(Favorite)
        .filter(Favorite.uid == current_user.uid, Favorite.mid == req.movieId)
        .first()
    )
    return {"favorited": existing is not None, "movieId": req.movieId}
