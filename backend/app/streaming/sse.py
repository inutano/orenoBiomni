import json
from collections.abc import AsyncGenerator


async def format_sse(events: AsyncGenerator[dict, None]) -> AsyncGenerator[dict, None]:
    """Format structured events into SSE-compatible dicts for sse-starlette."""
    async for event in events:
        yield {
            "event": event["event"],
            "data": json.dumps(event.get("data", {})),
        }
