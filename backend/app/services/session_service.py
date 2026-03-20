import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..models import Message, Session, User


async def get_or_create_default_user(db: AsyncSession) -> User:
    """Get or create a default anonymous user (until OAuth is implemented)."""
    result = await db.execute(select(User).where(User.email == "anonymous@local"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email="anonymous@local", display_name="Anonymous", provider="anonymous")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def create_session(db: AsyncSession, user_id: uuid.UUID, title: str | None = None) -> Session:
    session = Session(
        user_id=user_id,
        title=title,
        agent_config={"llm": settings.biomni_llm, "source": settings.biomni_source},
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def list_sessions(db: AsyncSession, user_id: uuid.UUID, limit: int = 20, offset: int = 0) -> list[Session]:
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id, Session.is_active.is_(True))
        .order_by(Session.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> Session | None:
    result = await db.execute(
        select(Session).where(Session.id == session_id).options(selectinload(Session.messages))
    )
    return result.scalar_one_or_none()


async def delete_session(db: AsyncSession, session_id: uuid.UUID) -> bool:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        return False
    session.is_active = False
    await db.commit()
    return True


async def add_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    role: str,
    content: str,
    message_type: str | None = None,
    metadata: dict | None = None,
) -> Message:
    # Lock the session row to serialize concurrent add_message calls,
    # preventing duplicate sequence numbers from SELECT MAX + INSERT race.
    await db.execute(
        select(Session.id).where(Session.id == session_id).with_for_update()
    )

    # Get next sequence number (safe under row lock)
    result = await db.execute(
        select(func.coalesce(func.max(Message.sequence_num), 0)).where(Message.session_id == session_id)
    )
    next_seq = result.scalar() + 1

    message = Message(
        session_id=session_id,
        role=role,
        content=content,
        message_type=message_type,
        metadata_=metadata,
        sequence_num=next_seq,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_messages(db: AsyncSession, session_id: uuid.UUID) -> list[Message]:
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.sequence_num)
    )
    return list(result.scalars().all())
