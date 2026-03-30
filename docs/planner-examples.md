# Planner Golden Examples

> 최종 갱신: 2026-03-24

각 planner 단계에 대한 **bad output vs. good output** 비교와 golden example을 정리한다.
이 문서는 프롬프트 품질 평가 기준으로 사용하며, demo project 3종의 출력을 이 기준에 맞춰 비교한다.

---

## 1. Script Planner

### Bad Output ✗

```json
{
  "title": "AI 기술 소개",
  "summary": "AI에 대한 영상",
  "hook": "안녕하세요, 오늘은 AI에 대해 알아보겠습니다.",
  "narrative_flow": ["AI 소개"],
  "sections": [
    {
      "title": "소개",
      "description": "AI를 소개한다",
      "narration": "AI는 인공지능의 약자입니다.",
      "visual_notes": "AI 관련 이미지",
      "duration_sec": 60
    }
  ],
  "ending_cta": "좋아요와 구독 부탁드립니다",
  "narration_draft": "AI는 인공지능의 약자입니다.",
  "estimated_duration_sec": 60
}
```

**문제점:**
- hook이 "안녕하세요"로 시작 → 주의를 못 끈다
- visual_notes가 "AI 관련 이미지"로 너무 모호
- section이 1개 → 구조가 없음
- summary가 너무 짧고 WHY가 없음
- ending_cta가 일반적

### Good Output ✓

```json
{
  "title": "당신이 모르는 AI의 3가지 진실",
  "summary": "많은 사람들이 AI를 단순히 ChatGPT로만 알고 있지만, AI는 이미 의료 진단, 기후 예측, 음악 작곡까지 혁신하고 있다. 이 영상은 가장 충격적인 3가지 사례를 통해 AI가 우리 일상을 어떻게 바꾸고 있는지 60초 안에 보여준다.",
  "hook": "지금 이 순간, AI가 당신보다 정확하게 암을 진단하고 있습니다.",
  "narrative_flow": [
    "충격적인 통계로 시작 — AI의 암 진단 정확도 94%",
    "일상 속 AI 사례 확장 — 음악, 날씨, 번역",
    "반전: AI가 못하는 것 — 창의적 도약, 감정적 공감",
    "결론: 도구로서의 AI, 대체가 아닌 확장"
  ],
  "sections": [
    {
      "title": "충격적 사실",
      "description": "AI 의료 진단 사례로 시선 확보",
      "narration": "지금 이 순간, AI가 당신보다 정확하게 암을 진단하고 있습니다. 구글 딥마인드의 AI는 유방암 검출에서 인간 의사보다 11.5% 높은 정확도를 보였습니다.",
      "visual_notes": "[Close-up] 의료 모니터에 CT 스캔 이미지가 표시되고 AI 분석 결과 오버레이. Lighting: cool blue screen glow on radiologist's face. Camera: slow dolly in toward screen.",
      "duration_sec": 12
    },
    {
      "title": "일상 속 AI",
      "description": "시청자의 일상과 연결하여 공감대 형성",
      "narration": "하지만 AI는 병원만이 아닙니다. 오늘 아침 들은 스포티파이 추천 음악, 날씨 앱의 정확한 예보, 심지어 이 영상의 자막까지 — 모두 AI입니다.",
      "visual_notes": "[Montage] 빠른 컷 시퀀스: 스마트폰에서 Spotify 재생 화면 → 날씨 앱 인터페이스 → 영상 자막이 실시간으로 생성되는 화면. Lighting: warm natural daylight. Camera: quick cuts with slight handheld feel.",
      "duration_sec": 15
    },
    {
      "title": "반전 — AI의 한계",
      "description": "균형 잡힌 시각 제공으로 신뢰도 확보",
      "narration": "그런데 AI가 절대 못하는 게 있습니다. 유머의 뉘앙스를 이해하는 것, 진짜 감동을 느끼는 것, 그리고 '왜'라는 질문을 스스로 던지는 것.",
      "visual_notes": "[Medium shot] 사람이 웃으며 대화하는 모습, AI 로봇이 옆에서 멈춘 표정. Split-screen 구도. Lighting: warm side lighting on human, cool flat lighting on robot. Camera: static, symmetric composition.",
      "duration_sec": 13
    },
    {
      "title": "결론",
      "description": "핵심 메시지 전달 및 행동 유도",
      "narration": "AI는 우리를 대체하는 것이 아니라, 우리의 능력을 확장하는 도구입니다. 중요한 건, 이 도구를 어떻게 쓸지 우리가 결정한다는 것.",
      "visual_notes": "[Wide shot] 사람이 노트북 앞에서 작업 중, 화면에 AI 인터페이스가 보이지만 최종 결정은 사람이 마우스 클릭으로 내리는 장면. Lighting: warm golden hour through window. Camera: slow crane up revealing workspace.",
      "duration_sec": 12
    }
  ],
  "ending_cta": "AI를 당신의 확장 도구로 만드는 방법이 궁금하다면, 다음 영상에서 구체적인 5가지 팁을 알려드립니다.",
  "narration_draft": "지금 이 순간, AI가 당신보다 정확하게 암을 진단하고 있습니다. 구글 딥마인드의 AI는 유방암 검출에서 인간 의사보다 11.5% 높은 정확도를 보였습니다. 하지만 AI는 병원만이 아닙니다. 오늘 아침 들은 스포티파이 추천 음악, 날씨 앱의 정확한 예보, 심지어 이 영상의 자막까지 — 모두 AI입니다. 그런데 AI가 절대 못하는 게 있습니다. 유머의 뉘앙스를 이해하는 것, 진짜 감동을 느끼는 것, 그리고 '왜'라는 질문을 스스로 던지는 것. AI는 우리를 대체하는 것이 아니라, 우리의 능력을 확장하는 도구입니다. 중요한 건, 이 도구를 어떻게 쓸지 우리가 결정한다는 것. AI를 당신의 확장 도구로 만드는 방법이 궁금하다면, 다음 영상에서 구체적인 5가지 팁을 알려드립니다.",
  "estimated_duration_sec": 52
}
```

