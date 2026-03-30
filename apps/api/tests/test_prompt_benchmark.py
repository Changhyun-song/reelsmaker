"""Tests for the prompt quality benchmark.

Validates that:
- Weak/generic prompts receive low scores
- Strong/detailed prompts receive high scores
- Scores are reproducible across identical runs
- Empty inputs degrade gracefully (no crashes)
- Score breakdown clearly separates quality tiers
"""

from __future__ import annotations

import pytest

from shared.qa.prompt_benchmark import (
    BenchmarkInput,
    BenchmarkScores,
    run_prompt_benchmark,
)
from shared.schemas.contracts import (
    FrameSpecItem,
    FrameSpecOutput,
    SceneBreakdownItem,
    SceneBreakdownOutput,
    ShotBreakdownItem,
    ShotBreakdownOutput,
    ScriptSection,
    ScriptPlanOutput,
)


# ── Fixtures: Weak prompt set ────────────────────────


def _weak_input() -> BenchmarkInput:
    """Minimal, vague prompts with almost no detail."""
    return BenchmarkInput(
        image_prompt="a person standing",
        video_prompt="show the scene",
        negative_prompt="bad",
        negative_video_prompt="",
        continuity_notes="",
    )


def _weak_with_plan() -> BenchmarkInput:
    """Weak prompts with planning outputs that are also vague."""
    script_plan = ScriptPlanOutput(
        title="My Video",
        summary="A video about something interesting.",
        hook="Watch this!",
        narrative_flow=["introduction", "main part"],
        sections=[
            ScriptSection(
                title="Intro",
                description="Introduction to the topic",
                narration="Today we will talk about something interesting that you need to know.",
                visual_notes="[Wide] Someone at a place. Lighting: natural. Camera: static.",
                duration_sec=10,
            ),
            ScriptSection(
                title="Main",
                description="The main content section",
                narration="Here is the main content where we discuss the topic in some detail.",
                visual_notes="[Medium] A person doing something. Lighting: good. Camera: medium.",
                duration_sec=15,
            ),
        ],
        ending_cta="Subscribe!",
        narration_draft=(
            "Today we will talk about something interesting that you need to know. "
            "Here is the main content where we discuss the topic in some detail."
        ),
        estimated_duration_sec=25,
    )

    scene_breakdown = SceneBreakdownOutput(
        scenes=[
            SceneBreakdownItem(
                scene_index=0,
                title="Scene 1",
                purpose="Show something",
                summary="A scene about stuff",
                narration_text="Let me tell you about stuff",
                setting="a room",
                mood="nice",
                emotional_tone="Calm and pleasant atmosphere",
                visual_intent="Warm palette, cozy vibes, relaxed 4000K",
                estimated_duration_sec=12,
            ),
            SceneBreakdownItem(
                scene_index=1,
                title="Scene 2",
                purpose="Show more stuff",
                summary="Another scene about things happening",
                narration_text="And here is the second part of the story",
                setting="another place",
                mood="ok",
                emotional_tone="Mildly engaging and somewhat neutral",
                visual_intent="Cool blue tones, distant city, 5600K daylight",
                estimated_duration_sec=13,
            ),
        ],
        total_duration_sec=25,
    )

    return BenchmarkInput(
        script_plan=script_plan,
        scene_breakdown=scene_breakdown,
        image_prompt="a person in a room",
        video_prompt="show the scene slowly",
        negative_prompt="bad quality",
        negative_video_prompt="",
    )


# ── Fixtures: Strong prompt set ──────────────────────


