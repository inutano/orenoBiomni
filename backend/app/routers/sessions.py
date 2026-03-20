import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from ..database import get_db
from ..schemas.session import ChatRequest, SessionCreate, SessionListItem, SessionRead
from ..services import agent_manager, session_service
from ..routers.metrics import inc_chat
from ..streaming.sse import format_sse

router = APIRouter(prefix="/sessions")


async def _get_user(db: AsyncSession):
    """Placeholder: returns anonymous user until OAuth is implemented."""
    return await session_service.get_or_create_default_user(db)


@router.post("", response_model=SessionListItem, status_code=201)
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    user = await _get_user(db)
    session = await session_service.create_session(db, user.id, body.title)
    return session


@router.get("", response_model=list[SessionListItem])
async def list_sessions(limit: int = 20, offset: int = 0, db: AsyncSession = Depends(get_db)):
    user = await _get_user(db)
    return await session_service.list_sessions(db, user.id, limit, offset)


@router.get("/{session_id}", response_model=SessionRead)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    session = await session_service.get_session(db, session_id)
    if not session or not session.is_active:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    deleted = await session_service.delete_session(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")


@router.post("/{session_id}/chat")
async def chat(session_id: uuid.UUID, body: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Validate session
    session = await session_service.get_session(db, session_id)
    if not session or not session.is_active:
        raise HTTPException(status_code=404, detail="Session not found")

    if not agent_manager.is_agent_ready():
        raise HTTPException(status_code=503, detail="Agent not ready")

    # Check if session is already processing before persisting the message
    if agent_manager.is_session_busy(session_id):
        raise HTTPException(status_code=409, detail="Session is already processing a request")

    # Persist user message (only after confirming session is not busy)
    inc_chat()
    await session_service.add_message(db, session_id, role="user", content=body.message)

    # Load message history and convert to LangChain messages
    db_messages = await session_service.get_messages(db, session_id)
    from langchain_core.messages import AIMessage, HumanMessage

    lc_messages = []
    for m in db_messages:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))

    # Stream agent response
    async def event_generator():
        async for event in agent_manager.stream_chat(session_id, lc_messages):
            # Persist assistant messages to DB
            if event["event"] in ("thinking", "execute", "solution", "error") and "content" in event.get("data", {}):
                await session_service.add_message(
                    db,
                    session_id,
                    role="assistant",
                    content=event["data"]["content"],
                    message_type=event["event"],
                )
            yield event

    return EventSourceResponse(format_sse(event_generator()))
