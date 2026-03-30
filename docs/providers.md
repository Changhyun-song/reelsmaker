# AI Provider 가이드

> 각 카테고리별 1개의 실제 provider와 1개의 mock provider가 존재한다.
> 환경변수로 전환하며, API 키가 없으면 자동으로 mock으로 fallback 한다.

---

## Provider 매트릭스

| 카테고리 | Mock | Real Provider | 환경변수 (선택) | 환경변수 (키) |
|----------|------|--------------|----------------|--------------|
| **Text** | — | Claude (Anthropic) | — | `ANTHROPIC_API_KEY` |
| **Image** | MockImageProvider | fal.ai (FLUX) | `IMAGE_PROVIDER=fal` | `FAL_KEY` |
| **Video** | MockVideoProvider | Runway (Gen-4 Turbo) | `VIDEO_PROVIDER=runway` | `RUNWAY_API_KEY` |
| **TTS** | MockTTSProvider | ElevenLabs | `TTS_PROVIDER=elevenlabs` | `ELEVENLABS_API_KEY` |

---

## 1. Text — Claude (Anthropic)

### 환경변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `ANTHROPIC_API_KEY` | **Yes** | — | Anthropic API 키 |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-20250514` | 사용할 모델 |

### 사용 위치
- Script planner, Scene planner, Shot planner, Frame planner

### 제한사항
- Rate limit: Tier 1 = 60 RPM, 60K TPM
- Max tokens: 모델에 따라 다름 (기본 4096)
- JSON 모드 지원 없음 → 시스템 프롬프트에 JSON 지시문 삽입

### 예상 비용
- claude-sonnet-4-20250514: ~$3/M input, ~$15/M output
- Script plan 1회: ~$0.02-0.05

### Timeout / Retry
- Timeout: 120초 (기본)
- Retry: 3회 (validation 실패 시 자동 재시도, temperature 점진 증가)
- Rate limit (429): `retryable=True`로 arq 재시도 위임

### ProviderRun 기록 필드
```json
{
  "provider": "claude",
  "operation": "script_plan | scene_plan | shot_plan | frame_plan",
  "input_params": { "system_prompt_len", "user_prompt_len", "model", "temperature" },
  "output_summary": { "content_len", "content_preview", "parsed_keys" },
  "token_usage": { "input", "output", "total" },
  "latency_ms": 2500
}
```

---

## 2. Image — fal.ai (FLUX)

### 환경변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `IMAGE_PROVIDER` | No | `mock` | `"fal"` 로 설정하면 활성화 |
| `FAL_KEY` | Conditional | — | fal.ai API 키 (`IMAGE_PROVIDER=fal` 일 때 필수) |
| `FAL_IMAGE_MODEL` | No | `fal-ai/flux/schnell` | 사용할 FLUX 모델 |

### 지원 모델
| 모델 | 속도 | 품질 | 비용 |
|------|------|------|------|
| `fal-ai/flux/schnell` | ~2-4초 | Good | ~$0.003/이미지 |
| `fal-ai/flux/dev` | ~5-10초 | Better | ~$0.01/이미지 |
| `fal-ai/flux-pro/v1.1` | ~10-15초 | Best | ~$0.05/이미지 |

### 파라미터
- `prompt`: 이미지 설명 (영어 권장, 한글 가능)
- `negative_prompt`: 제외할 요소
- `width` / `height`: 최대 2048×2048
- `num_variants`: 1-4
- `guidance_scale`: 모델에 따라 다름 (기본 모델 자동)
- `seed`: 재현성을 위한 시드

### 제한사항
- 이미지 크기 최대 2048×2048
- 초당 요청 제한은 플랜에 따라 다름
- NSFW safety checker 기본 비활성화 (prompt_prefix로 제어)

### 예상 비용
- schnell: ~$0.003/이미지 (1024×1024 기준)
- 프로젝트 1개 (20 frames × 2 variants): ~$0.12

### Timeout / Retry
- Timeout: 120초
- 이미지 URL 다운로드 별도 timeout: 120초
- 실패 시 ProviderRun에 error 기록, Job 레벨 retry 위임

### ProviderRun 기록 필드
```json
{
  "provider": "fal",
  "operation": "image_generate",
  "input_params": { "prompt", "negative_prompt", "width", "height", "num_variants" },
  "output_summary": { "num_images", "latency_ms" },
  "cost_estimate": 0.006,
  "latency_ms": 3200
}
```

---

## 3. Video — Runway (Gen-4 Turbo)

### 환경변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `VIDEO_PROVIDER` | No | `mock` | `"runway"` 로 설정하면 활성화 |
| `RUNWAY_API_KEY` | Conditional | — | Runway API 키 (`VIDEO_PROVIDER=runway` 일 때 필수) |
| `RUNWAY_MODEL` | No | `gen4_turbo` | 사용할 모델 |

### 지원 모드
| 모드 | 입력 | 설명 |
|------|------|------|
| `image_to_video` | start frame 이미지 + 프롬프트 | 이미지 기반 비디오 생성 (주 사용) |
| `text_to_video` | 프롬프트만 | 텍스트 기반 비디오 생성 |
| `auto` | 자동 결정 | start frame이 있으면 i2v, 없으면 t2v |

### 파라미터
- `prompt_text`: 비디오 설명
- `prompt_image`: start frame (data URI 또는 URL)
- `ratio`: 종횡비 (예: `1080:1920`)
- `duration`: 5 또는 10 (초)

