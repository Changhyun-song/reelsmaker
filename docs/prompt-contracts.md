# Prompt Contracts

> 최종 갱신: 2026-03-24

모든 AI planning 호출은 **strict JSON**으로 응답해야 한다.
각 단계의 출력 스키마는 `packages/shared/shared/schemas/contracts.py`에 Pydantic 모델로 정의되어 있으며,
`generate_validated()` 함수가 응답을 자동 검증하고 실패 시 최대 3회 재시도한다.

Golden examples와 Bad/Good 비교는 → `docs/planner-examples.md`

---

## 1. Script Planner (`ScriptPlanOutput`)

**입력**: 주제, 타깃, 톤, 길이, 포맷, 언어, 제약사항
**출력**: 구조화된 대본 계획

### 필드 명세

| 필드 | 타입 | 검증 | 설명 |
|------|------|------|------|
| `title` | string | min_length=2 | 호기심을 유발하는 영상 제목 (≤12단어) |
| `summary` | string | min_length=10 | WHY를 설명하는 한 문단 엘리베이터 피치 |
| `hook` | string | min_length=5 | 첫 3초 주의 끌기. 통계/질문/반직관적 주장/What-if 중 하나 |
| `narrative_flow` | string[] | min_length=2 | 3-7개 핵심 스토리 비트 |
| `sections` | ScriptSection[] | min_length=2 | 영상 전체를 커버하는 논리적 섹션 |
| `ending_cta` | string | min_length=5 | 구체적 행동 유도 (단순 "좋아요/구독" 금지) |
| `narration_draft` | string | min_length=20 | 모든 섹션의 narration을 자연스럽게 연결 |
| `estimated_duration_sec` | float | 5-3600 | 총 예상 길이 |

### ScriptSection 필드

| 필드 | 타입 | 검증 | 설명 |
|------|------|------|------|
| `title` | string | min_length=2 | 섹션 라벨 |
| `description` | string | min_length=5 | 이 섹션이 달성하는 것 |
| `narration` | string | min_length=5 | 실제 발화 텍스트 |
| `visual_notes` | string | min_length=5 | `[Shot type] + 구체 장면 + Lighting + Camera` 형식 |
| `duration_sec` | float | 2-300 | 섹션 길이 |

### Cross-Validation
- sections의 duration_sec 합계가 estimated_duration_sec의 ±30% 이내

### 금지 패턴
- 일반적 인사: "안녕하세요", "Hi everyone"
- 필러 전환: "자, 그럼", "다음으로"
- 모호한 visual_notes: "관련 이미지", "show example"

---

## 2. Scene Planner (`SceneBreakdownOutput`)

**입력**: ScriptVersion.raw_text + target_duration + language
**출력**: Scene 목록 + total_duration_sec

### SceneBreakdownItem 필드

| 필드 | 타입 | 검증 | 설명 |
|------|------|------|------|
| `scene_index` | int | ≥0 | 0-based 순서 |
| `title` | string | min_length=2 | 간결한 장면 제목 (≤8 단어) |
| `purpose` | string | min_length=5 | 서사 기능: "통계로 시청자의 고정관념 파괴" ✓ / "시작" ✗ |
| `summary` | string | min_length=10 | 1-2문장 개요 |
| `narration_text` | string | min_length=5 | 이 장면의 정확한 내레이션 (원본 스크립트 언어) |
| `setting` | string | min_length=3 | 영어, 구체적 장소: "modern radiology room, dark, blue monitors" |
| `mood` | string | min_length=2 | 1-3 감정 키워드 |
| `emotional_tone` | string | min_length=5 | 시각/음악 방향 포함 상세 감정 연출 |
| `visual_intent` | string | min_length=15 | 영어, 이미지 AI에 사용 가능한 구체적 시각 묘사 |
| `transition_hint` | string | default="cut" | 다음 장면으로의 전환: cut, dissolve, fade_to_black, smash_cut, none |
| `estimated_duration_sec` | float | 2-300 | 장면 길이 |

