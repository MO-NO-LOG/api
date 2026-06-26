from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Comment, Review, ReviewLike, User
from app.schemas import (
    CommentListRequest,
    CommentListResponse,
    CommentReplyItem,
    ReviewCommentCreateRequest,
    ReviewCommentCreateResponse,
    ReviewCommentDeleteRequest,
    ReviewCreateRequest,
    ReviewDeleteRequest,
    ReviewListResponse,
    ReviewReactionCancelRequest,
    ReviewReactionRequest,
    ReviewResponseItem,
    ReplyCreateRequest,
    ReplyCreateResponse,
    ReplyDeleteRequest,
)
from app.utils import is_owner_or_admin

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _review_reaction_counts(
    db: Session, review_id: int, my_reaction: Optional[str]
) -> dict[str, Any]:
    like_count = (
        db.query(func.count(ReviewLike.lid))
        .filter(ReviewLike.rid == review_id, ReviewLike.type == "L")
        .scalar()
    )
    dislike_count = (
        db.query(func.count(ReviewLike.lid))
        .filter(ReviewLike.rid == review_id, ReviewLike.type == "D")
        .scalar()
    )
    return {
        "reviewId": review_id,
        "likeCount": like_count or 0,
        "dislikeCount": dislike_count or 0,
        "myReaction": my_reaction,
    }


def _set_review_reaction(
    db: Session, current_user: User, review_id: int, reaction_type: str
) -> dict[str, Any]:
    review = db.query(Review).filter(Review.rid == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    existing = (
        db.query(ReviewLike)
        .filter(ReviewLike.rid == review_id, ReviewLike.uid == current_user.uid)
        .first()
    )

    if existing:
        if existing.type != reaction_type:
            existing.type = reaction_type  # ty: ignore[invalid-assignment]
            db.commit()
    else:
        db.add(ReviewLike(rid=review_id, uid=current_user.uid, type=reaction_type))
        db.commit()

    return _review_reaction_counts(db, review_id, reaction_type)


def _comment_reply_item(reply: Comment) -> CommentReplyItem:
    return CommentReplyItem(
        commentId=reply.cid,  # ty: ignore[invalid-argument-type]
        reviewId=reply.rid,  # ty: ignore[invalid-argument-type]
        userId=reply.uid,  # ty: ignore[invalid-argument-type]
        userNickname=reply.user.nickname if reply.user else "Unknown",
        content=reply.dec,  # ty: ignore[invalid-argument-type]
        createdAt=reply.created_at,  # ty: ignore[invalid-argument-type]
    )


@router.get("/by-movie/{movie_id}", response_model=ReviewListResponse)
def get_reviews_by_movie(movie_id: int, db: Session = Depends(get_db)):
    reviews = (
        db.query(Review)
        .filter(Review.mid == movie_id)
        .options(joinedload(Review.user))
        .order_by(desc(Review.created_at))
        .all()
    )

    return {
        "reviews": [
            ReviewResponseItem(
                reviewId=r.rid,  # ty: ignore[invalid-argument-type]
                userId=r.uid,  # ty: ignore[invalid-argument-type]
                userNickname=r.user.nickname if r.user else "Unknown",
                rating=float(r.rat) if r.rat is not None else 0.0,  # ty: ignore[invalid-argument-type]
                content=r.dec,  # ty: ignore[invalid-argument-type]
                createdAt=r.created_at,  # ty: ignore[invalid-argument-type]
            )
            for r in reviews
        ]
    }


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
    result = _set_review_reaction(db, current_user, req.reviewId, "L")
    return {"message": "Review liked", **result}


@router.post("/dislike")
def dislike_review(
    req: ReviewReactionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = _set_review_reaction(db, current_user, req.reviewId, "D")
    return {"message": "Review disliked", **result}


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

    result = _review_reaction_counts(db, req.reviewId, None)
    return {"message": "Review reaction canceled", **result}


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
        commentId=new_comment.cid,  # ty: ignore[invalid-argument-type]
        reviewId=new_comment.rid,  # ty: ignore[invalid-argument-type]
        userId=current_user.uid,  # ty: ignore[invalid-argument-type]
        userNickname=current_user.nickname,  # ty: ignore[invalid-argument-type]
        content=new_comment.dec,  # ty: ignore[invalid-argument-type]
        createdAt=new_comment.created_at,  # ty: ignore[invalid-argument-type]
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

    if not is_owner_or_admin(review, current_user):
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

    if not is_owner_or_admin(comment, current_user):
        raise HTTPException(status_code=403, detail="Not allowed to delete comment")

    db.delete(comment)
    db.commit()

    return {"message": "Comment deleted", "commentId": req.commentId}


@router.post("/comment/list", response_model=CommentListResponse)
def list_review_comments(req: CommentListRequest, db: Session = Depends(get_db)):
    review = db.query(Review).filter(Review.rid == req.reviewId).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    top_level = (
        db.query(Comment)
        .filter(Comment.rid == req.reviewId, Comment.parent_cid.is_(None))
        .options(
            joinedload(Comment.user),
            joinedload(Comment.replies).joinedload(Comment.user),
        )
        .order_by(Comment.created_at)
        .all()
    )

    return {
        "comments": [
            {
                "commentId": c.cid,
                "reviewId": c.rid,
                "userId": c.uid,
                "userNickname": c.user.nickname if c.user else "Unknown",
                "content": c.dec,
                "createdAt": c.created_at,
                "replies": [
                    _comment_reply_item(r)
                    for r in sorted(c.replies, key=lambda x: x.created_at)
                ],
            }
            for c in top_level
        ]
    }


@router.post("/comment/reply/create", response_model=ReplyCreateResponse)
def create_reply(
    req: ReplyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parent = db.query(Comment).filter(Comment.cid == req.commentId).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Comment not found")

    if parent.parent_cid is not None:
        raise HTTPException(
            status_code=400, detail="Cannot reply to a reply (max depth: 1)"
        )

    new_reply = Comment(
        rid=parent.rid,
        uid=current_user.uid,
        dec=req.content,
        parent_cid=parent.cid,
    )
    db.add(new_reply)
    db.commit()
    db.refresh(new_reply)

    return ReplyCreateResponse(
        commentId=new_reply.cid,
        parentCommentId=parent.cid,
        reviewId=new_reply.rid,
        userId=current_user.uid,
        userNickname=current_user.nickname,
        content=new_reply.dec,
        createdAt=new_reply.created_at,
    )


@router.post("/comment/reply/delete")
def delete_reply(
    req: ReplyDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reply = db.query(Comment).filter(Comment.cid == req.commentId).first()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")

    if reply.parent_cid is None:
        raise HTTPException(status_code=400, detail="Target is not a reply")

    if not is_owner_or_admin(reply, current_user):
        raise HTTPException(status_code=403, detail="Not allowed to delete this reply")

    db.delete(reply)
    db.commit()

    return {"message": "Reply deleted", "commentId": req.commentId}
