from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    test_database_url: str | None = None
    secret_key: SecretStr = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=30, gt=0)
    cookie_secure: bool = False
    frontend_origin: str = "http://localhost:5173"
    admin_name: str = "Administrator"
    admin_email: str = "admin@example.com"
    admin_password: SecretStr = SecretStr("CHANGE_ME_BEFORE_BOOTSTRAP")
    ai_provider: Literal["openai"] = "openai"
    ai_api_key: SecretStr | None = None
    ai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: int = Field(default=30, gt=0, le=30)
    default_timezone: str = "Asia/Karachi"

    @field_validator("default_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("DEFAULT_TIMEZONE must be a valid IANA timezone.") from exc
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