### Cross-Validation
- scenes의 duration 합 = total_duration_sec (오차 ≤5초)
- total_duration_sec가 target의 ±20% 이내

### 연속성 규칙
- 인접 장면 간 mood 급변 금지 (calm → intense는 전환 beat 필요)
- 마지막 장면의 transition_hint는 반드시 "none"
- visual_intent는 narration을 그대로 번역한 것이 아니라 시각적 묘사여야 함

### 금지 패턴
- purpose: "continue the story", "transition", "middle part"
- setting: "relevant location", "적절한 배경", "a place"
- visual_intent: narration을 영어로 번역한 것

---

## 3. Shot Planner (`ShotBreakdownOutput`)

**입력**: Scene 정보 (title, duration, narration, setting, mood, visual_intent)
**출력**: Shot 목록 + total_duration_sec

### ShotBreakdownItem 필드

| 필드 | 타입 | 검증 | 설명 |
|------|------|------|------|
| `shot_index` | int | ≥0 | 0-based 순서 |
| `purpose` | string | min_length=5 | 이 샷이 달성하는 것 |
| `duration_sec` | float | 1.5-15 | 2-8초 권장 |
| `shot_type` | string | min_length=3 | establishing, insert, reaction, action, cutaway, over_the_shoulder, point_of_view, montage_element, detail, reveal, transition, title_card |
| `camera_framing` | string | min_length=3 | extreme_wide ~ extreme_close_up, overhead, low_angle, birds_eye |
| `camera_motion` | string | min_length=3 | static, slow_pan_left/right, dolly_in/out, tracking, crane, handheld, zoom, push_in, orbit |
| `subject` | string | min_length=5 | 영어, 구체적: "woman in navy blazer holding tablet" ✓ / "a person" ✗ |
| `environment` | string | min_length=5 | 영어, 5+ 디테일: "modern open-plan office, floor-to-ceiling windows, dusk skyline" |
| `emotion` | string | min_length=3 | 구체적 감정: "focused determination" ✓ / "good" ✗ |
| `narration_segment` | string | 선택 | 이 샷 위에 흐르는 narration 부분 (원본 언어) |
| `transition_in` | string | default="cut" | cut, fade_in, dissolve_in, wipe_in |
| `transition_out` | string | default="cut" | cut, fade_out, dissolve_out, wipe_out |
| `asset_strategy` | string | default="image_to_video" | image_to_video, still_image, direct_video, mixed |
| `description` | string | min_length=30 | **핵심 필드** — 독립적 이미지/비디오 프롬프트 |

### description 필드 구조

이 필드는 이미지/비디오 AI에 바로 투입되므로 최소 30자, 아래 요소 포함:

```
[Camera framing] of [subject + action/pose] in [environment],
[lighting description], [mood/atmosphere], [style keywords], [quality tags]
```

예시:
```
Medium-wide shot slowly panning right across a row of high-resolution medical
monitors in a dark radiology reading room, each screen displaying AI-analyzed
CT scan heatmaps with confidence percentage overlays, cool blue ambient
lighting reflecting off glass partitions, cinematic medical drama lighting,
photorealistic 8k
```

### Cross-Validation
- shots의 duration_sec 합 = total_duration_sec (오차 ≤3초)
- total_duration_sec가 scene duration의 ±10% 이내

### 리듬 규칙
- 동일 camera_framing 3연속 금지
- 첫 샷은 보통 wider (establishing), 마지막 샷은 결론적
- camera_motion과 감정 강도 매칭: static=차분, dolly_in=집중, handheld=긴장

### Asset Strategy 가이드
| 전략 | 용도 |
|------|------|
| `image_to_video` | 대부분의 샷. 정적 이미지 → 애니메이션. 단순/예측 가능한 동작 |
| `still_image` | 타이틀 카드, 텍스트 오버레이, 인포그래픽 |
| `direct_video` | 복잡한 액션, 다수 움직이는 피사체 |
| `mixed` | 합성 접근 |

### 금지 패턴
- description < 30자
- subject: "the subject", "a person", "someone"
- environment: "a place", "background", "some location"

---

## 4. Frame Planner (`FrameSpecOutput`)

