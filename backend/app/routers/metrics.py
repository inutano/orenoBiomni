"""Prometheus-compatible metrics endpoint.

Exposes key application metrics in Prometheus text format.
Scrape at /metrics with Prometheus.
"""

import time

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.job import Job, RunState
from ..services import agent_manager

router = APIRouter()

_start_time = time.time()

# Simple in-memory counters (reset on restart)
_request_count = 0
_chat_count = 0
_error_count = 0


def inc_request():
    global _request_count
    _request_count += 1


def inc_chat():
    global _chat_count
    _chat_count += 1


def inc_error():
    global _error_count
    _error_count += 1


@router.get("/metrics", include_in_schema=False)
async def metrics(db: AsyncSession = Depends(get_db)):
    lines = []

    def gauge(name, value, help_text="", labels=""):
        if help_text:
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name}{labels} {value}")

    def counter(name, value, help_text=""):
        if help_text:
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {value}")

    # Uptime
    gauge("orenoiomni_uptime_seconds", f"{time.time() - _start_time:.0f}",
          "Seconds since backend started")

    # Agent status
    gauge("orenoiomni_agent_ready", "1" if agent_manager.is_agent_ready() else "0",
          "Whether the LLM agent is initialized")
    gauge("orenoiomni_celery_active", "1" if agent_manager.is_celery_active() else "0",
          "Whether Celery workers are connected")

    # Active sessions (locks held)
    active = sum(1 for lock in agent_manager._session_locks.values() if lock.locked())
    gauge("orenoiomni_active_streams", str(active),
          "Number of currently streaming chat sessions")

    # Active threads
    gauge("orenoiomni_active_threads", str(len(agent_manager._active_threads)),
          "Number of active agent threads")

    # Request counters
    counter("orenoiomni_requests_total", str(_request_count),
            "Total API requests served")
    counter("orenoiomni_chat_requests_total", str(_chat_count),
            "Total chat messages processed")
    counter("orenoiomni_errors_total", str(_error_count),
            "Total errors encountered")

    # Job counts by state from database
    try:
        result = await db.execute(
            select(Job.state, func.count()).group_by(Job.state)
        )
        for state, count in result.all():
            gauge("orenoiomni_jobs", str(count),
                  "Number of jobs by state" if state == RunState.QUEUED else "",
                  labels=f'{{state="{state}"}}')
    except Exception:
        pass

    # Database connection check
    try:
        await db.execute(text("SELECT 1"))
        gauge("orenoiomni_db_up", "1", "Database connectivity")
    except Exception:
        gauge("orenoiomni_db_up", "0", "Database connectivity")

    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
