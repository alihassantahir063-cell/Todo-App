from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.services.pagination import paginate


def dashboard(db: Session) -> dict:
    total_users = db.scalar(select(func.count(User.id))) or 0
    active_users = db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
    total_tasks = db.scalar(select(func.count(Task.id))) or 0
    completed_tasks = db.scalar(
        select(func.count(Task.id)).where(Task.status == TaskStatus.COMPLETED)
    ) or 0
    pending_tasks = db.scalar(
        select(func.count(Task.id)).where(Task.status == TaskStatus.PENDING)
    ) or 0
    recent_users = list(db.scalars(select(User).order_by(User.created_at.desc(), User.id.desc()).limit(5)).all())
    recent_tasks = list(
        db.scalars(
            select(Task).options(joinedload(Task.owner)).order_by(Task.created_at.desc(), Task.id.desc()).limit(5)
        ).unique().all()
    )
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "recent_users": recent_users,
        "recent_tasks": recent_tasks,
    }


def list_users(
    db: Session,
    *,
    search: str | None,
    role: UserRole | None,
    is_active: bool | None,
    page: int,
    page_size: int,
) -> dict:
    statement = select(User)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(User.name.ilike(pattern) | User.email.ilike(pattern))
    if role:
        statement = statement.where(User.role == role)
    if is_active is not None:
        statement = statement.where(User.is_active.is_(is_active))
    return paginate(db, statement.order_by(User.created_at.desc(), User.id.desc()), page, page_size)


def user_details(db: Session, user_id: int) -> dict | None:
    user = db.get(User, user_id)
    if user is None:
        return None
    counts = db.execute(
        select(
            func.count(Task.id),
            func.count(Task.id).filter(Task.status == TaskStatus.COMPLETED),
        ).where(Task.user_id == user_id)
    ).one()
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "task_count": counts[0],
        "completed_task_count": counts[1],
    }
