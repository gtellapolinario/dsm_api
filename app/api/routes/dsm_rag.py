"""DSM RAG endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import rate_limit_dependency
from app.schemas.rag import DsmRagRequest, DsmRagResponse
from app.services.rag_service import DsmRagService

router = APIRouter(prefix="/api/dsm/rag", tags=["dsm-rag"])


@router.post("/retrieve", response_model=DsmRagResponse)
async def retrieve(request: DsmRagRequest, session: AsyncSession = Depends(get_session)):
    return await DsmRagService(session).retrieve(request)


@router.post("/answer", response_model=DsmRagResponse, dependencies=[Depends(rate_limit_dependency("dsm_rag_answer"))])
async def answer(request: DsmRagRequest, session: AsyncSession = Depends(get_session)):
    return await DsmRagService(session).answer(request)
