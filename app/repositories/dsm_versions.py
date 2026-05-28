"""Repository for DSM versions."""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiagnosticVersion


class DsmVersionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self) -> list[DiagnosticVersion]:
        return list((await self.session.scalars(select(DiagnosticVersion).order_by(DiagnosticVersion.created_at.desc()))).all())

    async def get(self, version_id: str) -> DiagnosticVersion | None:
        return await self.session.get(DiagnosticVersion, version_id)

    async def get_active(self) -> DiagnosticVersion | None:
        return await self.session.scalar(select(DiagnosticVersion).where(DiagnosticVersion.status == "active"))

    async def create(self, version: DiagnosticVersion) -> DiagnosticVersion:
        self.session.add(version)
        await self.session.flush()
        return version

    async def activate(self, version_id: str) -> DiagnosticVersion | None:
        version = await self.get(version_id)
        if version is None:
            return None
        await self.session.execute(update(DiagnosticVersion).where(DiagnosticVersion.status == "active").values(status="archived"))
        await self.session.execute(
            update(DiagnosticVersion)
            .where(DiagnosticVersion.id == version_id)
            .values(status="active", activated_at=__import__("sqlalchemy").func.now())
        )
        await self.session.flush()
        return await self.get(version_id)
