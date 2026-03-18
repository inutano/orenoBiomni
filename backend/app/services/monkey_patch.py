"""Monkey-patch Biomni execution functions to dispatch to Celery workers.

After agent initialization, this replaces `run_with_timeout` in the biomni.utils
module so that code execution goes through Celery instead of running in-process.
The LangGraph agent loop is unaware of this — it just sees `run_with_timeout`
return a result string as before.
"""

import contextvars
import logging
import uuid

logger = logging.getLogger(__name__)

# Context variable to track which session is currently executing.
# Set by agent_manager.stream_chat before spawning the background thread.
current_session_id: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "current_session_id", default=None
)


def _celery_run_with_timeout(func, args=None, kwargs=None, timeout=600):
    """Drop-in replacement for biomni.utils.run_with_timeout.

    Instead of running the function in a thread with a timeout, submits a Celery
    task and blocks until it completes.
    """
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    session_id = current_session_id.get()
    if session_id is None:
        # Fallback: run locally if no session context (shouldn't happen in normal flow)
        logger.warning("No session context — running execution locally")
        return func(*args, **kwargs)

    # Determine job type from the function being called
    func_name = getattr(func, "__name__", str(func))
    if "python" in func_name.lower() or "repl" in func_name.lower():
        job_type = "python"
    elif "r_code" in func_name.lower():
        job_type = "r"
    elif "bash" in func_name.lower():
        job_type = "bash"
    else:
        # Unknown function — run locally
        logger.warning("Unknown execution function %s — running locally", func_name)
        return func(*args, **kwargs)

    # The first positional arg is always the code string
    code = args[0] if args else kwargs.get("code", "")

    from .execution_service import submit_job_sync

    _job_id, result = submit_job_sync(session_id, code, job_type, timeout)
    return result


def patch_execution():
    """Replace biomni.utils.run_with_timeout with Celery-dispatching version."""
    import biomni.utils

    biomni.utils.run_with_timeout = _celery_run_with_timeout

    # Also patch the reference in a1.py's module scope if it imported directly
    try:
        import biomni.agent.a1 as a1_module

        if hasattr(a1_module, "run_with_timeout"):
            a1_module.run_with_timeout = _celery_run_with_timeout
    except ImportError:
        pass

    logger.info("Patched biomni execution functions to use Celery workers")


def unpatch_execution():
    """Restore original execution functions (for testing)."""
    import importlib

    import biomni.utils

    importlib.reload(biomni.utils)
    logger.info("Restored original biomni execution functions")
