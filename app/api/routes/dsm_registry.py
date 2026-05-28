"""DSM registry endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.repositories.dsm_registry import DsmRegistryRepository
from app.schemas.dsm import DsmRegistryRead

router = APIRouter(prefix="/api/dsm/registry", tags=["dsm-registry"])


@router.get("", response_model=list[DsmRegistryRead])
async def list_registry(version_id: str = "active", category: str | None = None, session: AsyncSession = Depends(get_session)):
    return await DsmRegistryRepository(session).list(version_id, category)


@router.get("/minimal", response_model=list[DsmRegistryRead])
async def list_minimal(version_id: str = "active", session: AsyncSession = Depends(get_session)):
    return await DsmRegistryRepository(session).list(version_id, "MINIMAL")


@router.get("/excluded", response_model=list[DsmRegistryRead])
async def list_excluded(version_id: str = "active", session: AsyncSession = Depends(get_session)):
    return await DsmRegistryRepository(session).list(version_id, "EXCLUDE")
