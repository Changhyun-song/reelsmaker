"""Higgsfield video generation provider — unified platform for 100+ AI video models."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx

from shared.providers.video_base import (
    GeneratedVideo,
    VideoGenerationRequest,
    VideoGenerationResponse,
    VideoProvider,
)

logger = logging.getLogger("reelsmaker.providers.higgsfield_video")

BASE_URL = "https://platform.higgsfield.ai"
DEFAULT_I2V_MODEL = "kling-video/v2.1/pro/image-to-video"
DEFAULT_T2V_MODEL = "kling-video/v2.1/pro/text-to-video"
POLL_INTERVAL_SEC = 3
MAX_POLL_ATTEMPTS = 120


class HiggsFieldVideoProvider(VideoProvider):
    """Generate video clips using HiggsField platform.

    Requires HIGGSFIELD_API_KEY_ID and HIGGSFIELD_API_KEY_SECRET.
    Uses fal.ai CDN to upload local images into publicly accessible URLs
    before passing them to Higgsfield (which only accepts HTTP URLs).
    """

    def __init__(
        self,
        api_key_id: str,
        api_key_secret: str,
        fal_key: str = "",
        default_model: str = DEFAULT_I2V_MODEL,
        timeout_sec: int = 300,
    ):
        if not api_key_id or not api_key_secret:
            raise ValueError("HIGGSFIELD_API_KEY_ID and HIGGSFIELD_API_KEY_SECRET are required")
        self._api_key_id = api_key_id
        self._api_key_secret = api_key_secret
        self._fal_key = fal_key
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

    def _upload_to_cdn(self, image_bytes: bytes, mime: str = "image/png") -> str:
        """Upload image bytes to fal.ai CDN and return public URL."""
        try:
            import fal_client
        except ImportError as exc:
            raise ImportError("fal-client package required for Higgsfield image uploads") from exc

        prev_key = os.environ.get("FAL_KEY")
        os.environ["FAL_KEY"] = self._fal_key
        try:
            url = fal_client.upload(image_bytes, mime)
            logger.info("uploaded image to fal CDN: %s (%d KB)", url[:80], len(image_bytes) // 1024)
            return url
        finally:
            if prev_key is not None:
                os.environ["FAL_KEY"] = prev_key
            elif "FAL_KEY" in os.environ:
                del os.environ["FAL_KEY"]

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        start = time.monotonic()

        if request.mode == "image_to_video" and request.start_frame_bytes:
            model = request.model or self._default_model
            payload = self._build_i2v_payload(request)
        else:
            model = request.model or DEFAULT_T2V_MODEL
            payload = self._build_t2v_payload(request)

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

        logger.info("higgsfield submitted: model=%s request_id=%s", model, request_id)

        result = await self._poll_until_complete(request_id)

        video_url = ""
        video_info = result.get("video", {})
        if isinstance(video_info, dict):
            video_url = video_info.get("url", "")
        if not video_url:
            raise RuntimeError(f"Higgsfield completed but no video URL: {result}")

        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.get(video_url)
            resp.raise_for_status()
            video_bytes = resp.content

        total_latency = int((time.monotonic() - start) * 1000)

        video = GeneratedVideo(
            video_bytes=video_bytes,
            width=request.width,
            height=request.height,
            duration_sec=request.duration_sec,
            fps=request.fps,
            mime_type="video/mp4",
            seed=request.seed,
            metadata={
                "model": model,
                "mode": request.mode,
                "request_id": request_id,
                "video_url": video_url,
                "prompt_preview": request.prompt[:100],
            },
        )

        logger.info(
            "higgsfield complete: model=%s request_id=%s latency=%dms size=%dKB",
            model, request_id, total_latency, len(video_bytes) // 1024,
        )

        return VideoGenerationResponse(
            video=video,
            model=model,
            provider="higgsfield",
            latency_ms=total_latency,
            cost_estimate=0.05,
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
                raise RuntimeError(f"Higgsfield generation {status}: {data}")
            if status == "queued":
                logger.debug("higgsfield %s: queued (attempt %d)", request_id, attempt + 1)
            elif status == "in_progress":
                logger.debug("higgsfield %s: in_progress (attempt %d)", request_id, attempt + 1)

        raise TimeoutError(f"Higgsfield request {request_id} timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SEC}s")

    def _build_i2v_payload(self, request: VideoGenerationRequest) -> dict[str, Any]:
        mime = request.start_frame_mime or "image/png"

        if self._fal_key:
            image_url = self._upload_to_cdn(request.start_frame_bytes, mime)
        else:
            raise RuntimeError(
                "Higgsfield requires a publicly accessible image URL. "
                "Set FAL_KEY to enable automatic CDN upload via fal.ai."
            )

        payload: dict[str, Any] = {
            "image_url": image_url,
            "prompt": request.prompt,
        }

        if request.duration_sec:
            payload["duration"] = int(request.duration_sec)

        aspect = request.provider_options.get("aspect_ratio", request.aspect_ratio)
        if aspect:
            payload["aspect_ratio"] = aspect

        resolution = request.provider_options.get("resolution")
        if resolution:
            payload["resolution"] = resolution

        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        for k, v in request.provider_options.items():
            if k not in payload:
                payload[k] = v
        return payload

    def _build_t2v_payload(self, request: VideoGenerationRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "prompt": request.prompt,
        }

        if request.duration_sec:
            payload["duration"] = int(request.duration_sec)

        aspect = request.provider_options.get("aspect_ratio", request.aspect_ratio)
        if aspect:
            payload["aspect_ratio"] = aspect

        resolution = request.provider_options.get("resolution", "720p")
        payload["resolution"] = resolution

        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        for k, v in request.provider_options.items():
            if k not in payload:
                payload[k] = v
        return payload

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
