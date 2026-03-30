"""Centralized provider factory — selects mock or real provider based on config.

Usage:
    from shared.providers.factory import get_image_provider, get_video_provider, get_tts_provider

Each function reads Settings to determine which provider to instantiate.
Falls back to mock if the required API key is missing.
"""

from __future__ import annotations

import logging

from shared.config import get_settings
from shared.providers.image_base import ImageProvider
from shared.providers.video_base import VideoProvider
from shared.providers.tts_base import TTSProvider

logger = logging.getLogger("reelsmaker.providers.factory")


# ── Image Providers ──────────────────────────────────


def get_image_provider() -> ImageProvider:
    """Return configured image provider (fal / openai / gemini / higgsfield / mock)."""
    settings = get_settings()
    choice = settings.image_provider.lower()

    if choice == "higgsfield":
        if not settings.higgsfield_api_key_id or not settings.higgsfield_api_key_secret:
            logger.warning("IMAGE_PROVIDER=higgsfield but HIGGSFIELD_API_KEY_ID/SECRET is empty — falling back to mock")
        else:
            try:
                from shared.providers.higgsfield_image import HiggsFieldImageProvider
                logger.info("Using Higgsfield image provider (model=%s)", settings.higgsfield_image_model)
                return HiggsFieldImageProvider(
                    api_key_id=settings.higgsfield_api_key_id,
                    api_key_secret=settings.higgsfield_api_key_secret,
                    default_model=settings.higgsfield_image_model,
                    timeout_sec=settings.provider_timeout_sec,
                )
            except Exception as exc:
                logger.warning("Failed to initialize Higgsfield image provider, falling back to mock: %s", exc)

    if choice == "fal":
        if not settings.fal_key:
            logger.warning("IMAGE_PROVIDER=fal but FAL_KEY is empty — falling back to mock")
        else:
            try:
                from shared.providers.fal_image import FalImageProvider
                logger.info("Using fal.ai image provider (model=%s)", settings.fal_image_model)
                return FalImageProvider(
                    api_key=settings.fal_key,
                    default_model=settings.fal_image_model,
                    timeout_sec=settings.provider_timeout_sec,
                )
            except Exception as exc:
                logger.warning("Failed to initialize fal provider, falling back to mock: %s", exc)

    if choice == "openai":
        if not settings.openai_api_key:
            logger.warning("IMAGE_PROVIDER=openai but OPENAI_API_KEY is empty — falling back to mock")
        else:
            try:
                from shared.providers.openai_image import OpenAIImageProvider
                logger.info("Using OpenAI image provider (model=%s)", settings.openai_image_model)
                return OpenAIImageProvider(
                    api_key=settings.openai_api_key,
                    default_model=settings.openai_image_model,
                    timeout_sec=settings.provider_timeout_sec,
                )
            except Exception as exc:
                logger.warning("Failed to initialize OpenAI image provider, falling back to mock: %s", exc)

    if choice == "gemini":
        if not settings.google_api_key:
            logger.warning("IMAGE_PROVIDER=gemini but GOOGLE_API_KEY is empty — falling back to mock")
        else:
            try:
                from shared.providers.gemini_image import GeminiImageProvider
                logger.info("Using Gemini image provider (model=%s)", settings.gemini_image_model)
                return GeminiImageProvider(
                    api_key=settings.google_api_key,
                    default_model=settings.gemini_image_model,
                    timeout_sec=settings.provider_timeout_sec,
                )
            except Exception as exc:
                logger.warning("Failed to initialize Gemini image provider, falling back to mock: %s", exc)

    from shared.providers.mock_image import MockImageProvider
    return MockImageProvider()


# ── Video Providers ──────────────────────────────────


