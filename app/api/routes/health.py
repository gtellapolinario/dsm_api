"""Health endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session

router = APIRouter(prefix="/api", tags=["health"])


async def _db_status(session: AsyncSession) -> dict[str, str]:
    database = "ok"
    pgvector = "ok"
    try:
        await session.execute(text("SELECT 1"))
        row = await session.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"))
        pgvector = "ok" if row.scalar() else "missing"
    except Exception:
        database = "unavailable"
        pgvector = "unknown"
    return {"database": database, "pgvector": pgvector}


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    status = await _db_status(session)
    return {"status": "ok", **status}


@router.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    status = await _db_status(session)
    return {"status": "ok" if status["database"] == "ok" else "unavailable", "database": status["database"]}


@router.get("/health/vector")
async def health_vector(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    status = await _db_status(session)
    return {"status": "ok" if status["pgvector"] == "ok" else "degraded", "pgvector": status["pgvector"]}


@router.get("/health/readiness")
async def readiness(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    status = await _db_status(session)
    ready = status["database"] == "ok" and status["pgvector"] == "ok"
    return {"status": "ready" if ready else "not_ready", **status}
