"""Kling video generation provider — Kling 2.0 via fal.ai platform."""

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

logger = logging.getLogger("reelsmaker.providers.kling_video")

_DEFAULT_VIDEO_NEGATIVE = (
    "temporal flicker, frame jitter, morphing face, warped hands, rubber limbs, "
    "sudden camera shake, inconsistent lighting between frames, subtitle text, "
    "watermark, compression artifacts, duplicated subject, ghosting, "
    "unnatural motion blur, face distortion, floating limbs"
)

# cfg_scale defaults per quality mode — lower = more creative, higher = more faithful
_CFG_DEFAULTS: dict[str, float] = {
    "speed": 0.5,
    "balanced": 0.5,
    "quality": 0.7,
}


class KlingVideoProvider(VideoProvider):
    """Generate video clips using Kling 2.0 Master via fal.ai.

    Requires FAL_KEY environment variable (shared with fal.ai image provider).
    Supports image_to_video and text_to_video modes.
    """

    I2V_MODEL = "fal-ai/kling-video/v2/master/image-to-video"
    T2V_MODEL = "fal-ai/kling-video/v2.1/master/text-to-video"

    def __init__(
        self,
        api_key: str,
        default_model: str = "fal-ai/kling-video/v2/master/image-to-video",
        timeout_sec: int = 300,
    ):
        if not api_key:
            raise ValueError("FAL_KEY is required for KlingVideoProvider")
        self._api_key = api_key
        self._default_model = default_model
        self._timeout = timeout_sec

    @property
    def provider_name(self) -> str:
        return "kling"

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        try:
            import fal_client
        except ImportError as exc:
            raise ImportError("fal-client package required: pip install fal-client") from exc

        start = time.monotonic()

        if request.mode == "image_to_video" and request.start_frame_bytes:
            model = self.I2V_MODEL
            arguments = self._build_i2v_args(request)
        else:
            model = self.T2V_MODEL
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
            raise RuntimeError(f"Kling returned no video URL: {result}")

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
                "quality_mode": request.provider_options.get("quality_mode", "balanced"),
            },
        )

        logger.info(
            "kling generate: model=%s latency=%dms size=%dKB",
            model, total_latency, len(video_bytes) // 1024,
        )

        return VideoGenerationResponse(
            video=video,
            model=model,
            provider="kling",
            latency_ms=total_latency,
            cost_estimate=0.04,
            metadata={"fal_request_id": result.get("request_id", "")},
        )

    def _resolve_negative(self, request: VideoGenerationRequest) -> str:
        """Merge request negative with baseline, deduplicating tokens."""
        baseline_tokens = [t.strip() for t in _DEFAULT_VIDEO_NEGATIVE.split(",")]
        user_tokens = []
        if request.negative_prompt:
            user_tokens = [t.strip() for t in request.negative_prompt.split(",") if t.strip()]

        seen: set[str] = set()
        merged: list[str] = []
        for t in user_tokens + baseline_tokens:
            key = t.lower()
            if key and key not in seen:
                seen.add(key)
                merged.append(t)
        return ", ".join(merged)

    def _resolve_cfg(self, request: VideoGenerationRequest) -> float:
        """Determine cfg_scale from explicit option > quality mode > default."""
        if "cfg_scale" in request.provider_options:
            return float(request.provider_options["cfg_scale"])
        mode = request.provider_options.get("quality_mode", "balanced")
        return _CFG_DEFAULTS.get(mode, 0.5)

    def _build_i2v_args(self, request: VideoGenerationRequest) -> dict[str, Any]:
        mime = request.start_frame_mime or "image/png"
        b64 = base64.b64encode(request.start_frame_bytes).decode()
        data_uri = f"data:{mime};base64,{b64}"

        duration = "10" if request.duration_sec >= 9 else "5"

        args: dict[str, Any] = {
            "prompt": request.prompt,
            "image_url": data_uri,
            "duration": duration,
            "negative_prompt": self._resolve_negative(request),
            "cfg_scale": self._resolve_cfg(request),
        }

        _internal_keys = {"quality_mode", "cfg_scale", "negative_video", "aspect_ratio"}
        for k, v in request.provider_options.items():
            if k not in _internal_keys and k not in args:
                args[k] = v
        return args

    def _build_t2v_args(self, request: VideoGenerationRequest) -> dict[str, Any]:
        duration = "10" if request.duration_sec >= 9 else "5"
        ratio = request.provider_options.get("aspect_ratio", "16:9")

        args: dict[str, Any] = {
            "prompt": request.prompt,
            "duration": duration,
            "aspect_ratio": ratio,
            "negative_prompt": self._resolve_negative(request),
            "cfg_scale": self._resolve_cfg(request),
        }

        _internal_keys = {"quality_mode", "cfg_scale", "negative_video", "aspect_ratio"}
        for k, v in request.provider_options.items():
            if k not in _internal_keys and k not in args:
                args[k] = v
        return args

    async def health_check(self) -> bool:
        try:
            import fal_client
            os.environ["FAL_KEY"] = self._api_key
            return True
        except Exception:
            return False
