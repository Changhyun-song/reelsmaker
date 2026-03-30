# ReelsMaker — Domain Model

> 최종 갱신: 2026-03-24

## 개요

ReelsMaker의 도메인은 14개 핵심 엔티티로 구성된다.
아래는 전체 관계도이며, 이어서 각 엔티티의 책임과 필드를 상세히 설명한다.

```
Project ─────────────────────────────────────────────────────┐
  │                                                          │
  ├── ProjectSettings (embedded JSON)                        │
  │                                                          │
  ├── StylePreset (1:N)                                      │
  │                                                          │
  ├── CharacterProfile (1:N)                                 │
  │     └── reference images → Asset                         │
  │                                                          │
  ├── ScriptVersion (1:N, versioned)                         │
  │     └── Scene (1:N, ordered)                             │
  │           └── Shot (1:N, ordered)                        │
  │                 └── FrameSpec (1:N, ordered)             │
  │                       ├── → CharacterProfile (M:N)       │
  │                       └── VoiceTrack (0..1)              │
  │                             └── → Asset (audio)          │
  │                                                          │
  ├── SubtitleTrack (1:N)                                    │
  │     └── → Asset (subtitle file)                          │
  │                                                          │
  ├── Asset (1:N, polymorphic parent)                        │
  │     └── → ProviderRun (0..1, 생성 출처)                   │
  │                                                          │
  ├── Timeline (1:N)                                         │
  │     └── RenderJob (1:N)                                  │
  │           └── → Asset (render output)                    │
  │                                                          │
  └── ProviderRun (1:N, 외부 API 호출 로그)                    │
       └── → Asset (0..1, 결과물)                             │
─────────────────────────────────────────────────────────────┘
```

---

## 엔티티 상세

### 1. Project

**책임**: 영상 제작 프로젝트의 루트 컨테이너. 모든 하위 엔티티의 소유자.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| title | string | 프로젝트 이름 |
| description | text? | 프로젝트 설명 |
| style_preset_id | UUID? | 활성 StylePreset FK |
| status | enum | draft → scripting → generating → composing → rendered → archived |
| settings | JSON | ProjectSettings (embedded) |
| created_at | datetime | 생성 시각 |
| updated_at | datetime | 수정 시각 |

**관계**: StylePreset(1:N), CharacterProfile(1:N), ScriptVersion(1:N), Asset(1:N), Timeline(1:N), ProviderRun(1:N)

---

### 2. ProjectSettings

**책임**: 프로젝트의 기술적 설정. Project.settings JSON 필드에 임베드.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| width | int | 1920 | 출력 해상도 폭 (px) |
| height | int | 1080 | 출력 해상도 높이 (px) |
| fps | int | 30 | 프레임 레이트 |
| aspect_ratio | string | "16:9" | 화면 비율 |
| output_format | string | "mp4" | 출력 포맷 |
| default_frame_duration_ms | int | 3000 | FrameSpec 기본 길이 |

**구현 방식**: 별도 테이블이 아니라 Project.settings JSON 컬럼에 저장.
Pydantic 모델로 유효성 검증.

---

### 3. ScriptVersion

**책임**: 대본의 버전 관리 단위. 수정할 때마다 새 행을 생성하여 이전 버전을 보존한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project |
| version | int | 프로젝트 내 자동 증가 버전 번호 |
| raw_text | text? | 사용자가 입력하거나 AI가 생성한 원문 |
| status | enum | draft → structuring → structured → approved |
| parent_version_id | UUID? | 이전 버전 FK (diff/롤백용) |
| created_at | datetime | 생성 시각 |

**관계**: Scene(1:N, cascade delete). 새 ScriptVersion을 만들 때 Scene/Shot/FrameSpec도 새로 생성한다.

**활성 버전 결정**: project_id 기준 가장 높은 version + status ≥ "structured"

---

### 4. Scene

**책임**: 대본 내 논리적 장면 단위. 배경·분위기·예상 길이를 정의한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| script_version_id | UUID | FK → ScriptVersion |
| order_index | int | 정렬 순서 (0-based) |
| title | string? | 장면 제목 |
| description | text? | 장면 설명 |
| setting | string? | 장소/환경 ("밤의 도시 거리") |
| mood | string? | 분위기 ("긴장감", "평화로운") |
| duration_estimate_sec | float? | 예상 장면 길이 (초) |
| status | enum | draft → ready |
| created_at | datetime | |
| updated_at | datetime | |

**관계**: Shot(1:N, ordered by order_index, cascade delete)

---

### 5. Shot

**책임**: Scene 내 카메라 샷 단위. 앵글·움직임·길이를 정의한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| scene_id | UUID | FK → Scene |
| order_index | int | 정렬 순서 |
| shot_type | string? | wide / medium / close-up / detail / POV / aerial |
| description | text? | 샷 설명 |
| camera_movement | string? | static / pan_left / pan_right / zoom_in / zoom_out / dolly / tracking |
| duration_sec | float? | 샷 길이 (초) |
| status | enum | draft → ready |
| created_at | datetime | |
| updated_at | datetime | |

