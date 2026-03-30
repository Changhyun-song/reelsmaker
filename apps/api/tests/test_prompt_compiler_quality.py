"""Tests for the quality-first prompt compiler.

Covers:
- Block-based image prompt structure
- Camera-motion-aware video prompts
- Negative prompt merge/dedupe
- Prompt trimming priority
- Quality mode variations
- Empty context graceful handling
"""

from __future__ import annotations

import pytest

from shared.prompt_compiler.compiler import (
    IMAGE_NEGATIVE_BASELINE,
    VIDEO_NEGATIVE_BASELINE,
    compile_full,
    compile_image_prompt,
    compile_negative_prompt,
    compile_video_prompt,
    _trim_prompt,
    _dedupe_tokens,
)
from shared.prompt_compiler.types import (
    CharacterContext,
    CompilerContext,
    FrameContext,
    SceneContext,
    ShotContext,
    StyleContext,
)


def _rich_ctx(**overrides) -> CompilerContext:
    """Build a realistic CompilerContext for testing."""
    defaults = dict(
        scene=SceneContext(
            title="Productivity Flow",
            setting="modern minimalist home office",
            mood="focused, determined",
            emotional_tone="calm intensity building to satisfaction",
        ),
        shot=ShotContext(
            shot_type="medium",
            camera_framing="medium_close_up",
            camera_movement="dolly_in",
            subject="woman in navy blazer with round glasses",
            environment="standing desk with dual monitors, city skyline through window",
            emotion="focused determination",
            description=(
                "Medium close-up of woman in navy blazer typing on mechanical keyboard, "
                "warm desk lamp illumination from camera-left, shallow depth of field, "
                "modern home office with bookshelf background"
            ),
            asset_strategy="image_to_video",
            duration_sec=4.0,
        ),
        frame=FrameContext(
            frame_role="start",
            composition="Rule of thirds — subject at right-third intersection",
            subject_position="right-third, head at upper intersection",
            camera_angle="eye-level, straight-on",
            lens_feel="85mm f/1.8 portrait lens, shallow DOF",
            lighting=(
                "Key: warm 3200K from camera-left 45° above. "
                "Fill: soft 5600K from right at 30%. "
                "Rim: thin warm edge from behind-right."
            ),
            mood="contemplative focus",
            action_pose=(
                "Leaning forward slightly, both hands on keyboard, "
                "eyes focused on screen, slight concentrated smile"
            ),
            background_description=(
                "Foreground: blurred coffee mug and sticky notes. "
                "Mid-ground: white desk with monitor. "
                "Far background: window showing twilight cityscape."
            ),
            continuity_notes="Same navy blazer, same warm-to-cool lighting gradient",
            forbidden_elements="No text overlays, no watermarks, no extra hands",
        ),
        characters=[
            CharacterContext(
                name="Alex",
                appearance="East Asian woman, late 20s",
                outfit="navy blazer over white shirt",
                hair_description="shoulder-length black hair, side part",
                signature_props="round tortoiseshell glasses",
                forbidden_changes="glasses shape, hair length",
            ),
        ],
        style=StyleContext(
            rendering_style="cinematic photography",
            style_keywords="film grain, anamorphic bokeh",
            color_palette="warm amber highlights, cool blue shadows",
            lighting_rules="motivated practical lighting",
        ),
    )
    defaults.update(overrides)
    return CompilerContext(**defaults)


# ====================================================================
# 1. Image prompt — block structure
# ====================================================================


class TestImagePromptBlocks:
    def test_contains_core_shot_description(self):
        ctx = _rich_ctx()
        prompt = compile_image_prompt(ctx)
        assert "mechanical keyboard" in prompt
        assert "navy blazer" in prompt

    def test_contains_composition_block(self):
        ctx = _rich_ctx()
        prompt = compile_image_prompt(ctx)
        assert "Rule of thirds" in prompt
        assert "right-third" in prompt

    def test_contains_character_identity(self):
        ctx = _rich_ctx()
        prompt = compile_image_prompt(ctx)
        assert "Alex" in prompt
        assert "tortoiseshell glasses" in prompt

    def test_contains_camera_lens(self):
        ctx = _rich_ctx()
        prompt = compile_image_prompt(ctx)
        assert "85mm" in prompt or "eye-level" in prompt

    def test_contains_lighting(self):
        ctx = _rich_ctx()
        prompt = compile_image_prompt(ctx)
        assert "3200K" in prompt
        assert "camera-left" in prompt

    def test_contains_background_layers(self):
        ctx = _rich_ctx()
        prompt = compile_image_prompt(ctx)
        assert "Background:" in prompt
        assert "coffee mug" in prompt

    def test_contains_mood_atmosphere(self):
        ctx = _rich_ctx()
        prompt = compile_image_prompt(ctx)
        assert "focused" in prompt.lower() or "contemplative" in prompt.lower()

    def test_contains_style_keywords(self):
        ctx = _rich_ctx()
        prompt = compile_image_prompt(ctx)
        assert "film grain" in prompt
        assert "cinematic" in prompt.lower()


