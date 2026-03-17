import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import health, sessions
from .services import agent_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
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
    # Shutdown
    logger.info("Shutting down orenoBiomni backend.")


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
