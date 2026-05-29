"""Repository for non-renderable DSM registry entries."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiagnosticRegistry, DiagnosticVersion


class DsmRegistryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, version_id: str = "active", category: str | None = None) -> list[DiagnosticRegistry]:
        stmt = select(DiagnosticRegistry)
        if version_id == "active":
            stmt = stmt.join(DiagnosticVersion, DiagnosticVersion.id == DiagnosticRegistry.version_id).where(DiagnosticVersion.status == "active")
        else:
            stmt = stmt.where(DiagnosticRegistry.version_id == version_id)
        if category:
            stmt = stmt.where(DiagnosticRegistry.category == category)
        stmt = stmt.order_by(DiagnosticRegistry.chapter_id, DiagnosticRegistry.name)
        return list((await self.session.scalars(stmt)).all())

    async def get_by_item_id(self, item_id: str, version_id: str = "active") -> DiagnosticRegistry | None:
        stmt = select(DiagnosticRegistry).where(DiagnosticRegistry.item_id == item_id)
        if version_id == "active":
            stmt = stmt.join(DiagnosticVersion, DiagnosticVersion.id == DiagnosticRegistry.version_id).where(DiagnosticVersion.status == "active")
        else:
            stmt = stmt.where(DiagnosticRegistry.version_id == version_id)
        return await self.session.scalar(stmt)

    async def bulk_add(self, rows: list[DiagnosticRegistry]) -> None:
        self.session.add_all(rows)
        await self.session.flush()
