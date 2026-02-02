#!/usr/bin/env python3
"""
S3 연결 테스트 스크립트

이 스크립트는 S3 설정이 올바르게 구성되었는지 확인합니다.

사용법:
    uv run python scripts/test_s3_connection.py
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from botocore.exceptions import ClientError
except ImportError:
    ClientError = Exception  # type: ignore

from app.config import settings
from app.routers.file import (
    check_s3_object_exists,
    delete_from_s3,
    ensure_bucket_exists,
    get_s3_client,
    upload_to_s3,
)


def print_config():
    """현재 S3 설정 출력"""
    print("=" * 60)
    print("S3 Configuration")
    print("=" * 60)
    print(f"Endpoint URL:      {settings.S3_ENDPOINT_URL or '(AWS S3 default)'}")
    print(
        f"Access Key ID:     {settings.S3_ACCESS_KEY_ID[:8]}..."
        if settings.S3_ACCESS_KEY_ID
        else "Access Key ID:     (not set)"
    )
    print(
        f"Secret Access Key: {'*' * 20}"
        if settings.S3_SECRET_ACCESS_KEY
        else "Secret Access Key: (not set)"
    )
    print(f"Bucket Name:       {settings.S3_BUCKET_NAME}")
    print(f"Region:            {settings.S3_REGION}")
    print(f"Public URL:        {settings.S3_PUBLIC_URL or '(not set)'}")
    print(f"Path Style:        {settings.S3_USE_PATH_STYLE}")
    print("=" * 60)
    print()


def test_connection():
    """S3 연결 테스트"""
    print("🔌 Testing S3 connection...")
    try:
        s3_client = get_s3_client()
        # 버킷 목록 조회 (권한 확인)
        response = s3_client.list_buckets()
        print("✅ Connection successful!")
        print(f"   Found {len(response['Buckets'])} bucket(s)")
        return True
    except ClientError as e:
        print(f"❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_bucket_access():
    """버킷 접근 권한 테스트"""
    print(f"\n📦 Testing bucket access: {settings.S3_BUCKET_NAME}...")
    try:
        s3_client = get_s3_client()
        s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        print("✅ Bucket exists and accessible!")
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "404":
            print(f"⚠️  Bucket '{settings.S3_BUCKET_NAME}' does not exist")
            print("   Attempting to create bucket...")
            try:
                ensure_bucket_exists()
                print("✅ Bucket created successfully!")
                return True
            except Exception as create_error:
                print(f"❌ Failed to create bucket: {create_error}")
                return False
        elif error_code == "403":
            print(f"❌ Access denied to bucket '{settings.S3_BUCKET_NAME}'")
            print("   Check your credentials and IAM permissions")
            return False
        else:
            print(f"❌ Error accessing bucket: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_upload_download():
    """파일 업로드/다운로드 테스트"""
    print("\n📤 Testing file upload...")
    test_key = "test_file.txt"
    test_content = b"Hello, S3! This is a test file."

    try:
        # 업로드 테스트
        url = upload_to_s3(test_content, test_key, "text/plain")
        print("✅ Upload successful!")
        print(f"   URL: {url}")

        # 존재 확인 테스트
        print("\n🔍 Testing file existence check...")
        exists = check_s3_object_exists(test_key)
        if exists:
            print("✅ File exists!")
        else:
            print("❌ File not found!")
            return False

        # 다운로드 테스트
        print("\n📥 Testing file download...")
        s3_client = get_s3_client()
        response = s3_client.get_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=test_key,
        )
        downloaded_content = response["Body"].read()

        if downloaded_content == test_content:
            print("✅ Download successful and content matches!")
        else:
            print("❌ Downloaded content does not match!")
            return False

        # 삭제 테스트
        print("\n🗑️  Testing file deletion...")
        success = delete_from_s3(test_key)
        if success:
            print("✅ Deletion successful!")
        else:
            print("❌ Deletion failed!")
            return False

        # 삭제 확인
        exists_after_delete = check_s3_object_exists(test_key)
        if not exists_after_delete:
            print("✅ File confirmed deleted!")
        else:
            print("⚠️  File still exists after deletion!")

        return True

    except ClientError as e:
        print(f"❌ Test failed: {e}")
        # 정리: 테스트 파일 삭제 시도
        try:
            delete_from_s3(test_key)
        except Exception:
            pass
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        # 정리: 테스트 파일 삭제 시도
        try:
            delete_from_s3(test_key)
        except Exception:
            pass
        return False


def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("S3 Connection Test")
    print("=" * 60 + "\n")

    # 설정 출력
    print_config()

    # 필수 설정 확인
    if not settings.S3_ACCESS_KEY_ID or not settings.S3_SECRET_ACCESS_KEY:
        print("❌ S3 credentials not configured!")
        print("   Please set S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY in .env")
        sys.exit(1)

    # 테스트 실행
    tests = [
        ("Connection Test", test_connection),
        ("Bucket Access Test", test_bucket_access),
        ("Upload/Download Test", test_upload_download),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # 결과 요약
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 All tests passed! S3 is configured correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please check your S3 configuration.")
        print("   See docs/S3_STORAGE_SETUP.md for setup instructions.")
        sys.exit(1)


if __name__ == "__main__":
    main()
