from app.config import settings
from app.valkey_client import get_valkey_client


class SystemSettingsService:
    EMAIL_VERIFICATION_ENABLED_KEY = "system:email_verification_enabled"

    @staticmethod
    def _parse_enabled_value(value: str | None) -> bool:
        if value is None:
            return settings.EMAIL_VERIFICATION_ENABLED
        return str(value).lower() not in ("false", "0", "disabled", "no", "off")

    @staticmethod
    async def is_email_verification_enabled() -> bool:
        try:
            client = get_valkey_client()
            value = await client.get(
                SystemSettingsService.EMAIL_VERIFICATION_ENABLED_KEY
            )
            return SystemSettingsService._parse_enabled_value(value)
        except Exception:
            return settings.EMAIL_VERIFICATION_ENABLED

    @staticmethod
    async def set_email_verification_enabled(enabled: bool) -> bool:
        try:
            client = get_valkey_client()
            await client.set(
                SystemSettingsService.EMAIL_VERIFICATION_ENABLED_KEY,
                "enabled" if enabled else "disabled",
            )
            return True
        except Exception:
            return False