**관계**: FrameSpec(1:N, ordered by order_index, cascade delete)

---

### 6. FrameSpec

**책임**: AI 에셋을 생성할 수 있는 최소 단위. 비주얼 프롬프트, 대사, 타이밍, 트랜지션을 정의한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| shot_id | UUID | FK → Shot |
| order_index | int | 정렬 순서 |
| visual_prompt | text? | 이미지/비디오 생성용 프롬프트 |
| negative_prompt | text? | 네거티브 프롬프트 |
| character_ids | UUID[]? | 등장 캐릭터 ID 목록 |
| dialogue | text? | TTS용 대사 텍스트 |
| dialogue_character_id | UUID? | 대사를 말하는 캐릭터 |
| duration_ms | int | 프레임 지속 시간 (기본 3000ms) |
| transition_type | string | cut / fade / dissolve / wipe (기본 cut) |
| status | enum | draft → prompts_ready → generating → generated → failed |
| created_at | datetime | |
| updated_at | datetime | |

**관계**:
- CharacterProfile (M:N, character_ids 배열)
- VoiceTrack (0..1)
- Asset (1:N, parent_type="frame_spec")

**prompt 컴파일 규칙**: 생성 시 아래 순서로 프롬프트가 조합된다.
```
[StylePreset.prompt_prefix]
[CharacterProfile.visual_prompt (등장 캐릭터들)]
[FrameSpec.visual_prompt]
[StylePreset.prompt_suffix]
```

---

### 7. CharacterProfile

**책임**: 등장 캐릭터의 시각적·음성적 정의. 일관성 유지의 핵심.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project |
| name | string | 캐릭터 이름 |
| description | text? | 자연어 캐릭터 설명 |
| visual_prompt | text? | 생성 프롬프트에 주입할 외형 묘사 |
| reference_image_keys | string[]? | 참조 이미지 S3 키 목록 |
| voice_id | string? | ElevenLabs 음성 ID |
| voice_settings | JSON? | stability, similarity_boost 등 |
| style_attributes | JSON? | age, gender, clothing 등 구조화된 속성 |
| created_at | datetime | |
| updated_at | datetime | |

**관계**: Project(N:1), FrameSpec(N:M, character_ids 역참조)

---

### 8. StylePreset

**책임**: 프로젝트 전역에 적용되는 시각 스타일 가이드. 프롬프트 조각과 모델 선호도를 정의한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID? | FK → Project (null이면 글로벌 프리셋) |
| name | string | 프리셋 이름 ("시네마틱", "애니메이션") |
| description | text? | 프리셋 설명 |
| prompt_prefix | text? | 모든 visual prompt 앞에 추가 |
| prompt_suffix | text? | 모든 visual prompt 뒤에 추가 |
| negative_prompt | text? | 모든 negative prompt에 추가 |
| model_preferences | JSON? | 선호 이미지/비디오 모델, 파라미터 |
| example_image_key | string? | 참조 이미지 S3 키 |
| created_at | datetime | |
| updated_at | datetime | |

**관계**: Project(N:1, nullable)

---

### 9. Asset

**책임**: 생성된 모든 파일(이미지, 비디오, 오디오, 자막, 렌더 결과)의 메타데이터와 저장 위치를 관리한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project |
| parent_type | string | "frame_spec" / "shot" / "scene" / "project" / "voice_track" / "timeline" |
| parent_id | UUID | 부모 엔티티 ID |
| asset_type | enum | image / video / audio_tts / audio_bgm / subtitle / render |
| storage_key | string? | S3 객체 키 (`{project_id}/{asset_type}/{id}.{ext}`) |
| filename | string? | 원본 파일명 |
| mime_type | string? | MIME 타입 |
| file_size_bytes | bigint? | 파일 크기 |
| metadata | JSON? | 해상도, 길이, 샘플레이트 등 |
| version | int | 같은 부모에서의 재생성 버전 (1부터 시작) |
| provider_run_id | UUID? | FK → ProviderRun (생성 출처) |
| status | enum | pending → generating → ready → failed |
| created_at | datetime | |

**관계**: Project(N:1), ProviderRun(N:1, nullable)

**활성 Asset 결정**: 같은 (parent_type, parent_id, asset_type)에서 가장 높은 version + status="ready"

---

### 10. VoiceTrack

**책임**: FrameSpec의 대사에 대한 TTS 생성 결과. 음성 파일과 워드 레벨 타이밍 정보를 관리한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project |
| frame_spec_id | UUID | FK → FrameSpec |
| character_profile_id | UUID? | FK → CharacterProfile (화자) |
| text | text | 발화 텍스트 |
| voice_id | string | 사용된 ElevenLabs 음성 ID |
| asset_id | UUID? | FK → Asset (생성된 오디오 파일) |
| duration_ms | int? | 실제 음성 길이 |
| timestamps | JSON? | 워드/구절 레벨 타이밍 [{word, start_ms, end_ms}] |
| status | enum | pending → generating → ready → failed |
| created_at | datetime | |

