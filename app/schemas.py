from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


# User Schemas
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str
    nickname: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    bio: Optional[str] = None


class UserLogin(UserBase):
    password: str
    remember_me: bool = False


class UserResponse(UserBase):
    uid: int
    birth_date: Optional[date] = None
    nickname: str
    img: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    is_admin: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    birth_date: Optional[date] = None
    nickname: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    img: Optional[str] = None


# Movie Schemas
class MovieResponseItem(BaseModel):
    id: int
    title: str
    posterUrl: Optional[str] = None
    genres: List[str] = []
    averageRating: float
    releaseDate: Optional[date] = None


class MovieDetailResponse(MovieResponseItem):
    description: Optional[str] = None


# Search Schemas
class MovieSearchResponse(BaseModel):
    movies: List[MovieResponseItem]
    totalPages: int


# Review Schemas
class ReviewCreateRequest(BaseModel):
    movieId: int
    content: str
    rating: float


class ReviewResponseItem(BaseModel):
    reviewId: int
    userId: int
    userNickname: str
    rating: float
    content: str
    createdAt: datetime


class ReviewListResponse(BaseModel):
    reviews: List[ReviewResponseItem]


class ReviewListRequest(BaseModel):
    movieId: int


class ReviewReactionRequest(BaseModel):
    reviewId: int


class ReviewReactionCancelRequest(BaseModel):
    reviewId: int


class ReviewCommentCreateRequest(BaseModel):
    reviewId: int
    content: str


class ReviewCommentCreateResponse(BaseModel):
    commentId: int
    reviewId: int
    userId: int
    userNickname: str
    content: str
    createdAt: datetime


class ReviewDeleteRequest(BaseModel):
    reviewId: int


class ReviewCommentDeleteRequest(BaseModel):
    commentId: int


# User Detail Schemas
class UserDetailReviewItem(BaseModel):
    reviewId: int
    movieId: int
    movieTitle: str
    rating: Optional[float] = None
    content: str
    createdAt: datetime


class UserDetailResponse(BaseModel):
    userId: int
    nickname: str
    email: str
    profileImage: Optional[str] = None
    bio: Optional[str] = None
    reviewCount: int
    commentCount: int
    joinedAt: datetime
    reviews: List[UserDetailReviewItem] = []


# Auth Token
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Email Verification Schemas
class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationConfirmRequest(BaseModel):
    email: EmailStr
    code: str


class EmailVerificationStatusResponse(BaseModel):
    verified: bool


# Ranking Schemas
class MovieRankingItem(BaseModel):
    rank: int
    id: int
    title: str
    posterUrl: Optional[str] = None
    genres: List[str] = []
    averageRating: float
    releaseDate: Optional[date] = None
    reviewCount: int


class MovieRankingResponse(BaseModel):
    movies: List[MovieRankingItem]


# Comment Schemas
class CommentReplyItem(BaseModel):
    commentId: int
    reviewId: int
    userId: int
    userNickname: str
    content: str
    createdAt: datetime


class CommentListItem(BaseModel):
    commentId: int
    reviewId: int
    userId: int
    userNickname: str
    content: str
    createdAt: datetime
    replies: List[CommentReplyItem] = []


class CommentListResponse(BaseModel):
    comments: List[CommentListItem]


class CommentListRequest(BaseModel):
    reviewId: int


class ReplyCreateRequest(BaseModel):
    commentId: int
    content: str


class ReplyCreateResponse(BaseModel):
    commentId: int
    parentCommentId: int
    reviewId: int
    userId: int
    userNickname: str
    content: str
    createdAt: datetime


class ReplyDeleteRequest(BaseModel):
    commentId: int


# Favorite Schemas
class FavoriteToggleRequest(BaseModel):
    movieId: int


class FavoriteItem(BaseModel):
    movieId: int
    title: str
    posterUrl: Optional[str] = None
    createdAt: datetime


class FavoriteListResponse(BaseModel):
    favorites: List[FavoriteItem]


# Admin Schemas
class AdminUserResponse(BaseModel):
    uid: int
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


class AdminUserUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None


class AdminMovieCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    director: Optional[str] = None
    posterUrl: Optional[str] = None
    releaseDate: Optional[str] = None
    genres: List[str] = []


class AdminMovieUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    director: Optional[str] = None
    posterUrl: Optional[str] = None
    releaseDate: Optional[str] = None


class TMDBImportRequest(BaseModel):
    tmdbUrl: str
