# ReelsMaker — Production Pipeline

> 최종 갱신: 2026-03-24

## 개요

주제 입력부터 최종 mp4 export까지, ReelsMaker는 **12단계 파이프라인**을 순차적으로 실행한다.
각 단계는 독립적인 Job으로 실행되며, 실패 시 해당 단계만 재시도할 수 있다.

```
주제/키워드 입력
      │
      ▼
 ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
 │ 1.Script │────▶│ 2.Scene  │────▶│ 3.Shot   │────▶│ 4.Frame  │
 │ Planning │     │ Planning │     │ Planning │     │ Planning │
 └──────────┘     └──────────┘     └──────────┘     └──────────┘
                                                          │
      ┌───────────────────────────────────────────────────┘
      ▼
 ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
 │ 5.Prompt │────▶│ 6.Image  │────▶│ 7.Video  │────▶│ 8.TTS    │
 │ Compile  │     │ Generate │     │ Generate │     │ Generate │
 └──────────┘     └──────────┘     └──────────┘     └──────────┘
                                                          │
      ┌───────────────────────────────────────────────────┘
      ▼
 ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
 │ 9.Sub-   │────▶│10.Time-  │────▶│11.Render │────▶│12.QA /   │
 │ title    │     │ line     │     │          │     │ Retry    │
 └──────────┘     └──────────┘     └──────────┘     └──────────┘
                                                          │
                                                          ▼
                                                    📁 mp4 Export
```

---

## Stage 1: Script Planning (대본 생성)

| 항목 | 내용 |
|------|------|
| **트리거** | 사용자가 주제/키워드를 입력하고 "대본 생성" 클릭 |
| **처리** | 비동기 (Worker Job: `script_generate`) |
| **입력** | 주제, 키워드, 원하는 길이, 톤, Project.settings |
| **프로바이더** | OpenAI GPT-4o |
| **프롬프트 전략** | 시스템 프롬프트로 영상 내레이션 전문가 역할 부여. 출력 형식 지정 (순수 내레이션 텍스트) |
| **출력** | ScriptVersion.raw_text (내레이션 원문) |
| **상태 변화** | ScriptVersion: draft → (완료 후 사용자 검토) |
| **ProviderRun** | 기록: provider=openai, operation=chat_completion |

### 대안 경로
- 사용자가 직접 대본을 입력하는 경우 이 단계를 건너뛴다.
- 기존 ScriptVersion을 복사하여 수정하는 것도 가능하다.

---

## Stage 2: Scene Planning (장면 분해)

| 항목 | 내용 |
|------|------|
| **트리거** | 사용자가 대본을 승인하고 "구조화" 클릭 |
| **처리** | 비동기 (Worker Job: `script_structure` — scene 단계) |
| **입력** | ScriptVersion.raw_text, Project.settings |
| **프로바이더** | OpenAI GPT-4o |
| **프롬프트 전략** | 대본을 논리적 장면으로 분해. JSON 배열 출력 강제 |
| **출력** | Scene 행 목록 (title, description, setting, mood, duration_estimate_sec) |
| **상태 변화** | ScriptVersion: draft → structuring |

### GPT 출력 스키마 (예시)
```json
[
  {
    "title": "도시의 밤",
    "description": "주인공이 네온 빛이 가득한 도시 거리를 걷는다",
    "setting": "밤, 네온사인이 빛나는 도심 골목",
    "mood": "몽환적, 고독",
    "duration_estimate_sec": 15
  }
]
```

---

## Stage 3: Shot Planning (샷 분해)

| 항목 | 내용 |
|------|------|
| **트리거** | Scene Planning 완료 후 자동 연계 |
| **처리** | 비동기 (Worker Job: `script_structure` — shot 단계) |
| **입력** | 각 Scene의 description + setting + mood |
| **프로바이더** | OpenAI GPT-4o |
| **프롬프트 전략** | 각 Scene을 카메라 샷으로 분해. 샷 타입, 카메라 무빙, 길이 지정 |
| **출력** | Shot 행 목록 (shot_type, description, camera_movement, duration_sec) |

### 단계적 요청 이유
Scene → Shot을 한 번에 요청하지 않고 Scene마다 별도로 요청한다:
1. 토큰 제한 회피
2. Scene 컨텍스트를 집중적으로 전달
3. 실패 시 해당 Scene의 Shot만 재생성

