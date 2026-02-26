from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.middleware import (
    CsrfMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.routers import admin, auth, file, movies, ranking, reviews, user

app = FastAPI()


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": "HTTP_ERROR",
            "message": str(exc.detail),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors(),
        },
    )


# app.add_middleware(SecurityHeadersMiddleware)  # ty:ignore[invalid-argument-type]
app.add_middleware(RateLimitMiddleware)  # ty:ignore[invalid-argument-type]
app.add_middleware(CsrfMiddleware)  # ty:ignore[invalid-argument-type]

app.add_middleware(
    CORSMiddleware,  # ty:ignore[invalid-argument-type]
    allow_origins=[
        "http://localhost:4321",
        "http://localhost:8000",
        "http://localhost:5500",
        "http://127.0.0.1:4321",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "https://api.mono-log.fun",
        "https://mono-log.fun",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/api")
app.include_router(movies.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(ranking.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(file.router, prefix="/api")


@app.get("/")
def read_root():
    return {"message": "Welcome to the MONO-LOG.fun API!"}
