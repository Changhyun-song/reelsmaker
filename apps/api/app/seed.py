"""Seed global style presets + demo project on first startup."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.style_preset import StylePreset
from shared.models.project import Project
from shared.models.script_version import ScriptVersion
from shared.models.scene import Scene
from shared.models.shot import Shot
from shared.models.character_profile import CharacterProfile

logger = logging.getLogger("reelsmaker.seed")

# ── Global Style Presets ──────────────────────────────

GLOBAL_PRESETS = [
    {
        "name": "Cinematic Realistic",
        "description": "영화적 사실주의 스타일. 자연스러운 조명과 깊은 피사계 심도.",
        "style_keywords": "cinematic, photorealistic, film grain, dramatic lighting",
        "color_palette": "rich warm tones, deep shadows, golden highlights",
        "rendering_style": "photorealistic 8K",
        "camera_language": "shallow depth of field, anamorphic lens flare",
        "lighting_rules": "natural light, golden hour, rim lighting",
        "negative_rules": "cartoon, anime, illustration, low quality, blurry",
        "prompt_prefix": "cinematic, photorealistic, 8k, film grain, dramatic lighting, shallow depth of field",
        "negative_prompt": "cartoon, anime, illustration, low quality, blurry",
        "model_preferences": {"image": "fal", "video": "runway"},
    },
    {
        "name": "Premium Product Ad",
        "description": "고급 제품 광고 스타일. 깔끔한 배경, 고급스러운 조명.",
        "style_keywords": "luxury, premium, clean, elegant, product photography",
        "color_palette": "neutral whites, soft grays, metallic accents",
        "rendering_style": "studio photography",
        "camera_language": "macro lens, product focus, clean background",
        "lighting_rules": "softbox lighting, rim light, gradient background",
        "negative_rules": "cluttered, noisy, low budget, amateur",
        "prompt_prefix": "luxury product photography, studio lighting, clean background, premium quality",
        "negative_prompt": "cluttered, noisy, low budget, amateur, cartoon",
        "model_preferences": {"image": "fal", "video": "runway"},
    },
    {
        "name": "Korean Webtoon",
        "description": "한국 웹툰 스타일. 선명한 선과 생동감 있는 색채.",
        "style_keywords": "webtoon, manhwa, korean illustration, vivid colors",
        "color_palette": "vivid pastels, clean whites, bold accents",
        "rendering_style": "digital illustration, webtoon style",
        "camera_language": "dynamic angles, dramatic perspective, close-ups",
        "lighting_rules": "cel shading, flat colors with soft gradients",
        "negative_rules": "photorealistic, 3d render, western comic",
        "prompt_prefix": "korean webtoon style, manhwa, clean lineart, vivid colors, digital illustration",
        "negative_prompt": "photorealistic, 3d render, western comic, sketch, rough",
        "model_preferences": {"image": "fal", "video": "runway"},
    },
    {
        "name": "Minimalist Infographic",
        "description": "미니멀 인포그래픽 스타일. 깔끔한 아이콘과 텍스트 레이아웃.",
        "style_keywords": "minimalist, infographic, flat design, icon, data visualization",
        "color_palette": "monochrome with one accent color, white space",
        "rendering_style": "flat vector, clean geometry",
        "camera_language": "straight-on, isometric, bird's eye view",
        "lighting_rules": "flat lighting, no shadows, clean contrast",
        "negative_rules": "photorealistic, complex textures, 3d, gradients",
        "prompt_prefix": "minimalist infographic, flat design, clean vector, modern icons",
        "negative_prompt": "photorealistic, complex, 3d render, gradients, shadows",
        "model_preferences": {"image": "fal", "video": "runway"},
    },
    {
        "name": "Anime",
        "description": "일본 애니메이션 스타일. 큰 눈, 선명한 색감, 역동적 구도.",
        "style_keywords": "anime, japanese animation, vivid, dynamic",
        "color_palette": "saturated colors, cherry blossom pink, sky blue",
        "rendering_style": "anime cel animation",
        "camera_language": "dynamic angles, speed lines, dramatic close-ups",
        "lighting_rules": "anime lighting, glow effects, rim light",
        "negative_rules": "photorealistic, western cartoon, blurry",
        "prompt_prefix": "anime style, detailed, vivid colors, dynamic composition, studio quality anime",
        "negative_prompt": "photorealistic, western cartoon, blurry, low quality",
        "model_preferences": {"image": "fal", "video": "runway"},
    },
]

# ── Demo Project Data ────────────────────────────────

DEMO_PROJECT = {
    "title": "Demo: 30초 AI 소개 영상",
    "description": "AI 기술의 현재와 미래를 소개하는 30초 숏폼 영상 데모 프로젝트입니다. "
    "seed 데이터로 생성되었으며 파이프라인 테스트에 사용할 수 있습니다.",
    "status": "scripting",
}

DEMO_SCRIPT_INPUT = {
    "topic": "2025년 AI 기술 트렌드와 일상 속 AI 활용법",
    "target_audience": "20~30대 직장인, 테크에 관심 있는 일반인",
    "tone": "감성적, 교육적, 활기찬",
    "duration_sec": 30,
    "format": "youtube_short",
    "language": "ko",
    "constraints": "",
}

DEMO_PLAN_JSON = {
    "title": "AI가 바꾸는 우리의 일상",
    "summary": "2025년 AI 기술이 어떻게 우리 삶에 녹아들고 있는지 감성적으로 보여주는 30초 영상",
    "hook": "당신이 오늘 아침 커피를 마시는 동안, AI는 이미 당신의 하루를 바꾸고 있습니다.",
    "narrative_flow": [
        "훅 — 일상 속 AI의 존재감을 환기",
        "전개 — 구체적 활용 사례 나열",
        "전환 — 감정적 연결과 미래 비전",
        "마무리 — 행동 유도 (CTA)",
    ],
    "sections": [
        {
            "title": "오프닝 — 일상의 AI",
            "description": "아침 루틴 속 AI 기술을 자연스럽게 보여준다",
            "narration": "오늘 아침, AI가 추천한 음악으로 눈을 뜨고, AI가 분석한 날씨로 옷을 골랐습니다.",
            "visual_notes": "아침 햇살이 드는 방, 스마트폰 알람, 커피 머신",
            "duration_sec": 8,
        },
        {
            "title": "전개 — 업무와 창작",
            "description": "업무와 창작 영역에서의 AI 활용",
            "narration": "회의록은 AI가 정리하고, 프레젠테이션은 AI와 함께 만듭니다. 당신은 더 중요한 일에 집중할 수 있죠.",
            "visual_notes": "사무실, 노트북 화면, AI 어시스턴트 인터페이스",
            "duration_sec": 10,
        },
        {
            "title": "전환 — 감성 연결",
            "description": "기술 너머의 인간적 가치",
            "narration": "기술이 발전할수록, 우리에게 진짜 중요한 건 사람과의 연결입니다.",
            "visual_notes": "가족 식사, 친구와의 대화, 따뜻한 조명",
            "duration_sec": 7,
        },
        {
            "title": "마무리 — CTA",
            "description": "행동 유도와 마무리",
            "narration": "AI와 함께하는 내일, 지금 시작하세요.",
            "visual_notes": "미래적 도시 풍경, 로고, 구독 유도",
            "duration_sec": 5,
        },
    ],
    "ending_cta": "AI와 함께하는 내일, 지금 시작하세요.",
    "narration_draft": (
        "오늘 아침, AI가 추천한 음악으로 눈을 뜨고, AI가 분석한 날씨로 옷을 골랐습니다. "
        "회의록은 AI가 정리하고, 프레젠테이션은 AI와 함께 만듭니다. "
        "당신은 더 중요한 일에 집중할 수 있죠. "
        "기술이 발전할수록, 우리에게 진짜 중요한 건 사람과의 연결입니다. "
        "AI와 함께하는 내일, 지금 시작하세요."
    ),
    "estimated_duration_sec": 30,
}

DEMO_SCENES = [
    {
        "order_index": 0,
        "title": "오프닝 — 일상의 AI",
        "purpose": "시청자의 일상에서 AI가 이미 함께하고 있음을 환기",
        "narration_text": "오늘 아침, AI가 추천한 음악으로 눈을 뜨고, AI가 분석한 날씨로 옷을 골랐습니다.",
        "duration_estimate_sec": 8,
        "emotional_tone": "편안한, 호기심",
        "visual_intent": "따뜻한 아침 햇살, 일상적이면서 세련된 공간",
        "transition_hint": "cut",
        "status": "drafted",
    },
    {
        "order_index": 1,
        "title": "전개 — 업무와 창작",
        "purpose": "AI가 업무 생산성과 창작 활동을 어떻게 지원하는지 보여준다",
        "narration_text": "회의록은 AI가 정리하고, 프레젠테이션은 AI와 함께 만듭니다. 당신은 더 중요한 일에 집중할 수 있죠.",
        "duration_estimate_sec": 10,
        "emotional_tone": "활기찬, 전문적",
        "visual_intent": "모던한 사무실, 깔끔한 UI 화면, 빠른 편집",
        "transition_hint": "dissolve",
        "status": "drafted",
    },
    {
        "order_index": 2,
        "title": "전환 — 감성 연결",
        "purpose": "기술 너머 인간적 가치를 강조하여 감정적 공감 유도",
        "narration_text": "기술이 발전할수록, 우리에게 진짜 중요한 건 사람과의 연결입니다.",
        "duration_estimate_sec": 7,
        "emotional_tone": "감성적, 따뜻한",
        "visual_intent": "가족 식사, 친구 대화, 따뜻한 조명",
        "transition_hint": "dissolve",
        "status": "drafted",
    },
    {
        "order_index": 3,
        "title": "마무리 — CTA",
        "purpose": "행동 유도와 브랜드 각인",
        "narration_text": "AI와 함께하는 내일, 지금 시작하세요.",
        "duration_estimate_sec": 5,
        "emotional_tone": "동기부여, 미래지향",
        "visual_intent": "미래적 도시 풍경, 밝은 색감, 로고",
        "transition_hint": "fade",
        "status": "drafted",
    },
]

DEMO_SHOTS = {
    0: [
        {
            "order_index": 0,
            "shot_type": "establishing",
            "camera_framing": "wide",
            "camera_movement": "slow_dolly_in",
            "duration_sec": 4,
            "purpose": "아침 분위기 설정",
            "subject": "침실, 아침 햇살",
            "environment": "모던한 원룸, 큰 창문",
            "emotion": "편안함",
            "narration_segment": "오늘 아침, AI가 추천한 음악으로 눈을 뜨고,",
            "asset_strategy": "image_to_video",
        },
        {
            "order_index": 1,
            "shot_type": "detail",
            "camera_framing": "close_up",
            "camera_movement": "static",
            "duration_sec": 4,
            "purpose": "AI 인터페이스 디테일",
            "subject": "스마트폰 화면, 날씨 앱",
            "environment": "손에 들린 폰, 배경 블러",
            "emotion": "호기심",
            "narration_segment": "AI가 분석한 날씨로 옷을 골랐습니다.",
            "asset_strategy": "image_to_video",
        },
    ],
    1: [
        {
            "order_index": 0,
            "shot_type": "medium",
            "camera_framing": "medium",
            "camera_movement": "pan_right",
            "duration_sec": 5,
            "purpose": "업무 환경 소개",
            "subject": "사무실 데스크, 모니터",
            "environment": "밝은 오피스, 미니멀 인테리어",
            "emotion": "활기찬",
            "narration_segment": "회의록은 AI가 정리하고, 프레젠테이션은 AI와 함께 만듭니다.",
            "asset_strategy": "image_to_video",
        },
        {
            "order_index": 1,
            "shot_type": "over_shoulder",
            "camera_framing": "medium_close_up",
            "camera_movement": "static",
            "duration_sec": 5,
            "purpose": "집중하는 사용자",
            "subject": "노트북 화면의 AI 인터페이스",
            "environment": "어깨 너머 시점",
            "emotion": "전문적",
            "narration_segment": "당신은 더 중요한 일에 집중할 수 있죠.",
            "asset_strategy": "image_to_video",
        },
    ],
    2: [
        {
            "order_index": 0,
            "shot_type": "medium",
            "camera_framing": "medium",
            "camera_movement": "slow_dolly_in",
            "duration_sec": 7,
            "purpose": "따뜻한 인간 관계 강조",
            "subject": "가족 식사 테이블",
            "environment": "따뜻한 조명, 가정집",
            "emotion": "따뜻함",
            "narration_segment": "기술이 발전할수록, 우리에게 진짜 중요한 건 사람과의 연결입니다.",
            "asset_strategy": "image_to_video",
        },
    ],
    3: [
        {
            "order_index": 0,
            "shot_type": "wide",
            "camera_framing": "extreme_wide",
            "camera_movement": "crane_up",
            "duration_sec": 5,
            "purpose": "미래 비전과 CTA",
            "subject": "미래적 도시 스카이라인",
            "environment": "일몰, 밝은 미래 분위기",
            "emotion": "동기부여",
            "narration_segment": "AI와 함께하는 내일, 지금 시작하세요.",
            "asset_strategy": "image_to_video",
        },
    ],
}

DEMO_CHARACTER = {
    "name": "나레이터",
    "role": "narrator",
    "description": "영상의 내레이션을 담당하는 가상 화자. 화면에 등장하지 않음.",
    "appearance": None,
    "personality": "따뜻하고 지적인, 친근하면서 전문적인 톤",
    "voice_id": "narrator-ko-male",
}


# ── Seed Functions ────────────────────────────────────


async def seed_style_presets(session: AsyncSession) -> None:
    """Seed global style presets if none exist."""
    result = await session.execute(
        select(StylePreset).where(StylePreset.is_global.is_(True)).limit(1)
    )
    if result.scalar_one_or_none() is not None:
        return

    logger.info("Seeding %d global style presets", len(GLOBAL_PRESETS))
    for data in GLOBAL_PRESETS:
        session.add(StylePreset(project_id=None, is_global=True, **data))
    await session.commit()
    logger.info("Global style presets seeded")


async def seed_demo_project(session: AsyncSession) -> str:
    """Create a fully populated demo project. Returns the project ID."""
    now = datetime.now(timezone.utc)

    # Project
    project = Project(
        title=DEMO_PROJECT["title"],
        description=DEMO_PROJECT["description"],
        status=DEMO_PROJECT["status"],
    )
    session.add(project)
    await session.flush()
    project_id = project.id
    logger.info("Demo project created: %s", project_id)

    # Link a global style preset
    preset_result = await session.execute(
        select(StylePreset).where(StylePreset.is_global.is_(True)).limit(1)
    )
    preset = preset_result.scalar_one_or_none()
    if preset:
        project.active_style_preset_id = preset.id

    # ScriptVersion
    sv = ScriptVersion(
        project_id=project_id,
        version=1,
        status="structured",
        input_params=DEMO_SCRIPT_INPUT,
        plan_json=DEMO_PLAN_JSON,
        raw_text=DEMO_PLAN_JSON["narration_draft"],
    )
    session.add(sv)
    await session.flush()
    sv_id = sv.id

    # Scenes + Shots
    for sc_data in DEMO_SCENES:
        scene_idx = sc_data["order_index"]
        scene = Scene(
            script_version_id=sv_id,
            **sc_data,
        )
        session.add(scene)
        await session.flush()

        shot_list = DEMO_SHOTS.get(scene_idx, [])
        for sh_data in shot_list:
            session.add(Shot(scene_id=scene.id, **sh_data))

    # Character
    session.add(CharacterProfile(project_id=project_id, **DEMO_CHARACTER))

    await session.commit()
    logger.info(
        "Demo project seeded: %d scenes, %d shots",
        len(DEMO_SCENES),
        sum(len(v) for v in DEMO_SHOTS.values()),
    )
    return str(project_id)


async def run_all_seeds(session: AsyncSession) -> None:
    """Run all seed functions."""
    await seed_style_presets(session)

    result = await session.execute(
        select(Project).where(Project.title == DEMO_PROJECT["title"]).limit(1)
    )
    if result.scalar_one_or_none() is None:
        await seed_demo_project(session)
    else:
        logger.info("Demo project already exists, skipping")

    from app.seed_evaluation import seed_evaluation_projects
    await seed_evaluation_projects(session)