---

## Stage 4: Frame Planning (프레임 분해)

| 항목 | 내용 |
|------|------|
| **트리거** | Shot Planning 완료 후 자동 연계 |
| **처리** | 비동기 (Worker Job: `script_structure` — frame 단계) |
| **입력** | 각 Shot의 description + Scene 컨텍스트 + CharacterProfile 목록 |
| **프로바이더** | OpenAI GPT-4o |
| **프롬프트 전략** | 각 Shot을 렌더링 가능한 프레임으로 분해. 비주얼 프롬프트, 대사, 길이 지정 |
| **출력** | FrameSpec 행 목록 (visual_prompt, dialogue, dialogue_character_id, duration_ms, transition_type) |
| **상태 변화** | ScriptVersion: structuring → structured |

### 프레임 분해 기준
- 하나의 Shot이 1개 이상의 FrameSpec을 가질 수 있다
- 시각적 변화가 있거나 대사가 바뀌는 지점에서 프레임을 분리
- 각 FrameSpec은 하나의 이미지/비디오 생성 단위

---

## Stage 5: Prompt Compilation (프롬프트 조합)

| 항목 | 내용 |
|------|------|
| **트리거** | 사용자가 FrameSpec을 검토/수정하고 "생성 시작" 클릭 |
| **처리** | 동기 (API 내부, 즉시 처리) |
| **입력** | FrameSpec.visual_prompt + StylePreset + CharacterProfile |
| **프로바이더** | 없음 (내부 로직) |

### 프롬프트 조합 순서

```
최종 프롬프트 =
  [StylePreset.prompt_prefix]         ← 스타일 전역 설정
  + "\n"
  + [CharacterProfile.visual_prompt]  ← 등장 캐릭터 외형 묘사 (복수 가능)
  + "\n"
  + [FrameSpec.visual_prompt]         ← 프레임 고유 장면 묘사
  + "\n"
  + [StylePreset.prompt_suffix]       ← 스타일 보조 설정

최종 네거티브 프롬프트 =
  [FrameSpec.negative_prompt]
  + ", "
  + [StylePreset.negative_prompt]
```

이 조합 결과는 FrameSpec에 저장하지 않고, 생성 직전에 매번 계산한다.
StylePreset이나 CharacterProfile이 수정되면 다음 생성에 자동 반영된다.

---

## Stage 6: Image Generation (이미지 생성)

| 항목 | 내용 |
|------|------|
| **트리거** | Prompt Compilation 완료 후 자동 |
| **처리** | 비동기 (Worker Job: `image_generate`) |
| **입력** | 컴파일된 프롬프트 + 모델 설정 |
| **프로바이더** | fal.ai (Flux Pro, Flux Dev 등) |
| **출력** | Asset (type=image, PNG/WebP) |
| **병렬 처리** | FrameSpec별로 독립 Job. 여러 프레임 동시 생성 가능 |

### 프로바이더 설정 (StylePreset.model_preferences에서 읽음)
```json
{
  "image_model": "fal-ai/flux-pro/v1.1",
  "image_size": "landscape_16_9",
  "num_inference_steps": 28,
  "guidance_scale": 3.5
}
```

### 실패 처리
- fal.ai API 오류 → Job status=failed, error_message 기록
- 사용자가 개별 FrameSpec 재생성 가능
- ProviderRun에 전체 요청/응답 로깅

---

## Stage 7: Video Generation (비디오 생성)

| 항목 | 내용 |
|------|------|
| **트리거** | 해당 FrameSpec의 이미지 생성 완료 후 |
| **처리** | 비동기 (Worker Job: `video_generate`) |
| **입력** | 생성된 이미지 + Shot.camera_movement + Shot.duration_sec |
| **프로바이더** | Runway Gen-3 Alpha Turbo |
| **출력** | Asset (type=video, MP4 클립) |

### 이미지 → 비디오 워크플로우
```
FrameSpec의 이미지 (Asset, type=image, status=ready)
      │
      ▼
Runway API: image_to_video
  - image: 이미지 URL (presigned)
  - prompt: Shot.description + camera_movement
  - duration: Shot.duration_sec
      │
      ▼
비디오 클립 (MP4) → MinIO에 업로드 → Asset 생성
```

