import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.core.event_queue import event_worker, get_event_queue
from app.api.v1 import auth, projects, flags, api_keys, rules, evaluate, events, analytics

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — launch the event worker as a background asyncio task
    worker_task = asyncio.create_task(event_worker(AsyncSessionLocal))
    logger.info("FlagBase startup complete")
    yield
    # Shutdown — send stop signal and wait for queue to drain
    await get_event_queue().put(None)
    await worker_task
    logger.info("Event worker shut down cleanly")


app = FastAPI(title="FlagBase API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────

# Phase 2
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])

# Phase 3
app.include_router(
    flags.router,
    prefix="/api/v1/projects/{project_id}/flags",
    tags=["flags"],
)
app.include_router(
    api_keys.router,
    prefix="/api/v1/projects/{project_id}/api-keys",
    tags=["api-keys"],
)
app.include_router(
    rules.router,
    prefix="/api/v1/flags/{flag_id}/rules",
    tags=["rules"],
)
app.include_router(evaluate.router, prefix="/api/v1", tags=["evaluation"])
app.include_router(events.router, prefix="/api/v1", tags=["events"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])


@app.get("/health", tags=["system"])
async def health():
    db_status = "connected"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    queue_depth = get_event_queue().qsize()
    overall = "healthy" if db_status == "connected" else "unhealthy"

    payload = {
        "status": overall,
        "db": db_status,
        "event_queue_depth": queue_depth,
        "version": "2.0.0",
        "environment": settings.environment,
    }

    if overall == "unhealthy":
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=payload)

    return payload