# ReelsMaker

**1인용 고품질 AI 영상 제작 파이프라인.**

주제 입력 → 대본 생성 → Scene/Shot/Frame 구조화 → 이미지·비디오·TTS 생성 →
자막 → 타임라인 합성 → 최종 렌더(FFmpeg) → mp4 내보내기.

> 공개 서비스가 아닌, 개발자 본인만 사용하는 내부 도구입니다.

---

## 빠른 시작 (3단계)

```bash
# 1. 환경 변수 설정
cp .env.example .env
# .env를 열어 ANTHROPIC_API_KEY를 실제 키로 변경

# 2. 전체 서비스 빌드 + 시작
make build

# 3. 데모 프로젝트 확인
open http://localhost:3000/projects
```

첫 기동 시 자동으로:
- DB 마이그레이션 실행
- 5개 글로벌 스타일 프리셋 시드
- **"Demo: 30초 AI 소개 영상"** 데모 프로젝트 생성 (4 Scene, 6 Shot)
- **품질 평가용 3종 프로젝트** 자동 생성 (아래 참고)

---

## 서비스 & 포트

| 서비스 | 기술 | 포트 | 설명 |
|--------|------|------|------|
| **web** | Next.js 16 | :3000 | 프론트엔드 UI |
| **api** | FastAPI | :8000 | REST API + Swagger (`/docs`) |
| **worker** | arq (Python) | — | 비동기 Job 처리 |
| **postgres** | PostgreSQL 16 | :5432 | 데이터베이스 |
| **redis** | Redis 7 | :6379 | Job Queue |
| **minio** | MinIO | :9000 / :9001 | S3 호환 스토리지 (API / Console) |

기동 후 접속:
- **http://localhost:3000** — 프론트엔드
- **http://localhost:3000/projects** — 프로젝트 목록 (데모 프로젝트 포함)
- **http://localhost:8000/docs** — API Swagger UI
- **http://localhost:9001** — MinIO Console (minioadmin / minioadmin)

---

## Makefile 명령어

### Lifecycle

```bash
make build       # 빌드 + 시작
make up          # 시작 (이미 빌드됨)
make down        # 중지
make restart     # 재시작
make clean       # 전체 중지 + 볼륨 삭제 (초기화)
```

### Database

```bash
make migrate     # Alembic 마이그레이션 실행
make seed        # 스타일 프리셋 + 데모 프로젝트 시드
make reset-db    # DB 초기화: downgrade → migrate → seed
```

### Testing

```bash
make test        # 전체 테스트 실행
make test-smoke  # API smoke test만 실행
```

### Logs & Status

```bash
make logs        # 전체 로그
make logs-api    # API 로그만
make logs-worker # Worker 로그만
make ps          # 서비스 상태
make health      # API 헬스체크
```

### Shell Access

```bash
make shell-api   # API 컨테이너 셸
make shell-db    # PostgreSQL psql 셸
```

---

## 환경 변수

`.env.example`을 `.env`로 복사한 후 수정합니다.

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | — | **필수.** Claude API 키 |
| `CLAUDE_MODEL` | claude-sonnet-4-20250514 | 사용할 Claude 모델 |
| `DEBUG` | true | 디버그 모드 |
| `LOG_LEVEL` | INFO | 로그 레벨 (DEBUG/INFO/WARNING/ERROR) |
| `SQL_ECHO` | false | true면 모든 SQL 쿼리 로깅 |
| `POSTGRES_USER` | reelsmaker | DB 사용자 |
| `POSTGRES_PASSWORD` | reelsmaker | DB 비밀번호 |
| `S3_ACCESS_KEY` | minioadmin | MinIO 접근 키 |

나머지 AI 프로바이더 키(`OPENAI_API_KEY`, `FAL_KEY`, `RUNWAY_API_KEY`, `ELEVENLABS_API_KEY`)는 해당 기능 사용 시에만 필요합니다.

---

## 품질 평가용 데모 프로젝트 (Evaluation Baselines)