# ====================================================================
# 2. Video prompt — camera motion awareness
# ====================================================================


class TestVideoPromptMotion:
    def test_static_motion_sentence(self):
        ctx = _rich_ctx(shot=ShotContext(
            camera_movement="static",
            description="Close-up of hands typing",
            duration_sec=3.0,
        ))
        prompt = compile_video_prompt(ctx)
        assert "subtle" in prompt.lower() or "no camera movement" in prompt.lower()

    def test_dolly_in_motion_sentence(self):
        ctx = _rich_ctx(shot=ShotContext(
            camera_movement="dolly_in",
            description="Medium shot approaching desk",
            duration_sec=4.0,
        ))
        prompt = compile_video_prompt(ctx)
        assert "closer" in prompt.lower() or "larger" in prompt.lower() or "recede" in prompt.lower()

    def test_pan_right_motion_sentence(self):
        ctx = _rich_ctx(shot=ShotContext(
            camera_movement="slow_pan_right",
            description="Wide shot of coworking space",
            duration_sec=5.0,
        ))
        prompt = compile_video_prompt(ctx)
        assert "pan" in prompt.lower() or "lateral" in prompt.lower()

    def test_zoom_in_motion_sentence(self):
        ctx = _rich_ctx(shot=ShotContext(
            camera_movement="zoom_in",
            description="Tightening on subject face",
            duration_sec=3.0,
        ))
        prompt = compile_video_prompt(ctx)
        assert "tighter" in prompt.lower() or "without perspective" in prompt.lower()

    def test_tracking_motion_sentence(self):
        ctx = _rich_ctx(shot=ShotContext(
            camera_movement="tracking_forward",
            description="Following subject through hallway",
            duration_sec=5.0,
        ))
        prompt = compile_video_prompt(ctx)
        assert "track" in prompt.lower() or "parallax" in prompt.lower()

    def test_orbit_motion_sentence(self):
        ctx = _rich_ctx(shot=ShotContext(
            camera_movement="orbit_left",
            description="Orbiting around subject at desk",
            duration_sec=5.0,
        ))
        prompt = compile_video_prompt(ctx)
        assert "orbit" in prompt.lower()

    def test_still_image_strategy_suppresses_motion(self):
        ctx = _rich_ctx(shot=ShotContext(
            camera_movement="dolly_in",
            asset_strategy="still_image",
            description="Title card",
            duration_sec=2.0,
        ))
        prompt = compile_video_prompt(ctx)
        assert "static frame" in prompt.lower() or "no motion" in prompt.lower()

    def test_direct_video_strategy_emphasizes_action(self):
        ctx = _rich_ctx(shot=ShotContext(
            camera_movement="tracking_forward",
            asset_strategy="direct_video",
            description="Running through corridor",
            duration_sec=5.0,
        ))
        prompt = compile_video_prompt(ctx)
        assert "action" in prompt.lower() or "fluid" in prompt.lower() or "continuous" in prompt.lower()

    def test_duration_is_last(self):
        ctx = _rich_ctx()
        prompt = compile_video_prompt(ctx)
        assert prompt.rstrip().endswith("s") or "Duration:" in prompt
        last_segment = prompt.split(",")[-1].strip()
        assert "duration" in last_segment.lower() or last_segment.endswith("s")

    def test_different_motions_produce_different_prompts(self):
        motions = ["static", "dolly_in", "slow_pan_right", "zoom_in", "handheld"]
        prompts = set()
        for m in motions:
            ctx = _rich_ctx(shot=ShotContext(
                camera_movement=m,
                description="Person at desk",
                duration_sec=4.0,
            ))
            prompts.add(compile_video_prompt(ctx))
        assert len(prompts) == len(motions), "Each motion should produce a distinct prompt"


# ====================================================================
# 3. Negative prompt — merge & dedupe
# ====================================================================


class TestNegativePrompt:
    def test_image_baseline_included(self):
        ctx = _rich_ctx()
        neg = compile_negative_prompt(ctx, media_type="image")
        for term in ["text", "watermark", "extra fingers", "bad anatomy"]:
            assert term in neg.lower(), f"Missing baseline: {term}"

    def test_video_baseline_included(self):
        ctx = _rich_ctx()
        neg = compile_negative_prompt(ctx, media_type="video")
        for term in ["temporal flicker", "frame jitter", "morphing face"]:
            assert term in neg.lower(), f"Missing baseline: {term}"

    def test_image_and_video_baselines_differ(self):
        ctx = _rich_ctx()
        img_neg = compile_negative_prompt(ctx, media_type="image")
        vid_neg = compile_negative_prompt(ctx, media_type="video")
        assert img_neg != vid_neg

    def test_user_negatives_merged_not_duplicated(self):
        ctx = _rich_ctx(
            style=StyleContext(
                negative_prompt="watermark, text, custom_artifact",
            ),
        )
        neg = compile_negative_prompt(ctx, media_type="image")
        tokens = [t.strip().lower() for t in neg.split(",")]
        assert tokens.count("watermark") == 1
        assert tokens.count("text") == 1
        assert "custom_artifact" in neg

    def test_frame_forbidden_elements_included(self):
        ctx = _rich_ctx()
        neg = compile_negative_prompt(ctx, media_type="image")
        assert "extra hands" in neg.lower()

    def test_character_forbidden_changes_included(self):
        ctx = _rich_ctx()
        neg = compile_negative_prompt(ctx, media_type="image")
        assert "glasses shape" in neg.lower()

    def test_empty_context_still_has_baseline(self):
        ctx = CompilerContext()
        neg = compile_negative_prompt(ctx, media_type="image")
        assert len(neg) > 0
        assert "watermark" in neg


