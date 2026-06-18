from app.valkey_client import get_valkey_client


class SystemSettingsService:
    EMAIL_VERIFICATION_ENABLED_KEY = "system:email_verification_enabled"

    @staticmethod
    async def is_email_verification_enabled() -> bool:
        valkey_client = None
        try:
            valkey_client = get_valkey_client()
            value = await valkey_client.get(
                SystemSettingsService.EMAIL_VERIFICATION_ENABLED_KEY
            )
            if value is None:
                return True
            return value.lower() not in ("false", "0", "disabled")
        except Exception:
            return True
        finally:
            if valkey_client:
                await valkey_client.aclose()

    @staticmethod
    async def set_email_verification_enabled(enabled: bool) -> bool:
        valkey_client = None
        try:
            valkey_client = get_valkey_client()
            await valkey_client.set(
                SystemSettingsService.EMAIL_VERIFICATION_ENABLED_KEY,
                "enabled" if enabled else "disabled",
            )
            return True
        except Exception:
            return False
        finally:
            if valkey_client:
                await valkey_client.aclose()
