/* ── Shared types for ReelsMaker frontend ──────────── */

export interface Project {
  id: string;
  title: string;
  description: string | null;
  status: string;
  active_style_preset_id: string | null;
  settings: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ScriptSection {
  title: string;
  description: string;
  narration: string;
  visual_notes: string;
  duration_sec: number;
}

export interface ScriptPlan {
  title: string;
  summary: string;
  hook: string;
  narrative_flow: string[];
  sections: ScriptSection[];
  ending_cta: string;
  narration_draft: string;
  estimated_duration_sec: number;
}

export interface ScriptVersion {
  id: string;
  project_id: string;
  version: number;
  status: string;
  raw_text: string | null;
  input_params: Record<string, unknown> | null;
  plan_json: ScriptPlan | null;
  parent_version_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface SceneData {
  id: string;
  script_version_id: string;
  order_index: number;
  title: string | null;
  description: string | null;
  setting: string | null;
  mood: string | null;
  duration_estimate_sec: number | null;
  status: string;
  purpose: string | null;
  narration_text: string | null;
  emotional_tone: string | null;
  visual_intent: string | null;
  transition_hint: string | null;
  created_at: string;
  updated_at: string;
}

export interface ShotData {
  id: string;
  scene_id: string;
  order_index: number;
  shot_type: string | null;
  description: string | null;
  camera_movement: string | null;
  duration_sec: number | null;
  status: string;
  purpose: string | null;
  camera_framing: string | null;
  subject: string | null;
  environment: string | null;
  emotion: string | null;
  narration_segment: string | null;
  transition_in: string | null;
  transition_out: string | null;
  asset_strategy: string | null;
}

export interface FrameData {
  id: string;
  shot_id: string;
  order_index: number;
  frame_role: string | null;
  composition: string | null;
  subject_position: string | null;
  camera_angle: string | null;
  lens_feel: string | null;
  lighting: string | null;
  mood: string | null;
  action_pose: string | null;
  background_description: string | null;
  continuity_notes: string | null;
  forbidden_elements: string | null;
  visual_prompt: string | null;
  negative_prompt: string | null;
  dialogue: string | null;
  duration_ms: number;
  transition_type: string;
  status: string;
}

export interface AssetData {
  id: string;
  project_id: string;
  parent_type: string;
  parent_id: string;
  asset_type: string;
  storage_key: string | null;
  filename: string | null;
  mime_type: string | null;
  file_size_bytes: number | null;
  metadata_: Record<string, unknown> | null;
  version: number;
  status: string;
  is_selected: boolean;
  generation_batch: string | null;
  quality_note: string | null;
  created_at: string;
  url: string | null;
}

export interface SubtitleSegmentData {
  index: number;
  start_ms: number;
  end_ms: number;
  text: string;
  shot_id: string | null;
  speaker: string | null;
}

export interface SubtitleTrackData {
  id: string;
  project_id: string;
  script_version_id: string | null;
  language: string;
  format: string;
  timing_source: string;
  segments: SubtitleSegmentData[] | null;
  style_settings: Record<string, unknown> | null;
  content: string | null;
  total_segments: number | null;
  total_duration_ms: number | null;
  asset_id: string | null;
  status: string;
  created_at: string;
}

export interface TimelineSummaryData {
  id: string;
  status: string;
  total_duration_ms: number;
  total_shots: number;
  shots_with_video: number;
  shots_with_image_only: number;
  shots_missing_visual: number;
  shots_with_audio: number;
  shots_missing_audio: number;
  has_subtitle: boolean;
  has_bgm: boolean;
  warnings: string[];
  created_at: string;
}

export interface TimelineListItem {
  id: string;
  project_id: string;
  script_version_id: string;
  total_duration_ms: number | null;
  status: string;
  created_at: string;
}

export interface Job {
  id: string;
  job_type: string;
  status: string;
  progress: number;
  result: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
}

export interface QAResultData {
  id: string;
  project_id: string;
  script_version_id: string | null;
  scope: string;
  target_type: string | null;
  target_id: string | null;
  check_type: string;
  severity: string;
  message: string;
  details: Record<string, unknown> | null;
  suggestion: string | null;
  resolved: boolean;
  source: string;
  created_at: string;
}

export interface QASummaryData {
  total: number;
  errors: number;
  warnings: number;
  infos: number;
  by_check_type: Record<string, number>;
  by_scope: Record<string, number>;
  render_ready: boolean;
  blocking_issues: QAResultData[];
}

export interface CompiledPromptData {
  concise_prompt: string;
  detailed_prompt: string;
  video_prompt: string;
  negative_prompt: string;
  continuity_notes: string;
  provider_options: Record<string, unknown>;
}

export interface VoiceTrackData {
  id: string;
  shot_id: string;
  frame_spec_id: string | null;
  asset_id: string | null;
  voice_id: string;
  duration_ms: number | null;
  duration_sec: number | null;
  timestamps: unknown;
  tts_metadata: Record<string, unknown> | null;
  status: string;
  is_selected: boolean;
  version: number;
  created_at: string;
}

export interface VoicePreset {
  id: string;
  name: string;
  language: string;
}

export interface ProgressData {
  script: boolean;
  scenes: number;
  shots: number;
  frames: number;
  images: number;
  videos: number;
  voices: number;
  subtitles: number;
  timelines: number;
  renders: number;
  active_jobs: { id: string; job_type: string; status: string; progress: number }[];
}

export interface StylePreset {
  id: string;
  project_id: string | null;
  name: string;
  description: string | null;
  prompt_prefix: string | null;
  prompt_suffix: string | null;
  negative_prompt: string | null;
  style_keywords: string | null;
  rendering_style: string | null;
  color_palette: string | null;
  camera_language: string | null;
  lighting_rules: string | null;
  negative_rules: string | null;
  style_anchor: string | null;
  color_temperature: string | null;
  texture_quality: string | null;
  depth_style: string | null;
  environment_rules: string | null;
  example_image_key: string | null;
  is_global: boolean;
  created_at: string;
  updated_at: string;
}

/* ── Constants ─────────────────────────────────────── */

export const FORMAT_OPTIONS = [
  { value: "youtube_short", label: "YouTube Shorts (<60s)" },
  { value: "tiktok", label: "TikTok (<60s)" },
  { value: "instagram_reel", label: "Instagram Reels (<90s)" },
  { value: "youtube_standard", label: "YouTube Standard (2-10min)" },
  { value: "explainer", label: "설명 영상 (1-5min)" },
];

export const TONE_SUGGESTIONS = [
  "감성적", "유머러스", "교육적", "진지한", "활기찬", "차분한", "미스터리", "동기부여",
];

export const STYLE_CATEGORIES = [
  { id: "realistic", name: "사실적", description: "포토 리얼리스틱, 영화 스틸컷" },
  { id: "anime", name: "일본 애니메이션", description: "일본 애니 스타일" },
  { id: "3d", name: "3D 애니메이션", description: "픽사/디즈니 스타일 3D" },
  { id: "illustration", name: "일러스트", description: "플랫/힐링 일러스트" },
  { id: "stickman", name: "스틱맨", description: "귀여운/스케치 스틱맨" },
  { id: "collage", name: "콜라주", description: "믹스 미디어 콜라주" },
  { id: "cinematic", name: "시네마틱", description: "영화급 시네마틱 룩" },
  { id: "news", name: "뉴스 스타일", description: "뉴스/카드 해설 스타일" },
];
