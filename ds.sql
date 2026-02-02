-- ==========================================
-- Database Schema for MO-NO-LOG
-- ==========================================
-- This SQL file is generated based on init_db.py and models.py
-- It includes DDL for table creation and sample data insertion
-- Drop tables if they exist (in reverse dependency order)
DROP TABLE IF EXISTS comment_like CASCADE;

DROP TABLE IF EXISTS review_like CASCADE;

DROP TABLE IF EXISTS comment CASCADE;

DROP TABLE IF EXISTS review CASCADE;

DROP TABLE IF EXISTS movie_genre CASCADE;

DROP TABLE IF EXISTS genre CASCADE;

DROP TABLE IF EXISTS movie CASCADE;

DROP TABLE IF EXISTS user_salt CASCADE;

DROP TABLE IF EXISTS users CASCADE;

-- ==========================================
-- Table: users
-- ==========================================
CREATE TABLE
    users (
        uid SERIAL PRIMARY KEY,
        name VARCHAR(50) NOT NULL,
        dec TEXT,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        img VARCHAR(255) DEFAULT '/images/default.png',
        gender CHAR(1) CHECK (gender IN ('M', 'F')),
        birth_date DATE,
        is_admin BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP
        WITH
            TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX idx_users_uid ON users (uid);

CREATE INDEX idx_users_email ON users (email);

-- ==========================================
-- Table: user_salt
-- ==========================================
CREATE TABLE
    user_salt (
        uid INTEGER PRIMARY KEY REFERENCES users (uid) ON DELETE CASCADE,
        salt VARCHAR(255) NOT NULL,
        created_at TIMESTAMP
        WITH
            TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        WITH
            TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

-- ==========================================
-- Table: movie
-- ==========================================
CREATE TABLE
    movie (
        mid SERIAL PRIMARY KEY,
        title VARCHAR(200) NOT NULL,
        dec TEXT,
        rat NUMERIC(2, 1) DEFAULT 0,
        release_date DATE,
        created_at TIMESTAMP
        WITH
            TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            director VARCHAR(100),
            poster_url VARCHAR(255)
    );

CREATE INDEX idx_movie_mid ON movie (mid);

-- ==========================================
-- Table: genre
-- ==========================================
CREATE TABLE
    genre (
        gid SERIAL PRIMARY KEY,
        name VARCHAR(50) UNIQUE NOT NULL
    );

CREATE INDEX idx_genre_gid ON genre (gid);

-- ==========================================
-- Table: movie_genre (Many-to-Many)
-- ==========================================
CREATE TABLE
    movie_genre (
        mid INTEGER REFERENCES movie (mid) ON DELETE CASCADE,
        gid INTEGER REFERENCES genre (gid) ON DELETE CASCADE,
        PRIMARY KEY (mid, gid)
    );

-- ==========================================
-- Table: review
-- ==========================================
CREATE TABLE
    review (
        rid SERIAL PRIMARY KEY,
        uid INTEGER NOT NULL REFERENCES users (uid) ON DELETE CASCADE,
        mid INTEGER NOT NULL REFERENCES movie (mid) ON DELETE CASCADE,
        title VARCHAR(200),
        dec TEXT NOT NULL,
        rat NUMERIC(2, 1) CHECK (
            rat >= 1
            AND rat <= 5
        ),
        created_at TIMESTAMP
        WITH
            TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX idx_review_rid ON review (rid);

-- ==========================================
-- Table: comment
-- ==========================================
CREATE TABLE
    comment (
        cid SERIAL PRIMARY KEY,
        rid INTEGER NOT NULL REFERENCES review (rid) ON DELETE CASCADE,
        uid INTEGER NOT NULL REFERENCES users (uid) ON DELETE CASCADE,
        dec TEXT NOT NULL,
        created_at TIMESTAMP
        WITH
            TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX idx_comment_cid ON comment (cid);

-- ==========================================
-- Table: review_like
-- ==========================================
CREATE TABLE
    review_like (
        lid SERIAL PRIMARY KEY,
        rid INTEGER NOT NULL REFERENCES review (rid) ON DELETE CASCADE,
        uid INTEGER NOT NULL REFERENCES users (uid) ON DELETE CASCADE,
        type CHAR(1) CHECK (type IN ('L', 'D')),
        created_at TIMESTAMP
        WITH
            TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX idx_review_like_lid ON review_like (lid);

-- ==========================================
-- Table: comment_like
-- ==========================================
CREATE TABLE
    comment_like (
        lid SERIAL PRIMARY KEY,
        cid INTEGER NOT NULL REFERENCES comment (cid) ON DELETE CASCADE,
        uid INTEGER NOT NULL REFERENCES users (uid) ON DELETE CASCADE,
        type CHAR(1) CHECK (type IN ('L', 'D')),
        created_at TIMESTAMP
        WITH
            TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX idx_comment_like_lid ON comment_like (lid);
