"""
DB에 예시 데이터를 추가하는 스크립트

Usage:
    uv run python scripts/seed_data.py
"""

import os
import sys
from datetime import date

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Comment,
    CommentLike,
    Genre,
    Movie,
    MovieGenre,
    Review,
    ReviewLike,
    User,
)
from app.utils import get_password_hash


# =========================
# USERS
# =========================
def seed_users(db: Session):
    """사용자 예시 데이터 추가"""
    print("Adding sample users...")

    users_data = [
        {
            "name": "관리자",
            "nickname": "admin",
            "email": "admin@mono-log.com",
            "password": get_password_hash("admin1234"),
            "img": "",
            "bio": "MO-NO-LOG 관리자입니다.",
            "gender": "M",
            "is_admin": True,
        },
        {
            "name": "김영화",
            "nickname": "movie_lover",
            "email": "kim@example.com",
            "password": get_password_hash("password123"),
            "img": "",
            "bio": "영화를 사랑하는 평범한 직장인입니다.",
            "gender": "F",
            "is_admin": False,
        },
        {
            "name": "박리뷰",
            "nickname": "reviewer_park",
            "email": "park@example.com",
            "password": get_password_hash("password123"),
            "img": "",
            "bio": "주말마다 영화관을 찾는 영화 매니아입니다.",
            "gender": "M",
            "is_admin": False,
        },
        {
            "name": "이시네마",
            "nickname": "cinema_lee",
            "email": "lee@example.com",
            "password": get_password_hash("password123"),
            "img": "",
            "bio": "고전 영화부터 최신작까지 두루 섭렵합니다.",
            "gender": "F",
            "is_admin": False,
        },
        {
            "name": "최영상",
            "nickname": "film_choi",
            "email": "choi@example.com",
            "password": get_password_hash("password123"),
            "img": "",
            "bio": "영화 제작 공부 중인 학생입니다.",
            "gender": "M",
            "is_admin": False,
        },
    ]

    users = []
    for user_data in users_data:
        user = User(**user_data)
        db.add(user)
        users.append(user)

    db.commit()
    print(f"✓ Added {len(users)} users")
    return users


# =========================
# GENRES
# =========================
def seed_genres(db: Session):
    """장르 예시 데이터 추가"""
    print("Adding sample genres...")

    genre_names = [
        "액션",
        "코미디",
        "드라마",
        "SF",
        "스릴러",
        "공포",
        "로맨스",
        "애니메이션",
        "판타지",
        "미스터리",
        "범죄",
        "모험",
        "다큐멘터리",
        "전쟁",
        "뮤지컬",
    ]

    genres = []
    for name in genre_names:
        genre = Genre(name=name)
        db.add(genre)
        genres.append(genre)

    db.commit()
    print(f"✓ Added {len(genres)} genres")
    return genres


