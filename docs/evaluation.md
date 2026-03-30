# 품질 평가 시스템 (Quality Evaluation)

> 프로젝트와 Shot 단위로 품질을 기록·비교할 수 있는 이중 평가 체계.
> **자동 평가** (규칙 기반 점수)와 **수동 평가** (사람이 직접 채점)를 모두 지원한다.

---

## 평가 항목 (10개 기준)

| # | key | 라벨 | 설명 | 스코프 | 가중치 |
|---|-----|------|------|--------|--------|
| 1 | `script_quality` | 대본 품질 | 주제 전달력, 훅/내러티브/CTA 구조, 나레이션 자연스러움 | project | 1.2 |
| 2 | `scene_structure` | 씬 구조 | 씬 분할 적절성, 흐름 연결, 감정 곡선, 시간 배분 | project, scene | 1.0 |
| 3 | `shot_quality` | 샷 디자인 | 구도/카메라/전환 설계 품질, 나레이션 세그먼트 매칭 | project, shot | 1.0 |
| 4 | `frame_specificity` | 프레임 구체성 | FrameSpec의 구도/조명/배경 지시 구체성 | project, shot | 0.8 |
| 5 | `style_consistency` | 스타일 일관성 | StylePreset과 실제 생성물의 시각적 일관성 | project, shot | 1.2 |
| 6 | `image_quality` | 이미지 품질 | 생성 이미지의 구도, 디테일, 아티팩트 여부 | project, shot | 1.0 |
| 7 | `video_quality` | 비디오 품질 | 비디오 클립의 모션 자연스러움, 프레임 연속성 | project, shot | 1.0 |
| 8 | `tts_quality` | TTS 품질 | 음성 자연스러움, 발음 정확도, 감정 전달력 | project | 0.8 |
| 9 | `subtitle_sync` | 자막 싱크 | 자막 타이밍 정확도, 줄 나눔 가독성 | project | 0.6 |
| 10 | `final_output_quality` | 최종 결과물 | 렌더 mp4의 전체 완성도, 편집 리듬, 시청 몰입도 | project | 1.5 |

**총점**: 각 항목의 `가중치 × 점수(1~5)`의 가중 평균으로 산출.

---

## 자동 평가 vs 수동 평가

| 구분 | 자동 평가 (auto) | 수동 평가 (manual) |
|------|-----------------|-------------------|
| **실행** | API 호출 1회 | 사람이 폼에서 채점 |
| **reviewer** | `system` | `human` |
| **채점 기준** | 규칙 기반 (데이터 완성도, 비율, 에셋 존재 여부) | 사람의 주관적 품질 판단 |
| **장점** | 빠름, 일관적, 반복 가능 | 실제 시청 품질 반영 |
| **한계** | 생성물의 "미적 품질"은 평가 불가 | 주관적, 시간 소요 |

### 자동 평가 규칙 예시

| 항목 | 점수 산출 로직 |
|------|--------------|
| `script_quality` | ScriptVersion 존재 여부 + Scene/나레이션/목표 시간 유무 |
| `scene_structure` | Scene 수, 전체 duration 비율, 나레이션 커버리지 |
| `shot_quality` | narration_segment/asset_strategy 비율, duration 범위 적합성 |
| `frame_specificity` | FrameSpec 커버리지, start/end frame 존재 비율 |
| `image_quality` | ready 상태 이미지 에셋 비율 |
| `video_quality` | ready 상태 비디오 에셋 비율 |
| `final_output_quality` | 타임라인 존재 + 비디오 커버리지 + 실패 job 여부 |

---

## API

### 평가 기준 조회

```
GET /api/projects/{id}/evaluations/criteria?scope=project
```

### 자동 평가 실행

```
POST /api/projects/{id}/evaluations/auto
Body: { "script_version_id": "...", "run_label": "v1 initial" }
```

### 수동 평가 제출