def get_video_provider() -> VideoProvider:
    """Return configured video provider (runway / kling / luma / mock)."""
    settings = get_settings()
    choice = settings.video_provider.lower()

    if choice == "runway":
        if not settings.runway_api_key:
            logger.warning("VIDEO_PROVIDER=runway but RUNWAY_API_KEY is empty — falling back to mock")
        else:
            try:
                from shared.providers.runway_video import RunwayVideoProvider
                logger.info("Using Runway video provider (model=%s)", settings.runway_model)
                return RunwayVideoProvider(
                    api_key=settings.runway_api_key,
                    default_model=settings.runway_model,
                    timeout_sec=settings.provider_timeout_sec,
                )
            except Exception as exc:
                logger.warning("Failed to initialize Runway provider, falling back to mock: %s", exc)

    if choice == "kling":
        if not settings.fal_key:
            logger.warning("VIDEO_PROVIDER=kling but FAL_KEY is empty (Kling runs via fal.ai) — falling back to mock")
        else:
            try:
                from shared.providers.kling_video import KlingVideoProvider
                logger.info("Using Kling video provider (model=%s)", settings.kling_model)
                return KlingVideoProvider(
                    api_key=settings.fal_key,
                    default_model=settings.kling_model,
                    timeout_sec=settings.provider_timeout_sec,
                )
            except Exception as exc:
                logger.warning("Failed to initialize Kling provider, falling back to mock: %s", exc)

    if choice == "luma":
        if not settings.luma_api_key:
            logger.warning("VIDEO_PROVIDER=luma but LUMA_API_KEY is empty — falling back to mock")
        else:
            try:
                from shared.providers.luma_video import LumaVideoProvider
                logger.info("Using Luma video provider (model=%s)", settings.luma_model)
                return LumaVideoProvider(
                    api_key=settings.luma_api_key,
                    default_model=settings.luma_model,
                    timeout_sec=settings.provider_timeout_sec,
                )
            except Exception as exc:
                logger.warning("Failed to initialize Luma provider, falling back to mock: %s", exc)

    if choice == "higgsfield":
        if not settings.higgsfield_api_key_id or not settings.higgsfield_api_key_secret:
            logger.warning("VIDEO_PROVIDER=higgsfield but HIGGSFIELD_API_KEY_ID/SECRET is empty — falling back to mock")
        else:
            try:
                from shared.providers.higgsfield_video import HiggsFieldVideoProvider
                logger.info("Using Higgsfield video provider (model=%s)", settings.higgsfield_model)
                return HiggsFieldVideoProvider(
                    api_key_id=settings.higgsfield_api_key_id,
                    api_key_secret=settings.higgsfield_api_key_secret,
                    fal_key=settings.fal_key,
                    default_model=settings.higgsfield_model,
                    timeout_sec=settings.provider_timeout_sec,
                )
            except Exception as exc:
                logger.warning("Failed to initialize Higgsfield provider, falling back to mock: %s", exc)

    from shared.providers.mock_video import MockVideoProvider
    return MockVideoProvider()


# ── TTS Providers ────────────────────────────────────


def get_tts_provider() -> TTSProvider:
    """Return configured TTS provider (elevenlabs or mock)."""
    settings = get_settings()
    choice = settings.tts_provider.lower()

    if choice == "elevenlabs":
        if not settings.elevenlabs_api_key:
            logger.warning("TTS_PROVIDER=elevenlabs but ELEVENLABS_API_KEY is empty — falling back to mock")
        else:
            try:
                from shared.providers.elevenlabs_tts import ElevenLabsTTSProvider
                logger.info("Using ElevenLabs TTS provider (model=%s)", settings.elevenlabs_model)
                return ElevenLabsTTSProvider(
                    api_key=settings.elevenlabs_api_key,
                    default_model=settings.elevenlabs_model,
                    default_voice_id=settings.elevenlabs_default_voice,
                    timeout_sec=settings.provider_timeout_sec,
                )
            except Exception as exc:
                logger.warning("Failed to initialize ElevenLabs provider, falling back to mock: %s", exc)

    from shared.providers.mock_tts import MockTTSProvider
    return MockTTSProvider()