# =========================
# MOVIES (포스터 경로는 저장소 파일명에 정확히 맞춤)
# =========================
def seed_movies(db: Session, genres: list):
    print("Adding sample movies...")

    # 주의: poster_url 값은 저장소의 실제 파일명(공백/온점/한글 포함)과 정확히 일치해야 합니다.
    movies_data = [
        {
            "title": "인셉션",
            "dec": "꿈 속의 꿈을 통해 타인의 잠재의식에 침투하는 특수 요원들의 이야기",
            "rat": 4.5,
            "release_date": date(2010, 7, 21),
            "director": "크리스토퍼 놀란",
            "poster_url": "/images/posters/12. 인셉션.webp",
            "genre_names": ["SF", "액션", "스릴러"],
        },
        {
            "title": "기생충",
            "dec": "전원 백수인 기택 가족이 부유한 박 사장 가족에게 기생하며 벌어지는 이야기",
            "rat": 4.8,
            "release_date": date(2019, 5, 30),
            "director": "봉준호",
            "poster_url": "/images/posters/7. 기생충.webp",
            "genre_names": ["드라마", "스릴러", "코미디"],
        },
        {
            "title": "인터스텔라",
            "dec": "황폐해진 지구를 떠나 인류의 새로운 보금자리를 찾는 우주 탐사대의 모험",
            "rat": 4.6,
            "release_date": date(2014, 11, 6),
            "director": "크리스토퍼 놀란",
            "poster_url": "/images/posters/13. 인터스텔라.webp",
            "genre_names": ["SF", "모험", "드라마"],
        },
        {
            "title": "포레스트 검프",
            "dec": "불편한 다리, 남들보다 조금 떨어지는 지능을 가진 외톨이 소년 포레스트 검프. 헌신적이고 강인한 어머니의 보살핌과 콩깍지 첫사랑 소녀 제니와의 만남으로 사회의 편견과 괴롭힘 속에서도 따뜻하고 순수한 마음을 지니고 성장한다. 여느 날과 같이 또래들의 괴롭힘을 피해 도망치던 포레스트는 누구보다 빠르게 달릴 수 있는 자신의 재능을 깨닫고 늘 달리는 삶을 살아간다. 포레스트의 재능을 발견한 대학에서 그를 미식축구 선수로 발탁하고, 졸업 후에도 뛰어난 신체능력으로 군에 들어가 누구도 예상치 못한 성과를 거둬 무공훈장을 수여받는 등 탄탄한 인생 가도에 오르게 된 포레스트. 하지만 영원히 행복할 것만 같았던 시간도 잠시, 어머니가 병에 걸려 죽음을 맞이하고 첫사랑 제니 역시 그의 곁을 떠나가며 다시 한번 인생의 전환점을 맞이하게 되는데… 과연, 포레스트는 진정한 삶의 행복을 발견할 수 있을까?",
            "rat": 4.1,
            "release_date": date(1994, 10, 15),
            "director": "로버트 저메키스",
            "poster_url": "/images/imgnum/34.webp",
            "genre_names": ["멜로/로맨스", "서사/드라마", "코미디"],
        },
        {
            "title": "어벤져스: 엔드게임",
            "dec": "타노스에게 패배한 어벤져스가 다시 모여 최후의 반격을 시도하는 이야기",
            "rat": 4.4,
            "release_date": date(2019, 4, 24),
            "director": "앤서니 루소, 조 루소",
            "poster_url": "/images/posters/10. 어벤져스 엔드게임.webp",
            "genre_names": ["액션", "SF", "모험"],
        },
        {
            "title": "조커",
            "dec": "코미디언을 꿈꾸던 한 남자가 광기 어린 악당 조커로 변해가는 과정",
            "rat": 4.2,
            "release_date": date(2019, 10, 2),
            "director": "토드 필립스",
            "poster_url": "/images/imgnum/47.webp",
            "genre_names": ["드라마", "스릴러", "범죄"],
        },
        {
            "title": "센과 치히로의 행방불명",
            "dec": "신들의 세계로 들어간 소녀 치히로가 부모를 구하기 위해 고군분투하는 판타지 애니메이션",
            "rat": 4.7,
            "release_date": date(2001, 7, 20),
            "director": "미야자키 하야오",
            "poster_url": "/images/posters/5. 센과 치히로의 행방불명.webp",
            "genre_names": ["애니메이션", "판타지", "모험"],
        },
        {
            "title": "다크 나이트",
            "dec": "배트맨과 조커의 대결을 그린 배트맨 시리즈의 두 번째 작품",
            "rat": 4.6,
            "release_date": date(2008, 7, 18),
            "director": "크리스토퍼 놀란",
            "poster_url": "/images/imgnum/28.webp",
            "genre_names": ["액션", "범죄", "드라마"],
        },
        {
            "title": "쇼생크 탈출",
            "dec": "억울하게 누명을 쓴 은행가가 교도소에서 희망을 잃지 않고 탈출을 준비하는 이야기",
            "rat": 4.9,
            "release_date": date(1994, 9, 23),
            "director": "프랭크 다라본트",
            "poster_url": "/images/imgnum/40.webp",
            "genre_names": ["드라마"],
        },
        {
            "title": "아바타: 불과 재",
            "dec": "인간들과의 전쟁으로 첫째 아들 ‘네테이얌’을 잃은 후, ‘제이크’와 ‘네이티리’는 깊은 슬픔에 빠진다. 상실에 빠진 이들 앞에 '바랑'이 이끄는 재의 부족이 등장하면서, 판도라는 더욱 큰 위험에 빠지게 되고, ‘설리’ 가족은 선택의 기로에 서게 되는데...",
            "rat": 3.5,
            "release_date": date(2025, 12, 17),
            "director": "제임스 카메론",
            "poster_url": "/images/imgnum/32.webp",
            "genre_names": ["SF", "액션", "어드벤처"],
        },
    ]

    genre_dict = {g.name: g for g in genres}

    movies = []
    for data in movies_data:
        genre_names = data.pop("genre_names")
        movie = Movie(**data)
        db.add(movie)
        db.flush()

        for gname in genre_names:
            if gname in genre_dict:
                db.add(MovieGenre(mid=movie.mid, gid=genre_dict[gname].gid))

        movies.append(movie)

    db.commit()
    print(f"✓ Added {len(movies)} movies")
    return movies


