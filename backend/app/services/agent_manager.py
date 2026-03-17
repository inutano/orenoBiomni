import asyncio
import logging
import re
import threading
import uuid
from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

# Global state
_agent = None
_agent_ready = False
_agent_lock = asyncio.Lock()
_session_locks: dict[uuid.UUID, asyncio.Lock] = {}


def _get_session_lock(session_id: uuid.UUID) -> asyncio.Lock:
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


async def init_agent(settings) -> None:
    """Initialize the A1 agent. Called once during app startup."""
    global _agent, _agent_ready

    import os
    os.environ["OLLAMA_HOST"] = settings.ollama_base_url

    logger.info("Initializing A1 agent (model=%s, source=%s)...", settings.biomni_llm, settings.biomni_source)

    def _create():
        from biomni.agent import A1
        return A1(
            path=settings.biomni_data_path,
            llm=settings.biomni_llm,
            source=settings.biomni_source,
            base_url=settings.biomni_custom_base_url,
            api_key=settings.biomni_custom_api_key,
            expected_data_lake_files=[],
            use_tool_retriever=settings.biomni_use_tool_retriever,
            timeout_seconds=settings.biomni_timeout_seconds,
        )

    _agent = await asyncio.to_thread(_create)
    _agent_ready = True
    logger.info("A1 agent ready.")


def is_agent_ready() -> bool:
    return _agent_ready


def get_agent():
    if not _agent_ready or _agent is None:
        raise RuntimeError("Agent not initialized")
    return _agent


async def stream_chat(session_id: uuid.UUID, messages: list) -> AsyncGenerator[dict, None]:
    """Stream agent responses as structured events.

    Runs the synchronous LangGraph generator in a background thread,
    piping events through an asyncio.Queue.
    """
    agent = get_agent()
    lock = _get_session_lock(session_id)

    if lock.locked():
        yield {"event": "error", "data": {"error": "Session is already processing a request"}}
        return

    async with lock:
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def _run_stream():
            try:
                inputs = {"messages": messages, "next_step": None}
                config = {"recursion_limit": 500, "configurable": {"thread_id": str(session_id)}}
                for state in agent.app.stream(inputs, stream_mode="values", config=config):
                    if state.get("messages"):
                        last_msg = state["messages"][-1]
                        event = _parse_message_to_event(last_msg)
                        if event:
                            loop.call_soon_threadsafe(queue.put_nowait, event)
                loop.call_soon_threadsafe(queue.put_nowait, {"event": "done", "data": {}})
            except Exception as e:
                logger.exception("Agent streaming error")
                loop.call_soon_threadsafe(queue.put_nowait, {"event": "error", "data": {"error": str(e)}})
                loop.call_soon_threadsafe(queue.put_nowait, None)

        thread = threading.Thread(target=_run_stream, daemon=True)
        thread.start()

        while True:
            event = await queue.get()
            if event is None:
                break
            yield event
            if event["event"] in ("done", "error"):
                break

        thread.join(timeout=5)


def _parse_message_to_event(msg) -> dict | None:
    """Parse a LangChain message into a structured SSE event."""
    from langchain_core.messages import AIMessage, HumanMessage

    if isinstance(msg, HumanMessage):
        return None  # Don't echo back user messages

    if not isinstance(msg, AIMessage):
        return None

    content = msg.content
    if isinstance(content, list):
        content = "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") in ("text", "output_text")
        )

    # Strip think blocks
    content_stripped = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL | re.IGNORECASE).strip()

    # Check for solution
    solution_match = re.search(r"<solution>(.*?)</solution>", content_stripped, re.DOTALL | re.IGNORECASE)
    if solution_match:
        return {"event": "solution", "data": {"content": solution_match.group(1).strip()}}

    # Check for execute
    execute_match = re.search(r"<execute>(.*?)</execute>", content_stripped, re.DOTALL | re.IGNORECASE)
    if execute_match:
        return {"event": "execute", "data": {"content": execute_match.group(1).strip()}}

    # Check for observation (execution result)
    if "Execution terminated" in content or "parsing error" in content.lower():
        return {"event": "error", "data": {"content": content_stripped}}

    # General assistant message (thinking, intermediate text)
    if content_stripped:
        return {"event": "thinking", "data": {"content": content_stripped}}

    return None
