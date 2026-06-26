from app.config import settings
from app.services.base import valkey_operation


class SystemSettingsService:
    EMAIL_VERIFICATION_ENABLED_KEY = "system:email_verification_enabled"

    @staticmethod
    def _parse_enabled_value(value: str | None) -> bool:
        if value is None:
            return settings.EMAIL_VERIFICATION_ENABLED
        return str(value).lower() not in ("false", "0", "disabled", "no", "off")

    @staticmethod
    @valkey_operation
    async def is_email_verification_enabled(client) -> bool:
        try:
            value = await client.get(
                SystemSettingsService.EMAIL_VERIFICATION_ENABLED_KEY
            )
            return SystemSettingsService._parse_enabled_value(value)
        except Exception:
            return settings.EMAIL_VERIFICATION_ENABLED

    @staticmethod
    @valkey_operation
    async def set_email_verification_enabled(client, enabled: bool) -> bool:
        try:
            await client.set(
                SystemSettingsService.EMAIL_VERIFICATION_ENABLED_KEY,
                "enabled" if enabled else "disabled",
            )
            return True
        except Exception:
            return False
