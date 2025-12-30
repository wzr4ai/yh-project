from fastapi import APIRouter, HTTPException

from app.models import schemas
from app.services.llm import LLMService, LLMServiceError

router = APIRouter()


@router.post("/llm/chat", response_model=schemas.LLMChatResponse)
async def llm_chat(payload: schemas.LLMChatRequest):
    service = LLMService()
    try:
        return await service.chat(
            payload.messages,
            model_tier=payload.model_tier,
            protocol=payload.protocol,
            model=payload.model,
            temperature=payload.temperature,
            max_output_tokens=payload.max_output_tokens,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
