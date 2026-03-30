# ReelsMaker — System Architecture

> 최종 갱신: 2026-03-24

## 1. 시스템 아키텍처 개요

```
사용자 (브라우저)
       │
       ▼
┌──────────────────┐
│  Next.js 16      │  ← 프론트엔드 (SSR + CSR)
│  :3000           │     /api/* → FastAPI로 프록시 (rewrites)
└────────┬─────────┘
         │ HTTP (JSON)
         ▼
┌──────────────────┐         ┌──────────────────┐
│  FastAPI          │────────▶│  PostgreSQL 16   │
│  Backend API      │  async  │  :5432           │
│  :8000            │  SQL    │                  │
└────────┬─────────┘         └──────────────────┘
         │
         │ enqueue (arq)
         ▼
┌──────────────────┐         ┌──────────────────┐
│  Redis 7         │◀────────│  arq Worker      │
│  :6379           │  poll   │  (Python)        │
│  (Job Queue)     │         │                  │
└──────────────────┘         └────────┬─────────┘
                                      │
                     ┌────────────────┼────────────────┐
                     ▼                ▼                ▼
              ┌────────────┐  ┌────────────┐  ┌────────────┐
              │ AI 프로바이더 │  │ FFmpeg     │  │ MinIO (S3) │
              │ OpenAI      │  │ ffprobe    │  │ :9000/9001 │
              │ fal.ai      │  │            │  │            │
              │ Runway      │  └────────────┘  └────────────┘
              │ ElevenLabs  │
              └────────────┘
```

---

## 2. 컴포넌트 역할

### 2.1 Web — Next.js 16

