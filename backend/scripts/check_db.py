import sys
import secrets
from pathlib import Path

from sqlalchemy import select

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User, UserRole


def main() -> None:
    with SessionLocal() as db:
        user = User(
            name="Database Verification",
            email="db-check@example.invalid",
            hashed_password=hash_password(secrets.token_urlsafe(24)),
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.flush()
        task = Task(
            title="Verify database models",
            description="Temporary row created by scripts/check_db.py",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            user_id=user.id,
        )
        db.add(task)
        db.flush()

        verified_user = db.scalar(select(User).where(User.id == user.id))
        verified_task = db.scalar(select(Task).where(Task.id == task.id))
        if verified_user is None or verified_task is None or verified_task.owner.id != user.id:
            raise RuntimeError("The test rows could not be read back with their relationship intact.")
        print(f"Verified user {verified_user.email} and task {verified_task.title}.")

        db.delete(task)
        db.delete(user)
        db.commit()
        print("Temporary user and task removed.")


if __name__ == "__main__":
    main()