def _strong_input() -> BenchmarkInput:
    """Rich, detailed prompts covering all specificity axes."""
    shot_breakdown = ShotBreakdownOutput(
        shots=[
            ShotBreakdownItem(
                shot_index=0,
                purpose="Establish the workspace environment",
                duration_sec=4,
                shot_type="establishing",
                camera_framing="medium_wide",
                camera_motion="dolly_in",
                subject=(
                    "Young woman developer in navy blazer, "
                    "seated at standing desk with mechanical keyboard"
                ),
                environment=(
                    "Modern home office with white walls, floating wooden shelves, "
                    "large monitor displaying code, small potted succulent"
                ),
                emotion="focused determination",
                narration_segment="In the quiet of her home office, she begins another sprint.",
                transition_in="fade_in",
                transition_out="cut",
                asset_strategy="image_to_video",
                description=(
                    "Young woman developer in navy blazer typing on mechanical keyboard "
                    "at standing desk. Modern home office with white walls, floating wooden "
                    "shelves, large ultrawide monitor showing code editor. Warm golden-hour "
                    "light from camera-left window at 45°, cool fill light from monitor. "
                    "Focused, determined mood. Shallow DOF with soft bokeh on background shelves."
                ),
            ),
        ],
        total_duration_sec=4,
    )

    frame_spec = FrameSpecOutput(
        frames=[
            FrameSpecItem(
                frame_role="start",
                composition=(
                    "Rule of thirds — subject at right-third intersection, "
                    "leading lines from desk edge toward monitor"
                ),
                subject_position=(
                    "Right-third intersection, upper body filling center-right 40%"
                ),
                camera_angle="Eye-level, slightly right of center",
                lens_feel="85mm portrait, shallow DOF f/1.8, gentle bokeh on shelves",
                lighting=(
                    "Key: warm 3200K from camera-left window at 45°. "
                    "Fill: cool 5600K bounce from monitor screen. "
                    "Rim: thin edge light from behind-right at 135°."
                ),
                mood="focused concentration",
                action_pose=(
                    "Seated upright, both hands resting on mechanical keyboard, "
                    "slight forward lean, eyes fixed on monitor, relaxed shoulders"
                ),
                background_description=(
                    "Foreground: edge of standing desk with coffee mug. "
                    "Mid-ground: floating wooden shelves with tech books and small plant. "
                    "Far background: soft-focused white wall with warm ambient glow."
                ),
                continuity_notes=(
                    "Must maintain same blazer color and hair style across all frames. "
                    "Identity lock: consistent facial features, same skin tone throughout."
                ),
                forbidden_elements=(
                    "extra fingers, floating objects, text overlay, watermark, "
                    "second person, inconsistent shadow direction"
                ),
            ),
            FrameSpecItem(
                frame_role="end",
                composition=(
                    "Tighter framing — subject fills center-right 55%, "
                    "desk surface visible in lower third"
                ),
                subject_position=(
                    "Center-right, head and shoulders dominant, "
                    "keyboard hands visible at bottom"
                ),
                camera_angle="Eye-level, closer, slightly above",
                lens_feel="85mm portrait, shallow DOF f/1.8, tighter crop",
                lighting=(
                    "Key: warm 3200K from camera-left at 45° (unchanged). "
                    "Fill: slightly brighter monitor glow as code scrolls. "
                    "Rim: maintained edge light from behind-right."
                ),
                mood="satisfied accomplishment",
                action_pose=(
                    "Leaning back slightly, right hand lifting from keyboard, "
                    "subtle smile forming, eyes still on screen"
                ),
                background_description=(
                    "Foreground: mechanical keyboard in sharp detail. "
                    "Mid-ground: monitor edge with code visible. "
                    "Far background: same shelves, slightly more blurred from closer framing."
                ),
                continuity_notes="Same blazer, same hair, same desk setup as start frame",
                forbidden_elements=(
                    "changed clothing, different hair, extra limbs, "
                    "face distortion, temporal flicker"
                ),
            ),
        ],
    )

    return BenchmarkInput(
        shot_breakdown=shot_breakdown,
        frame_spec=frame_spec,
        image_prompt=(
            "Young woman developer in navy blazer typing on mechanical keyboard "
            "at standing desk. Rule of thirds composition, subject at right-third. "
            "[Developer: mid-20s, navy blazer, short dark hair, fair skin, always with: "
            "mechanical keyboard] Eye-level, 85mm portrait, shallow DOF f/1.8. "
            "Key: warm 3200K from camera-left 45°. Fill: cool 5600K from monitor. "
            "Rim: edge light from behind-right. Background: floating shelves with tech books, "
            "soft-focused white wall. Focused, determined mood, modern home office atmosphere. "
            "Cinematic quality, sharp detail, photorealistic rendering. "
            "[STYLE ANCHOR: cinematic photorealistic || COLOR LOCK: warm golden 3200K-5600K || "
            "CHARACTER LOCK: consistent identity]"
        ),
        video_prompt=(
            "Young woman developer typing on keyboard at standing desk. "
            "Camera physically moves closer — subject grows larger in frame, "
            "background recedes with natural parallax. Dolly in reveals focused expression. "
            "Action: leaning forward, both hands on keyboard, slight concentration. "
            "Eye-level, 85mm portrait. Background: modern home office with shelves. "
            "Focused, calm atmosphere. Cinematic quality, smooth motion. Duration: 4.0s"
        ),
        negative_prompt=(
            "text, watermark, logo, blurry, low detail, extra fingers, "
            "extra limbs, bad anatomy, duplicated subject, deformed face, "
            "asymmetrical eyes, floating objects, inconsistent shadows, "
            "second person, changed clothing"
        ),
        negative_video_prompt=(
            "temporal flicker, frame jitter, morphing face, warped hands, "
            "rubber limbs, sudden camera shake, inconsistent lighting, "
            "subtitle text, watermark, compression artifacts, "
            "face distortion, floating limbs"
        ),
        continuity_notes=(
            "STYLE ANCHOR: cinematic photorealistic || "
            "LIGHTING BASELINE: warm key from camera-left || "
            "CHARACTER LOCK: [Developer] consistent facial features, same navy blazer"
        ),
    )


