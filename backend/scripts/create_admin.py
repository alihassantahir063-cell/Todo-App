import sys
from pathlib import Path

from sqlalchemy import select

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.schemas.user import validate_password


def main() -> None:
    name = settings.admin_name.strip()
    email = settings.admin_email.strip().lower()
    password = settings.admin_password.get_secret_value()
    if (
        not name
        or name == "PLACEHOLDER_ADMIN"
        or not email
        or email == "admin@example.com"
        or not password
        or password == "PLACEHOLDER_PASSWORD"
        or password == "CHANGE_ME_BEFORE_BOOTSTRAP"
    ):
        raise SystemExit("Set ADMIN_NAME, ADMIN_EMAIL, and a strong ADMIN_PASSWORD in backend/.env before running.")
    try:
        validate_password(password)
    except ValueError as exc:
        raise SystemExit(f"ADMIN_PASSWORD is too weak: {exc}") from exc

    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            if existing.role != UserRole.ADMIN:
                raise SystemExit(f"Account {email} already exists as a non-admin; refusing to promote it implicitly.")
            print(f"Administrator {email} already exists; no changes made.")
            return

        admin = User(
            name=name,
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Administrator {email} created.")


if __name__ == "__main__":
    main()
