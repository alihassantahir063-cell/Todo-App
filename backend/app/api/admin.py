from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.models.task import Task
from app.models.user import User, UserRole
from app.schemas.admin import AdminDashboard, UserStatusUpdate
from app.schemas.common import Page
from app.schemas.task import AdminTaskOut
from app.schemas.user import AdminUserOut, UserOut
from app.services.admin_service import dashboard, list_users, user_details
from app.services.pagination import paginate
from app.services.task_service import admin_task_query

router = APIRouter(prefix="/admin", tags=["administration"], dependencies=[Depends(require_admin)])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/dashboard", response_model=AdminDashboard)
def get_dashboard(db: DbSession) -> dict:
    return dashboard(db)


@router.get("/users", response_model=Page[UserOut])
def get_users(
    db: DbSession,
    search: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> dict:
    return list_users(db, search=search, role=role, is_active=is_active, page=page, page_size=page_size)


@router.get("/users/{user_id}", response_model=AdminUserOut)
def get_user(user_id: int, db: DbSession) -> dict:
    user = user_details(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/users/{user_id}/status", response_model=UserOut)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: DbSession,
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account")
    user.is_active = payload.is_active
    db.flush()
    return user


@router.get("/tasks", response_model=Page[AdminTaskOut])
def get_tasks(
    db: DbSession,
    user_id: int | None = Query(default=None, ge=1),
    status_filter: Literal["pending", "completed"] | None = Query(default=None, alias="status"),
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> dict:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="date_from must not be after date_to")
    statement = admin_task_query(
        user_id=user_id,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        search=search,
    ).options(joinedload(Task.owner))
    return paginate(db, statement, page, page_size)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: DbSession) -> Response:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    db.delete(task)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
