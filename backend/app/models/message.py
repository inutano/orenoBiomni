import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user, assistant, system, observation
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str | None] = mapped_column(String(30))  # thinking, execute, solution, observation, error
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    sequence_num: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("Session", back_populates="messages")
