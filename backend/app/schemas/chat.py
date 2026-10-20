from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None


class ChatAction(BaseModel):
    type: str
    items: list[dict] | None = None
    data: dict | None = None


class ChatMessageResponse(BaseModel):
    conversation_id: UUID
    reply: str
    actions: list[ChatAction] = Field(default_factory=list)


class ChatMessageOut(BaseModel):
    role: str
    content: str | None
    created_at: str
