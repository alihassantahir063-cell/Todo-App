import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import limiter
from app.chat.provider import AIProvider, ChatProviderError, get_ai_provider
from app.chat.service import run_chat
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.chat import ChatConversation, ChatMessage
from app.models.user import User
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Provider = Annotated[AIProvider, Depends(get_ai_provider)]


@router.post("/message", response_model=ChatMessageResponse)
@limiter.limit("20/minute")
def send_message(
    request: Request,
    payload: ChatMessageRequest,
    db: DbSession,
    current_user: CurrentUser,
    provider: Provider,
) -> dict:
    if not payload.message.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message cannot be blank.")
    try:
        return run_chat(db, current_user, payload.message.strip(), payload.conversation_id, provider)
    except SQLAlchemyError as exc:
        logger.error(
            "Chat database operation failed for user_id=%s error_type=%s",
            current_user.id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat could not be completed because the database is temporarily unavailable.",
        ) from exc
    except ChatProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="The AI provider is temporarily unavailable.") from exc


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> Response:
    conversation = db.scalar(
        select(ChatConversation).where(
            ChatConversation.id == str(conversation_id),
            ChatConversation.user_id == current_user.id,
        )
    )
    if conversation is not None:
        db.delete(conversation)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
