"""Google Gemini image generation provider — Nano Banana models via google-genai SDK."""

from __future__ import annotations

import logging
import time
from typing import Any

from shared.providers.image_base import (
    GeneratedImage,
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageProvider,
)

logger = logging.getLogger("reelsmaker.providers.gemini_image")


class GeminiImageProvider(ImageProvider):
    """Generate images using Google Gemini (Nano Banana / Imagen 3).

    Requires GOOGLE_API_KEY environment variable.
    Models: gemini-2.5-flash-image, gemini-3.1-flash-image-preview, gemini-3-pro-image-preview
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "gemini-2.5-flash-image",
        timeout_sec: int = 120,
    ):
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for GeminiImageProvider")
        self._api_key = api_key
        self._default_model = default_model
        self._timeout = timeout_sec

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ImportError(
                "google-genai package required: pip install google-genai"
            ) from exc

        model = request.model or self._default_model
        start = time.monotonic()

        client = genai.Client(api_key=self._api_key)

        prompt_parts = [request.prompt]
        if request.negative_prompt:
            prompt_parts.append(f"Avoid: {request.negative_prompt}")

        images: list[GeneratedImage] = []

        for variant_idx in range(request.num_variants):
            response = client.models.generate_content(
                model=model,
                contents=prompt_parts,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                ),
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    img_bytes = part.inline_data.data
                    mime = part.inline_data.mime_type or "image/png"
                    images.append(GeneratedImage(
                        image_bytes=img_bytes,
                        width=request.width,
                        height=request.height,
                        mime_type=mime,
                        variant_index=variant_idx,
                        metadata={
                            "model": model,
                            "prompt_preview": request.prompt[:100],
                        },
                    ))
                    break

        if not images:
            raise RuntimeError(f"Gemini returned no images for model {model}")

        total_latency = int((time.monotonic() - start) * 1000)

        logger.info(
            "gemini generate: model=%s variants=%d latency=%dms",
            model, len(images), total_latency,
        )

        return ImageGenerationResponse(
            images=images,
            model=model,
            provider="gemini",
            latency_ms=total_latency,
            cost_estimate=len(images) * 0.02,
            metadata={"model": model},
        )

    async def health_check(self) -> bool:
        try:
            from google import genai
            genai.Client(api_key=self._api_key)
            return True
        except Exception:
            return False
