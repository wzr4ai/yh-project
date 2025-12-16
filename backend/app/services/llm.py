import os
from typing import Literal, Sequence

import httpx

from app.models import schemas

Protocol = Literal["gemini", "openai", "open"]
ModelTier = Literal["low", "mid", "high"]


class LLMServiceError(Exception):
    """Raised when the upstream LLM request fails."""


class LLMService:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        default_protocol: str | None = None,
    ):
        self.base_url = (base_url or os.getenv("LLM_BASE_URL") or "").rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.default_protocol = (default_protocol or os.getenv("LLM_PROTOCOL") or "gemini").lower()
        self.model_low = os.getenv("LLM_MODEL_LOW", "gemini-2.5-flash-lite")
        self.model_mid = os.getenv("LLM_MODEL_MID", "gemini-2.5-flash")
        self.model_high = os.getenv("LLM_MODEL_HIGH", "gemini-2.5-pro")

    async def chat(
        self,
        messages: Sequence[schemas.LLMMessage],
        model_tier: ModelTier = "mid",
        protocol: Protocol | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_output_tokens: int = 512,
        response_mime_type: str | None = None,
    ) -> schemas.LLMChatResponse:
        if not messages:
            raise ValueError("messages is required")
        if not self.base_url:
            raise ValueError("LLM_BASE_URL is not configured")

        protocol = (protocol or self.default_protocol).lower()
        model_name = model or self._model_for_tier(model_tier)
        if not model_name:
            raise ValueError(f"no model configured for tier '{model_tier}'")

        if protocol.startswith("open"):
            return await self._call_openai(messages, model_name, temperature, max_output_tokens)
        return await self._call_gemini(
            messages, model_name, temperature, max_output_tokens, response_mime_type=response_mime_type
        )

    def _model_for_tier(self, tier: ModelTier) -> str:
        if tier == "low":
            return self.model_low
        if tier == "high":
            return self.model_high
        return self.model_mid

    async def _call_openai(
        self,
        messages: Sequence[schemas.LLMMessage],
        model: str,
        temperature: float,
        max_output_tokens: int,
    ) -> schemas.LLMChatResponse:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": model,
            "messages": [msg.model_dump() for msg in messages],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            try:
                resp = await client.post("/v1/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text
                raise LLMServiceError(f"openai request failed ({exc.response.status_code}): {detail}") from exc
            except httpx.HTTPError as exc:
                raise LLMServiceError(f"openai request failed: {exc}") from exc

        data = resp.json()
        choices = data.get("choices") or []
        first_choice = choices[0] if choices else {}
        message = first_choice.get("message") or {}
        content = message.get("content") or ""
        finish_reason = first_choice.get("finish_reason")
        usage = data.get("usage")
        used_model = data.get("model") or model

        return schemas.LLMChatResponse(
            content=content,
            model=used_model,
            protocol="openai",
            finish_reason=finish_reason,
            raw_usage=usage,
        )

    async def _call_gemini(
        self,
        messages: Sequence[schemas.LLMMessage],
        model: str,
        temperature: float,
        max_output_tokens: int,
        response_mime_type: str | None = None,
    ) -> schemas.LLMChatResponse:
        system_instruction, contents = self._split_system_and_contents(messages)
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }
        if response_mime_type:
            payload["generationConfig"]["responseMimeType"] = response_mime_type
        if system_instruction:
            payload["systemInstruction"] = {"role": "system", "parts": [{"text": system_instruction}]}

        params = {}
        if self.api_key:
            params["key"] = self.api_key

        url = f"{self.base_url}/v1beta/models/{model}:generateContent"
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(url, params=params, json=payload)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text
                raise LLMServiceError(f"gemini request failed ({exc.response.status_code}): {detail}") from exc
            except httpx.HTTPError as exc:
                raise LLMServiceError(f"gemini request failed: {exc}") from exc

        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise LLMServiceError("gemini returned no candidates")
        first = candidates[0]
        parts = (first.get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        finish_reason = first.get("finishReason") or first.get("finish_reason")

        return schemas.LLMChatResponse(
            content=text,
            model=model,
            protocol="gemini",
            finish_reason=finish_reason,
            raw_usage=data.get("usageMetadata"),
        )

    def _split_system_and_contents(self, messages: Sequence[schemas.LLMMessage]) -> tuple[str | None, list[dict]]:
        system_messages = []
        contents = []
        for msg in messages:
            if msg.role == "system":
                system_messages.append(msg.content)
                continue
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})
        system_instruction = "\n".join(system_messages) if system_messages else None
        return system_instruction, contents