| 항목 | 내용 |
|------|------|
| 역할 | 사용자 인터페이스. 프로젝트 관리, 대본 편집, 생성 컨트롤, 프리뷰, 다운로드 |
| 기술 | Next.js 16 + TypeScript + Tailwind CSS + shadcn/ui |
| 라우팅 | App Router (src/app/) |
| API 통신 | /api/* 경로를 next.config.ts rewrites로 FastAPI에 프록시 |
| 상태 관리 | 서버 컴포넌트 위주 + 필요 시 클라이언트 상태 (React state / SWR) |
| 책임 범위 | UI 렌더링만. 비즈니스 로직과 데이터 영속성은 Backend에 위임 |

### 2.2 API — FastAPI

| 항목 | 내용 |
|------|------|
| 역할 | 모든 비즈니스 로직의 진입점. CRUD, 유효성 검증, Job 발행 |
| 기술 | FastAPI + Pydantic v2 + SQLAlchemy 2.0 (async) |
| 데이터 접근 | asyncpg를 통한 PostgreSQL 비동기 쿼리 |
| 외부 통신 | Worker에 Job 발행 (arq/Redis), MinIO에 presigned URL 발급 |
| 문서 | /docs (Swagger UI) 자동 생성 |

**API는 직접 AI 프로바이더를 호출하지 않는다.**
무거운 생성 작업은 반드시 Worker에게 위임한다.

### 2.3 Worker — arq (Python)

| 항목 | 내용 |
|------|------|
| 역할 | 비동기 작업 실행. AI 호출, 미디어 처리, 렌더링 |
| 기술 | arq (Redis-backed async job queue) |
| 작업 종류 | 대본 생성, 구조화, 이미지/비디오/TTS 생성, 자막, 타임라인 합성, 렌더 |
| 외부 호출 | OpenAI, fal.ai, Runway, ElevenLabs API |
| 파일 처리 | FFmpeg/ffprobe 실행, 결과물 MinIO 업로드 |
| 에러 처리 | 실패 시 Job 상태 업데이트 + error_message 기록. 개별 재시도 가능 |

### 2.4 DB — PostgreSQL 16

| 항목 | 내용 |
|------|------|
| 역할 | 모든 도메인 데이터의 영속 저장소 |
| 접근 | SQLAlchemy 2.0 async ORM (asyncpg 드라이버) |
| 마이그레이션 | Alembic (async 지원) |
| 주요 테이블 | projects, script_versions, scenes, shots, frame_specs, character_profiles, style_presets, assets, voice_tracks, subtitle_tracks, timelines, render_jobs, provider_runs |

### 2.5 Redis 7

| 항목 | 내용 |
|------|------|
| 역할 | Job Queue 브로커 |
| 사용 패턴 | arq가 Redis를 폴링하여 작업 소비. 결과도 Redis에 임시 저장 |
| 캐시 | 현재 미사용. 필요 시 API 응답 캐시로 확장 가능 |

### 2.6 Object Storage — MinIO (S3-compatible)

| 항목 | 내용 |
|------|------|
| 역할 | 모든 생성 파일(이미지, 비디오, 오디오, 자막, 렌더 결과)의 바이너리 저장소 |
| 접근 | boto3 (S3 API). Backend가 presigned URL 발급, Worker가 직접 업로드 |
| 버킷 구조 | `{bucket}/{project_id}/{asset_type}/{asset_id}.{ext}` |
| 개발환경 | Docker Compose의 MinIO 컨테이너 |
| 프로덕션 | 동일 인터페이스로 AWS S3, Cloudflare R2 등으로 교체 가능 |

### 2.7 FFmpeg / ffprobe

| 항목 | 내용 |
|------|------|
| 역할 | 미디어 합성 및 분석 |
| 사용 위치 | Worker 컨테이너 내부 (Dockerfile에서 설치) |
| 주요 작업 | 비디오+오디오 합성, 자막 오버레이, 트랜지션, 최종 렌더, 메타데이터 추출 |
| 호출 방식 | subprocess (ffmpeg-python 래퍼 또는 직접 호출) |

---

## 3. 동기 요청과 비동기 작업 분리 기준

| 기준 | 동기 (API 직접 응답) | 비동기 (Worker Job) |
|------|---------------------|-------------------|
| 응답 시간 | < 2초 | > 2초 또는 불확정 |
| 외부 의존 | 없음 또는 빠른 DB 쿼리 | AI 프로바이더 API 호출 |
| 실패 가능성 | 낮음 | 높음 (네트워크, 프로바이더 오류) |
| 재시도 필요 | 불필요 | 필요 |
| 비용 | 무료 | 유료 (API 호출 과금) |

### 동기로 처리하는 것

- CRUD 작업 (프로젝트, 대본, Scene/Shot/Frame, 캐릭터, 스타일)
- 목록 조회, 상세 조회
- 상태 변경 (승인, 아카이브)
- Presigned URL 발급
- Job 상태 조회

### 비동기로 처리하는 것

- 대본 AI 생성 (`script_generate`)
- 대본 구조화 (`script_structure`)
- 이미지 생성 (`image_generate`)
- 비디오 생성 (`video_generate`)
- TTS 생성 (`tts_generate`)
- 자막 생성 (`subtitle_generate`)
- 타임라인 합성 (`timeline_compose`)
- 최종 렌더 (`render_final`)

**규칙: API가 Job을 발행하면 즉시 Job ID를 반환한다.**
프론트엔드는 Job ID로 폴링하여 진행 상황을 확인한다.

---

## 4. Scene / Shot / Frame 파이프라인

### 계층 구조

```
ScriptVersion
  └── Scene (논리적 장면)
        └── Shot (카메라 샷)
              └── FrameSpec (생성 가능한 최소 단위)
```

### 각 레벨의 책임

| 레벨 | 결정하는 것 | 예시 |
|------|-----------|------|
| Scene | 어디서, 어떤 분위기로 | "밤의 도시 거리, 긴장감" |
| Shot | 어떤 앵글로, 얼마나 길게 | "클로즈업, 3초, 천천히 줌인" |
| FrameSpec | 정확히 무엇을, 누가 말하며 | "주인공이 걸어가는 모습, prompt: ..., dialogue: ..." |

### 구조화 프로세스

```
                  ScriptVersion.raw_text
                          │
                    ┌─────▼──────┐
                    │  GPT-4o    │  scene planning
                    │  구조화    │
                    └─────┬──────┘
                          │
                ┌─────────▼──────────┐
                │  Scene 목록 생성    │
                │  (title, setting,  │
                │   mood, duration)  │
                └─────────┬──────────┘
                          │  각 Scene에 대해
                ┌─────────▼──────────┐
                │  Shot 목록 생성     │
                │  (shot_type,       │
                │   camera, duration)│
                └─────────┬──────────┘
                          │  각 Shot에 대해
                ┌─────────▼──────────┐
                │  FrameSpec 생성    │
                │  (visual_prompt,   │
                │   dialogue,        │
                │   duration_ms)     │
                └────────────────────┘
```

GPT-4o에 한 번에 전체를 요청하지 않고, **Scene → Shot → Frame 순서로 단계적으로** 요청한다.
이유: 한 번에 요청하면 토큰 제한에 걸리거나 품질이 떨어진다.

---

## 5. 부분 재생성 전략

### 핵심 원칙

모든 생성 단위(FrameSpec, Shot, Scene)는 독립적으로 재생성할 수 있다.
재생성은 해당 단위의 Asset만 교체하며, 나머지는 그대로 유지한다.

### 재생성 단위

| 단위 | 재생성 범위 | 트리거 조건 |
|------|-----------|-----------|
| FrameSpec | 이미지 1장 또는 비디오 1클립 재생성 | 프롬프트 수정, 품질 불만족, 생성 실패 |
| Shot | 해당 Shot의 모든 FrameSpec 에셋 재생성 | Shot 설명 변경 |
| Scene | 해당 Scene의 모든 Shot 재생성 | Scene 구조 변경 |
| TTS | 특정 FrameSpec의 VoiceTrack 재생성 | 대사 수정, 음성 불만족 |
| Timeline | 타임라인 재합성 (기존 에셋 재사용) | 순서 변경, 트랜지션 변경 |

### 재생성 흐름

```
1. 사용자가 FrameSpec의 visual_prompt를 수정
2. API가 해당 FrameSpec의 status를 "draft"로 리셋
3. 사용자가 "재생성" 클릭
4. API가 image_generate Job 발행 (target: 해당 FrameSpec)
5. Worker가 새 이미지 생성 → 새 Asset 생성 (이전 Asset은 보존, version 증가)
6. 다운스트림(비디오, 타임라인)은 아직 변경되지 않음
7. 사용자가 원하면 "비디오 재생성" → 해당 Shot의 video_generate Job 발행
8. 타임라인 재합성 시 최신 버전의 Asset을 자동 사용
```

### Asset 버전 관리

같은 parent_type + parent_id + asset_type에 여러 Asset이 존재할 수 있다.
`version` 필드로 구분하며, **최신 버전 + status=ready**인 Asset을 활성 에셋으로 사용한다.
이전 버전은 삭제하지 않고 보존하여 롤백이 가능하다.

---

## 6. 버전 관리 전략

### 대상별 버전 관리

| 대상 | 방식 | 설명 |
|------|------|------|
| 대본 | ScriptVersion 행 | 수정 시 새 행 생성. version 필드 자동 증가. 이전 버전 보존 |
| 구조 | ScriptVersion에 종속 | ScriptVersion이 바뀌면 새 Scene/Shot/FrameSpec 세트 생성 |
| Asset | Asset.version | 같은 부모에 대해 재생성 시 새 Asset(version+1) 생성. 이전 보존 |
| Timeline | Timeline 행 | 합성할 때마다 새 Timeline 생성. 이전 Timeline 보존 |
| Render | RenderJob 행 | 렌더할 때마다 새 RenderJob + 결과 Asset 생성 |

### 활성 버전 결정

- ScriptVersion: project 내 가장 높은 version + status가 "approved" 이상인 것
- Asset: 같은 (parent_type, parent_id, asset_type) 중 가장 높은 version + status="ready"
- Timeline: project 내 가장 최근 created_at + status가 "composed" 이상인 것

### 롤백

- ScriptVersion을 이전 버전으로 되돌리면 해당 버전의 Scene/Shot/FrameSpec 사용
- Asset은 이전 version의 것을 "활성"으로 지정하는 방식으로 롤백
- 데이터를 삭제하지 않고 버전을 전환하는 방식

---

## 7. Single-User Local Mode 전제

### 설계 기준

- **인증 없음**: 모든 API는 인증 없이 접근 가능. CORS는 localhost만 허용
- **단일 사용자**: user_id, tenant_id 컬럼 없음. 모든 데이터는 단일 소유자
- **로컬 네트워크**: Docker Compose로 로컬 또는 개인 서버에서 실행
- **외부 미노출**: 서비스 포트는 localhost 바인딩. 필요 시 VPN/SSH 터널로 접근

### 보안 고려사항

| 항목 | 대응 |
|------|------|
| API 키 보호 | .env 파일로 관리. .gitignore에 포함. Docker env로 주입 |
| 네트워크 | 로컬 바인딩 기본. 외부 노출 시 VPN 필수 |
| 데이터 보호 | 로컬 Docker Volume. 필요 시 볼륨 암호화 |
| CORS | localhost:3000만 허용 |

### 확장 경로 (필요 시)

현재 설계는 멀티유저 확장이 가능한 구조다:
1. projects 테이블에 `owner_id` 컬럼 추가
2. FastAPI 미들웨어에 auth 레이어 추가
3. API 쿼리에 owner 필터 적용

현재는 이 확장을 의도적으로 **하지 않는다**.

---

## 8. Job Lifecycle

### 개요

모든 비동기 작업(AI 호출, 렌더링, 미디어 처리)은 `Job` 레코드로 DB에 추적된다.
arq(Redis-backed)가 실제 큐잉과 워커 디스패치를 담당하고,
PostgreSQL의 `jobs` 테이블이 상태/결과/에러를 영속 저장한다.

### 상태 전이

```
  API enqueue
       │
       ▼
  ┌─────────┐    worker pickup    ┌──────────┐
  │ queued   │───────────────────▶│ running   │
  └────┬─────┘                    └─────┬─────┘
       │                                │
       │ cancel                         ├── success ─▶ completed
       ▼                                │
  ┌──────────┐                     failure
  │cancelled │               ┌──────────┴───────────┐
  └──────────┘               │                      │
                       retry_count             retry_count
                       < max_retries           ≥ max_retries
                             │                      │
                             ▼                      ▼
                        ┌─────────┐           ┌─────────┐
                        │ queued  │           │ failed  │
                        │ (retry) │           └─────────┘
                        └─────────┘
```

### Enqueue → Execute 흐름

```
1. 클라이언트 → POST /api/jobs/ (job_type, params)
2. API가 jobs 테이블에 레코드 생성 (status=queued)
3. API가 arq에 run_job(job_id) enqueue → 즉시 Job 응답 반환
4. Worker가 Redis에서 job을 꺼냄
5. run_job()이 DB에서 Job 로드 → status=running 갱신
6. job_type에 따라 handler 함수 디스패치
7. handler가 작업 수행 (progress 중간 업데이트 가능)
8. 성공: status=completed, result JSON 저장
9. 실패: retry 정책에 따라 재큐잉 또는 status=failed
```

### Retry 정책

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `max_retries` | 3 | Job별 최대 재시도 횟수. enqueue 시 지정 가능 |
| Backoff | linear | `retry_count × 10초` 대기 후 재시도 |
| `job_timeout` | 3600s | Worker 레벨. 이 시간 초과 시 arq가 job을 kill |
| arq `max_tries` | 1 | arq 레벨 자동 retry 비활성화. DB 기반 커스텀 retry 사용 |

**Retry 시 보존되는 것:**
- `Job.id` (동일 레코드 재사용)
- `Job.params` (동일 파라미터)
- `Job.retry_count` (누적)

**Retry 시 초기화되는 것:**
- `status` → queued
- `progress` → 0
- `started_at` → null

### 실패 로그

| 필드 | 내용 |
|------|------|
| `error_message` | 예외 메시지 (str(e)). 매 retry마다 최신 에러로 갱신 |
| `error_traceback` | Python traceback 마지막 2000자. 최종 실패 시에만 저장 |

### 수동 Retry / Cancel

- `POST /api/jobs/{id}/retry` — failed/cancelled 상태의 Job을 queued로 되돌리고 재enqueue
- `POST /api/jobs/{id}/cancel` — queued 상태의 Job을 cancelled로 변경

### 모니터링

- `GET /api/jobs/` — 필터링 가능 (status, job_type, project_id)
- Frontend `/jobs` 페이지에서 3초 간격 자동 polling
- 각 Job의 progress(0-100)를 실시간 표시

### Job Types

| job_type | 설명 | 현재 상태 |
|----------|------|----------|
| `demo` | 테스트용. N초 sleep + 선택적 실패 | ✅ 구현 완료 |
| `script_generate` | AI 대본 생성 | stub |
| `script_structure` | 대본 → Scene/Shot/Frame 구조화 | stub |
| `image_generate` | FrameSpec 이미지 생성 | stub |
| `video_generate` | Shot 비디오 생성 | stub |
| `tts_generate` | FrameSpec TTS 음성 생성 | stub |
| `subtitle_generate` | 자막 생성 | stub |
| `timeline_compose` | 타임라인 합성 | stub |
| `render_final` | 최종 mp4 렌더링 | stub |

---

## 7. QA / Critic Layer

### 7.1 개요

QA 레이어는 파이프라인의 각 단계 산출물을 자동 점검하여 누락, 불일치, 실패를 조기에 탐지한다.
규칙 기반(rule-based)으로 동작하며, 향후 Claude 기반 AI Critic으로 확장 가능한 구조를 갖는다.

```
사용자 → [QA 실행] → API(동기)
                        │
                        ├─ DB에서 프로젝트 데이터 수집 → QAContext 조립
                        ├─ Rule Engine 실행 (순수 함수)
                        ├─ QAResult rows 저장 (이전 미해결 결과 교체)
                        └─ 요약 응답 반환
```

### 7.2 QA 검사 항목

| check_type | scope | severity | 설명 |
|------------|-------|----------|------|
| `missing_frame_specs` | shot | warning | Frame spec이 생성되지 않은 Shot |
| `missing_start_frame` | shot | warning | Start frame이 없는 Shot |
| `missing_end_frame` | shot | info | End frame이 없는 Shot |
| `missing_images` | shot | warning | 이미지가 생성되지 않은 Shot |
| `missing_video_clip` | shot | error | 비디오 클립이 없는 Shot (렌더 차단) |
| `no_voice_track` | shot | warning | 나레이션이 있지만 TTS가 없는 Shot |
| `no_shots` | scene | warning | Shot이 분해되지 않은 Scene |
| `missing_narration` | scene | info | 나레이션 텍스트가 비어있는 Scene |
| `no_scenes` | project | error | Scene이 없는 프로젝트 |
| `duration_conflict` | project/scene/shot | warning | 길이 불일치 (목표 vs 실제) |
| `subtitle_missing` | project | warning | 자막 트랙 미생성 |
| `subtitle_duration_mismatch` | project | warning | 자막/영상 길이 불일치 |
| `render_not_ready` | project | error/warning | 비디오 누락으로 렌더 불가 |
| `no_timeline` | project | error | 타임라인 미조립 |
| `failed_jobs` | project | warning | 실패한 작업 요약 |
| `provider_failures` | project | warning | AI 프로바이더 실패 요약 |

### 7.3 Severity 등급

| 등급 | 의미 | 렌더 차단 |
|------|------|----------|
| `error` | 렌더를 실행할 수 없는 치명적 이슈 | Yes |
| `warning` | 품질에 영향을 주지만 렌더는 가능 | No |
| `info` | 참고 사항 | No |

**render_ready = (error 개수 == 0)**

### 7.4 데이터 모델

```
qa_results
├── id (UUID PK)
├── project_id (FK → projects)
├── script_version_id (nullable)
├── scope (project / scene / shot / frame)
├── target_type + target_id
├── check_type (규칙 이름)
├── severity (error / warning / info)
├── message (사람이 읽는 설명)
├── details (JSON — 수치 데이터 등)
├── suggestion (해결 방법 안내)
├── resolved (bool — 수동 해결 표시)
├── source (rule / critic)
└── created_at
```

### 7.5 API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| POST | `/projects/{id}/qa/run` | QA 전체 실행 (미해결 결과 교체) |
| GET | `/projects/{id}/qa` | 결과 목록 (severity/scope/resolved 필터) |
| GET | `/projects/{id}/qa/summary` | 요약 (오류/경고/정보 수, 렌더 준비 상태) |
| PATCH | `/projects/{id}/qa/{qa_id}/resolve` | 개별 이슈 해결 표시 |
| DELETE | `/projects/{id}/qa/clear` | 전체 결과 초기화 |

### 7.6 확장 계획

1. **AI Critic** — Claude에게 scene/shot 데이터를 전달하고 품질 평가를 받는 `source="critic"` 검사
2. **Auto-fix** — warning 수준의 이슈를 자동으로 재생성 job으로 연결
3. **Post-render QA** — 렌더 완료 후 ffprobe로 출력물 품질 검증
4. **Continuous QA** — 각 생성 단계 완료 시 해당 scope만 자동 QA 실행
