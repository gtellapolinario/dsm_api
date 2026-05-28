"""Renderable DSM document endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.repositories.dsm_documents import DsmDocumentRepository
from app.schemas.dsm import DsmDocumentListItem, DsmDocumentRead

router = APIRouter(prefix="/api/dsm", tags=["dsm-documents"])


@router.get("/documents", response_model=list[DsmDocumentListItem])
async def list_documents(
    version_id: str | None = "active", chapter_id: str | None = None, category: str | None = None,
    estrutura_diagnostica: str | None = None, ui_mode: str | None = None, severity_type: str | None = None,
    active: bool | None = True, q: str | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await DsmDocumentRepository(session).list(
        version_id=version_id, chapter_id=chapter_id, category=category, estrutura_diagnostica=estrutura_diagnostica,
        ui_mode=ui_mode, severity_type=severity_type, active=active, q=q, limit=limit, offset=offset,
    )


@router.get("/documents/{item_id}", response_model=DsmDocumentRead)
async def get_document(item_id: str, version_id: str = "active", session: AsyncSession = Depends(get_session)):
    doc = await DsmDocumentRepository(session).get_by_item_id(item_id, version_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="DSM document not found")
    return doc


@router.get("/chapters")
async def list_chapters(version_id: str = "active", session: AsyncSession = Depends(get_session)):
    return await DsmDocumentRepository(session).chapters(version_id)
