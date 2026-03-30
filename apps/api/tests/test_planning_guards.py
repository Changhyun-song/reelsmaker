"""Tests for semantic planning guards.

Each stage (script, scene, shot, frame) has ≥1 positive and ≥1 negative case
verifying that the guards catch vague/generic content while passing good output.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from shared.qa.planning_guards import (
    validate_frame_spec_semantic,
    validate_scene_breakdown_semantic,
    validate_script_plan_semantic,
    validate_shot_breakdown_semantic,
)


# ── Lightweight stubs ────────────────────────────────
# We use SimpleNamespace-like objects to mimic Pydantic models since the guards
# use getattr() and don't require real model instances.


class _Obj:
    """Attribute bag for building test fixtures."""

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


# ====================================================================
# 1. Script Plan
# ====================================================================


class TestScriptPlanGuard:
    """validate_script_plan_semantic tests."""

    def _good_plan(self):
        return _Obj(
            hook="Did you know 90% of startups fail within the first year?",
            sections=[
                _Obj(
                    visual_notes=(
                        "[Close-up] Smartphone screen showing Notion app in dark mode. "
                        "Lighting: soft blue screen glow on face. Camera: slow dolly in."
                    ),
                ),
                _Obj(
                    visual_notes=(
                        "[Medium] Developer typing on mechanical keyboard at standing desk. "
                        "Lighting: warm desk lamp from left. Camera: static tripod."
                    ),
                ),
            ],
            narration_draft="Did you know 90% of startups fail? Let me show you why.",
        )

    def test_good_plan_passes(self):
        errors = validate_script_plan_semantic(self._good_plan())
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_generic_hook_rejected(self):
        plan = self._good_plan()
        plan.hook = "안녕하세요 여러분, 오늘은 스타트업에 대해 이야기하겠습니다."
        errors = validate_script_plan_semantic(plan)
        assert any("generic opener" in e.lower() for e in errors), errors

    def test_short_visual_notes_rejected(self):
        plan = self._good_plan()
        plan.sections[0].visual_notes = "Show the app"
        errors = validate_script_plan_semantic(plan)
        assert any("too short" in e.lower() for e in errors), errors

    def test_generic_visual_notes_rejected(self):
        plan = self._good_plan()
        plan.sections[0].visual_notes = (
            "Show relevant image of the product being used in context"
        )
        errors = validate_script_plan_semantic(plan)
        assert any("generic phrase" in e.lower() or "lacks required format" in e.lower() for e in errors), errors

    def test_missing_format_visual_notes(self):
        plan = self._good_plan()
        plan.sections[0].visual_notes = (
            "Developer sitting at desk working on computer with warm ambiance and soft music playing"
        )
        errors = validate_script_plan_semantic(plan)
        assert any("lacks required format" in e.lower() for e in errors), errors

    def test_vague_descriptor_rejected(self):
        plan = self._good_plan()
        plan.sections[0].visual_notes = (
            "[Wide] Beautiful shot of the stunning cityscape at night. "
            "Lighting: ambient. Camera: pan."
        )
        errors = validate_script_plan_semantic(plan)
        assert any("vague descriptor" in e.lower() for e in errors), errors


# ====================================================================
# 2. Scene Breakdown
# ====================================================================


class TestSceneBreakdownGuard:
    """validate_scene_breakdown_semantic tests."""

    def _good_output(self):
        return _Obj(
            scenes=[
                _Obj(
                    setting=(
                        "modern minimalist home office, white standing desk with single "
                        "ultrawide monitor, afternoon golden-hour sunlight through wooden blinds"
                    ),
                    visual_intent=(
                        "Close shots of hands on keyboard, floating code snippets overlaid, "
                        "warm amber 3200K palette with cool blue monitor accents, smooth slow push-in"
                    ),
                    mood="focused, determined",
                    transition_hint="dissolve",
                ),
                _Obj(
                    setting=(
                        "open-plan coworking space with exposed brick walls, scattered potted plants, "
                        "diffused fluorescent overhead lighting mixed with warm pendant bulbs"
                    ),
                    visual_intent=(
                        "Medium shots of collaborative whiteboard session, pastel markers on glass, "
                        "neutral 5000K daylight through skylights, gentle handheld camera movement"
                    ),
                    mood="collaborative, energetic",
                    transition_hint="none",
                ),
            ],
        )

    def test_good_output_passes(self):
        errors = validate_scene_breakdown_semantic(self._good_output())
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_generic_setting_rejected(self):
        output = self._good_output()
        output.scenes[0].setting = "an office"
        errors = validate_scene_breakdown_semantic(output)
        assert any("generic" in e.lower() and "setting" in e.lower() for e in errors), errors

    def test_short_visual_intent_rejected(self):
        output = self._good_output()
        output.scenes[0].visual_intent = "Show the workspace"
        errors = validate_scene_breakdown_semantic(output)
        assert any("too short" in e.lower() for e in errors), errors

    def test_abstract_visual_intent_rejected(self):
        output = self._good_output()
        output.scenes[0].visual_intent = (
            "Capture the essence of productivity and the feeling of being in flow "
            "while working on meaningful projects that matter"
        )
        errors = validate_scene_breakdown_semantic(output)
        assert any("abstract" in e.lower() for e in errors), errors

    def test_mood_jump_with_hard_cut_rejected(self):
        output = self._good_output()
        output.scenes[0].mood = "calm, peaceful"
        output.scenes[0].transition_hint = "cut"
        output.scenes[1].mood = "intense, explosive"
        errors = validate_scene_breakdown_semantic(output)
        assert any("mood shift" in e.lower() for e in errors), errors

    def test_mood_jump_with_dissolve_accepted(self):
        output = self._good_output()
        output.scenes[0].mood = "calm, peaceful"
        output.scenes[0].transition_hint = "dissolve"
        output.scenes[1].mood = "intense, explosive"
        errors = validate_scene_breakdown_semantic(output)
        mood_errors = [e for e in errors if "mood shift" in e.lower()]
        assert mood_errors == [], f"Dissolve should soften mood jump: {mood_errors}"


# ====================================================================
# 3. Shot Breakdown
# ====================================================================


class TestShotBreakdownGuard:
    """validate_shot_breakdown_semantic tests."""

    def _good_output(self):
        return _Obj(
            shots=[
                _Obj(
                    description=(
                        "Close-up of woman in navy blazer typing on mechanical keyboard, "
                        "warm desk lamp illumination from camera-left, shallow depth of field, "
                        "modern minimalist office background, focused productivity mood"
                    ),
                    subject="woman in navy blazer with round glasses",
                    camera_framing="close_up",
                    narration_segment="첫 번째 단계는 아이디어를 검증하는 것입니다.",
                ),
                _Obj(
                    description=(
                        "Medium shot of laptop screen showing analytics dashboard with "
                        "colorful charts, soft ambient room lighting from overhead, "
                        "dark workspace environment, data-driven analytical mood"
                    ),
                    subject="laptop screen displaying real-time analytics dashboard",
                    camera_framing="medium",
                    narration_segment="데이터를 통해 시장의 반응을 확인합니다.",
                ),
                _Obj(
                    description=(
                        "Wide establishing shot of modern coworking space with large windows, "
                        "multiple people working at standing desks with dual monitors, "
                        "natural afternoon sunlight streaming through floor-to-ceiling windows, "
                        "warm collaborative atmosphere with soft overhead lighting"
                    ),
                    subject="modern coworking space interior with multiple workstations",
                    camera_framing="wide",
                    narration_segment="팀과 함께 빠르게 실행에 옮깁니다.",
                ),
            ],
        )

    def test_good_output_passes(self):
        errors = validate_shot_breakdown_semantic(self._good_output())
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_short_description_rejected(self):
        output = self._good_output()
        output.shots[0].description = "Person at desk working"
        errors = validate_shot_breakdown_semantic(output)
        assert any("too short" in e.lower() for e in errors), errors

    def test_generic_subject_rejected(self):
        output = self._good_output()
        output.shots[0].subject = "a person"
        errors = validate_shot_breakdown_semantic(output)
        assert any("generic" in e.lower() and "subject" in e.lower() for e in errors), errors

    def test_three_consecutive_framing_rejected(self):
        output = self._good_output()
        output.shots[0].camera_framing = "close_up"
        output.shots[1].camera_framing = "close_up"
        output.shots[2].camera_framing = "close_up"
        errors = validate_shot_breakdown_semantic(output)
        assert any("consecutive" in e.lower() and "framing" in e.lower() for e in errors), errors

    def test_missing_lighting_in_description(self):
        output = self._good_output()
        output.shots[0].description = (
            "Close-up of woman in navy blazer typing on mechanical keyboard "
            "at modern minimalist desk with bookshelf behind, shallow depth of field, "
            "clean professional composition, neutral color palette"
        )
        errors = validate_shot_breakdown_semantic(output)
        has_missing_element = any("missing elements" in e.lower() for e in errors)
        assert has_missing_element, f"Should flag missing lighting/mood element: {errors}"

    def test_unbalanced_narration_flagged(self):
        output = self._good_output()
        output.shots[0].narration_segment = "A"
        output.shots[1].narration_segment = "B" * 500
        output.shots[2].narration_segment = "C"
        errors = validate_shot_breakdown_semantic(output)
        narr_errors = [e for e in errors if "disproportionately" in e.lower()]
        assert len(narr_errors) > 0, f"Expected narration imbalance error, got: {errors}"


# ====================================================================
# 4. Frame Spec
# ====================================================================


class TestFrameSpecGuard:
    """validate_frame_spec_semantic tests."""

    def _good_output(self):
        return _Obj(
            frames=[
                _Obj(
                    frame_role="start",
                    lighting=(
                        "Key: warm 3200K tungsten from camera-left 45° above. "
                        "Fill: soft cool 5600K bounced from right at 30% intensity. "
                        "Rim: thin warm edge highlight from behind-right."
                    ),
                    action_pose=(
                        "Woman leaning forward slightly, both hands resting on keyboard, "
                        "eyes focused on screen, slight concentrated smile, shoulders relaxed"
                    ),
                    background_description=(
                        "Foreground: blurred coffee mug and scattered sticky notes. "
                        "Mid-ground: white desk with dual monitor setup. "
                        "Far background: large window showing twilight city skyline."
                    ),
                    composition=(
                        "Rule of thirds — subject at right-third intersection, "
                        "desk items creating foreground depth, monitor as midground anchor"
                    ),
                    subject_position="Subject at right-third, head at upper intersection",
                ),
                _Obj(
                    frame_role="end",
                    lighting=(
                        "Key: warm 3200K from camera-left 45° (same as start). "
                        "Fill: soft cool 5600K from right. "
                        "Rim: accent edge from behind emphasizing hair outline."
                    ),
                    action_pose=(
                        "Woman leaning back slightly, right hand reaching for coffee mug, "
                        "left hand still on keyboard, gentle satisfied smile, head tilted 5° right"
                    ),
                    background_description=(
                        "Foreground: keyboard and mouse in soft focus. "
                        "Mid-ground: monitor displaying completed code. "
                        "Far background: city lights now more prominent as twilight deepens."
                    ),
                    composition=(
                        "Subject shifts to center-right, tighter framing showing upper body, "
                        "coffee mug now in foreground frame-left creating depth"
                    ),
                    subject_position="Subject at center-right, tighter than start frame",
                ),
            ],
        )

    def test_good_output_passes(self):
        errors = validate_frame_spec_semantic(self._good_output())
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_insufficient_lighting_roles_rejected(self):
        output = self._good_output()
        output.frames[0].lighting = "Warm light from the left side at 3200K color temperature, creating a pleasant glow"
        errors = validate_frame_spec_semantic(output)
        assert any("lighting role" in e.lower() for e in errors), errors

    def test_vague_lighting_rejected(self):
        output = self._good_output()
        output.frames[0].lighting = "Good lighting with nice ambient feel and studio lighting setup from multiple angles"
        errors = validate_frame_spec_semantic(output)
        assert any("vague" in e.lower() and "lighting" in e.lower() for e in errors), errors

    def test_emotion_only_pose_rejected(self):
        output = self._good_output()
        output.frames[0].action_pose = "Happy and excited about the discovery, feeling accomplished and proud"
        errors = validate_frame_spec_semantic(output)
        assert any("physical posture" in e.lower() or "action_pose" in e.lower() for e in errors), errors

    def test_flat_background_rejected(self):
        output = self._good_output()
        output.frames[0].background_description = (
            "Modern office with white walls and clean aesthetic, bright and airy space"
        )
        errors = validate_frame_spec_semantic(output)
        assert any("depth layer" in e.lower() for e in errors), errors

    def test_identical_start_end_rejected(self):
        output = self._good_output()
        output.frames[1].composition = output.frames[0].composition
        output.frames[1].subject_position = output.frames[0].subject_position
        errors = validate_frame_spec_semantic(output)
        assert any("identical composition" in e.lower() for e in errors), errors
