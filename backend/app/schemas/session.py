import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str | None = None


class MessageRead(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    message_type: str | None = None
    metadata_: dict | None = None
    sequence_num: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionRead(BaseModel):
    id: uuid.UUID
    title: str | None
    agent_config: dict | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead] = []

    model_config = {"from_attributes": True}


class SessionListItem(BaseModel):
    id: uuid.UUID
    title: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=32768)
