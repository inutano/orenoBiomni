import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .routers import health, metrics, sessions, system_info, wes
from .services import agent_manager

# --- Structured JSON logging ---

_JSON_LOG = os.environ.get("LOG_FORMAT", "text") == "json"

if _JSON_LOG:
    import json as _json

    class _JsonFormatter(logging.Formatter):
        def format(self, record):
            return _json.dumps({
                "ts": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
                **({"exc": self.formatException(record.exc_info)} if record.exc_info else {}),
            })

    _formatter = _JsonFormatter()
else:
    _formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")

# Configure root logger
_root = logging.getLogger()
_root.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(_formatter)
_root.handlers = [_handler]

# Persistent file logging (if log directory exists)
_LOG_DIR = "/var/log/orenoiomni"
if os.path.isdir(_LOG_DIR):
    file_handler = RotatingFileHandler(
        os.path.join(_LOG_DIR, "backend.log"),
        maxBytes=50 * 1024 * 1024,  # 50 MB
        backupCount=5,
    )
    file_handler.setFormatter(_formatter)
    _root.addHandler(file_handler)

# Enable debug logging for the event parser
logging.getLogger("backend.app.services.agent_manager").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

# Audit logger — separate logger for security-relevant events
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)


# --- Rate limiting middleware ---

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory per-IP rate limiter."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Skip health checks and static assets
        if request.url.path in ("/api/v1/health",):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = now - 60

        # Clean old entries and check limit
        hits = self._hits[client_ip]
        self._hits[client_ip] = [t for t in hits if t > window]

        if len(self._hits[client_ip]) >= self.rpm:
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        self._hits[client_ip].append(now)
        metrics.inc_request()
        response = await call_next(request)
        if response.status_code >= 500:
            metrics.inc_error()
        return response


# --- App lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize agent
    logger.info("Starting orenoBiomni backend...")
    try:
        await agent_manager.init_agent(settings)
    except Exception:
        logger.exception("Failed to initialize agent — chat will be unavailable")
    yield
    # Shutdown: drain in-flight agent streams before exiting
    logger.info("Shutting down orenoBiomni backend...")
    await agent_manager.shutdown()


app = FastAPI(
    title="orenoBiomni API",
    description="Biomedical AI Agent backend — LLM-powered bioinformatics assistant with tool execution.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RateLimitMiddleware, requests_per_minute=120)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
app.include_router(system_info.router, prefix="/api/v1", tags=["system"])
app.include_router(wes.router, prefix="/ga4gh/wes/v1", tags=["WES"])
app.include_router(metrics.router, tags=["metrics"])
