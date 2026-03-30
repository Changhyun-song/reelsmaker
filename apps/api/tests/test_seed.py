"""Unit tests for seed data definitions — original demo + 3 evaluation projects."""
import pytest

from app.seed import (
    GLOBAL_PRESETS,
    DEMO_PROJECT,
    DEMO_PLAN_JSON,
    DEMO_SCENES,
    DEMO_SHOTS,
    DEMO_SCRIPT_INPUT,
)
from app.seed_evaluation import EVAL_PROJECTS, EXPLAINER, EMOTIONAL, PRODUCT_AD


# ── Global presets ────────────────────────────────────


def test_global_presets_have_required_fields():
    required = {"name", "description", "prompt_prefix", "negative_prompt"}
    for preset in GLOBAL_PRESETS:
        missing = required - set(preset.keys())
        assert not missing, f"Preset '{preset['name']}' missing: {missing}"


def test_global_presets_unique_names():
    names = [p["name"] for p in GLOBAL_PRESETS]
    assert len(names) == len(set(names)), "Duplicate preset names"


# ── Original demo project ────────────────────────────


def test_demo_project_has_title():
    assert DEMO_PROJECT["title"]
    assert len(DEMO_PROJECT["title"]) > 0


def test_demo_plan_sections_match_scenes():
    assert len(DEMO_PLAN_JSON["sections"]) == len(DEMO_SCENES)


def test_demo_plan_total_duration():
    total = sum(s["duration_sec"] for s in DEMO_PLAN_JSON["sections"])
    assert abs(total - DEMO_PLAN_JSON["estimated_duration_sec"]) <= 2


def test_demo_scenes_ordered():
    for i, scene in enumerate(DEMO_SCENES):
        assert scene["order_index"] == i


def test_demo_shots_cover_all_scenes():
    for i in range(len(DEMO_SCENES)):
        assert i in DEMO_SHOTS, f"No shots for scene {i}"
        assert len(DEMO_SHOTS[i]) > 0


def test_demo_shot_durations_match_scenes():
    for i, scene in enumerate(DEMO_SCENES):
        shot_dur = sum(s["duration_sec"] for s in DEMO_SHOTS[i])
        scene_dur = scene["duration_estimate_sec"]
        assert abs(shot_dur - scene_dur) <= 2, (
            f"Scene {i}: shot total {shot_dur}s vs scene {scene_dur}s"
        )


def test_demo_script_input_has_topic():
    assert DEMO_SCRIPT_INPUT["topic"]
    assert DEMO_SCRIPT_INPUT["duration_sec"] > 0


# ═══════════════════════════════════════════════════════
# Evaluation projects — parametrized tests
# ═══════════════════════════════════════════════════════

_EVAL_IDS = ["explainer", "emotional", "product_ad"]


@pytest.fixture(params=zip(_EVAL_IDS, EVAL_PROJECTS), ids=_EVAL_IDS)
def eval_data(request):
    """Yield (name, data_dict) for each evaluation project."""
    return request.param


# ── Structure integrity ───────────────────────────────


def test_eval_project_has_title(eval_data):
    name, data = eval_data
    assert data["project"]["title"], f"{name}: missing title"


def test_eval_project_has_eval_tag(eval_data):
    _, data = eval_data
    assert "[Eval]" in data["project"]["title"]


def test_eval_plan_sections_match_scenes(eval_data):
    name, data = eval_data
    assert len(data["plan_json"]["sections"]) == len(data["scenes"]), (
        f"{name}: plan sections ({len(data['plan_json']['sections'])}) != "
        f"scenes ({len(data['scenes'])})"
    )


def test_eval_scenes_ordered(eval_data):
    name, data = eval_data
    for i, scene in enumerate(data["scenes"]):
        assert scene["order_index"] == i, f"{name}: scene {i} wrong order_index"


def test_eval_shots_cover_all_scenes(eval_data):
    name, data = eval_data
    for i in range(len(data["scenes"])):
        assert i in data["shots"], f"{name}: no shots for scene {i}"
        assert len(data["shots"][i]) > 0, f"{name}: empty shots for scene {i}"


# ── Duration consistency ──────────────────────────────


def test_eval_plan_total_duration(eval_data):
    name, data = eval_data
    total = sum(s["duration_sec"] for s in data["plan_json"]["sections"])
    target = data["plan_json"]["estimated_duration_sec"]
    assert abs(total - target) <= 2, (
        f"{name}: plan section total {total}s vs target {target}s"
    )


def test_eval_scene_durations_match_target(eval_data):
    name, data = eval_data
    scene_total = sum(s["duration_estimate_sec"] for s in data["scenes"])
    target = data["script_input"]["duration_sec"]
    assert abs(scene_total - target) <= 3, (
        f"{name}: scene total {scene_total}s vs target {target}s"
    )


def test_eval_shot_durations_match_scenes(eval_data):
    name, data = eval_data
    for i, scene in enumerate(data["scenes"]):
        shot_dur = sum(s["duration_sec"] for s in data["shots"][i])
        scene_dur = scene["duration_estimate_sec"]
        assert abs(shot_dur - scene_dur) <= 2, (
            f"{name} scene {i}: shot total {shot_dur}s vs scene {scene_dur}s"
        )


# ── FrameSpec coverage ────────────────────────────────


def test_eval_frames_exist(eval_data):
    name, data = eval_data
    assert "frames" in data, f"{name}: missing frames dict"
    assert len(data["frames"]) > 0, f"{name}: empty frames dict"


def test_eval_every_shot_has_frames(eval_data):
    name, data = eval_data
    for si, shots in data["shots"].items():
        for shot in shots:
            shi = shot["order_index"]
            key = (si, shi)
            assert key in data["frames"], (
                f"{name}: no frames for scene {si} shot {shi}"
            )
            assert len(data["frames"][key]) >= 2, (
                f"{name}: scene {si} shot {shi} needs at least start+end frames"
            )


def test_eval_frame_roles_include_start_end(eval_data):
    name, data = eval_data
    for (si, shi), frames in data["frames"].items():
        roles = {f["frame_role"] for f in frames}
        assert "start" in roles, (
            f"{name}: scene {si} shot {shi} missing start frame"
        )
        assert "end" in roles, (
            f"{name}: scene {si} shot {shi} missing end frame"
        )


def test_eval_frame_required_fields(eval_data):
    name, data = eval_data
    required = {"order_index", "frame_role", "composition", "lighting", "mood"}
    for (si, shi), frames in data["frames"].items():
        for f in frames:
            missing = required - set(f.keys())
            assert not missing, (
                f"{name}: scene {si} shot {shi} frame {f.get('order_index')} "
                f"missing: {missing}"
            )


# ── Script input ──────────────────────────────────────


def test_eval_script_input_has_topic(eval_data):
    name, data = eval_data
    assert data["script_input"]["topic"], f"{name}: missing topic"
    assert data["script_input"]["duration_sec"] > 0, f"{name}: invalid duration"


# ── Character ─────────────────────────────────────────


def test_eval_character_exists(eval_data):
    name, data = eval_data
    assert "character" in data, f"{name}: missing character"
    assert data["character"]["name"], f"{name}: character missing name"
    assert data["character"]["role"] == "narrator"


# ── Cross-project uniqueness ─────────────────────────


def test_eval_projects_unique_titles():
    titles = [d["project"]["title"] for d in EVAL_PROJECTS]
    assert len(titles) == len(set(titles)), "Duplicate evaluation project titles"


def test_eval_projects_count():
    assert len(EVAL_PROJECTS) == 3
