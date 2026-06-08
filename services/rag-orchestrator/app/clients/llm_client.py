from __future__ import annotations

import json
from typing import Any, Dict

import httpx

from ..core.flow_logger import log_flow
from ..services.llm_generation_error import LlmGenerationError


class LlmClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=120.0)

    async def generate(
        self,
        prompt: str,
        context: Dict[str, Any] | None = None,
        *,
        system_prompt: str | None = None,
        response_format: Dict[str, Any] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 768,
        request_timeout: float | None = None,
    ) -> Dict[str, Any]:
        rendered_prompt = self._render_prompt(prompt, context)
        log_flow(
            "llm-engine",
            "completion.requested",
            "RAG orchestrator requested a completion from the LLM engine.",
            prompt_length=len(rendered_prompt),
            has_context=bool(context),
        )

        chat_payload: Dict[str, Any] = {
            "model": "local-model",
            "messages": self._build_messages(rendered_prompt, system_prompt),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            chat_payload["response_format"] = response_format

        try:
            response = await self._client.post(
                "/v1/chat/completions",
                json=chat_payload,
                timeout=request_timeout,
            )
            response.raise_for_status()
            completion_response = response.json()
            text = self._extract_chat_text(completion_response)
            if not text.strip():
                raise LlmGenerationError(
                    "LLM engine returned an empty completion response."
                )
            log_flow(
                "llm-engine",
                "completion.received",
                "RAG orchestrator received a chat completion response from the LLM engine.",
                status=response.status_code,
                endpoint="/v1/chat/completions",
                response_preview=text or "",
            )
            return {
                "text": text,
                "endpoint": "/v1/chat/completions",
                "raw": completion_response,
            }
        except Exception as exc:
            log_flow(
                "llm-engine",
                "completion.failed",
                "LLM completion request failed and the orchestrator cannot continue without model output.",
                prompt_length=len(rendered_prompt),
                error=str(exc),
            )
            if isinstance(exc, LlmGenerationError):
                raise
            raise LlmGenerationError(
                "LLM engine failed to generate a completion."
            ) from exc

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _build_messages(prompt: str, system_prompt: str | None) -> list[Dict[str, str]]:
        messages: list[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    @staticmethod
    def _render_prompt(prompt: str, context: Dict[str, Any] | None) -> str:
        if not context:
            return prompt
        context_json = json.dumps(context, ensure_ascii=True, sort_keys=True)
        return "\n\n".join([prompt, "Context JSON:", context_json])

    @staticmethod
    def _extract_chat_text(payload: Any) -> str:
        if not isinstance(payload, dict):
            return str(payload)
        choices = payload.get("choices") or []
        if not choices:
            return payload.get("content") or payload.get("text") or ""
        first_choice = choices[0] or {}
        message = first_choice.get("message") or {}
        return message.get("content") or first_choice.get("text") or payload.get("content") or payload.get("text") or ""
