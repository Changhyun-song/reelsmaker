"""fal.ai image generation provider — FLUX models via fal-client SDK."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from shared.providers.image_base import (
    GeneratedImage,
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageProvider,
)

logger = logging.getLogger("reelsmaker.providers.fal_image")


class FalImageProvider(ImageProvider):
    """Generate images using fal.ai FLUX models.

    Requires FAL_KEY environment variable.
    Default model: fal-ai/flux/schnell (fast, ~2-4s per image).
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "fal-ai/flux/schnell",
        timeout_sec: int = 120,
    ):
        if not api_key:
            raise ValueError("FAL_KEY is required for FalImageProvider")
        self._api_key = api_key
        self._default_model = default_model
        self._timeout = timeout_sec

    @property
    def provider_name(self) -> str:
        return "fal"

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        try:
            import fal_client
        except ImportError as exc:
            raise ImportError("fal-client package required: pip install fal-client") from exc

        model = request.model or self._default_model
        start = time.monotonic()

        arguments: dict[str, Any] = {
            "prompt": request.prompt,
            "image_size": {
                "width": request.width,
                "height": request.height,
            },
            "num_images": request.num_variants,
            "output_format": "png",
            "enable_safety_checker": False,
        }
        if request.negative_prompt:
            arguments["negative_prompt"] = request.negative_prompt
        if request.seed is not None:
            arguments["seed"] = request.seed
        if request.guidance_scale is not None:
            arguments["guidance_scale"] = request.guidance_scale

        arguments.update(request.provider_options)

        import os
        _prev_key = os.environ.get("FAL_KEY")
        os.environ["FAL_KEY"] = self._api_key
        try:
            result = fal_client.subscribe(
                model,
                arguments=arguments,
                with_logs=False,
            )
        finally:
            if _prev_key is not None:
                os.environ["FAL_KEY"] = _prev_key
            else:
                os.environ.pop("FAL_KEY", None)

        latency_ms = int((time.monotonic() - start) * 1000)
        raw_images = result.get("images", [])

        if not raw_images:
            raise RuntimeError(f"fal.ai returned no images for model {model}")

        images: list[GeneratedImage] = []
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            for i, img_data in enumerate(raw_images):
                url = img_data.get("url", "")
                if not url:
                    continue
                resp = await http.get(url)
                resp.raise_for_status()

                w = img_data.get("width", request.width)
                h = img_data.get("height", request.height)
                content_type = img_data.get("content_type", "image/png")

                images.append(GeneratedImage(
                    image_bytes=resp.content,
                    width=w,
                    height=h,
                    mime_type=content_type,
                    seed=result.get("seed"),
                    variant_index=i,
                    metadata={
                        "fal_url": url,
                        "prompt_preview": request.prompt[:100],
                    },
                ))

        total_latency = int((time.monotonic() - start) * 1000)

        logger.info(
            "fal generate: model=%s variants=%d latency=%dms",
            model, len(images), total_latency,
        )

        return ImageGenerationResponse(
            images=images,
            model=model,
            provider="fal",
            latency_ms=total_latency,
            cost_estimate=len(images) * 0.003,
            metadata={
                "fal_request_id": result.get("request_id", ""),
                "has_nsfw": result.get("has_nsfw_concepts", []),
            },
        )

    async def health_check(self) -> bool:
        try:
            import fal_client
            import os
            os.environ["FAL_KEY"] = self._api_key
            return True
        except Exception:
            return False
