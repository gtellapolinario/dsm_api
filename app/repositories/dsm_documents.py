"""Repository for renderable DSM documents."""
from sqlalchemy import Select, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiagnosticDocument


class DsmDocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _version_filter(self, stmt: Select, version_id: str | None) -> Select:
        if version_id and version_id != "active":
            return stmt.where(DiagnosticDocument.version_id == version_id)
        if version_id == "active" or version_id is None:
            from app.models import DiagnosticVersion

            return stmt.join(DiagnosticVersion, DiagnosticVersion.id == DiagnosticDocument.version_id).where(DiagnosticVersion.status == "active")
        return stmt

    async def list(self, **filters) -> list[DiagnosticDocument]:
        stmt = select(DiagnosticDocument)
        stmt = self._version_filter(stmt, filters.get("version_id"))
        for field in ["chapter_id", "category", "estrutura_diagnostica", "ui_mode", "severity_type", "active"]:
            value = filters.get(field)
            if value is not None:
                stmt = stmt.where(getattr(DiagnosticDocument, field) == value)
        q = filters.get("q")
        if q:
            stmt = stmt.where(DiagnosticDocument.name.ilike(f"%{q}%"))
        stmt = stmt.order_by(DiagnosticDocument.chapter_id, DiagnosticDocument.name).limit(filters.get("limit", 100)).offset(filters.get("offset", 0))
        return list((await self.session.scalars(stmt)).all())

    async def get_by_item_id(self, item_id: str, version_id: str = "active") -> DiagnosticDocument | None:
        stmt = select(DiagnosticDocument).where(DiagnosticDocument.item_id == item_id)
        stmt = self._version_filter(stmt, version_id)
        return await self.session.scalar(stmt)

    async def chapters(self, version_id: str = "active") -> list[dict[str, str]]:
        stmt = select(distinct(DiagnosticDocument.chapter_id), DiagnosticDocument.chapter_name)
        stmt = self._version_filter(stmt, version_id).order_by(DiagnosticDocument.chapter_id)
        rows = (await self.session.execute(stmt)).all()
        return [{"chapter_id": row[0], "chapter_name": row[1]} for row in rows]

    async def bulk_add(self, documents: list[DiagnosticDocument]) -> None:
        self.session.add_all(documents)
        await self.session.flush()
