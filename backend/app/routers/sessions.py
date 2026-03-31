import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from ..database import get_db, async_session
from ..middleware.auth import get_current_user
from ..models import User
from ..schemas.session import ChatRequest, SessionCreate, SessionListItem, SessionRead
from ..services import agent_manager, session_service
from ..routers.metrics import inc_chat
from ..streaming.sse import format_sse

logger = logging.getLogger(__name__)


class SessionUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

router = APIRouter(prefix="/sessions")


@router.post("", response_model=SessionListItem, status_code=201)
async def create_session(
    body: SessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.create_session(db, user.id, body.title)
    return session


@router.get("", response_model=list[SessionListItem])
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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


@router.patch("/{session_id}", response_model=SessionListItem)
async def update_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    updated = await session_service.update_session_title(db, session_id, body.title)
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found")
    session = await session_service.get_session(db, session_id)
    return session


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

    # Check if this is the first user message (title generation candidate)
    is_first_message = len(db_messages) == 1  # only the user message we just added

    # Stream agent response
    async def event_generator():
        solution_text = ""
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
                if event["event"] == "solution":
                    solution_text = event["data"]["content"]
            yield event

        # Generate title after the first exchange completes
        if is_first_message and session.title is None:
            asyncio.create_task(
                _generate_title(session_id, body.message, solution_text)
            )

    return EventSourceResponse(format_sse(event_generator()))


async def _generate_title(session_id: uuid.UUID, user_message: str, assistant_response: str) -> None:
    """Generate a short title for the session using the LLM."""
    try:
        from ..config import settings
        from biomni.llm import get_llm
        from langchain_core.messages import HumanMessage as HM

        llm = await asyncio.to_thread(
            get_llm,
            model=settings.biomni_llm,
            source=settings.biomni_source,
            base_url=settings.biomni_custom_base_url,
            api_key=settings.biomni_custom_api_key,
            temperature=0.3,
        )

        prompt = (
            "Generate a concise title (3-8 words) for this conversation. "
            "Return ONLY the title text, nothing else. No quotes, no punctuation at the end.\n\n"
            f"User: {user_message[:300]}\n"
            f"Assistant: {assistant_response[:500]}"
        )

        result = await asyncio.to_thread(llm.invoke, [HM(content=prompt)])
        title = result.content.strip().strip('"\'').strip()

        # Strip any <think>...</think> tags from reasoning models
        import re
        title = re.sub(r"<think(?:ing)?>.*?</think(?:ing)?>", "", title, flags=re.DOTALL).strip()

        if title and len(title) <= 255:
            async with async_session() as db:
                await session_service.update_session_title(db, session_id, title)
            logger.info("Generated title for session %s: %s", session_id, title)
        else:
            logger.warning("Title generation returned empty or too long result for session %s", session_id)
    except Exception:
        logger.exception("Failed to generate title for session %s", session_id)
