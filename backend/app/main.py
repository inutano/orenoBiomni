import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import health, sessions, system_info, wes
from .services import agent_manager

_LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"
logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT)

# Persistent file logging (if log directory exists)
_LOG_DIR = "/var/log/orenoiomni"
if os.path.isdir(_LOG_DIR):
    file_handler = RotatingFileHandler(
        os.path.join(_LOG_DIR, "backend.log"),
        maxBytes=50 * 1024 * 1024,  # 50 MB
        backupCount=5,
    )
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logging.getLogger().addHandler(file_handler)

# Enable debug logging for the event parser
logging.getLogger("backend.app.services.agent_manager").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


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
    version="0.1.0",
    lifespan=lifespan,
)

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
