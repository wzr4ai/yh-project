from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db import get_session
from app.models import schemas
from app.services import ai_assistant

router = APIRouter()


def _ensure_owner(user):
    if not user or getattr(user, "role", None) != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="owner only")


@router.post("/ai/chat", response_model=schemas.AIChatResponse)
async def ai_chat(
    payload: schemas.AIChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    _ensure_owner(current_user)
    try:
        return await ai_assistant.chat_with_ai(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/ai/action", response_model=schemas.AIActionResponse)
async def ai_action(
    payload: schemas.AIActionRequest,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(deps.get_current_user),
):
    _ensure_owner(current_user)
    try:
        return await ai_assistant.execute_action(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