def _strong_with_plan() -> BenchmarkInput:
    """Strong prompts augmented with rich planning data."""
    base = _strong_input()

    base.script_plan = ScriptPlanOutput(
        title="Deep Work: The Developer's Flow",
        summary="A cinematic short capturing the focused intensity of a developer in her element.",
        hook="What does true focus look like? 14 hours of deep work in 45 seconds.",
        narrative_flow=[
            "Open on the calm workspace before dawn",
            "Reveal the developer entering flow state",
            "Close on the satisfaction of shipping code",
        ],
        sections=[
            ScriptSection(
                title="The Workspace",
                description="Establishing the environment and setting the tone",
                narration="In the quiet hours before the world wakes, she sits at her desk.",
                visual_notes=(
                    "[Medium-wide] Woman developer at standing desk in modern home office. "
                    "Warm golden-hour light through window at camera-left 45°. "
                    "Lighting: Key 3200K window, Fill 5600K monitor. Camera: dolly in slowly."
                ),
                duration_sec=4,
            ),
            ScriptSection(
                title="The Flow",
                description="Capturing the intensity of focused coding",
                narration="Keystrokes become rhythm, code becomes craft.",
                visual_notes=(
                    "[Close-up] Hands on mechanical keyboard, screen reflections in eyes. "
                    "Lighting: warm 3200K key from left, cool 5600K fill from screen glow. "
                    "Camera: slow push in to extreme close-up of focused expression."
                ),
                duration_sec=4,
            ),
        ],
        ending_cta="Find your flow. Start shipping.",
        narration_draft=(
            "In the quiet hours before the world wakes, she sits at her desk. "
            "Keystrokes become rhythm, code becomes craft."
        ),
        estimated_duration_sec=8,
    )

    return base


# ── Test classes ─────────────────────────────────────


class TestWeakPrompts:
    """Weak/generic prompts should score low."""

    def test_weak_overall_below_40(self):
        result = run_prompt_benchmark(_weak_input())
        assert result.overall < 40, f"Weak prompt overall={result.overall} should be < 40"

    def test_weak_specificity_low(self):
        result = run_prompt_benchmark(_weak_input())
        assert result.specificity < 50, f"Weak specificity={result.specificity}"

    def test_weak_continuity_low(self):
        result = run_prompt_benchmark(_weak_input())
        assert result.continuity < 50, f"Weak continuity={result.continuity}"

    def test_weak_artifact_prevention_low(self):
        result = run_prompt_benchmark(_weak_input())
        assert result.artifact_prevention < 40, f"Weak artifact={result.artifact_prevention}"

    def test_weak_has_failure_reasons(self):
        result = run_prompt_benchmark(_weak_input())
        assert len(result.failure_reasons) >= 3, (
            f"Expected ≥3 failure reasons, got {len(result.failure_reasons)}"
        )

    def test_weak_with_plan_still_moderate(self):
        result = run_prompt_benchmark(_weak_with_plan())
        assert result.overall < 55, (
            f"Weak+plan overall={result.overall} should still be moderate"
        )


class TestStrongPrompts:
    """Strong/detailed prompts should score high."""

    def test_strong_overall_above_65(self):
        result = run_prompt_benchmark(_strong_input())
        assert result.overall > 65, f"Strong overall={result.overall} should be > 65"

    def test_strong_specificity_high(self):
        result = run_prompt_benchmark(_strong_input())
        assert result.specificity > 70, f"Strong specificity={result.specificity}"

    def test_strong_continuity_high(self):
        result = run_prompt_benchmark(_strong_input())
        assert result.continuity > 60, f"Strong continuity={result.continuity}"

    def test_strong_motion_clarity_high(self):
        result = run_prompt_benchmark(_strong_input())
        assert result.motion_clarity > 60, f"Strong motion={result.motion_clarity}"

    def test_strong_artifact_prevention_high(self):
        result = run_prompt_benchmark(_strong_input())
        assert result.artifact_prevention > 70, f"Strong artifact={result.artifact_prevention}"

    def test_strong_fewer_failure_reasons(self):
        weak = run_prompt_benchmark(_weak_input())
        strong = run_prompt_benchmark(_strong_input())
        assert len(strong.failure_reasons) < len(weak.failure_reasons), (
            f"Strong ({len(strong.failure_reasons)}) should have fewer "
            f"failures than weak ({len(weak.failure_reasons)})"
        )

    def test_strong_with_plan_even_higher(self):
        without_plan = run_prompt_benchmark(_strong_input())
        with_plan = run_prompt_benchmark(_strong_with_plan())
        assert with_plan.specificity >= without_plan.specificity, (
            f"Adding plan should not decrease specificity: "
            f"{with_plan.specificity} vs {without_plan.specificity}"
        )


