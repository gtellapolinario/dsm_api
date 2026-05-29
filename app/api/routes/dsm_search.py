"""DSM search endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import rate_limit_dependency
from app.schemas.search import DsmSearchRequest, DsmSearchResult
from app.services.hybrid_search import HybridSearchService

router = APIRouter(prefix="/api/dsm", tags=["dsm-search"])


@router.post("/search", response_model=DsmSearchResult, dependencies=[Depends(rate_limit_dependency("dsm_search"))])
async def search_dsm(request: DsmSearchRequest, session: AsyncSession = Depends(get_session)):
    return await HybridSearchService(session).search(request)
