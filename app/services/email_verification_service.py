import asyncio
import secrets
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from app.config import settings
from app.redis_client import get_redis_client


class EmailVerificationService:
    CODE_PREFIX = "email_verification:"
    VERIFIED_PREFIX = "email_verified:"
    TEMPLATE_PATH = (
        Path(__file__).resolve().parents[1] / "templates" / "email_verification.html"
    )

    @staticmethod
    def generate_code() -> str:
        return f"{secrets.randbelow(1000000):06d}"

    @staticmethod
    async def store_verification_code(email: str, code: str, ttl_seconds: int) -> bool:
        redis_client = None
        try:
            redis_client = get_redis_client()
            key = f"{EmailVerificationService.CODE_PREFIX}{email}"
            await redis_client.setex(key, ttl_seconds, code)
            return True
        except Exception as e:
            print(f"Error storing verification code: {e}")
            return False
        finally:
            if redis_client:
                await redis_client.aclose()

    @staticmethod
    async def verify_code(email: str, code: str, ttl_seconds: int) -> bool:
        redis_client = None
        try:
            redis_client = get_redis_client()
            code_key = f"{EmailVerificationService.CODE_PREFIX}{email}"
            stored_code = await redis_client.get(code_key)
            if not stored_code or stored_code != code:
                return False

            verified_key = f"{EmailVerificationService.VERIFIED_PREFIX}{email}"
            await redis_client.delete(code_key)
            await redis_client.setex(verified_key, ttl_seconds, "verified")
            return True
        except Exception as e:
            print(f"Error verifying code: {e}")
            return False
        finally:
            if redis_client:
                await redis_client.aclose()

    @staticmethod
    async def is_email_verified(email: str) -> bool:
        redis_client = None
        try:
            redis_client = get_redis_client()
            key = f"{EmailVerificationService.VERIFIED_PREFIX}{email}"
            result = await redis_client.exists(key)
            return bool(result > 0)
        except Exception as e:
            print(f"Error checking email verification: {e}")
            return False
        finally:
            if redis_client:
                await redis_client.aclose()

    @staticmethod
    async def clear_verification_code(email: str) -> bool:
        redis_client = None
        try:
            redis_client = get_redis_client()
            key = f"{EmailVerificationService.CODE_PREFIX}{email}"
            result = await redis_client.delete(key)
            return bool(result > 0)
        except Exception as e:
            print(f"Error clearing verification code: {e}")
            return False
        finally:
            if redis_client:
                await redis_client.aclose()

    @staticmethod
    async def clear_email_verified(email: str) -> bool:
        redis_client = None
        try:
            redis_client = get_redis_client()
            key = f"{EmailVerificationService.VERIFIED_PREFIX}{email}"
            result = await redis_client.delete(key)
            return bool(result > 0)
        except Exception as e:
            print(f"Error clearing email verified status: {e}")
            return False
        finally:
            if redis_client:
                await redis_client.aclose()

    @staticmethod
    def _build_email_message(to_email: str, code: str) -> EmailMessage:
        ttl_minutes = settings.EMAIL_VERIFICATION_TTL_MINUTES
        message = EmailMessage()
        message["Subject"] = "MONOLOG 이메일 인증 코드"
        message["From"] = formataddr(("MONOLOG", settings.SMTP_FROM))
        message["To"] = to_email
        message.set_content(
            "요청하신 인증 코드는 아래와 같습니다.\n"
            f"{code}\n\n"
            f"이 코드는 {ttl_minutes}분 후 만료됩니다."
        )
        html_content = EmailVerificationService._render_html_template(
            code=code, ttl_minutes=ttl_minutes
        )
        message.add_alternative(html_content, subtype="html")
        return message

    @staticmethod
    def _render_html_template(code: str, ttl_minutes: int) -> str:
        template = EmailVerificationService.TEMPLATE_PATH.read_text(encoding="utf-8")
        return template.replace("{{code}}", code).replace(
            "{{ttl_minutes}}", str(ttl_minutes)
        )

    @staticmethod
    def _send_email_sync(to_email: str, code: str) -> None:
        if not settings.SMTP_HOST or not settings.SMTP_FROM:
            raise ValueError("SMTP configuration is missing")

        message = EmailVerificationService._build_email_message(to_email, code)
        use_ssl = settings.SMTP_USE_SSL or settings.SMTP_PORT == 465
        if use_ssl:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USER and settings.SMTP_PASS:
                    server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.send_message(message)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASS:
                    server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.send_message(message)

    @staticmethod
    async def send_verification_email(to_email: str, code: str) -> None:
        await asyncio.to_thread(
            EmailVerificationService._send_email_sync, to_email, code
        )