### 제한사항
- 비동기 처리: task 생성 → 폴링 → 완료 (보통 30-120초)
- duration은 5초 또는 10초만 지원
- 해상도는 Runway가 자동 결정 (ratio만 지정)
- 동시 task 수 플랜에 따라 제한

### 예상 비용
- Gen-4 Turbo: ~$0.05/5초 클립
- 프로젝트 1개 (7 shots): ~$0.35

### Timeout / Retry
- Task 생성 timeout: 30초
- Polling 간격: 5초, 최대 120회 (10분)
- FAILED/CANCELLED 상태 → ProviderRun error 기록
- 실패 시 Job 레벨 retry 위임

### ProviderRun 기록 필드
```json
{
  "provider": "runway",
  "operation": "video_generate",
  "input_params": { "prompt", "mode", "duration_sec", "width", "height", "has_start_frame" },
  "output_summary": { "duration_sec", "fps", "width", "height", "file_size", "latency_ms" },
  "cost_estimate": 0.05,
  "latency_ms": 45000
}
```

---

## 4. TTS — ElevenLabs

### 환경변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `TTS_PROVIDER` | No | `mock` | `"elevenlabs"` 로 설정하면 활성화 |
| `ELEVENLABS_API_KEY` | Conditional | — | ElevenLabs API 키 |
| `ELEVENLABS_MODEL` | No | `eleven_multilingual_v2` | TTS 모델 |
| `ELEVENLABS_DEFAULT_VOICE` | No | — | 기본 voice_id (비워두면 Rachel) |

### 지원 모델
| 모델 | 언어 | 특징 |
|------|------|------|
| `eleven_multilingual_v2` | 29개 (한국어 포함) | 안정적, 고품질 |
| `eleven_flash_v2_5` | 32개 | 초저지연 75ms, 저비용 |
| `eleven_turbo_v2_5` | 32개 | 빠르고 표현력 좋음 |

### 파라미터
- `text`: 변환할 텍스트
- `voice_id`: ElevenLabs voice ID
- `model_id`: TTS 모델
- `output_format`: `mp3_44100_128` (고정)

### Voice 설정
```bash
# ElevenLabs 대시보드에서 voice_id 확인:
# https://elevenlabs.io/app/voice-library

# 또는 API로 조회:
curl -H "xi-api-key: YOUR_KEY" https://api.elevenlabs.io/v1/voices
```

### 제한사항
- 한국어 품질: multilingual v2 모델이 가장 좋음
- 무료 플랜: 10,000자/월
- Voice cloning은 유료 플랜 필요
- Word-level timestamps: API에서 직접 제공하지 않음 → 문자 길이 기반 추정

### 예상 비용
- ~$0.00003/문자 (Starter 플랜 기준)
- 30초 영상 나레이션 (~150자): ~$0.005

### Timeout / Retry
- Timeout: 60초
- Streaming 응답 (chunk 단위 수신)
- 실패 시 ProviderRun error 기록

### ProviderRun 기록 필드
```json
{
  "provider": "elevenlabs",
  "operation": "tts_generate",
  "input_params": { "text", "voice_id", "language", "speed", "emotion" },
  "output_summary": { "duration_ms", "sample_rate", "word_count", "file_size" },
  "cost_estimate": 0.005,
  "latency_ms": 1800
}
```

---

## Provider 전환 가이드

### Mock → Real 전환

```bash
# 1. .env에 API 키 추가
FAL_KEY=your-fal-key
RUNWAY_API_KEY=your-runway-key
ELEVENLABS_API_KEY=your-elevenlabs-key

# 2. provider 선택 변경
IMAGE_PROVIDER=fal
VIDEO_PROVIDER=runway
TTS_PROVIDER=elevenlabs

# 3. 서비스 재시작
make restart
```

### 개별 provider만 활성화

```bash
# 이미지만 real, 나머지는 mock
IMAGE_PROVIDER=fal
FAL_KEY=your-key
VIDEO_PROVIDER=mock
TTS_PROVIDER=mock
```

### Fallback 동작

API 키가 비어있거나 provider 초기화에 실패하면 자동으로 mock provider로 fallback된다.
로그에 경고가 출력된다:

```
[WARN] reelsmaker.providers.factory: IMAGE_PROVIDER=fal but FAL_KEY is empty — falling back to mock
```

---

## 아키텍처

```
┌─────────────┐
│   Handler    │  (image.py / video.py / tts.py)
└──────┬──────┘
       │ get_*_provider()
       ▼
┌─────────────┐
│   Factory    │  (factory.py) — Settings 기반 provider 선택
└──────┬──────┘
       │
       ├── mock?  → MockImageProvider / MockVideoProvider / MockTTSProvider
       │
       └── real?  → FalImageProvider / RunwayVideoProvider / ElevenLabsTTSProvider
                    │
                    ▼
              ┌───────────┐
              │ External   │  fal.ai API / Runway API / ElevenLabs API
              │ API Call   │
              └─────┬─────┘
                    │
                    ▼
              ┌───────────┐
              │ Asset +    │  S3 업로드 + ProviderRun 로그
              │ ProviderRun│
              └───────────┘
```

---

## 향후 확장 계획

| 카테고리 | 후보 Provider | 비고 |
|----------|-------------|------|
| Image | Midjourney API, DALL-E 3, Stable Diffusion | provider 인터페이스 동일 |
| Video | Pika, Kling, Minimax | VideoProvider 상속 |
| TTS | OpenAI TTS, Google Cloud TTS, VITS | TTSProvider 상속 |
| Music/BGM | Suno, Udio | 별도 MusicProvider ABC 필요 |
