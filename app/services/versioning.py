"""Version activation service."""
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiagnosticChunk, DiagnosticDocument, DiagnosticVersion
from app.repositories.dsm_versions import DsmVersionRepository


class DsmVersioningService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DsmVersionRepository(session)

    async def activate(self, version_id: str) -> DiagnosticVersion:
        document_count = await self.session.scalar(select(func.count()).select_from(DiagnosticDocument).where(DiagnosticDocument.version_id == version_id))
        chunk_count = await self.session.scalar(select(func.count()).select_from(DiagnosticChunk).where(DiagnosticChunk.version_id == version_id))
        if not document_count:
            raise HTTPException(status_code=409, detail="DSM version has no imported documents")
        if not chunk_count:
            raise HTTPException(status_code=409, detail="DSM version has no generated chunks")
        version = await self.repo.activate(version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="DSM version not found")
        return version
