"""DSM ingestion endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import require_admin_token
from app.schemas.ingestion import DsmImportRequest, DsmImportResult
from app.services.dsm_ingestion import DsmIngestionService

router = APIRouter(prefix="/api/dsm", tags=["dsm-ingestion"])


@router.post("/ingest", response_model=DsmImportResult, dependencies=[Depends(require_admin_token)])
async def ingest(request: DsmImportRequest, session: AsyncSession = Depends(get_session)):
    return await DsmIngestionService(session).import_release(request)