**왜 좋은가:**
- hook이 충격적 통계로 시작
- visual_notes가 `[Shot type] + 구체적 장면 + Lighting + Camera` 형식
- 4개 section이 기승전결 구조
- narration이 자연스럽게 연결됨
- CTA가 구체적 다음 콘텐츠를 제안

---

## 2. Scene Planner

### Bad Output ✗

```json
{
  "scene_index": 0,
  "title": "도입부",
  "purpose": "시작",
  "summary": "영상을 시작한다",
  "narration_text": "안녕하세요...",
  "setting": "적절한 배경",
  "mood": "좋음",
  "emotional_tone": "밝은",
  "visual_intent": "Show the beginning",
  "transition_hint": "fade",
  "estimated_duration_sec": 15
}
```

**문제점:**
- purpose가 "시작" → 서사적 기능 설명 없음
- setting이 "적절한 배경" → 이미지 AI가 사용 불가
- visual_intent가 "Show the beginning" → 구체적 시각 없음
- mood가 "좋음" → 감정 방향 없음

### Good Output ✓

```json
{
  "scene_index": 0,
  "title": "충격적 통계로 관심 확보",
  "purpose": "AI 의료 진단 정확도 통계로 시청자의 고정관념을 깨고 영상에 집중시킨다",
  "summary": "AI가 인간 의사보다 정확하게 암을 진단한다는 통계를 제시하며, 시청자가 'AI는 아직 먼 미래'라는 인식을 뒤집는다.",
  "narration_text": "지금 이 순간, AI가 당신보다 정확하게 암을 진단하고 있습니다. 구글 딥마인드의 AI는 유방암 검출에서 인간 의사보다 11.5% 높은 정확도를 보였습니다.",
  "setting": "modern radiology reading room, dark ambient with multiple DICOM monitors displaying CT scans, clean medical environment, blue-tinted overhead lighting",
  "mood": "awe, slight unease",
  "emotional_tone": "Start with quiet authority, build to surprising revelation. Viewer should feel a mix of amazement and slight concern. Music: minimal, low drone building to subtle accent on the statistic.",
  "visual_intent": "Open on extreme close-up of medical monitor showing AI analysis overlay on CT scan — colored heatmap highlighting suspicious regions. Cut to medium shot of empty radiology chair (no human needed). Cool blue-cyan color palette throughout, high contrast, clinical precision aesthetic. Camera slowly dollying toward the screen.",
  "transition_hint": "dissolve",
  "estimated_duration_sec": 12
}
```

