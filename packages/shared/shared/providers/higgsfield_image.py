"""Higgsfield image generation provider — Nano Banana 2 (google/nano-banana-2) via platform API."""

from __future__ import annotations

import asyncio
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

logger = logging.getLogger("reelsmaker.providers.higgsfield_image")

BASE_URL = "https://platform.higgsfield.ai"
POLL_INTERVAL_SEC = 2
MAX_POLL_ATTEMPTS = 90


def _dimensions_to_aspect(w: int, h: int) -> str:
    """Convert pixel dimensions to the closest standard aspect ratio string."""
    ratio = w / h
    if ratio >= 1.7:
        return "16:9"
    if ratio >= 1.3:
        return "4:3"
    if 0.95 <= ratio <= 1.05:
        return "1:1"
    if ratio <= 0.6:
        return "9:16"
    if ratio <= 0.77:
        return "3:4"
    return "16:9"


def _dimensions_to_resolution(w: int, h: int) -> str:
    """Pick resolution tier based on the larger dimension."""
    larger = max(w, h)
    if larger <= 768:
        return "720p"
    return "1080p"


class HiggsFieldImageProvider(ImageProvider):
    """Generate images via Higgsfield platform (Nano Banana 2, etc.).

    Uses the same async queue/poll pattern as the Higgsfield video provider.
    Auth: ``Authorization: Key {id}:{secret}``
    """

    def __init__(
        self,
        api_key_id: str,
        api_key_secret: str,
        default_model: str = "google/nano-banana-2",
        timeout_sec: int = 120,
    ):
        if not api_key_id or not api_key_secret:
            raise ValueError("HIGGSFIELD_API_KEY_ID and HIGGSFIELD_API_KEY_SECRET are required")
        self._api_key_id = api_key_id
        self._api_key_secret = api_key_secret
        self._default_model = default_model
        self._timeout = timeout_sec

    @property
    def provider_name(self) -> str:
        return "higgsfield"

    def _auth_header(self) -> dict[str, str]:
        return {
            "Authorization": f"Key {self._api_key_id}:{self._api_key_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        model = request.model or self._default_model
        start = time.monotonic()

        aspect = request.provider_options.get(
            "aspect_ratio",
            _dimensions_to_aspect(request.width, request.height),
        )
        resolution = request.provider_options.get(
            "resolution",
            _dimensions_to_resolution(request.width, request.height),
        )

        payload: dict[str, Any] = {
            "prompt": request.prompt,
            "aspect_ratio": aspect,
            "resolution": resolution,
        }

        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        for k, v in request.provider_options.items():
            if k not in payload:
                payload[k] = v

        async with httpx.AsyncClient(timeout=self._timeout) as http:
            submit_resp = await http.post(
                f"{BASE_URL}/{model}",
                headers=self._auth_header(),
                json=payload,
            )
            submit_resp.raise_for_status()
            submit_data = submit_resp.json()

        request_id = submit_data.get("request_id")
        if not request_id:
            raise RuntimeError(f"Higgsfield returned no request_id: {submit_data}")

        logger.info("higgsfield image submitted: model=%s request_id=%s", model, request_id)

        result = await self._poll_until_complete(request_id)

        raw_images = result.get("images", [])
        if not raw_images:
            raise RuntimeError(f"Higgsfield completed but no images: {result}")

        images: list[GeneratedImage] = []
        async with httpx.AsyncClient(timeout=60) as http:
            for i, img_data in enumerate(raw_images):
                url = img_data.get("url", "")
                if not url:
                    continue
                resp = await http.get(url)
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "image/png")
                if "jpeg" in content_type or "jpg" in content_type:
                    mime = "image/jpeg"
                elif "webp" in content_type:
                    mime = "image/webp"
                else:
                    mime = "image/png"

                images.append(GeneratedImage(
                    image_bytes=resp.content,
                    width=request.width,
                    height=request.height,
                    mime_type=mime,
                    seed=request.seed,
                    variant_index=i,
                    metadata={
                        "higgsfield_url": url,
                        "request_id": request_id,
                        "prompt_preview": request.prompt[:100],
                    },
                ))

        total_latency = int((time.monotonic() - start) * 1000)

        logger.info(
            "higgsfield image complete: model=%s request_id=%s count=%d latency=%dms",
            model, request_id, len(images), total_latency,
        )

        return ImageGenerationResponse(
            images=images,
            model=model,
            provider="higgsfield",
            latency_ms=total_latency,
            cost_estimate=len(images) * 0.02,
            metadata={"request_id": request_id},
        )

    async def _poll_until_complete(self, request_id: str) -> dict[str, Any]:
        status_url = f"{BASE_URL}/requests/{request_id}/status"

        for attempt in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL_SEC)

            async with httpx.AsyncClient(timeout=30) as http:
                resp = await http.get(status_url, headers=self._auth_header())
                resp.raise_for_status()
                data = resp.json()

            status = data.get("status", "")
            if status == "completed":
                return data
            if status in ("failed", "nsfw"):
                raise RuntimeError(f"Higgsfield image generation {status}: {data}")
            logger.info("higgsfield image polling %s: %s (attempt %d/%d)", request_id, status, attempt + 1, MAX_POLL_ATTEMPTS)

        raise TimeoutError(
            f"Higgsfield image request {request_id} timed out after "
            f"{MAX_POLL_ATTEMPTS * POLL_INTERVAL_SEC}s"
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                resp = await http.get(
                    f"{BASE_URL}/requests/health-check-ping/status",
                    headers=self._auth_header(),
                )
                return resp.status_code in (200, 404)
        except Exception:
            return False