**관계**: FrameSpec(N:1), CharacterProfile(N:1), Asset(1:1)

**자막 생성 시**: VoiceTrack.timestamps를 기반으로 SubtitleTrack을 자동 생성

---

### 11. SubtitleTrack

**책임**: 영상에 오버레이할 자막 데이터를 관리한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project |
| script_version_id | UUID | FK → ScriptVersion |
| format | string | "srt" / "ass" |
| content | text? | 자막 원문 (SRT/ASS 형식) |
| asset_id | UUID? | FK → Asset (자막 파일) |
| status | enum | pending → generating → ready → failed |
| created_at | datetime | |

**관계**: Project(N:1), ScriptVersion(N:1), Asset(1:1)

**생성 방식**: 모든 VoiceTrack의 timestamps를 시간순으로 합쳐 SRT/ASS 파일 생성

---

### 12. Timeline

**책임**: 최종 영상의 합성 계획. 어떤 에셋을 어떤 순서로 어떻게 합칠지를 정의한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project |
| script_version_id | UUID | FK → ScriptVersion |
| total_duration_ms | int? | 전체 영상 길이 |
| segments | JSON | 정렬된 세그먼트 목록 (아래 참조) |
| bgm_asset_id | UUID? | 배경음악 Asset FK |
| subtitle_track_id | UUID? | 자막 트랙 FK |
| status | enum | draft → composing → composed → failed |
| created_at | datetime | |

**segments 구조:**
```json
[
  {
    "frame_spec_id": "uuid",
    "video_asset_id": "uuid",
    "audio_asset_id": "uuid",
    "start_ms": 0,
    "end_ms": 3000,
    "transition": "cut"
  }
]
```

**관계**: Project(N:1), ScriptVersion(N:1), RenderJob(1:N)

---

### 13. RenderJob

**책임**: FFmpeg를 사용한 최종 렌더링 작업의 상태와 결과를 추적한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project |
| timeline_id | UUID | FK → Timeline |
| output_settings | JSON | 해상도, fps, 코덱, 비트레이트 등 |
| output_asset_id | UUID? | FK → Asset (렌더 결과 mp4) |
| status | enum | queued → rendering → completed → failed |
| progress | int | 0–100 |
| ffmpeg_command | text? | 실행된 ffmpeg 명령어 (디버깅용) |
| error_message | text? | 실패 시 에러 메시지 |
| started_at | datetime? | |
| completed_at | datetime? | |
| created_at | datetime | |

**관계**: Timeline(N:1), Asset(1:1, output)

---

### 14. ProviderRun

**책임**: 외부 AI 프로바이더 API 호출의 전체 기록. 디버깅, 비용 추적, 품질 분석에 사용한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project |
| provider | string | "openai" / "fal" / "runway" / "elevenlabs" |
| operation | string | "chat_completion" / "image_generate" / "video_generate" / "tts" |
| model | string? | 사용된 모델명 ("gpt-4o", "flux-pro", "gen-3-alpha") |
| input_params | JSON | 요청 파라미터 전체 |
| output_summary | JSON? | 응답 요약 (전체 응답은 너무 클 수 있음) |
| asset_id | UUID? | FK → Asset (결과물) |
| status | enum | started → completed → failed |
| latency_ms | int? | 응답 지연 시간 |
| token_usage | JSON? | 토큰 사용량 (LLM인 경우) |
| cost_estimate | float? | 추정 비용 (USD) |
| error_message | text? | 실패 시 에러 |
| created_at | datetime | |

**관계**: Project(N:1), Asset(1:1, nullable)

---

## 엔티티 간 핵심 규칙 요약

| 규칙 | 설명 |
|------|------|
| **Cascade Delete** | Project 삭제 시 모든 하위 엔티티 삭제. ScriptVersion 삭제 시 Scene/Shot/FrameSpec 삭제 |
| **Ordered Collections** | Scene, Shot, FrameSpec은 order_index로 정렬. 중간 삽입 시 리인덱싱 |
| **Versioned Assets** | 동일 부모의 같은 asset_type에 여러 버전 존재 가능. 최신 + ready = 활성 |
| **Prompt Compilation** | FrameSpec 생성 시 StylePreset + CharacterProfile이 자동 주입 |
| **ProviderRun 기록** | 모든 외부 API 호출은 ProviderRun에 기록. Asset.provider_run_id로 역추적 |
| **Immutable Versions** | ScriptVersion은 수정하지 않고 새 버전을 생성. 이전 버전은 읽기 전용으로 보존 |
