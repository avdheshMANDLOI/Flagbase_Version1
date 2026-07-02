from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.core.database import engine
from app.api.v1 import auth, projects

app = FastAPI(title="FlagBase API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])

# Phase 3 will add:
# app.include_router(flags.router, prefix="/api/v1/projects/{project_id}/flags", tags=["flags"])
# app.include_router(api_keys.router, prefix="/api/v1/projects/{project_id}/keys", tags=["api-keys"])
# app.include_router(rules.router, prefix="/api/v1/flags", tags=["rules"])
# app.include_router(evaluate.router, prefix="/api/v1", tags=["evaluation"])
# app.include_router(events.router, prefix="/api/v1", tags=["events"])


@app.get("/health", tags=["system"])
async def health():
    """
    Health check. Verifies DB connectivity.
    v1: DB only — Redis check added in v2 when caching is introduced.
    """
    db_status = "connected"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    overall = "healthy" if db_status == "connected" else "unhealthy"

    payload = {
        "status": overall,
        "db": db_status,
        "version": "1.0.0",
        "environment": settings.environment,
    }

    if overall == "unhealthy":
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=payload)

    return payload
