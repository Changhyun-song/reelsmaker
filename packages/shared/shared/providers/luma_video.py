"""Luma Dream Machine video generation provider — Ray 2 via REST API."""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any

import httpx

from shared.providers.video_base import (
    GeneratedVideo,
    VideoGenerationRequest,
    VideoGenerationResponse,
    VideoProvider,
)

logger = logging.getLogger("reelsmaker.providers.luma_video")

_API_BASE = "https://api.lumalabs.ai/dream-machine/v1"
_POLL_INTERVAL_SEC = 5
_MAX_POLL_ATTEMPTS = 120


class LumaVideoProvider(VideoProvider):
    """Generate video clips using Luma Dream Machine (Ray 2).

    Requires LUMA_API_KEY environment variable.
    Supports image_to_video (via keyframes) and text_to_video modes.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "ray-2",
        timeout_sec: int = 300,
    ):
        if not api_key:
            raise ValueError("LUMA_API_KEY is required for LumaVideoProvider")
        self._api_key = api_key
        self._default_model = default_model
        self._timeout = timeout_sec

    @property
    def provider_name(self) -> str:
        return "luma"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        model = request.model or self._default_model
        start = time.monotonic()

        body = self._build_body(request, model)

        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(
                f"{_API_BASE}/generations",
                headers=self._headers(),
                json=body,
            )
            resp.raise_for_status()
            gen = resp.json()

        gen_id = gen["id"]
        logger.info("luma generation created: id=%s model=%s", gen_id, model)

        video_url = await self._poll_until_complete(gen_id)
        video_bytes = await self._download_video(video_url)

        total_latency = int((time.monotonic() - start) * 1000)

        duration_str = body.get("duration", "5s")
        duration_sec = float(duration_str.replace("s", "")) if isinstance(duration_str, str) else 5.0

        video = GeneratedVideo(
            video_bytes=video_bytes,
            width=request.width,
            height=request.height,
            duration_sec=duration_sec,
            fps=request.fps,
            mime_type="video/mp4",
            seed=request.seed,
            metadata={
                "luma_generation_id": gen_id,
                "model": model,
                "mode": request.mode,
                "prompt_preview": request.prompt[:100],
                "video_url": video_url,
            },
        )

        logger.info(
            "luma generate: model=%s latency=%dms size=%dKB",
            model, total_latency, len(video_bytes) // 1024,
        )

        return VideoGenerationResponse(
            video=video,
            model=model,
            provider="luma",
            latency_ms=total_latency,
            cost_estimate=0.03,
            metadata={"generation_id": gen_id},
        )

    def _build_body(self, request: VideoGenerationRequest, model: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "prompt": request.prompt,
            "model": model,
        }

        aspect_ratio = request.provider_options.get("aspect_ratio", "16:9")
        body["aspect_ratio"] = aspect_ratio

        resolution = request.provider_options.get("resolution", "720p")
        body["resolution"] = resolution

        duration = "10s" if request.duration_sec >= 9 else "5s"
        body["duration"] = duration

        if request.mode == "image_to_video" and request.start_frame_bytes:
            start_url = request.provider_options.get("start_frame_url")
            if not start_url:
                mime = request.start_frame_mime or "image/png"
                b64 = base64.b64encode(request.start_frame_bytes).decode()
                start_url = f"data:{mime};base64,{b64}"

            body["keyframes"] = {
                "frame0": {
                    "type": "image",
                    "url": start_url,
                }
            }

        return body

    async def _poll_until_complete(self, gen_id: str) -> str:
        for attempt in range(_MAX_POLL_ATTEMPTS):
            await asyncio.sleep(_POLL_INTERVAL_SEC)

            async with httpx.AsyncClient(timeout=15) as http:
                resp = await http.get(
                    f"{_API_BASE}/generations/{gen_id}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                gen = resp.json()

            state = gen.get("state", "")

            if state == "completed":
                assets = gen.get("assets", {})
                video_url = assets.get("video", "")
                if not video_url:
                    raise RuntimeError(f"Luma generation completed but no video URL: {gen}")
                return video_url

            if state == "failed":
                reason = gen.get("failure_reason", "unknown")
                raise RuntimeError(f"Luma generation {gen_id} failed: {reason}")

            if attempt % 6 == 0:
                logger.info("luma polling: id=%s state=%s attempt=%d", gen_id, state, attempt)

        raise TimeoutError(
            f"Luma generation {gen_id} timed out after {_MAX_POLL_ATTEMPTS * _POLL_INTERVAL_SEC}s"
        )

    async def _download_video(self, url: str) -> bytes:
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.get(url)
            resp.raise_for_status()
            return resp.content

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                resp = await http.get(
                    f"{_API_BASE}/generations?limit=1",
                    headers=self._headers(),
                )
                return resp.status_code == 200
        except Exception:
            return False
