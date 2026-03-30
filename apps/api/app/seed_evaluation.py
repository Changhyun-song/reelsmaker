"""Evaluation demo projects — 3 distinct video types for baseline comparison.

Each project contains: Project → ScriptVersion → Scenes → Shots → FrameSpecs.
Run via `make seed` or on first startup.
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.project import Project
from shared.models.script_version import ScriptVersion
from shared.models.scene import Scene
from shared.models.shot import Shot
from shared.models.frame_spec import FrameSpec
from shared.models.character_profile import CharacterProfile
from shared.models.style_preset import StylePreset

logger = logging.getLogger("reelsmaker.seed")

EVAL_TAG = "[Eval]"

# ══════════════════════════════════════════════════════
# 1. demo_shorts_explainer — 교육/설명 숏폼 (45초)
# ══════════════════════════════════════════════════════

EXPLAINER = {
    "project": {
        "title": f"{EVAL_TAG} 45초 생산성 앱 추천 숏폼",
        "description": (
            "교육/설명형 숏폼 평가용. 빠른 템포, 리스트 구조, 인포그래픽 스타일. "
            "Scene 전환이 빠르고 정보 밀도가 높은 영상의 파이프라인 품질을 평가한다."
        ),
        "status": "scripting",
        "style_name": "Minimalist Infographic",
    },
    "script_input": {
        "topic": "직장인을 위한 5가지 무료 생산성 앱",
        "target_audience": "20~30대 직장인, 생산성에 관심 있는 직장인",
        "tone": "활기찬, 정보 전달, 신뢰감",
        "duration_sec": 45,
        "format": "youtube_short",
        "language": "ko",
        "constraints": "앱 이름을 화면에 텍스트로 표시, 빠른 전환",
    },
    "plan_json": {
        "title": "하루가 달라지는 5가지 앱",
        "summary": "직장인 생산성을 높여줄 무료 앱 5가지를 빠르게 소개하는 45초 숏폼",
        "hook": "매일 반복되는 업무, 이 앱 하나면 달라집니다.",
        "narrative_flow": [
            "훅 — 시청자의 고통점 자극",
            "앱 1~2 — 정리/관리 카테고리",
            "앱 3 — 집중력 카테고리",
            "앱 4+5 — 커뮤니케이션/일정",
            "마무리 — 요약 + CTA",
        ],
        "sections": [
            {
                "title": "오프닝 — 훅",
                "description": "직장인의 반복 업무 고통점을 짧게 환기",
                "narration": "매일 반복되는 업무, 이 앱 하나면 달라집니다.",
                "visual_notes": "바쁜 사무실, 쌓인 알림, 타이머",
                "duration_sec": 5,
            },
            {
                "title": "앱 1: Notion",
                "description": "메모, 프로젝트 관리, 위키를 한 곳에",
                "narration": "첫 번째, Notion. 메모부터 프로젝트 관리까지 하나로 끝.",
                "visual_notes": "Notion 인터페이스, 칸반 보드, 깔끔한 아이콘",
                "duration_sec": 10,
            },
            {
                "title": "앱 2: Todoist",
                "description": "할 일 관리의 정석",
                "narration": "두 번째, Todoist. 할 일을 놓치지 않는 가장 쉬운 방법.",
                "visual_notes": "체크리스트, 우선순위 색상, 완료 애니메이션",
                "duration_sec": 10,
            },
            {
                "title": "앱 3: Forest",
                "description": "집중력 향상, 스마트폰 중독 탈출",
                "narration": "세 번째, Forest. 스마트폰을 내려놓으면 나무가 자랍니다.",
                "visual_notes": "나무 자라는 애니메이션, 타이머, 숲 완성",
                "duration_sec": 8,
            },
            {
                "title": "마무리 — 보너스 앱 + CTA",
                "description": "Grammarly와 Calendly를 빠르게 소개 후 CTA",
                "narration": "보너스! 문법 교정은 Grammarly, 미팅 예약은 Calendly. "
                "다섯 가지 앱으로 내일부터 달라지세요.",
                "visual_notes": "앱 아이콘 그리드, CTA 텍스트, 구독 유도",
                "duration_sec": 12,
            },
        ],
        "ending_cta": "다섯 가지 앱으로 내일부터 달라지세요.",
        "narration_draft": (
            "매일 반복되는 업무, 이 앱 하나면 달라집니다. "
            "첫 번째, Notion. 메모부터 프로젝트 관리까지 하나로 끝. "
            "두 번째, Todoist. 할 일을 놓치지 않는 가장 쉬운 방법. "
            "세 번째, Forest. 스마트폰을 내려놓으면 나무가 자랍니다. "
            "보너스! 문법 교정은 Grammarly, 미팅 예약은 Calendly. "
            "다섯 가지 앱으로 내일부터 달라지세요."
        ),
        "estimated_duration_sec": 45,
    },
    "scenes": [
        {
            "order_index": 0,
            "title": "오프닝 — 훅",
            "purpose": "직장인의 업무 과부하를 짧게 자극하여 시선 고정",
            "narration_text": "매일 반복되는 업무, 이 앱 하나면 달라집니다.",
            "duration_estimate_sec": 5,
            "emotional_tone": "긴장감, 공감",
            "visual_intent": "어두운 사무실, 쌓인 알림 아이콘, 빠른 컷",
            "transition_hint": "cut",
            "status": "drafted",
        },
        {
            "order_index": 1,
            "title": "앱 1: Notion",
            "purpose": "Notion의 핵심 가치를 10초 안에 전달",
            "narration_text": "첫 번째, Notion. 메모부터 프로젝트 관리까지 하나로 끝.",
            "duration_estimate_sec": 10,
            "emotional_tone": "깔끔한, 신뢰감",
            "visual_intent": "미니멀 UI 화면, 칸반 보드, 플랫 아이콘",
            "transition_hint": "swipe_left",
            "status": "drafted",
        },
        {
            "order_index": 2,
            "title": "앱 2: Todoist",
            "purpose": "Todoist의 할 일 관리 편의성 전달",
            "narration_text": "두 번째, Todoist. 할 일을 놓치지 않는 가장 쉬운 방법.",
            "duration_estimate_sec": 10,
            "emotional_tone": "활기찬, 깔끔한",
            "visual_intent": "체크리스트 UI, 우선순위 색상 강조, 완료 모션",
            "transition_hint": "swipe_left",
            "status": "drafted",
        },
        {
            "order_index": 3,
            "title": "앱 3: Forest",
            "purpose": "집중력 회복이라는 감성적 가치 전달",
            "narration_text": "세 번째, Forest. 스마트폰을 내려놓으면 나무가 자랍니다.",
            "duration_estimate_sec": 8,
            "emotional_tone": "따뜻한, 동기부여",
            "visual_intent": "나무 성장 애니메이션, 초록 색감, 타이머",
            "transition_hint": "dissolve",
            "status": "drafted",
        },
        {
            "order_index": 4,
            "title": "마무리 — 보너스 앱 + CTA",
            "purpose": "나머지 앱을 빠르게 소개하고 행동 유도",
            "narration_text": "보너스! 문법 교정은 Grammarly, 미팅 예약은 Calendly. 다섯 가지 앱으로 내일부터 달라지세요.",
            "duration_estimate_sec": 12,
            "emotional_tone": "활기찬, 동기부여",
            "visual_intent": "앱 아이콘 그리드, 큰 CTA 텍스트, 밝은 색감",
            "transition_hint": "fade",
            "status": "drafted",
        },
    ],
    "shots": {
        0: [
            {
                "order_index": 0, "shot_type": "establishing", "camera_framing": "wide",
                "camera_movement": "zoom_in", "duration_sec": 5,
                "purpose": "업무 과부하 시각화", "subject": "사무실 책상, 알림 아이콘",
                "environment": "어두운 톤의 미니멀 오피스", "emotion": "긴장감",
                "narration_segment": "매일 반복되는 업무, 이 앱 하나면 달라집니다.",
                "asset_strategy": "image_to_video",
            },
        ],
        1: [
            {
                "order_index": 0, "shot_type": "medium", "camera_framing": "medium",
                "camera_movement": "static", "duration_sec": 5,
                "purpose": "Notion 화면 소개", "subject": "Notion 인터페이스",
                "environment": "깔끔한 모니터 화면", "emotion": "신뢰감",
                "narration_segment": "첫 번째, Notion.",
                "asset_strategy": "still_image",
            },
            {
                "order_index": 1, "shot_type": "detail", "camera_framing": "close_up",
                "camera_movement": "pan_right", "duration_sec": 5,
                "purpose": "칸반 보드 하이라이트", "subject": "칸반 보드, 태스크 카드",
                "environment": "UI 클로즈업", "emotion": "깔끔한",
                "narration_segment": "메모부터 프로젝트 관리까지 하나로 끝.",
                "asset_strategy": "image_to_video",
            },
        ],
        2: [
            {
                "order_index": 0, "shot_type": "medium", "camera_framing": "medium",
                "camera_movement": "static", "duration_sec": 5,
                "purpose": "Todoist 메인 화면", "subject": "Todoist 체크리스트",
                "environment": "깔끔한 UI 배경", "emotion": "활기찬",
                "narration_segment": "두 번째, Todoist.",
                "asset_strategy": "still_image",
            },
            {
                "order_index": 1, "shot_type": "detail", "camera_framing": "close_up",
                "camera_movement": "static", "duration_sec": 5,
                "purpose": "완료 체크 애니메이션", "subject": "체크 마크, 우선순위 색상",
                "environment": "컬러풀 UI 요소", "emotion": "성취감",
                "narration_segment": "할 일을 놓치지 않는 가장 쉬운 방법.",
                "asset_strategy": "image_to_video",
            },
        ],
        3: [
            {
                "order_index": 0, "shot_type": "medium", "camera_framing": "medium",
                "camera_movement": "slow_dolly_in", "duration_sec": 4,
                "purpose": "Forest 타이머 시작", "subject": "Forest 앱 타이머 화면",
                "environment": "따뜻한 톤, 초록 배경", "emotion": "차분한",
                "narration_segment": "세 번째, Forest.",
                "asset_strategy": "still_image",
            },
            {
                "order_index": 1, "shot_type": "detail", "camera_framing": "close_up",
                "camera_movement": "tilt_up", "duration_sec": 4,
                "purpose": "나무 성장 시각화", "subject": "자라나는 나무 그래픽",
                "environment": "초록 숲 배경", "emotion": "따뜻함",
                "narration_segment": "스마트폰을 내려놓으면 나무가 자랍니다.",
                "asset_strategy": "image_to_video",
            },
        ],
        4: [
            {
                "order_index": 0, "shot_type": "medium", "camera_framing": "medium",
                "camera_movement": "pan_right", "duration_sec": 6,
                "purpose": "보너스 앱 빠른 소개", "subject": "Grammarly + Calendly 아이콘",
                "environment": "밝은 그리드 레이아웃", "emotion": "활기찬",
                "narration_segment": "보너스! 문법 교정은 Grammarly, 미팅 예약은 Calendly.",
                "asset_strategy": "image_to_video",
            },
            {
                "order_index": 1, "shot_type": "wide", "camera_framing": "wide",
                "camera_movement": "static", "duration_sec": 6,
                "purpose": "CTA 텍스트와 마무리", "subject": "5개 앱 아이콘 + CTA 텍스트",
                "environment": "밝은 배경, 큰 텍스트", "emotion": "동기부여",
                "narration_segment": "다섯 가지 앱으로 내일부터 달라지세요.",
                "asset_strategy": "still_image",
            },
        ],
    },
    "frames": {
        (0, 0): [
            {"order_index": 0, "frame_role": "start",
             "composition": "중앙에 어두운 책상, 알림 아이콘이 위에서 쏟아지는 구도",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "wide_angle", "lighting": "dim office light, bluish monitor glow",
             "mood": "overwhelmed", "action_pose": "static desk with piling notifications",
             "background_description": "어두운 미니멀 사무실, 블루톤",
             "continuity_notes": "다음 씬 밝은 톤으로 전환 준비",
             "forbidden_elements": "사람 얼굴, 특정 브랜드 로고"},
            {"order_index": 1, "frame_role": "end",
             "composition": "알림이 사라지고 밝은 앱 아이콘 하나가 중앙에 떠오르는 구도",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "standard", "lighting": "bright clean light emerging",
             "mood": "hopeful", "action_pose": "app icon floating center",
             "background_description": "블루→화이트 그라데이션 전환",
             "continuity_notes": "다음 씬 Notion UI로 연결",
             "forbidden_elements": "사람 얼굴"},
        ],
        (1, 0): [
            {"order_index": 0, "frame_role": "start",
             "composition": "Notion 대시보드 전체 화면, 좌측 사이드바 보이는 구도",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "standard", "lighting": "flat even light, white background",
             "mood": "clean, organized", "action_pose": "static UI screenshot",
             "background_description": "순백 배경, 미니멀 UI",
             "continuity_notes": "이전 씬 밝아진 톤과 연결",
             "forbidden_elements": "실제 사용자 정보, 다른 브랜드"},
            {"order_index": 1, "frame_role": "end",
             "composition": "칸반 보드 영역을 중심으로 줌인된 상태",
             "subject_position": "center_right", "camera_angle": "straight_on",
             "lens_feel": "standard", "lighting": "flat even light",
             "mood": "efficient", "action_pose": "kanban cards highlighted",
             "background_description": "Notion 칸반 보드 UI",
             "continuity_notes": "다음 샷 칸반 디테일로 연결",
             "forbidden_elements": "실제 사용자 정보"},
        ],
        (1, 1): [
            {"order_index": 0, "frame_role": "start",
             "composition": "칸반 보드 카드 3~4개가 보이는 클로즈업",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "macro", "lighting": "flat, high contrast accent colors",
             "mood": "organized", "action_pose": "cards in grid",
             "background_description": "화이트 UI 위 컬러풀 카드",
             "continuity_notes": "이전 샷 Notion 전체에서 줌인",
             "forbidden_elements": "실제 텍스트 내용"},
            {"order_index": 1, "frame_role": "end",
             "composition": "카드가 우측으로 슬라이드되며 Todoist로 전환 준비",
             "subject_position": "right", "camera_angle": "straight_on",
             "lens_feel": "standard", "lighting": "bright transition",
             "mood": "energetic", "action_pose": "cards sliding right",
             "background_description": "밝은 배경으로 페이드",
             "continuity_notes": "다음 씬 Todoist UI로 연결",
             "forbidden_elements": "잔상, 블러"},
        ],
        (2, 0): [
            {"order_index": 0, "frame_role": "start",
             "composition": "Todoist 메인 리스트 뷰, 오늘 할 일 목록",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "standard", "lighting": "flat, clean white",
             "mood": "clear, actionable", "action_pose": "task list displayed",
             "background_description": "화이트 배경, 레드 accent",
             "continuity_notes": "이전 씬 Notion에서 전환",
             "forbidden_elements": "실제 할일 내용"},
            {"order_index": 1, "frame_role": "end",
             "composition": "같은 리스트 뷰, 상위 항목에 포커스",
             "subject_position": "center_top", "camera_angle": "straight_on",
             "lens_feel": "standard", "lighting": "flat, clean white",
             "mood": "focused", "action_pose": "top items highlighted",
             "background_description": "화이트 배경, 우선순위 색상",
             "continuity_notes": "다음 샷 체크 애니메이션으로 연결",
             "forbidden_elements": "실제 할일 내용"},
        ],
        (2, 1): [
            {"order_index": 0, "frame_role": "start",
             "composition": "체크박스가 비어 있는 할 일 항목 클로즈업",
             "subject_position": "center_left", "camera_angle": "straight_on",
             "lens_feel": "macro", "lighting": "flat, slight highlight on checkbox",
             "mood": "anticipation", "action_pose": "unchecked checkbox",
             "background_description": "미니멀 UI 배경",
             "continuity_notes": "체크 완료 프레임으로 연결",
             "forbidden_elements": "다른 UI 요소"},
            {"order_index": 1, "frame_role": "end",
             "composition": "체크 완료 + 취소선, 초록 체크 마크",
             "subject_position": "center_left", "camera_angle": "straight_on",
             "lens_feel": "macro", "lighting": "green glow on check mark",
             "mood": "satisfaction", "action_pose": "checked checkbox with strikethrough",
             "background_description": "동일한 UI 배경, 초록 강조",
             "continuity_notes": "다음 씬 Forest로 분위기 전환",
             "forbidden_elements": "다른 UI 요소"},
        ],
        (3, 0): [
            {"order_index": 0, "frame_role": "start",
             "composition": "Forest 앱 타이머 화면, 씨앗 아이콘 중앙",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "standard", "lighting": "warm green tones, soft glow",
             "mood": "calm", "action_pose": "seed icon in center, timer at top",
             "background_description": "연두색 그라데이션 배경",
             "continuity_notes": "이전 씬의 날카로운 UI에서 따뜻한 톤으로 전환",
             "forbidden_elements": "날카로운 직선, 차가운 색"},
            {"order_index": 1, "frame_role": "end",
             "composition": "타이머 진행 중, 씨앗이 새싹으로 성장",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "standard", "lighting": "warm green, slightly brighter",
             "mood": "nurturing", "action_pose": "sprout growing from seed",
             "background_description": "연두→초록 그라데이션",
             "continuity_notes": "다음 샷 완성된 나무로 연결",
             "forbidden_elements": "차가운 색"},
        ],
        (3, 1): [
            {"order_index": 0, "frame_role": "start",
             "composition": "새싹에서 작은 나무로 성장 중인 모습",
             "subject_position": "center_bottom", "camera_angle": "low_angle",
             "lens_feel": "wide_angle", "lighting": "warm sunlight from above",
             "mood": "growing", "action_pose": "small tree with few leaves",
             "background_description": "초록 숲 배경, 작은 나무들",
             "continuity_notes": "이전 프레임 새싹에서 연결",
             "forbidden_elements": "죽은 나무, 어두운 톤"},
            {"order_index": 1, "frame_role": "end",
             "composition": "완성된 큰 나무, 숲의 일부가 된 모습",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "wide_angle", "lighting": "golden sunlight through leaves",
             "mood": "fulfillment", "action_pose": "full tree in lush forest",
             "background_description": "울창한 미니 숲",
             "continuity_notes": "다음 씬 밝은 요약 화면으로 전환",
             "forbidden_elements": "시든 잎, 어두운 톤"},
        ],
        (4, 0): [
            {"order_index": 0, "frame_role": "start",
             "composition": "Grammarly + Calendly 아이콘이 좌우로 배치",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "standard", "lighting": "bright, flat, colorful accents",
             "mood": "energetic", "action_pose": "two app icons side by side",
             "background_description": "밝은 그리드 배경, 연한 파스텔",
             "continuity_notes": "이전 씬 따뜻한 톤에서 밝은 톤으로",
             "forbidden_elements": "복잡한 UI 디테일"},
            {"order_index": 1, "frame_role": "end",
             "composition": "두 아이콘이 뒤로 물러나고 5개 앱 아이콘 그리드 등장",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "wide_angle", "lighting": "bright, celebratory",
             "mood": "complete", "action_pose": "5 app icons in neat grid",
             "background_description": "밝은 배경, 앱 아이콘 그리드",
             "continuity_notes": "다음 샷 CTA로 연결",
             "forbidden_elements": "어두운 톤"},
        ],
        (4, 1): [
            {"order_index": 0, "frame_role": "start",
             "composition": "5개 앱 아이콘 그리드 위에 CTA 텍스트 등장 시작",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "standard", "lighting": "bright white, accent glow",
             "mood": "motivating", "action_pose": "text appearing above icons",
             "background_description": "화이트 배경, 컬러풀 아이콘",
             "continuity_notes": "이전 샷 그리드에서 연결",
             "forbidden_elements": "복잡한 배경"},
            {"order_index": 1, "frame_role": "end",
             "composition": "큰 CTA 텍스트 '내일부터 달라지세요' + 구독 유도",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "standard", "lighting": "bright, clean",
             "mood": "empowering", "action_pose": "bold text + subscribe button",
             "background_description": "화이트 배경, accent 컬러 CTA",
             "continuity_notes": "최종 프레임",
             "forbidden_elements": "어두운 톤, 작은 텍스트"},
        ],
    },
    "character": {
        "name": "설명자",
        "role": "narrator",
        "description": "빠르고 신뢰감 있는 톤의 남성 나레이터. 화면에 등장하지 않음.",
        "personality": "정확하고 활기찬, 전문가 느낌",
        "voice_id": "narrator-ko-male-fast",
    },
}


# ══════════════════════════════════════════════════════
# 2. demo_emotional_narration — 감성 내레이션 (60초)
# ══════════════════════════════════════════════════════

EMOTIONAL = {
    "project": {
        "title": f"{EVAL_TAG} 60초 감성 내레이션 — 비 오는 날의 서울",
        "description": (
            "감성/브이로그형 평가용. 느린 템포, 서정적 나레이션, 시네마틱 스타일. "
            "분위기 전달과 시각적 연속성 품질을 평가한다."
        ),
        "status": "scripting",
        "style_name": "Cinematic Realistic",
    },
    "script_input": {
        "topic": "비 오는 날의 서울, 혼자만의 산책",
        "target_audience": "20~40대, 감성 콘텐츠를 좋아하는 시청자",
        "tone": "서정적, 차분한, 사색적",
        "duration_sec": 60,
        "format": "youtube_short",
        "language": "ko",
        "constraints": "대사 없이 나레이션만, 빗소리 ASMR 분위기",
    },
    "plan_json": {
        "title": "비 오는 날의 서울",
        "summary": "비 내리는 서울의 골목과 카페를 걸으며 느끼는 고요한 사색을 담은 60초 영상",
        "hook": "빗소리가 좋은 건, 아무 말도 하지 않아도 되기 때문이다.",
        "narrative_flow": [
            "오프닝 — 비 내리는 도시 전경으로 분위기 설정",
            "산책 — 골목길의 디테일과 정서",
            "사색 — 카페에서의 고요한 시간",
            "마무리 — 비 그친 후의 환한 풍경",
        ],
        "sections": [
            {
                "title": "오프닝 — 비 내리는 서울",
                "description": "도시 전경과 빗줄기로 분위기를 설정한다",
                "narration": "빗소리가 좋은 건, 아무 말도 하지 않아도 되기 때문이다.",
                "visual_notes": "남산타워 보이는 스카이라인, 빗줄기, 회색 하늘",
                "duration_sec": 15,
            },
            {
                "title": "산책 — 골목길",
                "description": "좁은 골목의 디테일과 빗방울의 감성",
                "narration": "젖은 골목 사이로 커피 향이 번지고, 우산 끝에서 떨어지는 물방울이 작은 강을 만든다.",
                "visual_notes": "한옥 골목, 젖은 바닥, 빗방울, 카페 간판",
                "duration_sec": 15,
            },
            {
                "title": "사색 — 카페 안에서",
                "description": "따뜻한 카페에서 바깥 빗소리를 들으며 사색",
                "narration": "창밖을 보면 모든 것이 느려진다. 빗소리에 기대어 잠시, 아무것도 아닌 시간.",
                "visual_notes": "나무 테이블, 김 오르는 커피잔, 창밖 빗줄기 보케",
                "duration_sec": 15,
            },
            {
                "title": "마무리 — 비 그친 후",
                "description": "비가 그치고 햇살이 드는 순간의 전환",
                "narration": "비가 그치면, 세상은 한 번 씻긴 것처럼 선명해진다. 그래서 비 오는 날이 좋다.",
                "visual_notes": "젖은 도로 반사, 구름 사이 햇살, 밝아지는 하늘",
                "duration_sec": 15,
            },
        ],
        "ending_cta": "",
        "narration_draft": (
            "빗소리가 좋은 건, 아무 말도 하지 않아도 되기 때문이다. "
            "젖은 골목 사이로 커피 향이 번지고, 우산 끝에서 떨어지는 물방울이 작은 강을 만든다. "
            "창밖을 보면 모든 것이 느려진다. 빗소리에 기대어 잠시, 아무것도 아닌 시간. "
            "비가 그치면, 세상은 한 번 씻긴 것처럼 선명해진다. 그래서 비 오는 날이 좋다."
        ),
        "estimated_duration_sec": 60,
    },
    "scenes": [
        {
            "order_index": 0,
            "title": "오프닝 — 비 내리는 서울",
            "purpose": "비 내리는 도시의 정서를 시각적으로 확립",
            "narration_text": "빗소리가 좋은 건, 아무 말도 하지 않아도 되기 때문이다.",
            "duration_estimate_sec": 15,
            "emotional_tone": "고요한, 서정적",
            "visual_intent": "남산 스카이라인, 회색 하늘, 빗줄기, 시네마틱 와이드",
            "transition_hint": "fade_in",
            "status": "drafted",
        },
        {
            "order_index": 1,
            "title": "산책 — 골목길",
            "purpose": "디테일한 감각 자극으로 몰입감 형성",
            "narration_text": "젖은 골목 사이로 커피 향이 번지고, 우산 끝에서 떨어지는 물방울이 작은 강을 만든다.",
            "duration_estimate_sec": 15,
            "emotional_tone": "잔잔한, 감성적",
            "visual_intent": "한옥 골목, 젖은 돌바닥 반사, 빗방울 클로즈업",
            "transition_hint": "dissolve",
            "status": "drafted",
        },
        {
            "order_index": 2,
            "title": "사색 — 카페 안에서",
            "purpose": "내면적 사색 분위기로 깊이감 부여",
            "narration_text": "창밖을 보면 모든 것이 느려진다. 빗소리에 기대어 잠시, 아무것도 아닌 시간.",
            "duration_estimate_sec": 15,
            "emotional_tone": "사색적, 따뜻한",
            "visual_intent": "나무 테이블, 김 오르는 커피잔, 창밖 빗줄기 보케",
            "transition_hint": "dissolve",
            "status": "drafted",
        },
        {
            "order_index": 3,
            "title": "마무리 — 비 그친 후",
            "purpose": "분위기 반전으로 감정적 해소와 여운 제공",
            "narration_text": "비가 그치면, 세상은 한 번 씻긴 것처럼 선명해진다. 그래서 비 오는 날이 좋다.",
            "duration_estimate_sec": 15,
            "emotional_tone": "밝아지는, 희망적",
            "visual_intent": "젖은 도로 반사, 구름 사이 햇살, 선명한 색감",
            "transition_hint": "fade_out",
            "status": "drafted",
        },
    ],
    "shots": {
        0: [
            {
                "order_index": 0, "shot_type": "establishing", "camera_framing": "extreme_wide",
                "camera_movement": "slow_pan_right", "duration_sec": 8,
                "purpose": "도시 전경 분위기 설정", "subject": "남산타워와 서울 스카이라인",
                "environment": "회색 하늘, 빗줄기, 안개",
                "emotion": "고요한", "narration_segment": "빗소리가 좋은 건,",
                "asset_strategy": "image_to_video",
            },
            {
                "order_index": 1, "shot_type": "medium", "camera_framing": "medium_wide",
                "camera_movement": "slow_dolly_in", "duration_sec": 7,
                "purpose": "거리의 빗속 풍경", "subject": "젖은 거리, 우산 쓴 사람들 실루엣",
                "environment": "도심 도로, 물웅덩이 반사",
                "emotion": "서정적", "narration_segment": "아무 말도 하지 않아도 되기 때문이다.",
                "asset_strategy": "image_to_video",
            },
        ],
        1: [
            {
                "order_index": 0, "shot_type": "medium", "camera_framing": "medium",
                "camera_movement": "tracking", "duration_sec": 5,
                "purpose": "좁은 골목 진입", "subject": "한옥 골목, 돌담",
                "environment": "좁은 골목, 젖은 돌바닥",
                "emotion": "호기심", "narration_segment": "젖은 골목 사이로 커피 향이 번지고,",
                "asset_strategy": "image_to_video",
            },
            {
                "order_index": 1, "shot_type": "detail", "camera_framing": "extreme_close_up",
                "camera_movement": "static", "duration_sec": 4,
                "purpose": "빗방울 디테일", "subject": "처마 끝 빗방울, 물방울 파문",
                "environment": "나무 처마, 배경 블러",
                "emotion": "감각적", "narration_segment": "우산 끝에서 떨어지는 물방울이",
                "asset_strategy": "image_to_video",
            },
            {
                "order_index": 2, "shot_type": "medium", "camera_framing": "medium_wide",
                "camera_movement": "slow_dolly_in", "duration_sec": 6,
                "purpose": "카페 앞 도착", "subject": "빈티지 카페 간판, 문 앞 화분",
                "environment": "골목 끝 카페, 따뜻한 불빛",
                "emotion": "안도감", "narration_segment": "작은 강을 만든다.",
                "asset_strategy": "image_to_video",
            },
        ],
        2: [
            {
                "order_index": 0, "shot_type": "medium", "camera_framing": "medium",
                "camera_movement": "slow_dolly_in", "duration_sec": 8,
                "purpose": "카페 내부 분위기", "subject": "나무 테이블, 커피잔, 창",
                "environment": "따뜻한 조명, 나무 인테리어",
                "emotion": "편안한", "narration_segment": "창밖을 보면 모든 것이 느려진다.",
                "asset_strategy": "image_to_video",
            },
            {
                "order_index": 1, "shot_type": "detail", "camera_framing": "close_up",
                "camera_movement": "static", "duration_sec": 7,
                "purpose": "커피잔과 빗소리의 대비", "subject": "김 오르는 커피잔, 창밖 빗줄기 보케",
                "environment": "테이블 위, 보케 배경",
                "emotion": "사색적", "narration_segment": "빗소리에 기대어 잠시, 아무것도 아닌 시간.",
                "asset_strategy": "image_to_video",
            },
        ],
        3: [
            {
                "order_index": 0, "shot_type": "medium", "camera_framing": "medium",
                "camera_movement": "slow_dolly_out", "duration_sec": 7,
                "purpose": "비 그친 후 거리", "subject": "젖은 도로, 빗물 반사",
                "environment": "도시 거리, 구름 걷히는 하늘",
                "emotion": "선명한", "narration_segment": "비가 그치면, 세상은 한 번 씻긴 것처럼 선명해진다.",
                "asset_strategy": "image_to_video",
            },
            {
                "order_index": 1, "shot_type": "establishing", "camera_framing": "extreme_wide",
                "camera_movement": "crane_up", "duration_sec": 8,
                "purpose": "밝아진 서울 전경으로 마무리", "subject": "서울 스카이라인, 구름 사이 햇살",
                "environment": "비 그친 후 도시, 선명한 색감",
                "emotion": "희망적", "narration_segment": "그래서 비 오는 날이 좋다.",
                "asset_strategy": "image_to_video",
            },
        ],
    },
    "frames": {
        (0, 0): [
            {"order_index": 0, "frame_role": "start",
             "composition": "좌측에 남산타워, 우측으로 펼쳐진 스카이라인, 하늘 2/3 차지",
             "subject_position": "left_third", "camera_angle": "eye_level",
             "lens_feel": "telephoto_compression", "lighting": "overcast diffused light, grey sky",
             "mood": "melancholic beauty", "action_pose": "rain falling across frame",
             "background_description": "회색 하늘, 도시 실루엣, 빗줄기",
             "continuity_notes": "전체 영상의 첫 프레임 — 고요한 분위기 설정",
             "forbidden_elements": "밝은 햇살, 사람 클로즈업"},
            {"order_index": 1, "frame_role": "middle",
             "composition": "패닝 중 — 스카이라인 중앙, 빗줄기 더 뚜렷",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "telephoto_compression", "lighting": "same overcast, slightly darker",
             "mood": "deepening calm", "action_pose": "rain intensifying",
             "background_description": "도시 건물과 빗줄기가 겹치는 레이어",
             "continuity_notes": "start에서 자연스러운 패닝 연결",
             "forbidden_elements": "밝은 색상"},
            {"order_index": 2, "frame_role": "end",
             "composition": "패닝 끝 — 우측 건물 사이로 빗물이 흘러내리는 모습",
             "subject_position": "right_third", "camera_angle": "eye_level",
             "lens_feel": "telephoto_compression", "lighting": "overcast, faint warm glow from windows",
             "mood": "contemplative", "action_pose": "rain streaming down building surfaces",
             "background_description": "건물 유리창 반사, 빗물 줄기",
             "continuity_notes": "다음 샷 거리 레벨로 전환",
             "forbidden_elements": "밝은 하늘"},
        ],
        (0, 1): [
            {"order_index": 0, "frame_role": "start",
             "composition": "거리 레벨, 우산 쓴 실루엣이 원경에 보이는 구도",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "standard_50mm", "lighting": "overcast ambient, wet reflections",
             "mood": "solitary", "action_pose": "silhouettes walking with umbrellas",
             "background_description": "젖은 도로, 가로등, 물웅덩이 반사",
             "continuity_notes": "이전 샷 스카이라인에서 거리 레벨로 전환",
             "forbidden_elements": "선명한 얼굴"},
            {"order_index": 1, "frame_role": "end",
             "composition": "돌리 인 후 — 우산 실루엣이 더 가까워지고 골목 입구 보임",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "standard_50mm", "lighting": "overcast, warm light leaking from alley",
             "mood": "inviting", "action_pose": "figure approaching alley entrance",
             "background_description": "골목 입구, 따뜻한 불빛 새어나옴",
             "continuity_notes": "다음 씬 골목 내부로 자연스러운 진입",
             "forbidden_elements": "밝은 하늘, 선명한 얼굴"},
        ],
        (1, 0): [
            {"order_index": 0, "frame_role": "start",
             "composition": "좁은 골목, 돌담이 양쪽으로 이어지는 원근감",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "wide_angle_35mm", "lighting": "overcast, diffused",
             "mood": "intimate", "action_pose": "empty alley, wet stones",
             "background_description": "한옥 골목, 돌담, 기와 처마",
             "continuity_notes": "이전 씬 거리에서 골목으로 진입",
             "forbidden_elements": "현대식 건물"},
            {"order_index": 1, "frame_role": "end",
             "composition": "골목 중간 지점, 좌측에 카페 간판 힌트",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "wide_angle_35mm", "lighting": "overcast, warm hint from side",
             "mood": "curious", "action_pose": "walking deeper into alley",
             "background_description": "돌담 골목, 카페 간판 일부 보임",
             "continuity_notes": "다음 샷 빗방울 디테일로 전환",
             "forbidden_elements": "현대식 건물"},
        ],
        (1, 1): [
            {"order_index": 0, "frame_role": "start",
             "composition": "처마 끝에서 떨어지는 빗방울, 배경 골목 블러",
             "subject_position": "center_top", "camera_angle": "low_angle",
             "lens_feel": "macro_100mm", "lighting": "overcast, backlit droplets",
             "mood": "meditative", "action_pose": "water droplet about to fall",
             "background_description": "기와 처마 디테일, 배경 소프트 블러",
             "continuity_notes": "이전 샷 골목 전경에서 디테일로 전환",
             "forbidden_elements": "선명한 배경"},
            {"order_index": 1, "frame_role": "end",
             "composition": "물방울이 수면에 떨어져 파문 생기는 순간",
             "subject_position": "center", "camera_angle": "top_down",
             "lens_feel": "macro_100mm", "lighting": "overcast, reflected light in ripple",
             "mood": "tranquil", "action_pose": "ripple expanding from droplet impact",
             "background_description": "물웅덩이 표면, 동심원 파문",
             "continuity_notes": "다음 샷 카페 앞 도착으로 연결",
             "forbidden_elements": "복잡한 배경"},
        ],
        (1, 2): [
            {"order_index": 0, "frame_role": "start",
             "composition": "카페 간판과 문 앞 화분, 골목 끝 배경",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "standard_50mm", "lighting": "overcast + warm cafe light spill",
             "mood": "welcoming", "action_pose": "cafe entrance, door slightly ajar",
             "background_description": "빈티지 카페 외관, 젖은 바닥",
             "continuity_notes": "이전 샷 빗방울에서 카페 외관으로 전환",
             "forbidden_elements": "현대식 프랜차이즈"},
            {"order_index": 1, "frame_role": "end",
             "composition": "돌리 인 — 카페 문 가까이, 내부 따뜻한 빛 강조",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "standard_50mm", "lighting": "warm golden light from interior",
             "mood": "anticipation", "action_pose": "approaching entrance, warm glow",
             "background_description": "카페 문, 따뜻한 내부 빛",
             "continuity_notes": "다음 씬 카페 내부로 자연스러운 진입",
             "forbidden_elements": "차가운 조명"},
        ],
        (2, 0): [
            {"order_index": 0, "frame_role": "start",
             "composition": "카페 내부, 나무 테이블 중앙, 창 옆 좌석",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "standard_50mm", "lighting": "warm interior light, window backlight",
             "mood": "cozy", "action_pose": "empty seat, coffee on table, rain outside window",
             "background_description": "나무 인테리어, 따뜻한 조명, 창밖 빗줄기",
             "continuity_notes": "이전 씬 카페 외관에서 내부로 진입",
             "forbidden_elements": "형광등, 차가운 톤"},
            {"order_index": 1, "frame_role": "middle",
             "composition": "약간 줌인, 커피잔과 창의 빗줄기가 함께 보이는 구도",
             "subject_position": "center_left", "camera_angle": "eye_level",
             "lens_feel": "standard_50mm", "lighting": "warm, rim light from window",
             "mood": "contemplative", "action_pose": "steam rising from cup",
             "background_description": "창밖 빗줄기 보케, 나무 테이블",
             "continuity_notes": "start에서 자연스러운 줌인",
             "forbidden_elements": "선명한 외부 디테일"},
            {"order_index": 2, "frame_role": "end",
             "composition": "커피잔에 포커스, 배경 완전 보케",
             "subject_position": "center", "camera_angle": "slightly_above",
             "lens_feel": "portrait_85mm", "lighting": "warm spot on cup, soft ambient",
             "mood": "peaceful", "action_pose": "coffee cup with slight steam",
             "background_description": "완전한 보케 — 따뜻한 빛 점들",
             "continuity_notes": "다음 샷 커피잔 클로즈업으로 연결",
             "forbidden_elements": "차가운 색감"},
        ],
        (2, 1): [
            {"order_index": 0, "frame_role": "start",
             "composition": "커피잔 위 김이 모락모락, 뒤로 창밖 빗줄기 보케",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "macro_100mm", "lighting": "warm backlight from window",
             "mood": "intimate", "action_pose": "steam curling above cup rim",
             "background_description": "매크로 — 컵 테두리, 보케 배경",
             "continuity_notes": "이전 샷 커피잔 줌인에서 매크로로 전환",
             "forbidden_elements": "선명한 배경"},
            {"order_index": 1, "frame_role": "end",
             "composition": "김이 흩어지며 창밖이 살짝 더 밝아지는 힌트",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "macro_100mm", "lighting": "warm + hint of brighter light from window",
             "mood": "transitional hope", "action_pose": "steam thinning, light brightening",
             "background_description": "보케 배경이 살짝 밝아지는 변화",
             "continuity_notes": "다음 씬 비 그친 후 밝은 톤으로 전환 준비",
             "forbidden_elements": "갑작스러운 밝기 변화"},
        ],
        (3, 0): [
            {"order_index": 0, "frame_role": "start",
             "composition": "젖은 도로 표면, 하늘 반사, 구름 걷히기 시작",
             "subject_position": "center", "camera_angle": "low_angle",
             "lens_feel": "wide_angle_35mm", "lighting": "overcast breaking, warm light emerging",
             "mood": "refreshed", "action_pose": "wet road reflecting clearing sky",
             "background_description": "젖은 아스팔트, 물웅덩이 하늘 반사",
             "continuity_notes": "이전 씬 카페 따뜻함에서 외부 밝음으로 전환",
             "forbidden_elements": "어두운 톤"},
            {"order_index": 1, "frame_role": "end",
             "composition": "돌리 아웃 — 도로가 넓어지며 밝은 하늘 비율 증가",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "wide_angle_35mm", "lighting": "golden light breaking through clouds",
             "mood": "hopeful", "action_pose": "wider view, more sky visible",
             "background_description": "밝아진 도시 거리, 물기 반사",
             "continuity_notes": "다음 샷 스카이라인 와이드로 연결",
             "forbidden_elements": "비, 어두운 구름"},
        ],
        (3, 1): [
            {"order_index": 0, "frame_role": "start",
             "composition": "거리 레벨에서 서울 스카이라인, 구름 사이 햇살",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "telephoto_compression", "lighting": "golden hour light through clouds",
             "mood": "cathartic", "action_pose": "sunlight breaking through clouds over city",
             "background_description": "서울 스카이라인, 극적인 구름+햇살",
             "continuity_notes": "이전 샷 도로에서 스카이라인으로 시선 이동",
             "forbidden_elements": "비, 어두운 톤"},
            {"order_index": 1, "frame_role": "middle",
             "composition": "크레인 업 중 — 더 많은 하늘, 도시가 아래로",
             "subject_position": "center", "camera_angle": "high_angle",
             "lens_feel": "wide_angle", "lighting": "golden spread across skyline",
             "mood": "expansive", "action_pose": "rising above city, sunlight spreading",
             "background_description": "점점 넓어지는 도시 전경",
             "continuity_notes": "start에서 크레인 업으로 자연스러운 연결",
             "forbidden_elements": "어두운 그림자"},
            {"order_index": 2, "frame_role": "end",
             "composition": "하늘이 대부분, 구름 사이 밝은 빛, 도시는 하단 실루엣",
             "subject_position": "bottom_third", "camera_angle": "bird_eye",
             "lens_feel": "wide_angle", "lighting": "bright golden sky, warm horizon",
             "mood": "serene hope", "action_pose": "city silhouette against golden sky",
             "background_description": "황금빛 하늘, 도시 실루엣",
             "continuity_notes": "최종 프레임 — 영상의 마지막 인상",
             "forbidden_elements": "어두운 톤, 비"},
        ],
    },
    "character": {
        "name": "산책자 (나레이터)",
        "role": "narrator",
        "description": "차분하고 서정적인 여성 나레이터. 화면에 등장하지 않으며 내면의 독백을 전달.",
        "personality": "감성적, 사색적, 시적 표현",
        "voice_id": "narrator-ko-female-calm",
    },
}


# ══════════════════════════════════════════════════════
# 3. demo_product_ad — 프리미엄 제품 광고 (30초)
# ══════════════════════════════════════════════════════

PRODUCT_AD = {
    "project": {
        "title": f"{EVAL_TAG} 30초 프리미엄 이어폰 광고",
        "description": (
            "제품 광고형 평가용. 스튜디오 촬영 느낌, 제품 디테일 강조, 고급 톤. "
            "제품 중심 구도와 텍스트 오버레이 품질을 평가한다."
        ),
        "status": "scripting",
        "style_name": "Premium Product Ad",
    },
    "script_input": {
        "topic": "프리미엄 무선 이어폰 SoundX Pro 출시 광고",
        "target_audience": "25~45세, 오디오 기기에 관심 있는 소비자",
        "tone": "고급스러운, 미니멀, 임팩트 있는",
        "duration_sec": 30,
        "format": "instagram_reel",
        "language": "ko",
        "constraints": "제품명 SoundX Pro를 3회 이상 노출, 가격 미표시",
    },
    "plan_json": {
        "title": "SoundX Pro — 소리의 새로운 기준",
        "summary": "프리미엄 무선 이어폰 SoundX Pro의 디자인과 기술력을 30초에 압축한 광고",
        "hook": "당신이 듣는 건 음악이 아닙니다. 공간입니다.",
        "narrative_flow": [
            "티저 — 제품 실루엣으로 호기심 유발",
            "기능 — 핵심 셀링 포인트 3가지 (음질/ANC/디자인)",
            "CTA — 브랜드 각인과 행동 유도",
        ],
        "sections": [
            {
                "title": "티저 — 실루엣 등장",
                "description": "어둠 속 실루엣으로 시작, 조명이 켜지며 제품 공개",
                "narration": "당신이 듣는 건 음악이 아닙니다. 공간입니다.",
                "visual_notes": "어두운 배경, 림 라이트, 제품 실루엣→풀 공개",
                "duration_sec": 8,
            },
            {
                "title": "기능 — 음질 / ANC / 디자인",
                "description": "세 가지 핵심 기능을 빠르게 시각화",
                "narration": "Hi-Res 사운드. 적응형 노이즈 캔슬링. 티타늄 유니바디.",
                "visual_notes": "드라이버 유닛 매크로, 노이즈 캔슬링 시각화, 소재 디테일",
                "duration_sec": 14,
            },
            {
                "title": "CTA — SoundX Pro",
                "description": "라이프스타일 컷 후 로고와 제품명으로 마무리",
                "narration": "SoundX Pro. 소리의 새로운 기준.",
                "visual_notes": "착용 장면, 로고, 제품명 텍스트",
                "duration_sec": 8,
            },
        ],
        "ending_cta": "SoundX Pro. 소리의 새로운 기준.",
        "narration_draft": (
            "당신이 듣는 건 음악이 아닙니다. 공간입니다. "
            "Hi-Res 사운드. 적응형 노이즈 캔슬링. 티타늄 유니바디. "
            "SoundX Pro. 소리의 새로운 기준."
        ),
        "estimated_duration_sec": 30,
    },
    "scenes": [
        {
            "order_index": 0,
            "title": "티저 — 실루엣 등장",
            "purpose": "어둠 속 림 라이트로 호기심 극대화 후 제품 공개",
            "narration_text": "당신이 듣는 건 음악이 아닙니다. 공간입니다.",
            "duration_estimate_sec": 8,
            "emotional_tone": "미스터리, 고급스러운",
            "visual_intent": "어두운 배경, 림 라이트, 제품 실루엣→풀 공개",
            "transition_hint": "fade_in",
            "status": "drafted",
        },
        {
            "order_index": 1,
            "title": "기능 — 음질 / ANC / 디자인",
            "purpose": "핵심 셀링 포인트를 빠르고 임팩트 있게 전달",
            "narration_text": "Hi-Res 사운드. 적응형 노이즈 캔슬링. 티타늄 유니바디.",
            "duration_estimate_sec": 14,
            "emotional_tone": "임팩트, 신뢰감",
            "visual_intent": "드라이버 유닛 매크로, ANC 시각화, 소재 클로즈업",
            "transition_hint": "cut",
            "status": "drafted",
        },
        {
            "order_index": 2,
            "title": "CTA — SoundX Pro",
            "purpose": "브랜드 각인과 구매 욕구 유도",
            "narration_text": "SoundX Pro. 소리의 새로운 기준.",
            "duration_estimate_sec": 8,
            "emotional_tone": "자신감, 프리미엄",
            "visual_intent": "라이프스타일 착용 컷, 로고, 제품명 텍스트",
            "transition_hint": "fade_out",
            "status": "drafted",
        },
    ],
    "shots": {
        0: [
            {
                "order_index": 0, "shot_type": "detail", "camera_framing": "extreme_close_up",
                "camera_movement": "static", "duration_sec": 4,
                "purpose": "어둠 속 제품 실루엣", "subject": "이어폰 케이스 실루엣",
                "environment": "완전 블랙 배경, 얇은 림 라이트",
                "emotion": "미스터리", "narration_segment": "당신이 듣는 건 음악이 아닙니다.",
                "asset_strategy": "image_to_video",
            },
            {
                "order_index": 1, "shot_type": "medium", "camera_framing": "medium",
                "camera_movement": "slow_dolly_in", "duration_sec": 4,
                "purpose": "조명 켜지며 제품 풀 공개", "subject": "이어폰 + 케이스 전체",
                "environment": "그라데이션 배경, 스튜디오 조명",
                "emotion": "고급스러운", "narration_segment": "공간입니다.",
                "asset_strategy": "image_to_video",
            },
        ],
        1: [
            {
                "order_index": 0, "shot_type": "detail", "camera_framing": "extreme_close_up",
                "camera_movement": "slow_orbit", "duration_sec": 5,
                "purpose": "드라이버 유닛 매크로", "subject": "이어폰 내부 드라이버",
                "environment": "다크 배경, 스팟 조명",
                "emotion": "기술적 경외", "narration_segment": "Hi-Res 사운드.",
                "asset_strategy": "image_to_video",
            },
            {
                "order_index": 1, "shot_type": "medium", "camera_framing": "medium_close_up",
                "camera_movement": "static", "duration_sec": 5,
                "purpose": "노이즈 캔슬링 시각화", "subject": "착용 중 이어폰, 소음 차단 이펙트",
                "environment": "도시 배경 블러→무음 전환",
                "emotion": "고요함", "narration_segment": "적응형 노이즈 캔슬링.",
                "asset_strategy": "image_to_video",
            },
            {
                "order_index": 2, "shot_type": "detail", "camera_framing": "close_up",
                "camera_movement": "slow_orbit", "duration_sec": 4,
                "purpose": "소재 질감 디테일", "subject": "티타늄 표면, 텍스처",
                "environment": "다크 배경, 하이라이트 반사",
                "emotion": "프리미엄", "narration_segment": "티타늄 유니바디.",
                "asset_strategy": "image_to_video",
            },
        ],
        2: [
            {
                "order_index": 0, "shot_type": "medium", "camera_framing": "medium",
                "camera_movement": "slow_dolly_out", "duration_sec": 4,
                "purpose": "라이프스타일 착용 장면", "subject": "사람 옆모습, 이어폰 착용",
                "environment": "깔끔한 미니멀 공간, 자연광",
                "emotion": "자신감", "narration_segment": "SoundX Pro.",
                "asset_strategy": "image_to_video",
            },
            {
                "order_index": 1, "shot_type": "wide", "camera_framing": "wide",
                "camera_movement": "static", "duration_sec": 4,
                "purpose": "로고 + CTA 엔딩", "subject": "제품 + 로고 텍스트",
                "environment": "다크 그라데이션 배경, 중앙 정렬",
                "emotion": "각인", "narration_segment": "소리의 새로운 기준.",
                "asset_strategy": "still_image",
            },
        ],
    },
    "frames": {
        (0, 0): [
            {"order_index": 0, "frame_role": "start",
             "composition": "완전 블랙 중앙에 얇은 림 라이트로 윤곽만 보이는 이어폰 케이스",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "macro_100mm", "lighting": "single rim light, 95% dark",
             "mood": "mysterious anticipation", "action_pose": "static silhouette",
             "background_description": "순수 블랙",
             "continuity_notes": "영상 첫 프레임 — 최대한 어둡게 시작",
             "forbidden_elements": "다른 조명, 배경 디테일"},
            {"order_index": 1, "frame_role": "end",
             "composition": "림 라이트가 살짝 강해지며 케이스 형태가 더 드러남",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "macro_100mm", "lighting": "slightly brighter rim, still mostly dark",
             "mood": "building curiosity", "action_pose": "same silhouette, more visible",
             "background_description": "블랙→아주 어두운 그라데이션",
             "continuity_notes": "다음 샷 풀 조명으로 전환",
             "forbidden_elements": "풀 조명"},
        ],
        (0, 1): [
            {"order_index": 0, "frame_role": "start",
             "composition": "조명이 켜지기 시작, 제품 중앙, 그라데이션 배경",
             "subject_position": "center", "camera_angle": "slightly_above",
             "lens_feel": "standard_50mm", "lighting": "key light fading in, softbox",
             "mood": "reveal", "action_pose": "product becoming visible",
             "background_description": "다크→미디엄 그레이 그라데이션",
             "continuity_notes": "이전 샷 어둠에서 조명 전환",
             "forbidden_elements": "과도한 밝기"},
            {"order_index": 1, "frame_role": "end",
             "composition": "풀 스튜디오 조명, 제품 중앙 완전 공개, 그림자 디테일",
             "subject_position": "center", "camera_angle": "slightly_above",
             "lens_feel": "standard_50mm", "lighting": "full studio: key + fill + rim",
             "mood": "premium unveiling", "action_pose": "product fully lit, case open",
             "background_description": "스튜디오 그라데이션 배경, 부드러운 반사",
             "continuity_notes": "다음 씬 디테일 매크로로 전환",
             "forbidden_elements": "플랫 조명"},
        ],
        (1, 0): [
            {"order_index": 0, "frame_role": "start",
             "composition": "이어폰 드라이버 유닛 극 매크로, 메쉬 디테일",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "macro_extreme", "lighting": "spot light on driver, dark surround",
             "mood": "technical awe", "action_pose": "static driver unit",
             "background_description": "순수 블랙 배경, 스팟 조명",
             "continuity_notes": "이전 씬 풀 제품에서 내부 디테일로 전환",
             "forbidden_elements": "먼지, 지문"},
            {"order_index": 1, "frame_role": "end",
             "composition": "오빗 후 — 드라이버 측면, 금속 텍스처 강조",
             "subject_position": "center", "camera_angle": "45_degree",
             "lens_feel": "macro_extreme", "lighting": "spot + edge highlight",
             "mood": "precision", "action_pose": "driver from angle, metallic sheen",
             "background_description": "블랙, 금속 반사",
             "continuity_notes": "다음 샷 ANC 시각화로 전환",
             "forbidden_elements": "먼지, 지문, 스크래치"},
        ],
        (1, 1): [
            {"order_index": 0, "frame_role": "start",
             "composition": "사람 옆 얼굴 중간 클로즈업, 이어폰 착용, 도시 배경",
             "subject_position": "center_right", "camera_angle": "eye_level",
             "lens_feel": "portrait_85mm", "lighting": "natural light, background visible",
             "mood": "urban noise", "action_pose": "person with earphone, background noisy",
             "background_description": "도시 거리 — 버스, 사람, 소음 시각화",
             "continuity_notes": "이전 샷 드라이버에서 착용 장면으로 전환",
             "forbidden_elements": "정면 얼굴"},
            {"order_index": 1, "frame_role": "end",
             "composition": "동일 구도, 배경이 블러되며 고요해지는 시각 효과",
             "subject_position": "center_right", "camera_angle": "eye_level",
             "lens_feel": "portrait_85mm", "lighting": "same natural + background darkening",
             "mood": "silence, isolation", "action_pose": "same pose, background dissolving",
             "background_description": "도시 배경→블러→어둡게 (ANC 시각화)",
             "continuity_notes": "다음 샷 소재 디테일로 전환",
             "forbidden_elements": "정면 얼굴, 과도한 이펙트"},
        ],
        (1, 2): [
            {"order_index": 0, "frame_role": "start",
             "composition": "이어폰 본체 측면, 티타늄 표면 텍스처 매크로",
             "subject_position": "center", "camera_angle": "45_degree",
             "lens_feel": "macro_100mm", "lighting": "gradient light sweep starting",
             "mood": "material luxury", "action_pose": "static product, light moving across surface",
             "background_description": "블랙 배경, 하이라이트가 표면을 쓸듯이",
             "continuity_notes": "이전 샷 ANC에서 소재로 전환",
             "forbidden_elements": "지문, 스크래치"},
            {"order_index": 1, "frame_role": "end",
             "composition": "오빗 후 — 반대편 각도, 빛이 표면을 가로질러 완료",
             "subject_position": "center", "camera_angle": "opposite_45",
             "lens_feel": "macro_100mm", "lighting": "light sweep completed, highlights visible",
             "mood": "refined craftsmanship", "action_pose": "product from new angle",
             "background_description": "블랙 배경, 표면 반사",
             "continuity_notes": "다음 씬 라이프스타일로 전환",
             "forbidden_elements": "지문, 스크래치, 먼지"},
        ],
        (2, 0): [
            {"order_index": 0, "frame_role": "start",
             "composition": "사람 옆모습 미디엄, 이어폰 착용, 미니멀 배경",
             "subject_position": "center_left", "camera_angle": "eye_level",
             "lens_feel": "portrait_85mm", "lighting": "soft natural window light",
             "mood": "confident lifestyle", "action_pose": "person with earphone, relaxed",
             "background_description": "밝고 깔끔한 미니멀 공간",
             "continuity_notes": "이전 씬 제품 디테일에서 라이프스타일로 전환",
             "forbidden_elements": "정면 얼굴, 어두운 톤"},
            {"order_index": 1, "frame_role": "end",
             "composition": "돌리 아웃 — 공간이 넓어지며 여유로운 분위기",
             "subject_position": "center", "camera_angle": "eye_level",
             "lens_feel": "standard_50mm", "lighting": "soft natural light, wider",
             "mood": "aspirational", "action_pose": "person in wider lifestyle context",
             "background_description": "밝은 미니멀 인테리어 전체",
             "continuity_notes": "다음 샷 로고 엔딩으로 전환",
             "forbidden_elements": "정면 얼굴"},
        ],
        (2, 1): [
            {"order_index": 0, "frame_role": "start",
             "composition": "다크 배경 중앙에 제품, 위에 로고 텍스트 등장 시작",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "standard_50mm", "lighting": "studio spot on product, logo fade-in",
             "mood": "brand authority", "action_pose": "product static, text appearing",
             "background_description": "다크 그라데이션 배경",
             "continuity_notes": "이전 샷 라이프스타일에서 스튜디오로 전환",
             "forbidden_elements": "복잡한 배경"},
            {"order_index": 1, "frame_role": "end",
             "composition": "제품 + 'SoundX Pro' 로고 + '소리의 새로운 기준' 태그라인",
             "subject_position": "center", "camera_angle": "straight_on",
             "lens_feel": "standard_50mm", "lighting": "clean studio, balanced",
             "mood": "definitive, memorable", "action_pose": "product and text fully visible",
             "background_description": "다크 그라데이션, 프리미엄 톤",
             "continuity_notes": "최종 프레임 — 브랜드 각인용",
             "forbidden_elements": "복잡한 요소, 작은 텍스트"},
        ],
    },
    "character": {
        "name": "브랜드 보이스",
        "role": "narrator",
        "description": "깊고 권위 있는 남성 보이스. 고급 브랜드 광고 톤.",
        "personality": "절제된, 권위적, 미니멀한 화법",
        "voice_id": "narrator-ko-male-deep",
    },
}

# ── All evaluation projects ───────────────────────────

EVAL_PROJECTS = [EXPLAINER, EMOTIONAL, PRODUCT_AD]


# ── Generic seeder ────────────────────────────────────

async def _seed_one_eval_project(
    session: AsyncSession, data: dict, style_presets: dict[str, StylePreset],
) -> str:
    """Create one evaluation project with full hierarchy. Returns project ID."""
    pd = data["project"]

    project = Project(
        title=pd["title"],
        description=pd["description"],
        status=pd["status"],
    )
    session.add(project)
    await session.flush()
    pid = project.id

    # Link style preset if available
    preset = style_presets.get(pd.get("style_name", ""))
    if preset:
        project.active_style_preset_id = preset.id

    # ScriptVersion
    sv = ScriptVersion(
        project_id=pid,
        version=1,
        status="structured",
        input_params=data["script_input"],
        plan_json=data["plan_json"],
        raw_text=data["plan_json"]["narration_draft"],
    )
    session.add(sv)
    await session.flush()

    # Scenes → Shots → FrameSpecs
    scene_id_map: dict[int, "uuid.UUID"] = {}  # noqa: F821
    shot_id_map: dict[tuple[int, int], "uuid.UUID"] = {}  # noqa: F821

    for sc_data in data["scenes"]:
        si = sc_data["order_index"]
        scene = Scene(script_version_id=sv.id, **sc_data)
        session.add(scene)
        await session.flush()
        scene_id_map[si] = scene.id

        for sh_data in data["shots"].get(si, []):
            shi = sh_data["order_index"]
            shot = Shot(scene_id=scene.id, **sh_data)
            session.add(shot)
            await session.flush()
            shot_id_map[(si, shi)] = shot.id

    # FrameSpecs
    for (si, shi), frames in data.get("frames", {}).items():
        shot_id = shot_id_map.get((si, shi))
        if not shot_id:
            continue
        for f_data in frames:
            session.add(FrameSpec(shot_id=shot_id, **f_data))

    # Character
    if "character" in data:
        session.add(CharacterProfile(project_id=pid, **data["character"]))

    await session.flush()

    n_scenes = len(data["scenes"])
    n_shots = sum(len(v) for v in data["shots"].values())
    n_frames = sum(len(v) for v in data.get("frames", {}).values())
    logger.info(
        "Eval project seeded: '%s' — %d scenes, %d shots, %d frames",
        pd["title"], n_scenes, n_shots, n_frames,
    )
    return str(pid)


async def seed_evaluation_projects(session: AsyncSession) -> list[str]:
    """Seed all 3 evaluation demo projects if they don't exist. Returns list of project IDs."""
    # Load global style presets for linking
    result = await session.execute(
        select(StylePreset).where(StylePreset.is_global.is_(True))
    )
    presets = {p.name: p for p in result.scalars().all()}

    created_ids = []
    for data in EVAL_PROJECTS:
        title = data["project"]["title"]
        existing = await session.execute(
            select(Project).where(Project.title == title).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            logger.info("Eval project already exists: '%s', skipping", title)
            continue

        pid = await _seed_one_eval_project(session, data, presets)
        created_ids.append(pid)

    if created_ids:
        await session.commit()
        logger.info("Seeded %d evaluation projects", len(created_ids))
    return created_ids