```
POST /api/projects/{id}/evaluations
Body: {
  "target_type": "project",
  "scores": {
    "script_quality": 4,
    "scene_structure": 3,
    "shot_quality": 4,
    "frame_specificity": 3,
    "style_consistency": 4,
    "image_quality": 3,
    "video_quality": 2,
    "tts_quality": 4,
    "subtitle_sync": 3,
    "final_output_quality": 3
  },
  "comment": "이미지 품질은 좋지만 비디오 모션이 부자연스러움"
}
```

### 평가 이력 조회

```
GET /api/projects/{id}/evaluations?source=auto&limit=20
```

### 평가 요약

```
GET /api/projects/{id}/evaluations/summary
```

---

## 데이터 모델

```
quality_reviews
├── id (UUID, PK)
├── project_id (UUID, FK → projects)
├── target_type ("project" | "scene" | "shot")
├── target_id (UUID, nullable)
├── source ("manual" | "auto")
├── scores (JSON: {"script_quality": 4, ...})
├── overall_score (float, 가중 평균)
├── comment (text, nullable)
├── reviewer ("human" | "system" | "claude")
├── run_label (string, nullable — "v1", "after_regen" 등)
├── created_at
└── updated_at
```

---

## 평가용 데모 프로젝트 (Evaluation Baselines)

> `make seed` 실행 시 자동 생성되는 3종의 평가용 프로젝트.
> 서로 다른 영상 유형을 대표하며, 파이프라인 각 단계의 출력 품질을 비교/검증하는 데 사용한다.

### 프로젝트 목록

| ID | 프로젝트명 | 유형 | 길이 | 스타일 | Scene | Shot | Frame |
|----|-----------|------|------|--------|-------|------|-------|
| 1 | `[Eval] 45초 생산성 앱 추천 숏폼` | 교육/설명 | 45초 | Minimalist Infographic | 5 | 10 | 20 |
| 2 | `[Eval] 60초 감성 내레이션 — 비 오는 날의 서울` | 감성/브이로그 | 60초 | Cinematic Realistic | 4 | 9 | 22 |
| 3 | `[Eval] 30초 프리미엄 이어폰 광고` | 제품 광고 | 30초 | Premium Product Ad | 3 | 7 | 14 |

### 1. demo_shorts_explainer — 교육/설명 숏폼

**목적**: 빠른 템포, 높은 정보 밀도 환경에서의 파이프라인 품질 검증

| 단계 | 평가 포인트 |
|------|-----------|
| **Script** | 5개 앱이 균등한 시간에 배분되는지, CTA가 자연스러운지 |
| **Scene/Shot** | 각 앱별 독립된 씬 구분, UI 전체→디테일 줌인 패턴 유지 |
| **Frame** | start/end 프레임 간 구도 전환이 매끄러운지, 텍스트 영역 확보 |
| **Image** | 미니멀 인포그래픽 스타일 일관성, 앱 아이콘 표현 |
| **Video** | 빠른 전환 시 모션 품질, UI 패닝 자연스러움 |
| **TTS** | 빠른 나레이션 속도의 명료성 |
| **Subtitle** | 짧은 세그먼트 타이밍 정확도 |

### 2. demo_emotional_narration — 감성 내레이션

**목적**: 느린 템포, 분위기 중심 영상의 파이프라인 품질 검증

| 단계 | 평가 포인트 |
|------|-----------|
| **Script** | 서정적 나레이션의 자연스러움, 기승전결 구조 |
| **Scene/Shot** | 전경→디테일→전경 리듬, 분위기 그라데이션 |
| **Frame** | start→middle→end 3프레임의 시각적 연속성, 렌즈 필 일관성 |
| **Image** | 시네마틱 사실주의 품질, 빗줄기/보케 표현 |
| **Video** | 느린 카메라 무브먼트 품질, 비 내리는 모션 |
| **TTS** | 느린 템포의 감성적 전달력 |
| **Subtitle** | 시적 텍스트의 자연스러운 줄 나눔 |

### 3. demo_product_ad — 프리미엄 제품 광고

**목적**: 제품 중심 구도, 스튜디오 조명 환경의 파이프라인 품질 검증

