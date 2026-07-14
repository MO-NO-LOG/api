from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# User Schemas
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str
    nickname: str
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(None, pattern=r"^[MFO]$")
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
    gender: Optional[str] = Field(None, pattern=r"^[MFO]$")
    img: Optional[str] = None


# Movie Schemas
class MovieResponseItem(BaseModel):
    id: int
    title: str
    posterUrl: Optional[str] = None
    genres: List[str] = []
    averageRating: float
    releaseDate: Optional[date] = None

    @classmethod
    def from_movie(cls, movie, average_rating: float = 0.0) -> "MovieResponseItem":
        return cls(
            id=movie.mid,
            title=movie.title,
            posterUrl=movie.poster_url,
            genres=sorted({g.genre.name for g in movie.genres if g.genre}),
            averageRating=average_rating,
            releaseDate=movie.release_date,
        )


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
    rating: float = Field(..., ge=0, le=5)


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

    @classmethod
    def from_movie(cls, rank: int, movie, review_count: int = 0, average_rating: float = 0.0) -> "MovieRankingItem":
        return cls(
            rank=rank,
            id=movie.mid,
            title=movie.title,
            posterUrl=movie.poster_url,
            genres=sorted({g.genre.name for g in movie.genres if g.genre}),
            averageRating=average_rating,
            releaseDate=movie.release_date,
            reviewCount=review_count,
        )


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


# Favorite Schemas
class FavoriteToggleRequest(BaseModel):
    movieId: int


class FavoriteItem(BaseModel):
    movieId: int
    title: str
    posterUrl: Optional[str] = None
    createdAt: datetime

    @classmethod
    def from_favorite(cls, favorite) -> "FavoriteItem":
        return cls(
            movieId=favorite.mid,
            title=favorite.movie.title,
            posterUrl=favorite.movie.poster_url,
            createdAt=favorite.created_at,
        )


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

    @classmethod
    def from_user(cls, user, review_count: int = 0) -> "AdminUserResponse":
        return cls(
            uid=user.uid,
            nickname=user.nickname,
            email=user.email,
            img=user.img,
            bio=user.bio,
            gender=user.gender,
            createdAt=user.created_at,
            reviewCount=review_count,
        )


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

    @classmethod
    def from_movie(cls, movie, review_count: int = 0, average_rating: float = 0.0) -> "AdminMovieResponse":
        return cls(
            mid=movie.mid,
            title=movie.title,
            director=movie.director,
            posterUrl=movie.poster_url,
            releaseDate=str(movie.release_date) if movie.release_date else None,
            averageRating=average_rating,
            reviewCount=review_count,
            createdAt=movie.created_at,
        )


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

    @classmethod
    def from_review(cls, review, user, movie) -> "AdminReviewResponse":
        return cls(
            rid=review.rid,
            userId=user.uid,
            userNickname=user.nickname,
            movieId=movie.mid,
            movieTitle=movie.title,
            title=review.title,
            content=review.dec,
            rating=float(review.rat) if review.rat is not None else 0.0,
            createdAt=review.created_at,
        )


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
    releaseDate: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    genres: List[str] = []


class AdminMovieUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    director: Optional[str] = None
    posterUrl: Optional[str] = None
    releaseDate: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class TMDBImportRequest(BaseModel):
    tmdbUrl: str


class EmailVerificationSettingsResponse(BaseModel):
    enabled: bool


class EmailVerificationSettingsUpdateRequest(BaseModel):
    enabled: bool
