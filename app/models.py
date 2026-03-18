from sqlalchemy import (
    CHAR,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = "users"

    uid = Column(Integer, primary_key=True, index=True)  # User ID
    birth_date = Column(Date, nullable=True)  # Birth Date
    nickname = Column(
        String(50), unique=True, nullable=False, index=True
    )  # Display Name
    email = Column(
        String(100), unique=True, nullable=False, index=True
    )  # Email Address
    password = Column(String(255), nullable=False)  # Hashed Password
    img = Column(String(36), default="")  # Profile Image UUID (UUIDv7)
    bio = Column(Text, nullable=True)  # User Biography
    gender = Column(
        CHAR(1),
        nullable=True,  # Gender: M, F, O (Other)
    )
    is_admin = Column(Boolean, default=False)  # Admin Privileges
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # Account Creation Timestamp

    reviews = relationship("Review", back_populates="user")  # User's Reviews
    comments = relationship("Comment", back_populates="user")  # User's Comments


class Movie(Base):
    __tablename__ = "movie"

    mid = Column(Integer, primary_key=True, index=True)  # Movie ID
    title = Column(String(200), nullable=False)  # Movie Title
    dec = Column(Text, nullable=True)  # Movie Description
    rat = Column(Numeric(2, 1), default=0)  # Average Rating
    release_date = Column(Date, nullable=True)  # Release Date
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # Record Creation Timestamp
    director = Column(String(100), nullable=True)  # Director
    poster_url = Column(String(255), nullable=True)  # Poster Image URL

    genres = relationship("MovieGenre", back_populates="movie")  # Movie Genres
    reviews = relationship("Review", back_populates="movie")  # Movie Reviews


class Genre(Base):
    __tablename__ = "genre"

    gid = Column(Integer, primary_key=True, index=True)  # Genre ID
    name = Column(String(50), unique=True, nullable=False)  # Genre Name

    movies = relationship("MovieGenre", back_populates="genre")  # Movies in this Genre


class MovieGenre(Base):
    __tablename__ = "movie_genre"

    mid = Column(
        Integer, ForeignKey("movie.mid", ondelete="CASCADE"), primary_key=True
    )  # Movie ID
    gid = Column(
        Integer, ForeignKey("genre.gid", ondelete="CASCADE"), primary_key=True
    )  # Genre ID

    movie = relationship("Movie", back_populates="genres")  # Associated Movie
    genre = relationship("Genre", back_populates="movies")  # Associated Genre


class Review(Base):
    __tablename__ = "review"

    rid = Column(Integer, primary_key=True, index=True)  # Review ID
    uid = Column(
        Integer, ForeignKey("users.uid", ondelete="CASCADE"), nullable=False
    )  # User ID
    mid = Column(
        Integer, ForeignKey("movie.mid", ondelete="CASCADE"), nullable=False
    )  # Movie ID
    title = Column(String(200), nullable=True)  # Review Title
    dec = Column(Text, nullable=False)  # Review Content
    rat = Column(Numeric(2, 1), nullable=True)  # Rating Given
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # Review Creation Timestamp

    user = relationship("User", back_populates="reviews")  # Review Author
    movie = relationship("Movie", back_populates="reviews")  # Reviewed Movie
    comments = relationship("Comment", back_populates="review")  # Review Comments
    likes = relationship("ReviewLike", back_populates="review")  # Review Likes/Dislikes


class Comment(Base):
    __tablename__ = "comment"

    cid = Column(Integer, primary_key=True, index=True)  # Comment ID
    rid = Column(
        Integer, ForeignKey("review.rid", ondelete="CASCADE"), nullable=False
    )  # Review ID
    uid = Column(
        Integer, ForeignKey("users.uid", ondelete="CASCADE"), nullable=False
    )  # User ID
    dec = Column(Text, nullable=False)  # Comment Content
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # Comment Creation Timestamp

    parent_cid = Column(
        Integer, ForeignKey("comment.cid", ondelete="CASCADE"), nullable=True
    )  # Parent Comment ID (null = top-level comment)

    review = relationship("Review", back_populates="comments")  # Associated Review
    user = relationship("User", back_populates="comments")  # Comment Author
    likes = relationship(
        "CommentLike", back_populates="comment"
    )  # Comment Likes/Dislikes
    replies = relationship(
        "Comment",
        foreign_keys="Comment.parent_cid",
        backref=backref("parent", remote_side=[cid], uselist=False),
    )  # Replies to this comment


class ReviewLike(Base):
    __tablename__ = "review_like"

    lid = Column(Integer, primary_key=True, index=True)  # Like ID
    rid = Column(
        Integer, ForeignKey("review.rid", ondelete="CASCADE"), nullable=False
    )  # Review ID
    uid = Column(
        Integer, ForeignKey("users.uid", ondelete="CASCADE"), nullable=False
    )  # User ID
    type = Column(CHAR(1), nullable=True)  # L or D
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # Review Like Creation Timestamp

    review = relationship("Review", back_populates="likes")  # Associated Review


class CommentLike(Base):
    __tablename__ = "comment_like"

    lid = Column(Integer, primary_key=True, index=True)  # Like ID
    cid = Column(
        Integer, ForeignKey("comment.cid", ondelete="CASCADE"), nullable=False
    )  # Comment ID
    uid = Column(
        Integer, ForeignKey("users.uid", ondelete="CASCADE"), nullable=False
    )  # User ID
    type = Column(CHAR(1), nullable=True)  # L or D
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # Comment Like Creation Timestamp

    comment = relationship("Comment", back_populates="likes")  # Associated Comment


class Favorite(Base):
    __tablename__ = "favorite"

    fid = Column(Integer, primary_key=True, index=True)  # Favorite ID
    uid = Column(
        Integer, ForeignKey("users.uid", ondelete="CASCADE"), nullable=False
    )  # User ID
    mid = Column(
        Integer, ForeignKey("movie.mid", ondelete="CASCADE"), nullable=False
    )  # Movie ID
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # Favorite Creation Timestamp

    __table_args__ = (UniqueConstraint("uid", "mid", name="uq_favorite_user_movie"),)

    user = relationship("User")  # User who favorited
    movie = relationship("Movie")  # Favorited Movie
