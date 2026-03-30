"""Quality evaluation criteria definitions.

Each criterion has:
- key: unique identifier used in scores JSON
- label: Korean display name
- description: evaluation guidance
- scopes: which target_types can use this criterion
- weight: relative importance (1.0 = normal)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Criterion:
    key: str
    label: str
    description: str
    scopes: tuple[str, ...]
    weight: float = 1.0


CRITERIA: list[Criterion] = [
    Criterion(
        key="script_quality",
        label="대본 품질",
        description="주제 전달력, 훅/내러티브/CTA 구조, 나레이션 자연스러움",
        scopes=("project",),
        weight=1.2,
    ),
    Criterion(
        key="scene_structure",
        label="씬 구조",
        description="씬 분할 적절성, 흐름 연결, 감정 곡선, 시간 배분",
        scopes=("project", "scene"),
        weight=1.0,
    ),
    Criterion(
        key="shot_quality",
        label="샷 디자인",
        description="구도/카메라/전환 설계 품질, 나레이션 세그먼트 매칭",
        scopes=("project", "shot"),
        weight=1.0,
    ),
    Criterion(
        key="frame_specificity",
        label="프레임 구체성",
        description="FrameSpec의 구도/조명/배경 지시 구체성, 프롬프트 활용도",
        scopes=("project", "shot"),
        weight=0.8,
    ),
    Criterion(
        key="style_consistency",
        label="스타일 일관성",
        description="StylePreset/CharacterProfile과 실제 생성물의 시각적 일관성",
        scopes=("project", "shot"),
        weight=1.2,
    ),
    Criterion(
        key="image_quality",
        label="이미지 품질",
        description="생성 이미지의 구도, 디테일, 프롬프트 충실도, 아티팩트 여부",
        scopes=("project", "shot"),
        weight=1.0,
    ),
    Criterion(
        key="video_quality",
        label="비디오 품질",
        description="비디오 클립의 모션 자연스러움, 해상도, 프레임 연속성",
        scopes=("project", "shot"),
        weight=1.0,
    ),
    Criterion(
        key="tts_quality",
        label="TTS 품질",
        description="음성 자연스러움, 발음 정확도, 감정 전달력, 속도 적절성",
        scopes=("project",),
        weight=0.8,
    ),
    Criterion(
        key="subtitle_sync",
        label="자막 싱크",
        description="자막 타이밍 정확도, 줄 나눔 가독성, 텍스트 정확성",
        scopes=("project",),
        weight=0.6,
    ),
    Criterion(
        key="final_output_quality",
        label="최종 결과물",
        description="렌더 mp4의 전체 완성도, 편집 리듬, 시청 몰입도",
        scopes=("project",),
        weight=1.5,
    ),
]

CRITERIA_BY_KEY: dict[str, Criterion] = {c.key: c for c in CRITERIA}

CRITERIA_KEYS: list[str] = [c.key for c in CRITERIA]


def criteria_for_scope(scope: str) -> list[Criterion]:
    """Return criteria applicable to a given target_type scope."""
    return [c for c in CRITERIA if scope in c.scopes]


def compute_weighted_average(scores: dict[str, int | float]) -> float | None:
    """Compute weighted average from a scores dict. Returns None if empty."""
    total_weight = 0.0
    total_score = 0.0
    for key, value in scores.items():
        criterion = CRITERIA_BY_KEY.get(key)
        if criterion is None:
            continue
        w = criterion.weight
        total_weight += w
        total_score += value * w
    if total_weight == 0:
        return None
    return round(total_score / total_weight, 2)
