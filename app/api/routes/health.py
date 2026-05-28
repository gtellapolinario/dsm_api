"""Health endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    database = "ok"
    pgvector = "ok"
    try:
        await session.execute(text("SELECT 1"))
        row = await session.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"))
        pgvector = "ok" if row.scalar() else "missing"
    except Exception:
        database = "unavailable"
        pgvector = "unknown"
    return {"status": "ok", "database": database, "pgvector": pgvector}
