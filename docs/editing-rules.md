# Editing Rules Reference

이 문서는 타임라인 조립과 렌더링 단계에서 적용되는 편집 규칙을 정의합니다.
`packages/shared/shared/editing/` 모듈에 구현되어 있습니다.

---

## 1. Format Profiles (포맷별 페이싱)

| 프로필 | 대상 | hook 길이 | scene gap | intro fade | outro fade |
|--------|------|-----------|-----------|------------|------------|
| `shorts` | YouTube Shorts / Reels | 2.5초 | 150ms | 300ms | 500ms |
| `explainer` | 교육 / 설명 영상 | 4.0초 | 500ms | 500ms | 800ms |
| `product_ad` | 제품 광고 / CM | 2.0초 | 100ms | 200ms | 600ms |
| `emotional_narration` | 감성 나레이션 / 스토리 | 5.0초 | 800ms | 800ms | 1200ms |

### Zone 분류

모든 shot은 진행 시간에 따라 4개 zone 중 하나에 배치됩니다:

- **hook**: 영상 시작~hook_duration_sec (첫 2~5초). 빠른 컷, 임팩트 있는 모션
- **body**: hook 이후~전체의 60% 구간. 안정적인 리듬
- **climax**: 60~85% 구간. 텐션 고조
- **outro**: 마지막 15%. 느린 호흡, 마무리

### Pacing Rules per Zone

| zone | shorts max/min/pref (ms) | explainer max/min/pref (ms) | 리듬 |
|------|--------------------------|----------------------------|------|
| hook | 2500/800/1500 | 4000/1500/2500 | rapid / steady |
| body | 5000/1500/3000 | 8000/2500/5000 | varied / steady |
| climax | 4000/1000/2000 | 6000/2000/4000 | rapid / steady |
| outro | 6000/2000/4000 | 8000/3000/5000 | slow / slow |

---

## 2. Transition Presets

| 이름 | 타입 | 기본 길이 | 용도 |
|------|------|-----------|------|
| `cut` | cut | 0ms | 일반 컷 |
| `crossfade` | xfade(fade) | 500ms | 부드러운 전환 |
| `dip_to_black` | custom_dip | 400ms | scene 경계 |
| `dissolve` | xfade(dissolve) | 600ms | 감성적 전환 |
| `fade_in` | fade_in | 500ms | 영상 시작 |
| `fade_out` | fade_out | 500ms | 영상 끝 |
| `wipe_left` | xfade(wipeleft) | 400ms | 방향 전환 |
| `slide_left` | xfade(slideleft) | 400ms | 슬라이드 |
| `zoom_in` | xfade(smoothup) | 400ms | 줌 전환 |

### Transition 선택 로직

1. Shot의 `transition_in` / `transition_out` 힌트가 있으면 우선 적용
2. Scene 경계이면 format profile의 `scene_transition` 적용
3. 첫 shot → `fade_in`, 마지막 shot → `fade_out`
4. 그 외 → format profile의 `default_transition`

---

## 3. Image Motion Presets (Ken Burns)

| 이름 | 줌 시작→끝 | 방향 | easing | 용도 |
|------|-----------|------|--------|------|
| `slow_zoom_in` | 1.0→1.2 | center | ease_in_out | 기본 접근 |
| `slow_zoom_out` | 1.25→1.0 | center | ease_in_out | 전체 보기 |
| `gentle_pan_right` | 1.08→1.12 | left→right | linear | 수평 이동 |
| `gentle_pan_left` | 1.08→1.12 | right→left | linear | 수평 이동 |
| `tilt_up` | 1.05→1.1 | bottom→top | ease_out | 상승감 |
| `tilt_down` | 1.05→1.1 | top→bottom | ease_out | 하강감 |
| `dramatic_zoom_in` | 1.0→1.4 | center | ease_in | 강조/임팩트 |
| `push_in_left` | 1.0→1.25 | right→left | ease_in_out | 좌측 포커스 |
| `push_in_right` | 1.0→1.25 | left→right | ease_in_out | 우측 포커스 |
| `pull_back` | 1.35→1.0 | center | ease_out | 전체 공개 |
| `static_hold` | 1.0→1.02 | center | linear | 최소 움직임 |
| `hook_zoom` | 1.0→1.35 | center | ease_in | hook 전용 임팩트 |

### Motion 선택 로직

