from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.models.user import UserRole
from app.schemas.common import ORMModel


def validate_password(value: str) -> str:
    if len(value) < 8 or not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
        raise ValueError("Password must be at least 8 characters and contain a letter and a number")
    return value


class UserCreate(ORMModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def enforce_password_policy(cls, value: str) -> str:
        return validate_password(value)


class UserLogin(ORMModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class UserProfileUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None

    @field_validator("name", "email", mode="before")
    @classmethod
    def reject_null_profile_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("Use an omitted field to leave this value unchanged")
        return value

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        return value.lower() if value else value


class PasswordChange(ORMModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def enforce_password_policy(cls, value: str) -> str:
        return validate_password(value)


class UserOut(ORMModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminUserOut(UserOut):
    task_count: int = 0
    completed_task_count: int = 0
