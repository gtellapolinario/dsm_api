"""DSM version endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.repositories.dsm_versions import DsmVersionRepository
from app.schemas.dsm import DsmVersionRead
from app.services.versioning import DsmVersioningService

router = APIRouter(prefix="/api/dsm/versions", tags=["dsm-versions"])


@router.get("", response_model=list[DsmVersionRead])
async def list_versions(session: AsyncSession = Depends(get_session)):
    return await DsmVersionRepository(session).list()


@router.get("/current", response_model=DsmVersionRead)
async def current_version(session: AsyncSession = Depends(get_session)):
    version = await DsmVersionRepository(session).get_active()
    if version is None:
        raise HTTPException(status_code=404, detail="No active DSM version")
    return version


@router.post("/{version_id}/activate", response_model=DsmVersionRead)
async def activate_version(version_id: str, session: AsyncSession = Depends(get_session)):
    version = await DsmVersioningService(session).activate(version_id)
    await session.commit()
    return version
