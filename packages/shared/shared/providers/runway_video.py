"""Runway video generation provider — Gen-4 Turbo via runwayml SDK."""

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

logger = logging.getLogger("reelsmaker.providers.runway")

_POLL_INTERVAL_SEC = 5
_MAX_POLL_ATTEMPTS = 120  # 10 minutes max


class RunwayVideoProvider(VideoProvider):
    """Generate video clips using Runway Gen-4 Turbo.

    Requires RUNWAY_API_KEY environment variable.
    Supports image_to_video mode (primary) and text_to_video (prompt-only).
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "gen4_turbo",
        timeout_sec: int = 300,
    ):
        if not api_key:
            raise ValueError("RUNWAY_API_KEY is required for RunwayVideoProvider")
        self._api_key = api_key
        self._default_model = default_model
        self._timeout = timeout_sec

    @property
    def provider_name(self) -> str:
        return "runway"

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        try:
            from runwayml import AsyncRunwayML
        except ImportError as exc:
            raise ImportError("runwayml package required: pip install runwayml") from exc

        model = request.model or self._default_model
        start = time.monotonic()

        client = AsyncRunwayML(api_key=self._api_key)

        try:
            if request.mode == "image_to_video" and request.start_frame_bytes:
                task = await self._create_image_to_video(
                    client, model, request,
                )
            else:
                task = await self._create_text_to_video(
                    client, model, request,
                )

            task_id = task.id
            logger.info("runway task created: id=%s model=%s", task_id, model)

            output_url = await self._poll_until_complete(client, task_id)

            video_bytes = await self._download_video(output_url)

        finally:
            await client.close()

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
                "runway_task_id": task_id,
                "mode": request.mode,
                "prompt_preview": request.prompt[:100],
                "output_url": output_url,
            },
        )

        logger.info(
            "runway generate: model=%s latency=%dms size=%dKB",
            model, total_latency, len(video_bytes) // 1024,
        )

        return VideoGenerationResponse(
            video=video,
            model=model,
            provider="runway",
            latency_ms=total_latency,
            cost_estimate=0.05,
            metadata={"task_id": task_id},
        )

    async def _create_image_to_video(self, client, model, request: VideoGenerationRequest):
        """Create an image-to-video task."""
        mime = request.start_frame_mime or "image/png"
        b64 = base64.b64encode(request.start_frame_bytes).decode()
        data_uri = f"data:{mime};base64,{b64}"

        ratio = request.provider_options.get(
            "ratio",
            f"{request.width}:{request.height}",
        )

        kwargs: dict[str, Any] = {
            "model": model,
            "prompt_image": data_uri,
            "ratio": ratio,
        }
        if request.prompt:
            kwargs["prompt_text"] = request.prompt

        if request.duration_sec and request.duration_sec >= 9:
            kwargs["duration"] = 10
        else:
            kwargs["duration"] = 5

        return await client.image_to_video.create(**kwargs)

    async def _create_text_to_video(self, client, model, request: VideoGenerationRequest):
        """Create a text-to-video task (image_to_video with prompt only)."""
        ratio = request.provider_options.get(
            "ratio",
            f"{request.width}:{request.height}",
        )
        kwargs: dict[str, Any] = {
            "model": model,
            "prompt_text": request.prompt,
            "ratio": ratio,
        }
        if request.duration_sec and request.duration_sec >= 9:
            kwargs["duration"] = 10
        else:
            kwargs["duration"] = 5

        return await client.image_to_video.create(**kwargs)

    async def _poll_until_complete(self, client, task_id: str) -> str:
        """Poll task status until SUCCEEDED. Returns output URL."""
        for attempt in range(_MAX_POLL_ATTEMPTS):
            await asyncio.sleep(_POLL_INTERVAL_SEC)
            task = await client.tasks.retrieve(id=task_id)
            status = task.status

            if status == "SUCCEEDED":
                output = task.output
                if isinstance(output, list) and output:
                    return output[0]
                if isinstance(output, str):
                    return output
                raise RuntimeError(f"Runway task succeeded but no output URL: {output}")

            if status in ("FAILED", "CANCELLED"):
                failure = getattr(task, "failure", None)
                raise RuntimeError(
                    f"Runway task {task_id} {status}: {failure or 'unknown error'}"
                )

            if attempt % 6 == 0:
                logger.info("runway polling: task=%s status=%s attempt=%d", task_id, status, attempt)

        raise TimeoutError(
            f"Runway task {task_id} timed out after {_MAX_POLL_ATTEMPTS * _POLL_INTERVAL_SEC}s"
        )

    async def _download_video(self, url: str) -> bytes:
        """Download the generated video from Runway's CDN."""
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.get(url)
            resp.raise_for_status()
            return resp.content

    async def health_check(self) -> bool:
        try:
            from runwayml import AsyncRunwayML
            client = AsyncRunwayML(api_key=self._api_key)
            await client.close()
            return True
        except Exception:
            return False
