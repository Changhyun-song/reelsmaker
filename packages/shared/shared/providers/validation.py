from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from shared.providers.base import ProviderRequest, ProviderResponse, TextProvider

from shared.providers.base import ProviderError

logger = logging.getLogger("reelsmaker.providers.validation")

T = TypeVar("T", bound=BaseModel)


# ── JSON extraction ───────────────────────────────────


def extract_json(text: str) -> dict | list | None:
    """Best-effort extraction of JSON from AI response text."""
    text = text.strip()

    if text.startswith(("{", "[")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    for pattern in (
        r"```json\s*\n(.*?)\n\s*```",
        r"```\s*\n(.*?)\n\s*```",
    ):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    brace = text.find("{")
    bracket = text.find("[")
    start = -1
    if brace >= 0 and (bracket < 0 or brace < bracket):
        start = brace
        end = text.rfind("}")
    elif bracket >= 0:
        start = bracket
        end = text.rfind("]")
    else:
        return None

    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


# ── Pydantic validation ──────────────────────────────


def validate_response(
    content: str | dict | list,
    schema: type[T],
) -> tuple[T | None, list[str]]:
    """Validate *content* against a Pydantic *schema*.

    Returns ``(model_instance, errors)``.  If *errors* is empty the parse
    succeeded and *model_instance* is populated.
    """
    if isinstance(content, str):
        data = extract_json(content)
        if data is None:
            return None, ["Failed to extract JSON from response"]
    else:
        data = content

    try:
        model = schema.model_validate(data)
        return model, []
    except ValidationError as exc:
        errors = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
        return None, errors


# ── Validated generation with retry ──────────────────


async def generate_validated(
    provider: "TextProvider",
    request: "ProviderRequest",
    schema: type[T],
    max_attempts: int = 3,
) -> tuple["ProviderResponse", T]:
    """Call *provider*, validate against *schema*, retry on validation failure.

    On each retry the previous validation errors are appended to the user
    prompt so the model can self-correct.
    """
    from shared.providers.base import ProviderRequest as _Req

    accumulated_errors: list[str] = []

    for attempt in range(1, max_attempts + 1):
        current_request = request
        if accumulated_errors:
            feedback = (
                "\n\n--- PREVIOUS ATTEMPT FAILED VALIDATION ---\n"
                + "\n".join(accumulated_errors)
                + "\n\nFix the issues above and output valid JSON."
            )
            current_request = _Req(
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt + feedback,
                model=request.model,
                temperature=min(request.temperature + 0.05 * attempt, 1.0),
                max_tokens=request.max_tokens,
                response_format=request.response_format,
                metadata=request.metadata,
            )

        response = await provider.generate(current_request)

        payload = response.parsed if response.parsed is not None else response.content
        result, errors = validate_response(payload, schema)

        if result is not None:
            response.parsed = result.model_dump()
            return response, result

        accumulated_errors = errors
        logger.warning(
            "Attempt %d/%d validation failed: %s",
            attempt,
            max_attempts,
            accumulated_errors,
        )

    raise ProviderError(
        f"Validation failed after {max_attempts} attempts: {'; '.join(accumulated_errors)}",
        provider=provider.provider_name,
        retryable=False,
    )