### Runway 특성 고려
- 생성 시간: 30초–2분
- 출력 길이: 보통 4–10초
- 비용: 크레딧 기반
- ProviderRun에 latency, 비용 추정 기록

---

## Stage 8: TTS Generation (음성 생성)

| 항목 | 내용 |
|------|------|
| **트리거** | FrameSpec에 dialogue가 있는 경우, 이미지 생성과 병렬 실행 가능 |
| **처리** | 비동기 (Worker Job: `tts_generate`) |
| **입력** | FrameSpec.dialogue + CharacterProfile.voice_id + voice_settings |
| **프로바이더** | ElevenLabs |
| **출력** | VoiceTrack + Asset (type=audio_tts, WAV/MP3) |

### 타이밍 정보 수집
ElevenLabs API는 워드 레벨 타이밍을 반환할 수 있다.
이 정보를 VoiceTrack.timestamps에 저장하여 자막 생성에 사용한다:
```json
[
  {"word": "안녕하세요", "start_ms": 0, "end_ms": 800},
  {"word": "오늘은", "start_ms": 900, "end_ms": 1300}
]
```

### dialogue가 없는 FrameSpec
- TTS를 생성하지 않음
- VoiceTrack도 생성하지 않음
- 타임라인에서 무음 구간으로 처리

---

## Stage 9: Subtitle Sync (자막 생성)

| 항목 | 내용 |
|------|------|
| **트리거** | 모든 TTS 생성 완료 후 |
| **처리** | 비동기 (Worker Job: `subtitle_generate`) |
| **입력** | 모든 VoiceTrack의 timestamps + Timeline 순서 |
| **프로바이더** | 없음 (내부 로직) |
| **출력** | SubtitleTrack + Asset (type=subtitle, SRT/ASS 파일) |

### SRT 생성 로직
```
1. 모든 FrameSpec을 Timeline 순서로 정렬
2. 각 FrameSpec의 VoiceTrack.timestamps를 시간 오프셋 적용
3. 워드를 구절 단위로 그룹핑 (최대 글자 수 기준)
4. SRT 형식으로 포맷팅
5. MinIO에 업로드
```

### ASS 형식 (v2 예정)
- 폰트, 위치, 스타일링 제어를 위해 ASS 형식도 지원 예정
- v1에서는 SRT만 지원

---

## Stage 10: Timeline Compose (타임라인 합성)

| 항목 | 내용 |
|------|------|
| **트리거** | 모든 에셋 생성 완료 후, 사용자가 "타임라인 합성" 클릭 |
| **처리** | 비동기 (Worker Job: `timeline_compose`) |
| **입력** | ScriptVersion의 Scene/Shot/FrameSpec 구조 + 각 FrameSpec의 활성 Asset |
| **출력** | Timeline (segments JSON) |

### 타임라인 생성 알고리즘
```
segments = []
current_ms = 0

for scene in script_version.scenes (order_index순):
  for shot in scene.shots (order_index순):
    for frame in shot.frames (order_index순):
      video_asset = frame의 활성 video Asset (또는 이미지 fallback)
      audio_asset = frame의 VoiceTrack.asset (있으면)

      duration = max(frame.duration_ms, audio_asset.duration_ms or 0)

      segments.append({
        frame_spec_id: frame.id,
        video_asset_id: video_asset.id,
        audio_asset_id: audio_asset.id or null,
        start_ms: current_ms,
        end_ms: current_ms + duration,
        transition: frame.transition_type
      })

      current_ms += duration

timeline.total_duration_ms = current_ms
timeline.segments = segments
```

### 오디오 길이 우선 원칙
- TTS 음성이 있는 프레임: 음성 길이와 FrameSpec.duration_ms 중 긴 쪽을 채택
- TTS 음성이 없는 프레임: FrameSpec.duration_ms 사용

---

## Stage 11: Render (최종 렌더링)

| 항목 | 내용 |
|------|------|
| **트리거** | Timeline 합성 완료 후, 사용자가 "렌더링" 클릭 |
| **처리** | 비동기 (Worker Job: `render_final`) |
| **입력** | Timeline + 모든 에셋 파일 + ProjectSettings |
| **프로바이더** | FFmpeg (로컬) |
| **출력** | RenderJob + Asset (type=render, MP4) |