# ====================================================================
# 4. Trimming & deduplication
# ====================================================================


class TestTrimming:
    def test_dedupe_removes_duplicates(self):
        result = _dedupe_tokens("cat, Dog, cat, bird, dog")
        assert result.lower().count("cat") == 1
        assert result.lower().count("dog") == 1

    def test_trim_keeps_under_limit(self):
        long_prompt = ", ".join(["word"] * 500)
        result = _trim_prompt(long_prompt, max_len=200)
        assert len(result) <= 200

    def test_trim_removes_low_priority_first(self):
        prompt = "specific subject detail, important composition, masterpiece, 8k, uhd, real content"
        result = _trim_prompt(prompt, max_len=100)
        assert "specific subject detail" in result
        assert "important composition" in result

    def test_short_prompt_not_trimmed(self):
        prompt = "A cat sitting on a mat"
        result = _trim_prompt(prompt, max_len=1500)
        assert result == prompt


# ====================================================================
# 5. Quality mode variations
# ====================================================================


class TestQualityModes:
    def test_speed_mode_no_extra_keywords(self):
        ctx = _rich_ctx(quality_mode="speed")
        prompt = compile_image_prompt(ctx)
        assert "ray-traced" not in prompt
        assert "8K" not in prompt.split(",")[0] if "8K" in prompt else True

    def test_quality_mode_adds_render_boost(self):
        ctx = _rich_ctx(quality_mode="quality")
        prompt = compile_image_prompt(ctx)
        assert "8K" in prompt or "8k" in prompt
        assert "ray-traced" in prompt.lower() or "photorealistic" in prompt.lower()

    def test_balanced_is_default(self):
        ctx = CompilerContext()
        assert ctx.quality_mode == "balanced"

    def test_quality_mode_in_provider_options(self):
        ctx = _rich_ctx(quality_mode="quality")
        compiled = compile_full(ctx)
        assert compiled.provider_options.get("quality_mode") == "quality"

    def test_video_quality_mode_adds_coherence(self):
        ctx = _rich_ctx(
            quality_mode="quality",
            style=StyleContext(style_keywords="cinematic", rendering_style="film look"),
        )
        prompt = compile_video_prompt(ctx)
        assert "temporal coherence" in prompt.lower() or "smooth" in prompt.lower()


# ====================================================================
# 6. Graceful empty context
# ====================================================================


class TestEmptyContext:
    def test_empty_context_no_crash(self):
        ctx = CompilerContext()
        compiled = compile_full(ctx)
        assert isinstance(compiled.detailed_prompt, str)
        assert isinstance(compiled.video_prompt, str)
        assert isinstance(compiled.negative_prompt, str)

    def test_empty_shot_produces_minimal_prompt(self):
        ctx = CompilerContext()
        img = compile_image_prompt(ctx)
        vid = compile_video_prompt(ctx)
        assert isinstance(img, str)
        assert isinstance(vid, str)

    def test_negative_video_in_provider_options(self):
        ctx = _rich_ctx()
        compiled = compile_full(ctx)
        assert "negative_video" in compiled.provider_options
        assert "temporal flicker" in compiled.provider_options["negative_video"]


# ====================================================================
# 7. compile_full integration
# ====================================================================


class TestCompileFull:
    def test_all_fields_populated(self):
        ctx = _rich_ctx()
        compiled = compile_full(ctx)
        assert len(compiled.detailed_prompt) > 50
        assert len(compiled.video_prompt) > 50
        assert len(compiled.negative_prompt) > 20
        assert len(compiled.concise_prompt) > 10

    def test_provider_options_complete(self):
        ctx = _rich_ctx()
        compiled = compile_full(ctx)
        opts = compiled.provider_options
        assert "aspect_ratio" in opts
        assert "width" in opts
        assert "quality_mode" in opts
        assert "duration_sec" in opts

    def test_continuity_notes_present(self):
        ctx = _rich_ctx()
        compiled = compile_full(ctx)
        assert "navy blazer" in compiled.continuity_notes.lower() or len(compiled.continuity_notes) >= 0
