from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Comment, Movie, Review, User
from app.schemas import UserDetailReviewItem

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile/{nickname}")
def get_user_profile_by_nickname(
    nickname: str,
    limit: int = Query(20, ge=0, le=100, description="Number of reviews to return"),
    db: Session = Depends(get_db),
):
    """
    닉네임으로 사용자의 상세 정보를 조회합니다. (인증 불필요)
    - 남긴 리뷰 수
    - 남긴 댓글 수
    - 가입일
    - 지금까지 남긴 리뷰 목록 (기본 20개, 쿼리로 개수 지정 가능)
    """
    # 닉네임으로 사용자 조회
    user = db.query(User).filter(User.nickname == nickname).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 리뷰 수 조회
    review_count = (
        db.query(func.count(Review.rid)).filter(Review.uid == user.uid).scalar()
    )

    # 댓글 수 조회
    comment_count = (
        db.query(func.count(Comment.cid)).filter(Comment.uid == user.uid).scalar()
    )

    # 리뷰 목록 조회 (최신순, limit 적용)
    reviews = (
        db.query(Review, Movie)
        .join(Movie, Review.mid == Movie.mid)
        .filter(Review.uid == user.uid)
        .order_by(Review.created_at.desc())
        .limit(limit)
        .all()
    )

    # 리뷰 목록을 스키마 형식으로 변환
    review_items = [
        UserDetailReviewItem(
            reviewId=review.rid,
            movieId=review.mid,
            movieTitle=movie.title,
            rating=float(review.rat) if review.rat else None,
            content=review.dec,
            createdAt=review.created_at,
        )
        for review, movie in reviews
    ]

    return {
        "nickname": user.nickname,
        "profileImage": user.img,
        "bio": user.bio,
        "reviewCount": review_count or 0,
        "commentCount": comment_count or 0,
        "joinedAt": user.created_at,
        "reviews": review_items,
    }


@router.get("/profile/{nickname}/image")
def get_user_profile_image(nickname: str, db: Session = Depends(get_db)):
    """
    닉네임으로 사용자의 프로필 이미지를 조회합니다. (인증 불필요)
    """
    user = db.query(User).filter(User.nickname == nickname).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"profileImage": user.img}
