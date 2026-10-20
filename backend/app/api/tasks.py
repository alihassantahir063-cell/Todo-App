from typing import Annotated, Literal
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.task import Task, TaskPriority
from app.models.user import User
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskOut, TaskStats, TaskUpdate
from app.services.task_service import create_task, list_tasks, owned_task, task_stats, toggle_task, update_task

router = APIRouter(prefix="/tasks", tags=["tasks"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def find_owned_or_404(db: Session, task_id: int, user_id: int) -> Task:
    task = owned_task(db, task_id, user_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create(payload: TaskCreate, current_user: CurrentUser, db: DbSession) -> Task:
    return create_task(db, current_user, payload)


@router.get("", response_model=Page[TaskOut])
def list_mine(
    current_user: CurrentUser,
    db: DbSession,
    search: str | None = None,
    status_filter: Literal["all", "pending", "completed"] = Query(default="all", alias="status"),
    priority: TaskPriority | None = None,
    sort_by: Literal["created_at", "due_date", "priority"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    due_date_from: date | None = None,
    due_date_to: date | None = None,
) -> dict:
    if due_date_from and due_date_to and due_date_from > due_date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="due_date_from must not be after due_date_to",
        )
    return list_tasks(
        db,
        current_user.id,
        search=search,
        status_filter=status_filter,
        priority=priority,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
    )


@router.get("/stats", response_model=TaskStats)
def stats(current_user: CurrentUser, db: DbSession) -> dict:
    return task_stats(db, current_user.id)


@router.get("/{task_id}", response_model=TaskOut)
def get_one(task_id: int, current_user: CurrentUser, db: DbSession) -> Task:
    return find_owned_or_404(db, task_id, current_user.id)


@router.patch("/{task_id}", response_model=TaskOut)
def update(task_id: int, payload: TaskUpdate, current_user: CurrentUser, db: DbSession) -> Task:
    task = find_owned_or_404(db, task_id, current_user.id)
    return update_task(db, task, payload)


@router.patch("/{task_id}/toggle", response_model=TaskOut)
def toggle(task_id: int, current_user: CurrentUser, db: DbSession) -> Task:
    return toggle_task(db, find_owned_or_404(db, task_id, current_user.id))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(task_id: int, current_user: CurrentUser, db: DbSession) -> Response:
    task = find_owned_or_404(db, task_id, current_user.id)
    db.delete(task)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