### FFmpeg 렌더 파이프라인
```
1. MinIO에서 모든 비디오/오디오 에셋을 Worker 로컬에 다운로드
2. 각 세그먼트의 비디오를 트랜지션과 함께 concat
3. 오디오 트랙(TTS) 합성
4. 자막 오버레이 (SubtitleTrack.asset → SRT burn-in 또는 소프트 자막)
5. 출력 설정 적용 (해상도, fps, 코덱, 비트레이트)
6. 최종 mp4 파일 생성
7. MinIO에 업로드 → RenderJob.output_asset_id에 연결
```

### FFmpeg 명령어 구성 (개념)
```bash
ffmpeg \
  -i segment_001.mp4 -i segment_002.mp4 ... \
  -i tts_001.wav -i tts_002.wav ... \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=3[v01]; ..." \
  -vf "subtitles=subs.srt:force_style='FontSize=24'" \
  -c:v libx264 -preset medium -crf 18 \
  -c:a aac -b:a 192k \
  -r 30 -s 1920x1080 \
  output.mp4
```

### 진행률 추적
- FFmpeg의 stderr 출력에서 `time=` 파싱
- `현재 시간 / 전체 시간 × 100`으로 progress 계산
- RenderJob.progress를 주기적으로 업데이트

---

## Stage 12: QA / Retry (품질 검증 & 재시도)

| 항목 | 내용 |
|------|------|
| **트리거** | 각 단계 완료 후 사용자 검토 |
| **처리** | 사용자 판단 + 수동 트리거 |

### 재시도 시나리오

| 문제 | 재시도 단위 | 영향 범위 |
|------|-----------|----------|
| 이미지 품질 불만족 | FrameSpec 단위 `image_generate` 재실행 | 해당 프레임만 |
| 비디오 모션 부자연스러움 | Shot 단위 `video_generate` 재실행 | 해당 샷만 |
| TTS 발음/톤 이상 | FrameSpec 단위 `tts_generate` 재실행 | 해당 프레임만 |
| 대사 변경 | FrameSpec 수정 → TTS + 자막 재생성 | 해당 프레임 + 자막 |
| 장면 구성 변경 | Scene/Shot 수정 → 하위 재구조화 | 해당 Scene 이하 |
| 대본 전면 수정 | 새 ScriptVersion → 전체 재구조화 | 전체 |
| 타임라인 순서 변경 | `timeline_compose` 재실행 | 타임라인만 (에셋 재사용) |
| 렌더 설정 변경 | `render_final` 재실행 | 렌더만 (에셋 재사용) |

### 재생성 시 기존 에셋 처리
- 기존 Asset은 **삭제하지 않는다** (version이 올라갈 뿐)
- 활성 Asset = 같은 (parent_type, parent_id, asset_type)에서 최신 version + status=ready
- 롤백이 필요하면 이전 version을 다시 활성으로 지정

### 비용 인식
- 각 재생성의 예상 비용을 ProviderRun.cost_estimate로 추적
- 사용자가 재생성 전 "이 작업은 약 $X 입니다"를 인지할 수 있도록 UI 반영 (v2)

---

## 전체 파이프라인 상태 흐름

```
Project.status 변화:

  draft ──────▶ scripting ──────▶ generating ──────▶ composing ──────▶ rendered
    │              │                  │                  │                │
    │          Script생성         에셋 생성           타임라인합성       렌더완료
    │          구조화 진행        (이미지,비디오,      (Timeline 생성)   (mp4 준비)
    │                             TTS,자막)
    │
    └──── 언제든 archived로 전환 가능
```

---

## Job 의존관계 요약

```
script_generate
      │
      ▼
script_structure (scene → shot → frame, 단계적)
      │
      ▼
  ┌───┴───┐
  ▼       ▼
image   tts_generate    ← 병렬 실행 가능
generate    │
  │         ▼
  ▼     subtitle_generate
video
generate
  │
  ▼
timeline_compose    ← 모든 에셋 ready 필요
      │
      ▼
render_final
      │
      ▼
   📁 mp4
```
