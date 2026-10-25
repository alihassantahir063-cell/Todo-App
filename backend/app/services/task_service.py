from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.pagination import paginate


def owned_task(db: Session, task_id: int, user_id: int) -> Task | None:
    return db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user_id))


def create_task(db: Session, user: User, payload: TaskCreate) -> Task:
    task = Task(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
        reminder_at=payload.reminder_at,
        user_id=user.id,
        status=TaskStatus.PENDING,
        completed_at=None,
    )
    db.add(task)
    db.flush()
    return task


def list_tasks(
    db: Session,
    user_id: int,
    *,
    search: str | None,
    status_filter: str,
    priority: TaskPriority | None,
    sort_by: str,
    order: str,
    page: int,
    page_size: int,
    due_date_from: date | None = None,
    due_date_to: date | None = None,
) -> dict:
    statement = select(Task).where(Task.user_id == user_id)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(Task.title.ilike(pattern) | Task.description.ilike(pattern))
    if status_filter != "all":
        statement = statement.where(Task.status == TaskStatus(status_filter))
    if priority:
        statement = statement.where(Task.priority == priority)
    if due_date_from:
        statement = statement.where(Task.due_date >= due_date_from)
    if due_date_to:
        statement = statement.where(Task.due_date <= due_date_to)
    sort_column = {
        "created_at": Task.created_at,
        "due_date": Task.due_date,
        "priority": case(
            (Task.priority == TaskPriority.LOW, 1),
            (Task.priority == TaskPriority.MEDIUM, 2),
            (Task.priority == TaskPriority.HIGH, 3),
        ),
    }[sort_by]
    sort_expression = sort_column.asc() if order == "asc" else sort_column.desc()
    statement = statement.order_by(sort_expression, Task.id.asc())
    return paginate(db, statement, page, page_size)


def task_stats(db: Session, user_id: int, *, today: date | None = None) -> dict:
    today = today or date.today()
    total = db.scalar(select(func.count(Task.id)).where(Task.user_id == user_id)) or 0
    pending = db.scalar(
        select(func.count(Task.id)).where(Task.user_id == user_id, Task.status == TaskStatus.PENDING)
    ) or 0
    completed = db.scalar(
        select(func.count(Task.id)).where(Task.user_id == user_id, Task.status == TaskStatus.COMPLETED)
    ) or 0
    overdue = db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.status == TaskStatus.PENDING,
            Task.due_date < today,
        )
    ) or 0
    return {
        "total": total,
        "pending": pending,
        "completed": completed,
        "overdue": overdue,
        "completion_percentage": round(completed / total * 100, 2) if total else 0.0,
    }


def due_reminders(db: Session, user_id: int, *, now: datetime | None = None) -> list[Task]:
    now = now or datetime.now(timezone.utc)
    reminder_window_start = now - timedelta(days=7)
    return list(
        db.scalars(
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.status == TaskStatus.PENDING,
                Task.reminder_at <= now,
                Task.reminder_at >= reminder_window_start,
            )
            .order_by(Task.reminder_at.desc(), Task.id.asc())
            .limit(100)
        )
    )


def update_task(db: Session, task: Task, payload: TaskUpdate) -> Task:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    task.updated_at = datetime.now(timezone.utc)
    db.flush()
    return task


def toggle_task(db: Session, task: Task) -> Task:
    if task.status == TaskStatus.PENDING:
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
    else:
        task.status = TaskStatus.PENDING
        task.completed_at = None
    task.updated_at = datetime.now(timezone.utc)
    db.flush()
    return task


def admin_task_query(
    *,
    user_id: int | None,
    status_filter: str | None,
    date_from: date | None,
    date_to: date | None,
    search: str | None,
):
    statement = select(Task)
    if user_id is not None:
        statement = statement.where(Task.user_id == user_id)
    if status_filter:
        statement = statement.where(Task.status == TaskStatus(status_filter))
    if date_from:
        statement = statement.where(
            Task.created_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
        )
    if date_to:
        statement = statement.where(
            Task.created_at <= datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
        )
    if search:
        statement = statement.where(Task.title.ilike(f"%{search.strip()}%"))
    return statement.order_by(Task.created_at.desc(), Task.id.desc())