| 단계 | 평가 포인트 |
|------|-----------|
| **Script** | 핵심 셀링 포인트 3개의 임팩트, 브랜드 각인 |
| **Scene/Shot** | 티저→기능→CTA 3막 구조, 매크로/라이프스타일 전환 |
| **Frame** | 블랙 배경 대비 림 라이트 표현, 소재 질감 구도 |
| **Image** | 제품 사진 퀄리티, 스튜디오 조명 정확도 |
| **Video** | 오빗 카메라 품질, 조명 스윕 모션 |
| **TTS** | 권위적 보이스의 명료성 |
| **Subtitle** | 제품명/기능명 노출 정확도 |

---

## 반복 평가 워크플로우

```bash
# 1. 서비스 기동 + seed
make build

# 2. [Eval] 프로젝트 3개 확인
open http://localhost:3000/projects

# 3. 프로젝트 상세 → QA / 품질 평가 탭

# 4. 자동 평가 실행 (초기 baseline)
#    → "자동 평가" 버튼 클릭 또는:
curl -X POST http://localhost:8000/api/projects/{id}/evaluations/auto \
  -H "Content-Type: application/json" \
  -d '{"run_label": "baseline"}'

# 5. 파이프라인 단계 실행 (이미지/비디오/TTS 등)

# 6. 재평가하여 점수 변화 확인
curl -X POST http://localhost:8000/api/projects/{id}/evaluations/auto \
  -H "Content-Type: application/json" \
  -d '{"run_label": "after_image_gen"}'

# 7. 수동 평가 추가 (실제 결과물 시청 후)
#    → UI에서 "수동 평가" 버튼 클릭

# 8. 평가 이력 확인
curl http://localhost:8000/api/projects/{id}/evaluations/summary | jq .
```

### 3개 프로젝트 비교 평가

```bash
# 각 프로젝트에 대해 자동 평가 실행 후 점수 비교
for pid in PROJECT_ID_1 PROJECT_ID_2 PROJECT_ID_3; do
  curl -s -X POST "http://localhost:8000/api/projects/$pid/evaluations/auto" \
    -H "Content-Type: application/json" \
    -d '{"run_label": "baseline"}' | jq '{overall: .overall_score, scores: .scores}'
done
```

---

## 자동 테스트

```bash
make test   # test_seed.py에서 duration 정합성, 프레임 커버리지 자동 검증
```

---

## Prompt Quality Benchmark (Planning/Prompt 보조 지표)

> 기존 자동 평가는 **데이터 완성도** 중심이다 (에셋 존재 여부, duration 정합성 등).
> Prompt Benchmark는 이와 별도로 **planning/prompt 단계의 텍스트 품질**을 숫자로 측정하는 보조 지표이다.
> 이미지를 vision으로 보는 것이 아니라, 생성에 사용되는 **prompt 텍스트 자체**를 분석한다.

### 평가 축 (4개)

| 축 | 가중치 | 측정 내용 |
|----|--------|----------|
| **Specificity** | 35% | subject/action/environment/lighting/camera/lens/background/mood 커버리지 |
| **Continuity** | 20% | style anchor 반복, lighting direction 일관성, character identity lock |
| **Motion Clarity** | 20% | camera_motion에 맞는 start/end/motion language 존재 여부 |
| **Artifact Prevention** | 25% | negative prompt baseline 커버리지 + forbidden elements 풍부함 |

- 각 축: 0–100점
- Overall: 가중 평균 (0–100)
- Failure reasons: 최대 10개 요약

### 사용법

