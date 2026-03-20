import asyncio
import contextvars
import logging
import re
import threading
import uuid
from collections.abc import AsyncGenerator

from .monkey_patch import current_session_id

logger = logging.getLogger(__name__)

# Global state
_agent = None
_agent_ready = False
_agent_lock = asyncio.Lock()
_session_locks: dict[uuid.UUID, asyncio.Lock] = {}
_celery_patched = False


def _sanitize_error(msg: str) -> str:
    """Remove internal paths and sensitive details from error messages."""
    # Strip filesystem paths (e.g., /app/Biomni/..., /home/user/...)
    sanitized = re.sub(r"(/[\w./-]+){3,}", "<path>", msg)
    # Truncate overly long messages
    if len(sanitized) > 200:
        sanitized = sanitized[:200] + "..."
    return sanitized or "An internal error occurred"


def _get_session_lock(session_id: uuid.UUID) -> asyncio.Lock:
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


async def init_agent(settings) -> None:
    """Initialize the A1 agent. Called once during app startup."""
    global _agent, _agent_ready, _celery_patched

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

    # Apply Celery monkey-patch if Redis is available
    if settings.redis_url and not _celery_patched:
        try:
            import redis
            r = redis.from_url(settings.redis_url, socket_connect_timeout=3)
            r.ping()
            r.close()

            from .monkey_patch import patch_execution
            patch_execution()
            _celery_patched = True
        except Exception:
            logger.warning("Redis not available — code execution will run in-process (no Celery)")


def is_agent_ready() -> bool:
    return _agent_ready


def is_celery_active() -> bool:
    return _celery_patched


def get_agent():
    if not _agent_ready or _agent is None:
        raise RuntimeError("Agent not initialized")
    return _agent


def is_session_busy(session_id: uuid.UUID) -> bool:
    """Check if a session lock is currently held (i.e., a request is in progress)."""
    lock = _session_locks.get(session_id)
    return lock is not None and lock.locked()


async def stream_chat(session_id: uuid.UUID, messages: list) -> AsyncGenerator[dict, None]:
    """Stream agent responses as structured events.

    Runs the synchronous LangGraph generator in a background thread,
    piping events through an asyncio.Queue. Sets the session context
    variable so monkey-patched execution functions know which session
    to associate jobs with.
    """
    agent = get_agent()
    lock = _get_session_lock(session_id)

    if lock.locked():
        yield {"event": "error", "data": {"error": "Session is already processing a request"}}
        return

    async with lock:
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        # Set session context for the monkey-patched execution functions
        current_session_id.set(session_id)

        def _run_stream():
            try:
                inputs = {"messages": messages, "next_step": None}
                config = {"recursion_limit": 500, "configurable": {"thread_id": str(session_id)}}
                first_state = True
                seen_msg_count = 0
                for state in agent.app.stream(inputs, stream_mode="values", config=config):
                    msgs = state.get("messages", [])
                    if not msgs:
                        continue
                    if first_state:
                        # First emission contains input/historical messages — skip them all
                        seen_msg_count = len(msgs)
                        first_state = False
                        logger.debug("Initial state has %d messages, skipping", seen_msg_count)
                        continue
                    if len(msgs) <= seen_msg_count:
                        continue
                    # Process only new messages since last state
                    for new_msg in msgs[seen_msg_count:]:
                        for event in _parse_message_to_events(new_msg):
                            loop.call_soon_threadsafe(queue.put_nowait, event)
                    seen_msg_count = len(msgs)
                loop.call_soon_threadsafe(queue.put_nowait, {"event": "done", "data": {}})
            except Exception as e:
                logger.exception("Agent streaming error")
                # Sanitize error: don't expose internal paths or stack traces to clients
                safe_msg = _sanitize_error(str(e))
                loop.call_soon_threadsafe(queue.put_nowait, {"event": "error", "data": {"error": safe_msg}})
                loop.call_soon_threadsafe(queue.put_nowait, None)

        # Copy context so contextvars propagate to the background thread
        ctx = contextvars.copy_context()
        thread = threading.Thread(target=ctx.run, args=(_run_stream,), daemon=True)
        thread.start()

        while True:
            event = await queue.get()
            if event is None:
                break
            yield event
            if event["event"] in ("done", "error"):
                break

        thread.join(timeout=5)


