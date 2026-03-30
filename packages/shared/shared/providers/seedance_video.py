"""Seedance video generation provider — ByteDance Seedance via fal.ai platform."""

from __future__ import annotations

import base64
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

logger = logging.getLogger("reelsmaker.providers.seedance_video")

I2V_PRO = "fal-ai/bytedance/seedance/v1.5/pro/image-to-video"
I2V_LITE = "fal-ai/bytedance/seedance/v1/lite/image-to-video"
T2V_PRO = "fal-ai/bytedance/seedance/v1.5/pro/text-to-video"


class SeedanceVideoProvider(VideoProvider):
    """Generate video clips using ByteDance Seedance via fal.ai.

    Requires FAL_KEY. Supports image_to_video and text_to_video.
    Default model: Seedance 1.0 Lite (cheapest at ~$0.036/sec).
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = I2V_LITE,
        timeout_sec: int = 300,
    ):
        if not api_key:
            raise ValueError("FAL_KEY is required for SeedanceVideoProvider")
        self._api_key = api_key
        self._default_model = default_model
        self._timeout = timeout_sec

    @property
    def provider_name(self) -> str:
        return "seedance"

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        try:
            import fal_client
        except ImportError as exc:
            raise ImportError("fal-client package required: pip install fal-client") from exc

        start = time.monotonic()

        if request.mode == "image_to_video" and request.start_frame_bytes:
            model = request.model or self._default_model
            arguments = self._build_i2v_args(request)
        else:
            model = request.model or T2V_PRO
            arguments = self._build_t2v_args(request)

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

        video_info = result.get("video", {})
        video_url = video_info.get("url", "")
        if not video_url:
            raise RuntimeError(f"Seedance returned no video URL: {result}")

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
                "prompt_preview": request.prompt[:100],
                "video_url": video_url,
            },
        )

        logger.info(
            "seedance generate: model=%s latency=%dms size=%dKB",
            model, total_latency, len(video_bytes) // 1024,
        )

        cost_per_sec = 0.036
        estimated_cost = request.duration_sec * cost_per_sec

        return VideoGenerationResponse(
            video=video,
            model=model,
            provider="seedance",
            latency_ms=total_latency,
            cost_estimate=estimated_cost,
            metadata={"fal_request_id": result.get("request_id", "")},
        )

    def _build_i2v_args(self, request: VideoGenerationRequest) -> dict[str, Any]:
        mime = request.start_frame_mime or "image/png"
        b64 = base64.b64encode(request.start_frame_bytes).decode()
        image_url = f"data:{mime};base64,{b64}"

        duration = min(max(int(request.duration_sec), 2), 12)

        args: dict[str, Any] = {
            "prompt": request.prompt,
            "image_url": image_url,
            "duration": duration,
            "aspect_ratio": request.aspect_ratio or "16:9",
        }

        if request.end_frame_bytes:
            end_mime = request.end_frame_mime or "image/png"
            end_b64 = base64.b64encode(request.end_frame_bytes).decode()
            args["end_image_url"] = f"data:{end_mime};base64,{end_b64}"

        if request.seed is not None:
            args["seed"] = request.seed

        resolution = request.provider_options.get("resolution", "720p")
        args["resolution"] = resolution

        _internal_keys = {"quality_mode", "resolution", "aspect_ratio"}
        for k, v in request.provider_options.items():
            if k not in _internal_keys and k not in args:
                args[k] = v

        return args

    def _build_t2v_args(self, request: VideoGenerationRequest) -> dict[str, Any]:
        duration = min(max(int(request.duration_sec), 2), 12)

        args: dict[str, Any] = {
            "prompt": request.prompt,
            "duration": duration,
            "aspect_ratio": request.aspect_ratio or "16:9",
        }

        if request.seed is not None:
            args["seed"] = request.seed

        resolution = request.provider_options.get("resolution", "720p")
        args["resolution"] = resolution

        _internal_keys = {"quality_mode", "resolution", "aspect_ratio"}
        for k, v in request.provider_options.items():
            if k not in _internal_keys and k not in args:
                args[k] = v

        return args

    async def health_check(self) -> bool:
        try:
            import fal_client  # noqa: F401
            os.environ["FAL_KEY"] = self._api_key
            return True
        except Exception:
            return False
