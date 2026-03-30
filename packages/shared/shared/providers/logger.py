from __future__ import annotations

import logging
import uuid as _uuid

from shared.database import async_session_factory
from shared.models.provider_run import ProviderRun
from shared.providers.base import ProviderRequest, ProviderResponse

logger = logging.getLogger("reelsmaker.providers.logger")


async def log_provider_run(
    *,
    project_id: _uuid.UUID | str,
    operation: str,
    request: ProviderRequest,
    response: ProviderResponse | None = None,
    error: str | None = None,
) -> _uuid.UUID:
    """Persist a :class:`ProviderRun` record and return its *id*."""
    pid = _uuid.UUID(str(project_id)) if isinstance(project_id, str) else project_id

    if error:
        status = "failed"
    elif response:
        status = "completed"
    else:
        status = "started"

    input_summary = {
        "system_prompt_len": len(request.system_prompt),
        "user_prompt_len": len(request.user_prompt),
        "user_prompt_preview": request.user_prompt[:300],
        "model": request.model,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }

    output_summary = None
    token_usage = None
    latency_ms = None
    model_used = request.model

    if response:
        model_used = response.model
        latency_ms = response.latency_ms
        output_summary = {
            "content_len": len(response.content),
            "content_preview": response.content[:300],
            "parsed_keys": list(response.parsed.keys()) if isinstance(response.parsed, dict) else None,
        }
        token_usage = {
            "input": response.input_tokens,
            "output": response.output_tokens,
            "total": response.input_tokens + response.output_tokens,
        }

    async with async_session_factory() as session:
        run = ProviderRun(
            project_id=pid,
            provider=response.provider if response else "unknown",
            operation=operation,
            model=model_used,
            input_params=input_summary,
            output_summary=output_summary,
            status=status,
            latency_ms=latency_ms,
            token_usage=token_usage,
            error_message=error,
        )
        session.add(run)
        await session.commit()
        logger.info(
            "ProviderRun logged: %s op=%s status=%s latency=%sms",
            run.id,
            operation,
            status,
            latency_ms,
        )
        return run.id