**왜 좋은가:**
- purpose가 "시청자의 고정관념을 깨고 집중시킨다" → 명확한 서사 기능
- setting이 구체적 location + 조명 + 분위기
- visual_intent가 shot-level 구체성 — 색상 팔레트, 카메라 동선, 시각적 요소 명시
- emotional_tone이 음악 방향까지 포함

---

## 3. Shot Planner

### Bad Output ✗

```json
{
  "shot_index": 0,
  "purpose": "establishing",
  "duration_sec": 5,
  "shot_type": "wide",
  "camera_framing": "wide",
  "camera_motion": "static",
  "subject": "a room",
  "environment": "inside",
  "emotion": "calm",
  "narration_segment": "",
  "transition_in": "cut",
  "transition_out": "cut",
  "asset_strategy": "image_to_video",
  "description": "A wide shot of a room"
}
```

**문제점:**
- purpose가 shot_type 반복 → 왜 이 샷이 필요한지 모름
- subject가 "a room" → 이미지 AI에 쓸 수 없음
- environment가 "inside" → 아무 정보 없음
- description이 9단어 → 이미지 생성에 턱없이 부족

### Good Output ✓

```json
{
  "shot_index": 0,
  "purpose": "establish the high-tech medical environment and AI's silent authority",
  "duration_sec": 4,
  "shot_type": "establishing",
  "camera_framing": "medium_wide",
  "camera_motion": "slow_pan_right",
  "subject": "row of high-resolution DICOM medical monitors displaying colorful CT scan heatmaps, AI analysis interface with confidence percentages",
  "environment": "dark radiology reading room with blue ambient lighting, clean surfaces, professional medical equipment, glass partition reflecting monitor glow",
  "emotion": "clinical awe, quiet technological authority",
  "narration_segment": "지금 이 순간, AI가 당신보다 정확하게 암을 진단하고 있습니다.",
  "transition_in": "fade_in",
  "transition_out": "cut",
  "asset_strategy": "image_to_video",
  "description": "Medium-wide shot slowly panning right across a row of high-resolution medical monitors in a dark radiology reading room, each screen displaying AI-analyzed CT scan heatmaps with confidence percentage overlays, cool blue ambient lighting reflecting off glass partitions and clean desk surfaces, cinematic medical drama lighting with deep shadows and isolated monitor glow, photorealistic 8k, professional healthcare technology aesthetic"
}
```

**왜 좋은가:**
- purpose가 샷의 서사적 역할 설명
- subject가 구체적 시각 요소 나열 (monitors, heatmaps, interface)
- environment가 5개 이상의 디테일
- description이 50+ 단어, 독립적 이미지 프롬프트로 사용 가능
- camera_motion이 설명에도 반영 ("slowly panning right")

---

## 4. Frame Planner

### Bad Output ✗

```json
{
  "frame_role": "start",
  "composition": "centered",
  "subject_position": "in the middle",
  "camera_angle": "normal",
  "lens_feel": "standard",
  "lighting": "well lit",
  "mood": "good",
  "action_pose": "standing",
  "background_description": "a room",
  "continuity_notes": "",
  "forbidden_elements": ""
}
```

**문제점:**
- composition이 "centered" → 어떤 구도 기법인지 불명
- lighting이 "well lit" → 이미지 AI가 어떤 조명도 만들 수 있음
- action_pose가 "standing" → 어떤 자세? 표정? 손?
- background_description이 "a room" → 아무 이미지나 생성됨
- continuity_notes가 비어있음 → 인접 프레임과 불일치 발생

### Good Output ✓

