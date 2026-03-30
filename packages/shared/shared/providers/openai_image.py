"""OpenAI image generation provider — GPT Image models via openai SDK."""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

from shared.providers.image_base import (
    GeneratedImage,
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageProvider,
)

logger = logging.getLogger("reelsmaker.providers.openai_image")

_SIZE_MAP = {
    (1024, 1024): "1024x1024",
    (1536, 1024): "1536x1024",
    (1024, 1536): "1024x1536",
    (1792, 1024): "1792x1024",
    (1024, 1792): "1024x1792",
}


def _best_size(w: int, h: int) -> str:
    """Pick the closest supported OpenAI image size."""
    ratio = w / h
    if ratio > 1.6:
        return "1792x1024"
    if ratio > 1.2:
        return "1536x1024"
    if ratio < 0.625:
        return "1024x1792"
    if ratio < 0.85:
        return "1024x1536"
    return "1024x1024"


class OpenAIImageProvider(ImageProvider):
    """Generate images using OpenAI GPT Image (gpt-image-1, gpt-image-1.5).

    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-image-1",
        timeout_sec: int = 120,
    ):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIImageProvider")
        self._api_key = api_key
        self._default_model = default_model
        self._timeout = timeout_sec

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError("openai package required: pip install openai") from exc

        model = request.model or self._default_model
        start = time.monotonic()

        client = AsyncOpenAI(api_key=self._api_key, timeout=self._timeout)

        size = _best_size(request.width, request.height)
        quality = request.provider_options.get("quality", "auto")

        result = await client.images.generate(
            model=model,
            prompt=request.prompt,
            n=request.num_variants,
            size=size,
            quality=quality,
        )

        latency_ms = int((time.monotonic() - start) * 1000)

        images: list[GeneratedImage] = []
        for i, img_data in enumerate(result.data):
            raw = img_data.b64_json
            if not raw:
                continue
            img_bytes = base64.b64decode(raw)

            parsed_w, parsed_h = (int(x) for x in size.split("x"))

            images.append(GeneratedImage(
                image_bytes=img_bytes,
                width=parsed_w,
                height=parsed_h,
                mime_type="image/png",
                variant_index=i,
                metadata={
                    "model": model,
                    "quality": quality,
                    "prompt_preview": request.prompt[:100],
                },
            ))

        if not images:
            raise RuntimeError(f"OpenAI returned no images for model {model}")

        total_latency = int((time.monotonic() - start) * 1000)

        cost_per_image = 0.02 if "mini" in model else 0.04
        if "1.5" in model:
            cost_per_image = 0.04

        logger.info(
            "openai generate: model=%s variants=%d latency=%dms",
            model, len(images), total_latency,
        )

        return ImageGenerationResponse(
            images=images,
            model=model,
            provider="openai",
            latency_ms=total_latency,
            cost_estimate=len(images) * cost_per_image,
            metadata={"size": size, "quality": quality},
        )

    async def health_check(self) -> bool:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self._api_key, timeout=10)
            await client.models.list()
            return True
        except Exception:
            return False
