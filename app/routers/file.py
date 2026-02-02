from typing import Annotated

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy.orm import Session
from uuid_extension import uuid7

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/file", tags=["file"])

# 업로드 설정
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MiB
ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".avif",
    ".tiff",
    ".tif",
}


def get_s3_client():
    """
    S3 호환 클라이언트 생성 (AWS S3, MinIO, Cloudflare R2 등 지원)

    환경 변수 설정:
    - S3_ENDPOINT_URL: S3 엔드포인트 (MinIO, R2 등 사용 시 필수, AWS S3는 None)
    - S3_ACCESS_KEY_ID: Access Key
    - S3_SECRET_ACCESS_KEY: Secret Key
    - S3_REGION: 리전 (기본값: us-east-1)
    - S3_USE_PATH_STYLE: Path-style 사용 여부 (MinIO는 True, AWS S3는 False)
    """
    s3_config = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path" if settings.S3_USE_PATH_STYLE else "virtual"},
    )

    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
        config=s3_config,
    )


def ensure_bucket_exists():
    """S3 버킷이 존재하는지 확인하고 없으면 생성"""
    s3_client = get_s3_client()
    try:
        s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "404":
            # 버킷이 없으면 생성
            try:
                if settings.S3_REGION == "us-east-1":
                    s3_client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
                else:
                    s3_client.create_bucket(
                        Bucket=settings.S3_BUCKET_NAME,
                        CreateBucketConfiguration={
                            "LocationConstraint": settings.S3_REGION
                        },
                    )

                # 버킷 정책 설정 (다운로드는 인증 없이 가능하도록)
                bucket_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "PublicRead",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{settings.S3_BUCKET_NAME}/*"],
                        }
                    ],
                }
                import json

                s3_client.put_bucket_policy(
                    Bucket=settings.S3_BUCKET_NAME,
                    Policy=json.dumps(bucket_policy),
                )
            except ClientError:
                # 버킷 생성 실패 시 무시 (이미 존재하거나 권한 문제)
                pass


def validate_image_extension(filename: str) -> bool:
    """파일 확장자 검증"""
    from pathlib import Path

    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


async def validate_file_size(file: UploadFile, max_size: int) -> bytes:
    """파일 크기 검증 및 데이터 읽기"""
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {max_size / (1024 * 1024):.1f}MiB",
        )
    return contents


def convert_to_avif(image_data: bytes, quality: int = 85) -> bytes:
    """이미지를 AVIF 포맷으로 변환"""
    from io import BytesIO

    # 이미지 열기
    img = Image.open(BytesIO(image_data))

    # RGBA 또는 RGB로 변환 (필요한 경우)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    # AVIF로 변환
    output = BytesIO()
    img.save(output, format="AVIF", quality=quality)
    return output.getvalue()


def upload_to_s3(
    file_data: bytes, object_key: str, content_type: str = "image/avif"
) -> str:
    """
    S3에 파일 업로드

    Args:
        file_data: 업로드할 파일 데이터
        object_key: S3 객체 키 (파일명)
        content_type: Content-Type 헤더

    Returns:
        업로드된 파일의 공개 URL
    """
    s3_client = get_s3_client()

    try:
        # 파일 업로드 (ACL을 public-read로 설정하여 인증 없이 다운로드 가능)
        s3_client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=object_key,
            Body=file_data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000",  # 1년 캐시
        )

        # 공개 URL 생성
        if settings.S3_PUBLIC_URL:
            # 커스텀 CDN/공개 URL 사용
            return f"{settings.S3_PUBLIC_URL.rstrip('/')}/{object_key}"
        elif settings.S3_ENDPOINT_URL:
            # 커스텀 엔드포인트 사용 (MinIO, R2 등)
            endpoint = settings.S3_ENDPOINT_URL.rstrip("/")
            if settings.S3_USE_PATH_STYLE:
                return f"{endpoint}/{settings.S3_BUCKET_NAME}/{object_key}"
            else:
                return f"{endpoint}/{object_key}"
        else:
            # AWS S3 기본 URL
            return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.S3_REGION}.amazonaws.com/{object_key}"

    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload to S3: {str(e)}",
        )


def delete_from_s3(object_key: str) -> bool:
    """
    S3에서 파일 삭제

    Args:
        object_key: 삭제할 S3 객체 키

    Returns:
        삭제 성공 여부
    """
    s3_client = get_s3_client()

    try:
        s3_client.delete_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=object_key,
        )
        return True
    except ClientError:
        return False


def check_s3_object_exists(object_key: str) -> bool:
    """
    S3에 객체가 존재하는지 확인

    Args:
        object_key: 확인할 S3 객체 키

    Returns:
        존재 여부
    """
    s3_client = get_s3_client()

    try:
        s3_client.head_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=object_key,
        )
        return True
    except ClientError:
        return False


@router.post("/profile-image")
async def upload_profile_image(
    file: Annotated[UploadFile, File(description="프로필 이미지 파일 (최대 1MiB)")],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    사용자 프로필 이미지 업로드 (S3 저장)

    - 최대 파일 크기: 1MiB
    - 허용 확장자: jpg, jpeg, png, gif, bmp, webp, avif, tiff, tif
    - 저장 형식: UUIDv7.avif
    - 업로드: 인증 필요
    - 다운로드: 인증 불필요 (공개 URL)
    """
    # 파일명 검증
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # 확장자 검증
    if not validate_image_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    try:
        # 버킷 존재 확인 (첫 업로드 시)
        ensure_bucket_exists()

        # 파일 크기 검증 및 데이터 읽기
        file_data = await validate_file_size(file, MAX_FILE_SIZE)

        # UUIDv7 생성
        file_id = uuid7()

        # AVIF로 변환
        avif_data = convert_to_avif(file_data)

        # S3 객체 키 생성
        object_key = f"profile_images/{file_id}.avif"

        # 새 파일 업로드
        upload_to_s3(avif_data, object_key, "image/avif")

        # 이전 프로필 이미지 삭제 (선택사항)
        if current_user.img:
            # S3에서 이전 이미지 삭제 (UUID로부터 객체 키 생성)
            old_object_key = f"profile_images/{current_user.img}.avif"
            delete_from_s3(old_object_key)

        # 데이터베이스 업데이트 (UUID만 저장)
        current_user.img = str(file_id)
        db.commit()
        db.refresh(current_user)

        return {
            "message": "Profile image uploaded successfully",
            "filename": f"{file_id}.avif",
            "id": str(file_id),
            "size": len(avif_data),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image: {str(e)}",
        )


@router.delete("/profile-image")
async def delete_profile_image(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    사용자 프로필 이미지 삭제 (S3에서 삭제)
    """
    if not current_user.img:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile image to delete",
        )

    # S3에서 파일 삭제 (UUID로부터 객체 키 생성)
    object_key = f"profile_images/{current_user.img}.avif"
    delete_from_s3(object_key)

    # 데이터베이스 업데이트
    current_user.img = None
    db.commit()

    return {"message": "Profile image deleted successfully"}