```json
{
  "frame_role": "start",
  "composition": "Rule of thirds — monitors occupy left two-thirds of frame creating a wall of technology. Right third has negative space with soft blue ambient glow. Foreground: slightly blurred desk edge for depth. Midground: monitors in sharp focus. Background: glass partition with reflected screen lights, creating depth layers.",
  "subject_position": "Primary monitors centered-left, spanning from left edge to center. AI interface highlight at left-third vertical line, upper-third horizontal intersection. Desk surface visible at bottom 15% of frame.",
  "camera_angle": "Eye-level, straight-on, slight camera-right offset to create asymmetric balance",
  "lens_feel": "35mm f/2.8 wide-angle, moderate DOF — foreground desk edge slightly soft, monitors sharp, background glass partition with gentle bokeh",
  "lighting": "Key: cool blue LED strips from above monitors (5500K) casting downward. Fill: very subtle warm accent (3000K) from desk lamp at far right, barely visible. Rim: monitor screen glow creating self-illumination on desk surface. No overhead fluorescent — dark ceiling creates moody ambiance.",
  "mood": "clinical precision meets quiet technological authority — viewer should feel they're peering into a world of advanced capability",
  "action_pose": "No human subject in this frame. Monitors are the subject — screens actively displaying animated AI heatmap overlays with pulsing confidence indicators. One screen shows a rotating 3D CT reconstruction.",
  "background_description": "Immediate BG behind monitors: matte dark wall with small status LED indicators. Mid BG: glass partition wall reflecting blue monitor glow in overlapping rectangles. Far BG: dimly visible corridor through glass, suggesting larger hospital facility beyond. Color palette: deep navy, cyan, white screen highlights.",
  "continuity_notes": "This is the first frame of the video (fade_in). Establish the cool blue color temperature that will persist through this entire scene. Monitor layout and desk surface must remain consistent in end frame. The AI interface design (colored heatmap with percentage) must match across all frames in this shot.",
  "forbidden_elements": "No human hands or faces in this establishing frame. No cartoon/stylized elements. No visible text that would be unreadable at 1080p. No warm lighting — maintain cool blue-cyan palette. No messy cables or unprofessional elements."
}
```

**왜 좋은가:**
- composition이 구체적 삼분법 배치 + foreground/midground/background 레이어
- lighting이 Key/Fill/Rim 3점 조명 구조 + 색온도 수치
- action_pose가 "No human — monitors are active subjects" 식으로 구체적
- background가 3단계 깊이 (immediate/mid/far)
- continuity_notes가 색온도, 디자인 일관성, 인접 프레임 관계 명시
- forbidden_elements가 AI 생성 시 흔한 오류 방지

---

## Demo Project별 평가 기준

### demo_shorts_explainer (60초 설명 영상)
| 항목 | 체크포인트 |
|------|-----------|
| Script | hook이 질문/통계/반직관적 주장인가? sections ≥ 3개인가? |
| Scene | scene 3-5개, 각 10-20s, purpose가 서사 기능 설명인가? |
| Shot | description ≥ 30 chars? camera_framing 연속 반복 없는가? |
| Frame | lighting에 Key/Fill/Rim 있는가? start↔end 구도 차이가 camera_motion과 일치하는가? |

### demo_emotional_narration (감성 내레이션)
| 항목 | 체크포인트 |
|------|-----------|
| Script | 감정 arc가 있는가? (고조→절정→해소) visual_notes에 감정 색온도 변화가 있는가? |
| Scene | emotional_tone이 장면 간 자연스럽게 전환되는가? mood가 1-3 단어 구체적인가? |
| Shot | emotion 필드가 추상적("good")이 아닌 구체적("bittersweet nostalgia")인가? |
| Frame | mood가 조명/색온도/배경과 일치하는가? action_pose에 미세한 표정 묘사가 있는가? |

### demo_product_ad (제품 광고)
| 항목 | 체크포인트 |
|------|-----------|
| Script | 제품 특징이 section별로 분리되는가? CTA가 구체적 구매 행동을 유도하는가? |
| Scene | setting이 제품 사용 환경을 구체적으로 묘사하는가? |
| Shot | subject에 제품명/외형이 구체적인가? asset_strategy가 제품 클로즈업에 적합한가? |
| Frame | composition에 제품 배치가 광고 촬영 기법(hero shot, flat lay 등)인가? |

---

## 비교 흐름

1. `make seed` 실행 → demo project 3종 자동 생성
2. 각 프로젝트에서 Script → Scene → Shot → Frame planner 순서로 실행
3. 생성 결과를 이 문서의 Bad/Good 기준과 비교
4. `QA / 품질 평가` 패널에서 각 기준에 1-5점 평가
5. `docs/evaluation.md`의 평가 체계로 정량적 비교
