from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Comment, Review, ReviewLike, User
from app.schemas import (
    ReviewCommentCreateRequest,
    ReviewCommentCreateResponse,
    ReviewCommentDeleteRequest,
    ReviewCreateRequest,
    ReviewDeleteRequest,
    ReviewListResponse,
    ReviewReactionCancelRequest,
    ReviewReactionRequest,
    ReviewResponseItem,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/by-movie/{movie_id}", response_model=ReviewListResponse)
def get_reviews_by_movie(movie_id: int, db: Session = Depends(get_db)):
    reviews = (
        db.query(Review)
        .filter(Review.mid == movie_id)
        .order_by(desc(Review.created_at))
        .all()
    )

    result = []
    for r in reviews:
        # Fetch user nickname (r.user.nickname)
        # Note: r.user might load lazily.
        # If user is None (shouldn't happen with FK constraint), handle gracefully.
        nickname = r.user.nickname if r.user else "Unknown"

        result.append(
            ReviewResponseItem(
                reviewId=r.rid,
                userId=r.uid,
                userNickname=nickname,
                rating=float(r.rat),
                content=r.dec,
                createdAt=r.created_at,
            )
        )

    return {"reviews": result}


@router.post("/create")
def create_review(
    req: ReviewCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if already reviewed
    existing = (
        db.query(Review)
        .filter(Review.uid == current_user.uid, Review.mid == req.movieId)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="You have already reviewed this movie."
        )

    new_review = Review(
        uid=current_user.uid, mid=req.movieId, dec=req.content, rat=req.rating
    )
    db.add(new_review)
    db.commit()

    return {"message": "Review created successfully"}


@router.post("/like")
def like_review(
    req: ReviewReactionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review = db.query(Review).filter(Review.rid == req.reviewId).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    existing = (
        db.query(ReviewLike)
        .filter(ReviewLike.rid == req.reviewId, ReviewLike.uid == current_user.uid)
        .first()
    )

    if existing:
        if existing.type == "L":
            pass
        else:
            existing.type = "L"
            db.commit()
    else:
        db.add(
            ReviewLike(
                rid=req.reviewId,
                uid=current_user.uid,
                type="L",
            )
        )
        db.commit()

    like_count = (
        db.query(func.count(ReviewLike.lid))
        .filter(ReviewLike.rid == req.reviewId, ReviewLike.type == "L")
        .scalar()
    )
    dislike_count = (
        db.query(func.count(ReviewLike.lid))
        .filter(ReviewLike.rid == req.reviewId, ReviewLike.type == "D")
        .scalar()
    )

    return {
        "message": "Review liked",
        "reviewId": req.reviewId,
        "likeCount": like_count or 0,
        "dislikeCount": dislike_count or 0,
        "myReaction": "L",
    }


@router.post("/dislike")
def dislike_review(
    req: ReviewReactionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review = db.query(Review).filter(Review.rid == req.reviewId).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    existing = (
        db.query(ReviewLike)
        .filter(ReviewLike.rid == req.reviewId, ReviewLike.uid == current_user.uid)
        .first()
    )

    if existing:
        if existing.type == "D":
            pass
        else:
            existing.type = "D"
            db.commit()
    else:
        db.add(
            ReviewLike(
                rid=req.reviewId,
                uid=current_user.uid,
                type="D",
            )
        )
        db.commit()

    like_count = (
        db.query(func.count(ReviewLike.lid))
        .filter(ReviewLike.rid == req.reviewId, ReviewLike.type == "L")
        .scalar()
    )
    dislike_count = (
        db.query(func.count(ReviewLike.lid))
        .filter(ReviewLike.rid == req.reviewId, ReviewLike.type == "D")
        .scalar()
    )

    return {
        "message": "Review disliked",
        "reviewId": req.reviewId,
        "likeCount": like_count or 0,
        "dislikeCount": dislike_count or 0,
        "myReaction": "D",
    }


@router.post("/reaction/cancel")
def cancel_review_reaction(
    req: ReviewReactionCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review = db.query(Review).filter(Review.rid == req.reviewId).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    existing = (
        db.query(ReviewLike)
        .filter(ReviewLike.rid == req.reviewId, ReviewLike.uid == current_user.uid)
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()

    like_count = (
        db.query(func.count(ReviewLike.lid))
        .filter(ReviewLike.rid == req.reviewId, ReviewLike.type == "L")
        .scalar()
    )
    dislike_count = (
        db.query(func.count(ReviewLike.lid))
        .filter(ReviewLike.rid == req.reviewId, ReviewLike.type == "D")
        .scalar()
    )

    return {
        "message": "Review reaction canceled",
        "reviewId": req.reviewId,
        "likeCount": like_count or 0,
        "dislikeCount": dislike_count or 0,
        "myReaction": None,
    }


@router.post("/comment/create", response_model=ReviewCommentCreateResponse)
def create_review_comment(
    req: ReviewCommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review = db.query(Review).filter(Review.rid == req.reviewId).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    new_comment = Comment(
        rid=req.reviewId,
        uid=current_user.uid,
        dec=req.content,
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return ReviewCommentCreateResponse(
        commentId=new_comment.cid,
        reviewId=new_comment.rid,
        userId=current_user.uid,
        userNickname=current_user.nickname,
        content=new_comment.dec,
        createdAt=new_comment.created_at,
    )


@router.post("/delete")
def delete_review(
    req: ReviewDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review = db.query(Review).filter(Review.rid == req.reviewId).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.uid != current_user.uid and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to delete review")

    db.delete(review)
    db.commit()

    return {"message": "Review deleted", "reviewId": req.reviewId}


@router.post("/comment/delete")
def delete_review_comment(
    req: ReviewCommentDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.query(Comment).filter(Comment.cid == req.commentId).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.uid != current_user.uid and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to delete comment")

    db.delete(comment)
    db.commit()

    return {"message": "Comment deleted", "commentId": req.commentId}