**입력**: Shot 정보 + 인접 Shot 컨텍스트
**출력**: FrameSpec 목록 (start + [middle] + end, 최소 2개, 최대 4개)

### FrameSpecItem 필드

| 필드 | 타입 | 검증 | 설명 |
|------|------|------|------|
| `frame_role` | string | start\|middle\|end | 프레임 역할 |
| `composition` | string | min_length=10 | 삼분법/대칭/리딩라인/깊이 레이어/프레이밍 기법 구체 서술 |
| `subject_position` | string | min_length=5 | 그리드 기반: "right-third intersection, upper body 40%" |
| `camera_angle` | string | min_length=3 | eye-level, low-angle 15°, dutch angle 10° 등 |
| `lens_feel` | string | min_length=5 | 초점거리+조리개+효과: "85mm f/1.8, shallow DOF" |
| `lighting` | string | min_length=10 | 3점 조명 구조: Key(방향+색온도) + Fill + Rim/Accent |
| `mood` | string | min_length=3 | 이 프레임의 감정적 질감 |
| `action_pose` | string | min_length=5 | 구체적 물리 묘사: 자세, 제스처, 표정, 동작 |
| `background_description` | string | min_length=10 | 3단계 깊이: immediate/mid/far BG |
| `continuity_notes` | string | 선택 | 인접 프레임/샷과의 일관성 유지 항목 |
| `forbidden_elements` | string | 선택 | 생성 아티팩트 방지 요소 |

### Cross-Validation
- 반드시 start + end 프레임 포함
- shot ≥ 5초일 때만 middle 프레임 추가

### Camera Motion → Frame 관계 (핵심)

start와 end 프레임의 차이가 shot의 camera_motion을 반영해야 한다:

| camera_motion | start frame | end frame |
|---------------|-------------|-----------|
| static | 동일 구도 | 미세 표정/포즈 변화만 |
| slow_pan_right | subject 좌측 배치 | subject 우측으로 이동, 배경 좌측 이동 |
| dolly_in | 넓은 프레이밍, 환경 많이 보임 | 좁은 프레이밍, subject 크게, 배경 적게 |
| zoom_in | 환경 많이 보임 | subject가 프레임 더 차지 (원근감 변화 없음, dolly와 차이) |
| tilt_up | 하단 부분 보임 | 상단 부분 드러남 |
| tracking | subject 초기 위치 | subject 새 위치, 배경 시차 이동 |
| crane_up | 낮은 앵글 | 높은 앵글, 공간 전체 드러남 |

### Lighting 구조

모든 lighting 필드는 최소 Key light를 포함해야 한다:

```
Key: [색온도]K [방향] [강도/특성]
Fill: [색온도]K [방향] [Key 대비 비율]
Rim/Accent: [위치] [효과]
Practical: [환경 내 광원] (선택)
```

예시: "Key: warm 3200K from camera-left 45° above. Fill: soft cool 5600K from right, 2 stops under key. Rim: thin warm edge from behind-right. Practical: monitor screen glow."

### 금지 패턴
- composition: "balanced", "aesthetic" (기법 미명시)
- action_pose: "happy", "thinking" (감정만, 물리적 묘사 없음)
- lighting: "good lighting", "well lit" (방향/색온도 없음)
- background_description < 10자
- static이 아닌데 start/end 구도가 동일

---

## 5. Prompt Compiler (deterministic compilation)

> 코드: `packages/shared/shared/prompt_compiler/`

Prompt Compiler는 AI 호출 없이 **pure function**으로 동작한다.
FrameSpec + Shot + Scene + StylePreset + CharacterProfile을 조합해서
이미지/비디오 생성 AI에 전달할 최종 프롬프트를 컴파일한다.

### 입력 (CompilerContext)