`make seed` 실행 시 **서로 다른 영상 유형 3종**이 자동 생성됩니다.
각 프로젝트는 Project → Script → Scene → Shot → FrameSpec 전체 계층을 갖추고 있어,
파이프라인 각 단계의 출력을 즉시 비교/검증할 수 있습니다.

| 프로젝트 | 유형 | 길이 | 스타일 | Scene | Shot | Frame |
|---------|------|------|--------|-------|------|-------|
| `[Eval] 45초 생산성 앱 추천 숏폼` | 교육/설명 | 45초 | Minimalist Infographic | 5 | 10 | 20 |
| `[Eval] 60초 감성 내레이션 — 비 오는 날의 서울` | 감성/브이로그 | 60초 | Cinematic Realistic | 4 | 9 | 22 |
| `[Eval] 30초 프리미엄 이어폰 광고` | 제품 광고 | 30초 | Premium Product Ad | 3 | 7 | 14 |

### Seed 후 검증 방법

```bash
# 1. 서비스 기동 (첫 실행이면 make build, 기존 환경이면 make reset-db)
make build

# 2. 프로젝트 목록에서 [Eval] 태그 4개 확인 (1 기본 + 3 평가용)
open http://localhost:3000/projects

# 3. API로 직접 확인
curl -s http://localhost:8000/api/projects/ | python -m json.tool
# → "title"에 "[Eval]"이 포함된 프로젝트 3개 확인

# 4. 단위 테스트로 데이터 무결성 검증
make test
# → test_seed.py에서 duration 정합성, 프레임 커버리지, 필드 무결성 자동 검증

# 5. 특정 평가 프로젝트 상세 확인 (Scene/Shot/Frame 계층)
#    프로젝트 워크스페이스에서 "Scene/Shot/Frame" 섹션으로 이동
```

자세한 평가 기준은 [docs/evaluation.md](docs/evaluation.md) 참고.

---

## 워크스페이스 UI 흐름

프로젝트 상세 페이지는 **좌측 사이드바 기반 워크스페이스** 구성입니다.

### 페이지 구조

| 페이지 | 경로 | 역할 |
|--------|------|------|
| 홈 | `/` | 랜딩, 빠른 접근 링크 |
| 프로젝트 목록 | `/projects` | 프로젝트 CRUD, 목록 표시 |
| **프로젝트 워크스페이스** | `/projects/{id}` | 영상 제작 전체 파이프라인 |
| 작업 큐 | `/jobs` | 비동기 작업 모니터링 |
| 시스템 상태 | `/status` | 서비스 헬스체크 |

### 워크스페이스 사이드바 단계

```
┌──────────────┬───────────────────────────────────────┐
│  SIDEBAR     │  MAIN CONTENT                         │
│              │                                       │
│ [기본]       │  선택된 단계의 UI가 표시됩니다.       │
│  ● 프로젝트  │                                       │
│    개요      │  • 개요: 프로젝트 정보 + 진행 현황    │
│              │  • 대본: 생성 폼 + 플랜 뷰            │
│ [기획]       │  • 구조: Scene/Shot/Frame 계층         │
│  ● 대본 생성 │  • 스타일: 프리셋/캐릭터 관리         │
│  ● Scene/    │  • 이미지: 프레임별 이미지 생성       │
│    Shot/     │  • 비디오: Shot별 클립 생성            │
│    Frame     │  • TTS/자막: 음성 + 자막 트랙         │
│  ○ 스타일    │  • 타임라인: 타임라인 조립             │
│              │  • 렌더: FFmpeg 최종 렌더              │
│ [생성]       │  • QA: 자동 점검 + 이슈 목록           │
│  ○ 이미지    │  • 내보내기: MP4/SRT/JSON 다운로드     │
│  ○ 비디오    │                                       │
│  ○ TTS/자막  │                                       │
│              │                                       │
│ [합성]       │                                       │
│  ○ 타임라인  │                                       │
│  ○ 렌더      │                                       │
│              │                                       │
│ [검수]       │                                       │
│  ○ QA 점검   │                                       │
│  ○ 내보내기  │                                       │
└──────────────┴───────────────────────────────────────┘
```

