"""Agentic DSM endpoints with deterministic Pydantic contracts."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import (
    DsmAgentResponse,
    DsmAnswerRequest,
    DsmCriticRequest,
    DsmInterviewPlanRequest,
)
from app.core.database import get_session
from app.services.dsm_agent_service import DsmAgentService

router = APIRouter(prefix="/api/dsm/agent", tags=["dsm-agent"])


@router.post("/answer", response_model=DsmAgentResponse)
async def answer(request: DsmAnswerRequest, session: AsyncSession = Depends(get_session)):
    return await DsmAgentService(session).answer(request)


@router.post("/interview-plan", response_model=DsmAgentResponse)
async def interview_plan(request: DsmInterviewPlanRequest, session: AsyncSession = Depends(get_session)):
    return await DsmAgentService(session).interview_plan(request)


@router.post("/critic", response_model=DsmAgentResponse)
async def critic(request: DsmCriticRequest, session: AsyncSession = Depends(get_session)):
    return await DsmAgentService(session).critic(request)
