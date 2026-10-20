from datetime import date

from pydantic import BaseModel

from app.models.user import UserRole
from app.schemas.task import AdminTaskOut
from app.schemas.user import UserOut


class UserStatusUpdate(BaseModel):
    is_active: bool


class AdminDashboard(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    recent_users: list[UserOut]
    recent_tasks: list[AdminTaskOut]


class AdminUserFilters(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class AdminTaskFilters(BaseModel):
    user_id: int | None = None
    status: str | None = None
    date_from: date | None = None
    date_to: date | None = None
