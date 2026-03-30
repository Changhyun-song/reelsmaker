from __future__ import annotations

import json
import logging
import time

from shared.providers.base import (
    ProviderError,
    ProviderRequest,
    ProviderResponse,
    TextProvider,
)
from shared.providers.validation import extract_json

logger = logging.getLogger("reelsmaker.providers.claude")

_JSON_INSTRUCTION = (
    "\n\nCRITICAL: You MUST respond with valid JSON only. "
    "No markdown fences, no commentary, no trailing text. "
    "Start your response with { and end with }."
)


class ClaudeTextProvider(TextProvider):
    """Anthropic Claude adapter for structured text generation."""

    def __init__(
        self,
        api_key: str,
        default_model: str = "claude-sonnet-4-20250514",
        timeout_sec: int = 120,
    ):
        try:
            import anthropic  # noqa: F811
        except ImportError as exc:
            raise ImportError(
                "anthropic package is required: pip install anthropic"
            ) from exc

        if not api_key:
            raise ProviderError(
                "ANTHROPIC_API_KEY is not set", provider="claude"
            )

        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=timeout_sec,
        )
        self._default_model = default_model

    @property
    def provider_name(self) -> str:
        return "claude"

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        import anthropic

        model = request.model or self._default_model

        system_prompt = request.system_prompt
        if request.response_format == "json":
            system_prompt += _JSON_INSTRUCTION

        start = time.monotonic()
        try:
            resp = await self._client.messages.create(
                model=model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": request.user_prompt}],
            )
        except anthropic.RateLimitError as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.warning("Claude rate-limited after %dms: %s", latency_ms, exc)
            raise ProviderError(
                str(exc), provider="claude", retryable=True
            ) from exc
        except anthropic.APIStatusError as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            retryable = exc.status_code in (429, 500, 502, 503, 529)
            logger.warning("Claude API error (status=%d) after %dms: %s", exc.status_code, latency_ms, exc)
            raise ProviderError(
                str(exc), provider="claude", retryable=retryable
            ) from exc
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.error("Claude unexpected error after %dms: %s", latency_ms, exc)
            raise ProviderError(
                str(exc), provider="claude", retryable=False
            ) from exc

        latency_ms = int((time.monotonic() - start) * 1000)
        content = resp.content[0].text
        usage = resp.usage

        parsed = None
        if request.response_format == "json":
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = extract_json(content)

        return ProviderResponse(
            content=content,
            parsed=parsed,
            model=model,
            provider="claude",
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            latency_ms=latency_ms,
        )