### 일반적인 작업 흐름

1. **프로젝트 생성** → 2. **대본 생성** → 3. **Scene 분해** → 4. **Shot 분해** → 5. **Frame 생성** → 6. **스타일 설정** → 7. **이미지 생성** → 8. **비디오 생성** → 9. **TTS 생성** → 10. **자막 생성** → 11. **타임라인 조립** → 12. **QA 점검** → 13. **최종 렌더** → 14. **내보내기**

> **부분 재생성**: 어떤 단계든 개별 Scene/Shot/Frame 단위로 재생성 가능하며, 이전 결과는 보존됩니다.

---

## 디렉터리 구조

```
reelsmaker/
├── apps/
│   ├── web/                      # Next.js 프론트엔드
│   │   ├── src/app/              #   App Router 페이지
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   ├── api/                      # FastAPI 백엔드
│   │   ├── app/                  #   라우터, 서비스, seed
│   │   ├── alembic/              #   DB 마이그레이션
│   │   ├── tests/                #   pytest 테스트
│   │   ├── cli.py                #   CLI (seed, reset)
│   │   └── Dockerfile
│   │
│   └── worker/                   # arq 비동기 워커
│       ├── worker/               #   핸들러 (script, scene, shot, ...)
│       └── Dockerfile
│
├── packages/
│   └── shared/                   # 공유 Python 패키지
│       └── shared/
│           ├── config.py         #   환경 설정 + 로깅
│           ├── database.py       #   async DB 세션
│           ├── models/           #   SQLAlchemy 모델 (16개)
│           ├── schemas/          #   Pydantic 스키마
│           ├── providers/        #   AI 프로바이더 추상화
│           ├── prompt_compiler/  #   프롬프트 컴파일러
│           └── qa/               #   QA 규칙 엔진
│
├── infra/docker/
│   └── docker-compose.yml        # 전체 서비스 정의
│
├── docs/                         # 설계 문서
├── .env.example                  # 환경 변수 템플릿
├── Makefile                      # 빌드/테스트/관리 명령어
└── README.md
```

---

## 로컬 개발 (Docker 없이)

### API

```bash
cd packages/shared && pip install -e .
cd ../../apps/api && pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Worker

```bash
cd packages/shared && pip install -e .
cd ../../apps/worker && pip install -r requirements.txt
arq worker.main.WorkerSettings
```

### Web

```bash
cd apps/web
npm install
npm run dev
```

### 테스트 (로컬)

```bash
cd apps/api
python -m pytest tests/ -v
```

---

## 문서

| 문서 | 내용 |
|------|------|
| [docs/prd.md](docs/prd.md) | 제품 요구사항, 사용자 플로우, v1/v2 범위 |
| [docs/architecture.md](docs/architecture.md) | 시스템 아키텍처, 컴포넌트 역할 |
| [docs/domain-model.md](docs/domain-model.md) | 16개 도메인 엔티티 상세 |
| [docs/pipeline.md](docs/pipeline.md) | 12단계 생성 파이프라인 |
| [docs/prompt-contracts.md](docs/prompt-contracts.md) | AI 프롬프트 JSON 계약 — 필드 명세, validation 규칙, 금지 패턴 |
| [docs/planner-examples.md](docs/planner-examples.md) | Planner별 Bad/Good 비교 + Golden Examples + Demo 평가 기준 |
| [docs/providers.md](docs/providers.md) | AI provider 가이드 (키, 모델, 비용, 전환법) |
| [docs/evaluation.md](docs/evaluation.md) | 평가용 데모 프로젝트 3종 상세 |
| [docs/editing-rules.md](docs/editing-rules.md) | 편집 규칙 — 페이싱, 전환, 모션, 자막 강조, QA |
| [docs/non-goals.md](docs/non-goals.md) | 의도적으로 하지 않을 것들 |
