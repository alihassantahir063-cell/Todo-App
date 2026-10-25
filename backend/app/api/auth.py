import hashlib
import hmac
import logging
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.schemas.user import (
    PasswordChange,
    PasswordRecovery,
    PasswordReset,
    PasswordResetRequest,
    RecoveryCodeCreate,
    UserCreate,
    UserLogin,
    UserOut,
    UserProfileUpdate,
)
from app.services.email_service import send_password_reset_email, smtp_is_configured
from app.services.auth_service import authenticate_user, get_user_by_email, register_user

router = APIRouter(prefix="/auth", tags=["authentication"])
limiter = Limiter(key_func=get_remote_address)
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
logger = logging.getLogger(__name__)
PASSWORD_RESET_MESSAGE = "If an active account exists for that email, password reset instructions will be sent."


def deliver_password_reset_email(email: str, reset_url: str) -> None:
    try:
        send_password_reset_email(email, reset_url)
    except (OSError, RuntimeError, smtplib.SMTPException, TimeoutError, ValueError):
        logger.exception("Failed to deliver password reset email")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("8/minute")
def register(request: Request, payload: UserCreate, db: DbSession) -> User:
    if get_user_by_email(db, str(payload.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    try:
        return register_user(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists") from exc


@router.post("/login")
@limiter.limit("8/minute")
def login(request: Request, response: Response, payload: UserLogin, db: DbSession) -> dict:
    user = authenticate_user(db, str(payload.email), payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect")
    token = create_access_token(user.id)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return {"user": UserOut.model_validate(user)}


@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(
    request: Request,
    payload: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
) -> dict[str, str]:
    if not smtp_is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset email is not configured. Set the SMTP settings in the backend environment.",
        )

    user = get_user_by_email(db, str(payload.email))
    if user is None or not user.is_active:
        return {"message": PASSWORD_RESET_MESSAGE}

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    db.add(
        PasswordResetToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
    )
    db.commit()

    reset_url = f"{settings.frontend_origin.rstrip('/')}/reset-password#{urlencode({'token': raw_token})}"
    background_tasks.add_task(deliver_password_reset_email, user.email, reset_url)
    return {"message": PASSWORD_RESET_MESSAGE}


@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, payload: PasswordReset, db: DbSession) -> Response:
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    reset_token = db.scalar(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
        .with_for_update()
    )
    if reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid or expired. Request a new link.",
        )

    user = db.get(User, reset_token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid or expired. Request a new link.",
        )
    user.hashed_password = hash_password(payload.new_password)
    user.recovery_code_hash = None
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/recovery-code")
@limiter.limit("5/minute")
def create_recovery_code(
    request: Request,
    payload: RecoveryCodeCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, str]:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    recovery_code = secrets.token_urlsafe(24)
    current_user.recovery_code_hash = hashlib.sha256(recovery_code.encode("utf-8")).hexdigest()
    db.flush()
    return {"recovery_code": recovery_code}


@router.post("/reset-with-recovery-code", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
def reset_with_recovery_code(request: Request, payload: PasswordRecovery, db: DbSession) -> Response:
    user = db.scalar(
        select(User)
        .where(User.email == str(payload.email), User.is_active.is_(True))
        .with_for_update()
    )
    provided_hash = hashlib.sha256(payload.recovery_code.encode("utf-8")).hexdigest()
    stored_hash = user.recovery_code_hash if user is not None else "0" * 64
    if user is None or user.recovery_code_hash is None or not hmac.compare_digest(provided_hash, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or recovery code is incorrect, or the account is inactive.",
        )

    user.hashed_password = hash_password(payload.new_password)
    user.recovery_code_hash = None
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    response.delete_cookie(key="access_token", path="/", httponly=True, secure=settings.cookie_secure, samesite="lax")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
def me(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(payload: UserProfileUpdate, current_user: CurrentUser, db: DbSession) -> User:
    changes = payload.model_dump(exclude_unset=True)
    if "email" in changes:
        duplicate = db.scalar(select(User).where(User.email == changes["email"], User.id != current_user.id))
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    for field, value in changes.items():
        setattr(current_user, field, value)
    db.flush()
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: PasswordChange, current_user: CurrentUser, db: DbSession) -> Response:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    current_user.recovery_code_hash = None
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == current_user.id))
    db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