# =========================
# REVIEWS / COMMENTS / LIKES (간단 샘플 — 원하면 더 추가)
# =========================
def seed_reviews(db: Session, users: list, movies: list):
    print("Adding sample reviews...")

    reviews_data = [
        {
            "user_idx": 1,  # movie_lover
            "movie_idx": 0,  # 인셉션
            "title": "꿈과 현실의 경계를 허무는 걸작",
            "dec": "크리스토퍼 놀란의 상상력이 빛나는 작품입니다. 복잡한 구조임에도 불구하고 긴장감을 유지합니다.",
            "rat": 5.0,
        },
        {
            "user_idx": 2,
            "movie_idx": 1,
            "title": "한국 영화의 자랑스러운 걸작",
            "dec": "봉준호 감독의 연출이 돋보입니다.",
            "rat": 5.0,
        },
    ]

    reviews = []
    for r in reviews_data:
        user_idx = r.pop("user_idx")
        movie_idx = r.pop("movie_idx")
        review = Review(uid=users[user_idx].uid, mid=movies[movie_idx].mid, **r)
        db.add(review)
        reviews.append(review)

    db.commit()
    print(f"✓ Added {len(reviews)} reviews")
    return reviews


def seed_comments(db: Session, users: list, reviews: list):
    print("Adding sample comments...")

    comments_data = [
        {"review_idx": 0, "user_idx": 2, "dec": "정말 공감되는 리뷰네요!"},
        {"review_idx": 1, "user_idx": 1, "dec": "정말 훌륭한 작품이에요."},
    ]

    comments = []
    for c in comments_data:
        review_idx = c.pop("review_idx")
        user_idx = c.pop("user_idx")
        comment = Comment(rid=reviews[review_idx].rid, uid=users[user_idx].uid, **c)
        db.add(comment)
        comments.append(comment)

    db.commit()
    print(f"✓ Added {len(comments)} comments")
    return comments


def seed_likes(db: Session, users: list, reviews: list, comments: list):
    print("Adding sample likes...")

    # 아주 간단 샘플
    review_like = ReviewLike(rid=reviews[0].rid, uid=users[2].uid, type="L")
    db.add(review_like)

    comment_like = CommentLike(cid=comments[0].cid, uid=users[1].uid, type="L")
    db.add(comment_like)

    db.commit()
    print("✓ Added sample likes")


# =========================
# MAIN
# =========================
def seed_all():
    print("=" * 50)
    print("Starting DB seeding...")
    print("=" * 50)

    db = SessionLocal()
    try:
        users = seed_users(db)
        genres = seed_genres(db)
        movies = seed_movies(db, genres)
        reviews = seed_reviews(db, users, movies)
        comments = seed_comments(db, users, reviews)
        seed_likes(db, users, reviews, comments)

        print("=" * 50)
        print("✅ Seeding completed successfully!")
        print("=" * 50)
        print("\n샘플 로그인 정보:")
        print("  관리자: admin@mono-log.com / admin1234")
        print("  일반 사용자: kim@example.com / password123")
        print("=" * 50)

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
