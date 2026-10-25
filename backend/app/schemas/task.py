from datetime import date, datetime

from pydantic import Field, field_validator

from app.models.task import TaskPriority, TaskStatus
from app.schemas.common import ORMModel
from app.schemas.user import UserOut


class TaskCreate(ORMModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None
    reminder_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be blank")
        return value

    @field_validator("reminder_at")
    @classmethod
    def require_timezone_for_reminder(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Reminder time must include a timezone")
        return value


class TaskUpdate(ORMModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    reminder_at: datetime | None = None

    @field_validator("title", "priority", mode="before")
    @classmethod
    def reject_null_nonnullable_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("This field cannot be null")
        return value

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be blank")
        return value

    @field_validator("reminder_at")
    @classmethod
    def require_timezone_for_reminder(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Reminder time must include a timezone")
        return value


class TaskOut(ORMModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    reminder_at: datetime | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    user_id: int


class AdminTaskOut(TaskOut):
    owner: UserOut | None = None


class TaskStats(ORMModel):
    total: int
    pending: int
    completed: int
    overdue: int
    completion_percentage: float