| 레이어 | 소스 | 역할 |
|--------|------|------|
| `ProjectContext` | `Project.settings` | 해상도, aspect_ratio, 기본 모델 |
| `StyleContext` | `StylePreset` (active) | 스타일 키워드, 색상 팔레트, 렌더링 스타일, prefix/suffix, negative |
| `CharacterContext[]` | `CharacterProfile[]` | 외모, 의상, 포즈 규칙, 금지 변경 사항 |
| `SceneContext` | `Scene` | 배경, 분위기, 감정, 시각적 의도 |
| `ShotContext` | `Shot` | 샷 유형, 카메라, 환경, 감정, asset 전략 |
| `FrameContext` | `FrameSpec` | 구도, 카메라 앵글, 조명, 분위기, 행동, 연속성 |

### 출력 (CompiledPrompt)

```json
{
  "concise_prompt": "Cinematic close-up, woman in red coat, rain-soaked street, melancholic mood",
  "detailed_prompt": "Cinematic realism, close-up shot of a woman in a red coat walking down a rain-soaked city street at night, dark hair, pale skin, minimal makeup, eye-level angle, 50mm lens feel, volumetric rain backlit by neon signs, moody blue-orange grading, photorealistic, 8k",
  "video_prompt": "same as detailed + camera motion: slow dolly forward, action: walking slowly, duration: 4s",
  "negative_prompt": "cartoon, anime, low resolution, text, watermark, blurry, inconsistent features",
  "continuity_notes": "Character should maintain same red coat and hairstyle from previous shot",
  "provider_options": { ... }
}
```

### 컴파일 파이프라인 (image prompt)

```
1. Style prefix (prompt_prefix)
2. Shot description (핵심 시각 설명)
3. Frame composition + action + subject_position
4. Character snippets (appearance, outfit, traits, pose_rules)
5. Camera (angle/framing + lens_feel)
6. Lighting (frame > style fallback)
7. Background (frame > shot.environment fallback)
8. Mood/Atmosphere (frame.mood > shot.emotion + scene atmosphere)
9. Style keywords + rendering_style + color_palette
10. Style suffix (prompt_suffix)
```

### Video prompt 차이점
- 카메라 모션 포함 (`camera_movement`)
- action_pose가 모션 설명으로 사용
- `duration_sec` 포함

### Negative prompt 병합
중복 제거 후 합산:
1. `StylePreset.negative_prompt`
2. `StylePreset.negative_rules`
3. `FrameSpec.forbidden_elements`
4. 각 `CharacterProfile.forbidden_changes`

---

## Validation & Retry 정책

1. AI 응답을 JSON으로 파싱
2. Pydantic 모델로 검증 (강화된 min_length, cross-validation 포함)
3. 실패 시 **구체적 에러 메시지**를 프롬프트에 추가하여 재시도 (최대 3회)
4. 3회 실패 시 `ProviderError` 발생 → Job이 failed 상태로 전환

```
Attempt 1: Generate → Parse → Validate ✗
  Error: "description too short (12 chars, need ≥30)"
Attempt 2: Generate (+ error feedback) → Parse → Validate ✗
  Error: "section durations sum (85s) deviates >30% from estimated (60s)"
Attempt 3: Generate (+ error feedback) → Parse → Validate ✓
```

### 주요 Validation 체크

| 단계 | 체크 항목 |
|------|----------|
| Script | section duration 합 ≈ estimated_duration (±30%) |
| Scene | scene duration 합 = total_duration (±5s) |
| Shot | shot duration 합 = total_duration (±3s), description ≥ 30 chars |
| Frame | start+end 프레임 필수, composition ≥ 10 chars, lighting ≥ 10 chars |

---

## System Prompt 설계 원칙

1. **역할 부여**: 단계별 전문가 (screenwriter / video director / cinematographer / visual director)
2. **테이블 형식**: 필드별 규칙을 마크다운 테이블로 명시
3. **금지 패턴**: 각 단계마다 BANNED 섹션으로 모호한 표현 차단
4. **JSON 강제**: system prompt 끝에 "Output ONLY valid JSON" 지시
5. **구체성 예시**: 좋은 예시를 필드 설명에 포함 (description 포맷 등)
6. **연속성 강제**: 인접 요소와의 일관성 규칙 명시
7. **언어 규칙**: narration은 프로젝트 언어, visual/description은 영어