```python
from shared.qa.prompt_benchmark import BenchmarkInput, run_prompt_benchmark

inp = BenchmarkInput(
    script_plan=script_plan_output,        # ScriptPlanOutput (optional)
    scene_breakdown=scene_breakdown_output, # SceneBreakdownOutput (optional)
    shot_breakdown=shot_breakdown_output,   # ShotBreakdownOutput (optional)
    frame_spec=frame_spec_output,           # FrameSpecOutput (optional)
    image_prompt=compiled.detailed_prompt,
    video_prompt=compiled.video_prompt,
    negative_prompt=compiled.negative_prompt,
    negative_video_prompt=compiled.provider_options.get("negative_video", ""),
    continuity_notes=compiled.continuity_notes,
)

scores = run_prompt_benchmark(inp)
print(scores.to_dict())
# {
#   "specificity": 82.5,
#   "continuity": 65.0,
#   "motion_clarity": 75.0,
#   "artifact_prevention": 90.0,
#   "overall": 79.1,
#   "failure_reasons": ["Continuity: no character identity lock markers found"]
# }
```

### 테스트로 실행

```bash
# Docker 내부
make test-benchmark

# 또는 직접
docker compose --env-file .env -f infra/docker/docker-compose.yml \
  exec api python -m pytest tests/test_prompt_benchmark.py -v
```

### Baseline 프로젝트 3종 Before/After 비교

Prompt Compiler 개선 전후를 **동일한 기준**으로 비교하려면:

1. **Before**: 개선 전 compiler로 3종 프로젝트의 prompt를 생성
2. **Benchmark 실행**: 각 프로젝트별 `BenchmarkInput`을 구성하여 `run_prompt_benchmark()` 호출
3. **결과 기록**: overall 및 축별 점수를 기록
4. **After**: 개선된 compiler로 동일 입력에 대해 다시 prompt 생성 → benchmark 재실행
5. **비교**: 동일 축끼리 점수 차이 확인

```bash
# 예시: 3종 프로젝트 일괄 벤치마크 (pytest 기반)
make test-benchmark
# 테스트 내 weak vs strong 예시가 before/after 시뮬레이션 역할

# 커스텀 비교 스크립트 (선택)
docker compose --env-file .env -f infra/docker/docker-compose.yml \
  exec api python -c "
from shared.qa.prompt_benchmark import BenchmarkInput, run_prompt_benchmark
# ... 프로젝트별 compiled prompt를 BenchmarkInput으로 구성 ...
scores = run_prompt_benchmark(inp)
print(scores.to_dict())
"
```

| 프로젝트 | Before Overall | After Overall | 개선폭 |
|----------|---------------|---------------|--------|
| 45초 생산성 앱 추천 숏폼 | _측정_ | _측정_ | _Δ_ |
| 60초 감성 내레이션 | _측정_ | _측정_ | _Δ_ |
| 30초 프리미엄 이어폰 광고 | _측정_ | _측정_ | _Δ_ |

### 기존 자동 평가와의 관계

| 관점 | 자동 평가 (evaluator) | Prompt Benchmark |
|------|----------------------|------------------|
| 대상 | DB에 저장된 에셋/메타데이터 | 텍스트 prompt + planning output |
| 시점 | 에셋 생성 후 | 에셋 생성 전 (prompt 단계) |
| 방식 | 에셋 존재/커버리지/duration 규칙 | keyword coverage + structural pattern matching |
| 용도 | 파이프라인 전체 완성도 | prompt compiler 품질 개선 추적 |

두 지표를 함께 사용하면 "prompt가 좋아졌는데 생성물은 괜찮은가?" 를 양쪽에서 검증할 수 있다.

---

## 향후 확장

- [ ] Claude 기반 critic — 생성된 이미지/비디오를 직접 보고 품질 채점 (`reviewer: "claude"`)
- [ ] Shot 단위 수동 평가 — 개별 Shot에 대한 세부 점수
- [ ] 이미지/비디오 생성 후 A/B variant 비교 UI
- [ ] 평가 점수 트렌드 차트 (시간별 점수 변화)
- [ ] 렌더 결과물의 프레임별 QA 자동화
- [ ] 새 provider 추가 시 3종 프로젝트로 baseline 비교
- [ ] 평가 결과 export (CSV/JSON)
- [ ] Prompt Benchmark 점수를 DB에 저장하여 시계열 비교
- [ ] CI에서 prompt benchmark regression 자동 감지