def _extract_last_tag(tag: str, text: str) -> str | None:
    """Extract content from the LAST occurrence of <tag>...</tag> (or unclosed <tag>...).

    Only matches tags at the start of a line (with optional whitespace) to avoid
    prose mentions like 'I should use the <solution> tag'.
    """
    pattern = re.compile(rf"(?:^|\n)\s*<{tag}>(.*?)(?:</{tag}>|$)", re.DOTALL | re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if matches:
        return matches[-1].group(1).strip()
    return None


def _parse_message_to_events(msg) -> list[dict]:
    """Parse a LangChain message into structured SSE events.

    Returns a list because a single message may contain both <thinking>
    and <solution>/<execute> blocks.
    """
    from langchain_core.messages import AIMessage, HumanMessage

    if isinstance(msg, HumanMessage):
        return []

    if not isinstance(msg, AIMessage):
        return []

    content = msg.content
    if isinstance(content, list):
        content = "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") in ("text", "output_text")
        )

    logger.debug("Raw AI content (%d chars): %.200s...", len(content), content)

    events: list[dict] = []

    # Extract <thinking> content as a "thinking" event (before stripping)
    thinking_text = _extract_last_tag("think(?:ing)?", content)
    if thinking_text:
        logger.debug("Parsed THINKING (%d chars)", len(thinking_text))
        events.append({"event": "thinking", "data": {"content": thinking_text}})

    # Strip <think>/<thinking> blocks to check remaining content
    content_stripped = re.sub(r"<think(?:ing)?>.*?</think(?:ing)?>", "", content, flags=re.DOTALL | re.IGNORECASE)
    content_stripped = re.sub(r"<think(?:ing)?>(?:(?!</think)[\s\S])*$", "", content_stripped, flags=re.IGNORECASE)
    content_stripped = content_stripped.strip()

    # Check for solution — use LAST occurrence to skip prose mentions
    solution_text = _extract_last_tag("solution", content_stripped)
    if solution_text:
        logger.debug("Parsed SOLUTION (%d chars)", len(solution_text))
        events.append({"event": "solution", "data": {"content": solution_text}})
        return events

    # Check for execute — use LAST occurrence
    execute_text = _extract_last_tag("execute", content_stripped)
    if execute_text:
        logger.debug("Parsed EXECUTE (%d chars)", len(execute_text))
        events.append({"event": "execute", "data": {"content": execute_text}})
        return events

    # Detect Biomni-style untagged code blocks (#!PYTHON, #!BASH, #!R)
    code_match = re.match(r"^#!(PYTHON|BASH|R)\s*\n(.+)", content_stripped, re.DOTALL | re.IGNORECASE)
    if code_match:
        logger.debug("Parsed untagged %s code as EXECUTE (%d chars)", code_match.group(1), len(content_stripped))
        events.append({"event": "execute", "data": {"content": content_stripped}})
        return events

    # Check for observation tags (execution results from the agent)
    observation_text = _extract_last_tag("observation", content_stripped)
    if observation_text:
        logger.debug("Parsed OBSERVATION as THINKING (%d chars)", len(observation_text))
        events.append({"event": "thinking", "data": {"content": observation_text}})
        return events

    # Check for error indicators
    if "Execution terminated" in content or "parsing error" in content.lower():
        events.append({"event": "error", "data": {"content": content_stripped}})
        return events

    # Untagged AI content with no thinking = failed parse attempt, suppress.
    if content_stripped and not events:
        logger.debug("Suppressed untagged AI content (%d chars): %.120s...", len(content_stripped), content_stripped)

    return events
