from app.services.base import valkey_operation


class SystemSettingsService:
    EMAIL_VERIFICATION_ENABLED_KEY = "system:email_verification_enabled"

    @staticmethod
    @valkey_operation
    async def is_email_verification_enabled(client) -> bool:
        try:
            value = await client.get(
                SystemSettingsService.EMAIL_VERIFICATION_ENABLED_KEY
            )
            if value is None:
                return True
            return value.lower() not in ("false", "0", "disabled")
        except Exception:
            return True

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