1. Shot의 `camera_movement` 힌트 기반 매핑 (zoom in → slow_zoom_in 등)
2. 매핑 실패 시 zone 기반 순환:
   - hook: `hook_zoom`, `dramatic_zoom_in`, `push_in_right` 순환
   - body: `slow_zoom_in`, `gentle_pan_right`, `gentle_pan_left`, `tilt_up` 순환
   - climax: `dramatic_zoom_in`, `push_in_left`, `slow_zoom_out` 순환
   - outro: `slow_zoom_out`, `pull_back`, `static_hold` 순환

### Easing 함수

- `linear`: 일정 속도
- `ease_in`: 느리게 시작 → 빠르게 (t²)
- `ease_out`: 빠르게 시작 → 느리게 (1-(1-t)²)
- `ease_in_out`: 느리게 → 빠르게 → 느리게 (3t²-2t³)

---

## 4. Pause / Beat Segments

| 유형 | 발생 시점 | 기본 길이 | 비주얼 |
|------|-----------|-----------|--------|
| `scene_gap` | scene 경계 | format별 scene_gap_ms | fade_black / hold_last |
| `hook_pause` | hook zone 종료 직후 | format별 pause_after_hook_ms | hold_last |
| `beat` | 매 2번째 shot 뒤 (body zone) | format별 beat_marker_ms | hold_last |

### Shorts vs Explainer 비교

| | Shorts | Explainer |
|---|--------|-----------|
| scene_gap | 150ms (거의 없음) | 500ms (호흡) |
| hook_pause | 200ms (짧은 여운) | 400ms (안내 여백) |
| beat_marker | 100ms (미세 리듬) | 200ms (이해 여백) |

---

## 5. Subtitle Emphasis Rules

### 기본 규칙

| 이름 | 패턴 | 스타일 | 우선순위 |
|------|------|--------|----------|
| `number_stat` | 숫자+단위(%, 만, 원...) | **bold** | 10 |
| `quoted_phrase` | "인용문" | *italic* | 5 |
| `question_mark` | 단어? | **bold** | 3 |
| `exclamation` | 단어! | **bold** | 2 |
| `parenthetical` | (괄호 내용) | *italic* | 1 |

### Hook 전용 추가 규칙

| 이름 | 패턴 | 스타일 | 색상 |
|------|------|--------|------|
| `hook_number` | 모든 숫자 | **bold** | cyan |
| `hook_question` | 단어? | **bold** | cyan |

### 한국어 줄바꿈

기본 word-wrap 대신 한국어 조사 경계를 인식하여 자연스럽게 줄을 나눕니다:
- 우선 조사(는, 은, 이, 가, 을, 를, 에, 에서, 으로...) 뒤에서 줄바꿈
- 줄 길이 균형과 조사 위치를 함께 고려하여 최적 분리점 선택

---

## 6. QA Rules — 전환 일관성

`check_shot_transition_coherence` 규칙이 다음을 검사합니다:

| 검사 | 심각도 | 설명 |
|------|--------|------|
| `transition_stagnant` | info | 연속 3개 이상 정적 shot (카메라 움직임 없음) |
| `transition_monotonous` | info | 동일 asset_strategy 3회 이상 연속 |
| `transition_pacing_jump` | warning | 인접 shot 길이 차이 3배 이상 |
| `transition_missing_audio` | warning | 이전 shot에는 TTS가 있는데 현재 shot에 없음 |

---

## 7. Render Pipeline 요약

```
Shot Data
  ↓
Timeline Composer (editing rules 적용)
  ├── Zone 분류 (hook/body/climax/outro)
  ├── Pause/Beat 삽입
  ├── Transition Preset 결정
  ├── Image Motion Preset 결정
  └── Duration Clamping (zone별 min/max)
  ↓
TimelineData (v2)
  ↓
FFmpeg Builder
  ├── Eased Ken Burns (zoompan + easing)
  ├── Fade In / Fade Out
  ├── Pause Segment 렌더 (black/hold)
  ├── Subtitle Burn-in (emphasis 적용, style별)
  └── Audio Concat + Pad
  ↓
Final MP4
```

---

## 8. 확장 가이드

### 새 Format Profile 추가

`packages/shared/shared/editing/pacing.py`에 `FormatProfile` 인스턴스를 추가하고
`_PROFILES` dict에 등록합니다.

### 새 Motion Preset 추가

`packages/shared/shared/editing/motion.py`에 `MotionPreset` 인스턴스를 추가하고
`_PRESETS` dict에 등록합니다. `_CAMERA_MOTION_MAP`에 camera_movement 키워드 매핑을 추가합니다.

### 새 Transition Preset 추가

`packages/shared/shared/editing/transitions.py`에 `TransitionPreset` 인스턴스를 추가합니다.
`ffmpeg_xfade_name`은 ffmpeg의 xfade 트랜지션 이름과 일치해야 합니다.
