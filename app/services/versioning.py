"""Version activation service."""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.dsm_versions import DsmVersionRepository


class DsmVersioningService:
    def __init__(self, session: AsyncSession):
        self.repo = DsmVersionRepository(session)

    async def activate(self, version_id: str):
        version = await self.repo.activate(version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="DSM version not found")
        return version