class TestScoreSeparation:
    """Weak vs strong scores should show clear separation."""

    def test_overall_gap(self):
        weak = run_prompt_benchmark(_weak_input())
        strong = run_prompt_benchmark(_strong_input())
        gap = strong.overall - weak.overall
        assert gap > 30, (
            f"Gap between strong ({strong.overall}) and weak ({weak.overall}) "
            f"= {gap:.1f}, expected > 30"
        )

    def test_specificity_gap(self):
        weak = run_prompt_benchmark(_weak_input())
        strong = run_prompt_benchmark(_strong_input())
        gap = strong.specificity - weak.specificity
        assert gap > 25, f"Specificity gap={gap:.1f}, expected > 25"

    def test_artifact_prevention_gap(self):
        weak = run_prompt_benchmark(_weak_input())
        strong = run_prompt_benchmark(_strong_input())
        gap = strong.artifact_prevention - weak.artifact_prevention
        assert gap > 40, f"Artifact prevention gap={gap:.1f}, expected > 40"


class TestReproducibility:
    """Same input must produce identical scores every time."""

    def test_reproducible_weak(self):
        a = run_prompt_benchmark(_weak_input())
        b = run_prompt_benchmark(_weak_input())
        assert a.overall == b.overall
        assert a.specificity == b.specificity
        assert a.continuity == b.continuity
        assert a.motion_clarity == b.motion_clarity
        assert a.artifact_prevention == b.artifact_prevention

    def test_reproducible_strong(self):
        a = run_prompt_benchmark(_strong_input())
        b = run_prompt_benchmark(_strong_input())
        assert a.overall == b.overall
        assert a.specificity == b.specificity

    def test_to_dict_stable(self):
        a = run_prompt_benchmark(_strong_input()).to_dict()
        b = run_prompt_benchmark(_strong_input()).to_dict()
        for key in ["specificity", "continuity", "motion_clarity",
                     "artifact_prevention", "overall"]:
            assert a[key] == b[key], f"Mismatch on {key}: {a[key]} vs {b[key]}"


class TestEmptyInput:
    """Empty/missing data should not crash."""

    def test_completely_empty(self):
        result = run_prompt_benchmark(BenchmarkInput())
        assert result.overall == 0.0
        assert result.specificity == 0.0
        assert len(result.failure_reasons) > 0

    def test_only_image_prompt(self):
        result = run_prompt_benchmark(BenchmarkInput(
            image_prompt="a beautiful sunset over mountains with golden light"
        ))
        assert result.specificity > 0
        assert result.overall > 0

    def test_only_negative_prompt(self):
        result = run_prompt_benchmark(BenchmarkInput(
            negative_prompt=(
                "text, watermark, logo, blurry, extra fingers, "
                "extra limbs, bad anatomy, deformed face"
            ),
        ))
        assert result.artifact_prevention > 30


class TestScoreRange:
    """All scores must be 0-100."""

    def test_all_scores_in_range(self):
        for inp in [_weak_input(), _strong_input(), BenchmarkInput()]:
            result = run_prompt_benchmark(inp)
            for attr in ["specificity", "continuity", "motion_clarity",
                         "artifact_prevention", "overall"]:
                val = getattr(result, attr)
                assert 0 <= val <= 100, f"{attr}={val} out of range for {inp}"

    def test_failure_reasons_capped(self):
        result = run_prompt_benchmark(BenchmarkInput())
        assert len(result.failure_reasons) <= 10


class TestToDict:
    """to_dict() output format."""

    def test_has_all_keys(self):
        d = run_prompt_benchmark(_strong_input()).to_dict()
        expected_keys = {
            "specificity", "continuity", "motion_clarity",
            "artifact_prevention", "overall", "failure_reasons",
        }
        assert set(d.keys()) == expected_keys

    def test_values_are_rounded(self):
        d = run_prompt_benchmark(_strong_input()).to_dict()
        for key in ["specificity", "continuity", "motion_clarity",
                     "artifact_prevention", "overall"]:
            val = d[key]
            assert val == round(val, 1), f"{key}={val} not rounded to 1 decimal"
