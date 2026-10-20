from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import PasswordChange, UserCreate, UserLogin, UserOut, UserProfileUpdate
from app.services.auth_service import authenticate_user, get_user_by_email, register_user

router = APIRouter(prefix="/auth", tags=["authentication"])
limiter = Limiter(key_func=get_remote_address)
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


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
    db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
