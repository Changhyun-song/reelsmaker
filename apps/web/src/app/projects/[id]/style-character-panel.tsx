"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { apiUrl } from "@/lib/api";

/* ═══════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════ */

interface StylePreset {
  id: string;
  project_id: string | null;
  name: string;
  description: string | null;
  style_keywords: string | null;
  color_palette: string | null;
  rendering_style: string | null;
  camera_language: string | null;
  lighting_rules: string | null;
  negative_rules: string | null;
  prompt_prefix: string | null;
  prompt_suffix: string | null;
  negative_prompt: string | null;
  is_global: boolean;
  style_anchor: string | null;
  color_temperature: string | null;
  texture_quality: string | null;
  depth_style: string | null;
  environment_rules: string | null;
  reference_asset_ids: string[] | null;
}

interface CharacterProfile {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  role: string | null;
  appearance: string | null;
  outfit: string | null;
  age_impression: string | null;
  personality: string | null;
  facial_traits: string | null;
  pose_rules: string | null;
  forbidden_changes: string | null;
  visual_prompt: string | null;
  voice_id: string | null;
  reference_asset_id: string | null;
  body_type: string | null;
  hair_description: string | null;
  skin_tone: string | null;
  signature_props: string | null;
  forbidden_drift: string | null;
  reference_asset_ids: string[] | null;
}

interface ContinuityProfile {
  id: string;
  project_id: string;
  enabled: boolean;
  color_palette_lock: string | null;
  lighting_anchor: string | null;
  color_temperature_range: string | null;
  environment_consistency: string | null;
  style_anchor_summary: string | null;
  character_lock_notes: string | null;
  forbidden_global_drift: string | null;
  temporal_rules: string | null;
  reference_asset_ids: string[] | null;
}

interface ContinuityPreview {
  style_anchor: string;
  character_anchors: string[];
  color_rules: string;
  lighting_rules: string;
  environment_rules: string;
  forbidden_drift: string[];
  reference_count: number;
}

/* ═══════════════════════════════════════════════════════
   Genre / Visual Look / Tone presets
   ═══════════════════════════════════════════════════════ */

interface GenreOption {
  id: string;
  label: string;
  icon: string;
  desc: string;
  defaults: { rendering: string; camera: string; lighting: string; color: string };
}

const GENRES: GenreOption[] = [
  { id: "longform", label: "일반 롱폼", icon: "📹", desc: "유튜브/틱톡 등 일반 콘텐츠",
    defaults: { rendering: "cinematic", camera: "dynamic mixed angles", lighting: "natural key light", color: "neutral balanced" } },
  { id: "restaurant", label: "식당 홍보", icon: "🍽", desc: "음식/맛집/식당 소개 영상",
    defaults: { rendering: "commercial", camera: "close-up food detail + wide interior", lighting: "warm golden ambient", color: "warm 3200K golden hour" } },
  { id: "product", label: "제품 광고", icon: "📦", desc: "제품/브랜드 프로모션",
    defaults: { rendering: "premium_commercial", camera: "studio macro + lifestyle", lighting: "studio 3-point softbox", color: "clean white balance neutral" } },
  { id: "influencer", label: "AI 인플루언서", icon: "🤳", desc: "가상 인물 기반 콘텐츠",
    defaults: { rendering: "stylized_realism", camera: "portrait 85mm f/1.4", lighting: "beauty ring light", color: "skin-tone optimized warm" } },
  { id: "drama", label: "드라마/단편", icon: "🎬", desc: "스토리 기반 드라마/영화",
    defaults: { rendering: "cinematic_realism", camera: "cinematic anamorphic 2.39:1", lighting: "motivated source lighting", color: "film LUT orange-teal" } },
];

/* ═══════════════════════════════════════════════════════
   Starter Templates — one-click full presets per genre
   ═══════════════════════════════════════════════════════ */

interface StarterTemplate {
  id: string;
  genreId: string;
  name: string;
  tagline: string;
  icon: string;
  gradient: string;
  useCases: string[];
  preset: Record<string, string>;
  bible: Record<string, string>;
  shotRhythm: { avgDurationSec: number; cutsPerMinute: number; keyFrameRatio: number };
  characterConsistency: "low" | "medium" | "high";
}

const STARTER_TEMPLATES: StarterTemplate[] = [
  {
    id: "cinematic_story",
    genreId: "longform",
    name: "Cinematic Story",
    tagline: "영화적 톤의 스토리텔링 롱폼 콘텐츠",
    icon: "📹",
    gradient: "from-amber-900/40 via-orange-900/20 to-neutral-900",
    useCases: ["유튜브 에세이", "지식/정보 콘텐츠", "브이로그 하이라이트"],
    preset: {
      name: "Cinematic Story",
      description: "유튜브/소셜 미디어용 시네마틱 스토리텔링 프리셋",
      rendering_style: "cinematic_realism",
      style_keywords: "photorealistic, cinematic color grading, film grain, shallow depth of field, professional lighting",
      color_palette: "warm amber highlights, deep shadow blues, balanced skin tones, subtle orange-teal split",
      color_temperature: "4200K neutral warm",
      camera_language: "dynamic mixed: wide establishing → medium narration → close-up detail, motivated camera movement, 24fps cinematic cadence",
      lighting_rules: "natural key from 45° left, soft ambient fill, warm practical sources, golden hour preference for outdoor",
      texture_quality: "photorealistic 4K, subtle film grain ISO 400",
      depth_style: "shallow DOF f/2.8 for portraits, deep f/8 for landscapes",
      environment_rules: "realistic modern settings, clean composition, leading lines toward subject",
      negative_rules: "no cartoon style, no oversaturated neon, no dutch angle unless motivated, no lens flare abuse",
      negative_prompt: "text, watermark, blurry, low quality, cartoon, anime, oversaturated, fish-eye distortion",
      style_anchor: "Cinematic photorealistic storytelling with warm amber tones, professional 3-point lighting, and shallow depth of field. Film-like color grading with subtle grain.",
      prompt_prefix: "cinematic photorealistic scene, 4K, professional color grading,",
    },
    bible: {
      main_subject_identity: "Maintain consistent subject appearance across all cuts",
      palette_rules: "Warm amber highlights + cool blue shadows. Skin tones: natural warm. Accent: subtle orange-teal split-toning",
      lens_rules: "35mm-85mm range. Shallow DOF f/2.8 for subjects, deep f/8 for establishing shots. No fisheye or extreme wide.",
      character_visual_rules: "Subject maintains same clothing, hair, and physical features throughout. No age/build drift.",
      wardrobe_rules: "Consistent outfit per sequence. No unexplained costume changes between consecutive cuts.",
      forbidden_drift_rules: "No cartoon/anime style shift. No drastic color temperature jump. No sudden aspect ratio change.",
    },
    shotRhythm: { avgDurationSec: 4.0, cutsPerMinute: 12, keyFrameRatio: 0.25 },
    characterConsistency: "medium",
  },
  {
    id: "warm_food_commercial",
    genreId: "restaurant",
    name: "Warm Food Commercial",
    tagline: "식욕을 자극하는 따뜻한 푸드 광고 톤",
    icon: "🍽",
    gradient: "from-orange-900/40 via-amber-900/20 to-neutral-900",
    useCases: ["맛집 소개", "레시피 영상", "카페/베이커리 홍보"],
    preset: {
      name: "Warm Food Commercial",
      description: "음식을 가장 맛있게 보이게 하는 따뜻한 광고 프리셋",
      rendering_style: "premium_commercial",
      style_keywords: "food photography, warm golden light, steam detail, appetizing colors, close-up textures, bokeh background",
      color_palette: "rich amber, golden honey, warm cream, deep chocolate brown, fresh green accent",
      color_temperature: "3200K warm golden",
      camera_language: "macro close-up food detail 100mm f/2.8, wide interior 24mm establishing, overhead flat-lay, slow dolly reveal",
      lighting_rules: "warm key light from back-left for steam glow, soft fill from right, rim light on food edges for texture, warm practical candles/pendants",
      texture_quality: "8K sharp detail on food surfaces, visible texture and moisture",
      depth_style: "very shallow f/1.8-2.8 for hero food shots, moderate f/4 for interior ambiance",
      environment_rules: "clean table surfaces, natural wood/marble materials, warm ambient interior, soft background blur with bokeh lights",
      negative_rules: "no cold blue lighting on food, no harsh shadows on plates, no messy background, no fluorescent green tint",
      negative_prompt: "cold lighting, blue tint, messy background, blurry food, plastic appearance, cartoon, text overlay",
      style_anchor: "Warm golden food photography with appetizing close-up textures. Rich amber tones, steam highlights, and shallow bokeh. Premium restaurant commercial quality.",
      prompt_prefix: "appetizing food photography, warm golden light, close-up detail, professional food styling,",
    },
    bible: {
      main_subject_identity: "Food items maintain consistent plating and garnish across cuts",
      palette_rules: "Rich golden amber dominant. Food colors: saturated natural (no artificial enhancement). Background: warm neutral cream/wood.",
      lens_rules: "100mm macro for hero shots, 50mm for medium, 24mm wide for interiors. Always shallow DOF on food.",
      character_visual_rules: "If people appear: consistent server/chef outfit. Food: same plate arrangement throughout sequence.",
      wardrobe_rules: "Staff in consistent uniform. Table settings identical across cuts.",
      forbidden_drift_rules: "No cold blue/green color shift on food. No cartoon rendering. No harsh directional shadow on plates.",
    },
    shotRhythm: { avgDurationSec: 3.0, cutsPerMinute: 15, keyFrameRatio: 0.30 },
    characterConsistency: "low",
  },
  {
    id: "premium_product_ad",
    genreId: "product",
    name: "Premium Product Ad",
    tagline: "고급 브랜드 제품 촬영 룩",
    icon: "📦",
    gradient: "from-cyan-900/40 via-slate-900/20 to-neutral-900",
    useCases: ["제품 런칭", "브랜드 캠페인", "전자기기 리뷰"],
    preset: {
      name: "Premium Product Ad",
      description: "하이엔드 제품 광고용 클린 스튜디오 프리셋",
      rendering_style: "premium_commercial",
      style_keywords: "product photography, studio lighting, clean background, reflective surfaces, 8K macro detail, luxury feel",
      color_palette: "clean white, brushed silver, deep black, brand-accent color, subtle gradient",
      color_temperature: "5600K daylight neutral",
      camera_language: "studio macro 105mm product detail, 360 orbit rotation, slow dolly push-in, top-down flat lay, lifestyle context 35mm",
      lighting_rules: "3-point studio softbox: large key left, fill right, hair/rim from behind. Gradient background. Product reflection control.",
      texture_quality: "8K ultra-sharp, visible material texture, clean edges, reflection detail",
      depth_style: "moderate f/4 for full product, shallow f/2.0 for detail macro, deep f/11 for flat-lay",
      environment_rules: "clean minimal studio, gradient backdrop, floating/pedestal display, lifestyle scenes with modern interior",
      negative_rules: "no dust/fingerprints, no harsh shadow, no cluttered background, no warm tint on white products",
      negative_prompt: "dirty surface, fingerprints, cluttered background, low quality, blurry, warm tint on product, text overlay",
      style_anchor: "Premium studio product photography. Clean neutral lighting, razor-sharp macro detail, luxury material textures. Apple-commercial level production quality.",
      prompt_prefix: "premium product photography, studio lighting, clean background, razor-sharp detail,",
    },
    bible: {
      main_subject_identity: "Product maintains exact same model/color/finish across all cuts",
      palette_rules: "Clean neutral white dominant. Product color: accurate brand color. Accent: brand identity color only.",
      lens_rules: "105mm macro for detail, 50mm for full product, 35mm for lifestyle. No distortion on product edges.",
      character_visual_rules: "Product: same angle-consistent design. Hands (if shown): clean, groomed, neutral skin tone.",
      wardrobe_rules: "Minimal human presence. If hands appear: same clean style throughout.",
      forbidden_drift_rules: "No product color deviation. No background clutter. No warm/cool temperature drift. No style shift to cartoon.",
    },
    shotRhythm: { avgDurationSec: 3.5, cutsPerMinute: 14, keyFrameRatio: 0.35 },
    characterConsistency: "high",
  },
  {
    id: "polished_social_character",
    genreId: "influencer",
    name: "Polished Social Character",
    tagline: "매끈한 가상 인플루언서 룩",
    icon: "🤳",
    gradient: "from-pink-900/40 via-violet-900/20 to-neutral-900",
    useCases: ["AI 인플루언서 콘텐츠", "가상 캐릭터 소셜", "패션/뷰티 룩북"],
    preset: {
      name: "Polished Social Character",
      description: "가상 인물 기반 소셜 미디어 콘텐츠용 프리셋",
      rendering_style: "stylized_animation",
      style_keywords: "stylized realism, beauty lighting, flawless skin, vibrant but natural colors, social media aesthetic, portrait bokeh",
      color_palette: "soft pink highlights, clean warm skin tones, pastel accent, creamy background, subtle peach glow",
      color_temperature: "3800K warm beauty",
      camera_language: "portrait 85mm f/1.4 headshot, medium 50mm waist-up, selfie-angle POV, gentle parallax",
      lighting_rules: "beauty ring light front-fill, soft key from 45° right, hair light from behind, catchlights in eyes mandatory",
      texture_quality: "smooth skin rendering, detailed hair/clothing textures, clean edge anti-aliasing",
      depth_style: "very shallow f/1.4-1.8 for portraits, creamy circular bokeh background",
      environment_rules: "clean modern interior, café/lifestyle backdrop, soft natural daylight from window, minimal props",
      negative_rules: "no aging, no blemish, no harsh shadow, no unflattering angle, no desaturated skin",
      negative_prompt: "wrinkles, blemish, harsh shadow, unflattering angle, bad anatomy, extra fingers, ugly, deformed face",
      style_anchor: "Polished beauty-lit social media character. Flawless skin rendering, warm pastel tones, 85mm portrait bokeh. Consistent virtual influencer identity across all cuts.",
      prompt_prefix: "beautiful social media portrait, beauty lighting, flawless skin, 85mm bokeh,",
    },
    bible: {
      main_subject_identity: "Virtual character maintains exact same face, hair, body proportions in every frame",
      palette_rules: "Warm skin-tone optimized. Pastel pink/peach highlights. Clean neutral background. No cold desaturation.",
      lens_rules: "85mm f/1.4 for close-up, 50mm f/1.8 for medium. Always shallow DOF. Catchlights in eyes.",
      character_visual_rules: "Same face structure, eye color, hair style/color, skin tone. No drift in age, weight, or ethnicity.",
      wardrobe_rules: "Outfit consistent per video segment. Style: modern casual/fashion. Signature accessories maintained.",
      forbidden_drift_rules: "No face shape change. No skin tone shift. No age progression. No style shift to cartoon/anime unless intended.",
    },
    shotRhythm: { avgDurationSec: 3.0, cutsPerMinute: 15, keyFrameRatio: 0.40 },
    characterConsistency: "high",
  },
  {
    id: "moody_dramatic_film",
    genreId: "drama",
    name: "Moody Dramatic Film",
    tagline: "무디한 드라마/단편 영화 톤",
    icon: "🎬",
    gradient: "from-blue-900/40 via-indigo-900/20 to-neutral-900",
    useCases: ["단편 영화", "뮤직비디오", "감성 스토리"],
    preset: {
      name: "Moody Dramatic Film",
      description: "분위기 있는 드라마/단편 영화용 프리셋",
      rendering_style: "cinematic_realism",
      style_keywords: "cinematic anamorphic, moody atmospheric, motivated lighting, film noir influence, desaturated earth tones, dramatic contrast",
      color_palette: "desaturated earth tones, deep navy shadow, warm amber practicals, cool steel blue moonlight, skin: muted warm",
      color_temperature: "3600K tungsten warm key, 6500K cool fill",
      camera_language: "anamorphic 2.39:1, slow deliberate tracking, push-in for emotional peak, handheld tension, rack focus subject isolation",
      lighting_rules: "motivated source only: window light, practicals, streetlamps. Deep shadow ratio 4:1. Rim light for subject separation. No flat frontlight.",
      texture_quality: "filmic grain ISO 800, subtle lens aberration, organic texture",
      depth_style: "anamorphic oval bokeh f/2.0, rack focus between subjects, deep staging for blocking",
      environment_rules: "atmospheric haze/fog, practical light sources visible in frame, wet surfaces for reflection, moody interiors",
      negative_rules: "no flat lighting, no bright cheerful palette, no handheld shake without motivation, no modern pop-color accents",
      negative_prompt: "bright cheerful, oversaturated, cartoon, flat lighting, text overlay, lens flare, clean sterile environment",
      style_anchor: "Moody cinematic drama with anamorphic framing, motivated lighting, and desaturated earth tones. Film noir influence with deep shadows and atmospheric haze. Theatrical staging.",
      prompt_prefix: "cinematic dramatic scene, anamorphic 2.39:1, moody atmospheric lighting, filmic grain,",
    },
    bible: {
      main_subject_identity: "Characters maintain exact appearance: costume, hair, makeup, physical build across all scenes",
      palette_rules: "Desaturated earth tones dominant. Shadows: deep navy/steel blue. Highlights: warm amber from practicals. Skin: muted natural warm.",
      lens_rules: "Anamorphic 40-75mm. Oval bokeh. Rack focus for emphasis. Slow dolly/track only. No zoom. No steadicam unless motivated.",
      character_visual_rules: "Same costume per scene/sequence. Makeup continuity. Physical state continuity (injuries, fatigue).",
      wardrobe_rules: "Costume changes only at scene/time boundaries. Consistent weathering/aging of clothing.",
      forbidden_drift_rules: "No bright cheerful palette shift. No cartoon/anime style. No flat lighting. No breaking of light motivation.",
    },
    shotRhythm: { avgDurationSec: 5.0, cutsPerMinute: 8, keyFrameRatio: 0.20 },
    characterConsistency: "high",
  },
];

interface VisualLookOption {
  id: string;
  label: string;
  desc: string;
  color: string;
  keywords: string;
  recommended: string[];
}

const VISUAL_LOOKS: VisualLookOption[] = [
  { id: "cinematic_realism", label: "시네마틱 리얼리즘", desc: "영화 같은 현실적 화면",
    color: "from-amber-900/30 to-neutral-900", keywords: "photorealistic, cinematic color grading, film grain",
    recommended: ["longform", "drama"] },
  { id: "stylized_animation", label: "스타일화 애니메이션", desc: "2D/3D 하이브리드 스타일",
    color: "from-violet-900/30 to-neutral-900", keywords: "stylized 3d render, vibrant colors, smooth shading",
    recommended: ["influencer", "longform"] },
  { id: "webtoon_anime", label: "웹툰/애니메 룩", desc: "한국 웹툰 · 일본 애니메이션",
    color: "from-pink-900/30 to-neutral-900", keywords: "anime style, cel shading, bold outlines, vivid palette",
    recommended: ["longform", "drama"] },
  { id: "premium_commercial", label: "프리미엄 광고", desc: "고급 제품/브랜드 촬영",
    color: "from-cyan-900/30 to-neutral-900", keywords: "studio photography, product lighting, clean background, 8k detail",
    recommended: ["product", "restaurant"] },
  { id: "documentary_realism", label: "다큐멘터리 리얼리즘", desc: "자연스러운 다큐 톤",
    color: "from-emerald-900/30 to-neutral-900", keywords: "handheld natural light, muted tones, authentic textures",
    recommended: ["longform", "restaurant"] },
];

interface ToneOption {
  id: string;
  label: string;
  choices: { value: string; label: string }[];
}

const TONE_AXES: ToneOption[] = [
  { id: "color_temp", label: "색감", choices: [
    { value: "warm_golden", label: "따뜻한 골드" },
    { value: "neutral", label: "뉴트럴" },
    { value: "cool_blue", label: "차가운 블루" },
    { value: "high_contrast", label: "고대비" },
    { value: "pastel_soft", label: "파스텔 소프트" },
  ]},
  { id: "lighting", label: "조명", choices: [
    { value: "natural", label: "자연광" },
    { value: "studio_3point", label: "스튜디오 3점" },
    { value: "dramatic_shadow", label: "드라마틱 음영" },
    { value: "neon_vibrant", label: "네온/바이브런트" },
    { value: "soft_diffused", label: "소프트 확산" },
  ]},
  { id: "camera_style", label: "카메라 스타일", choices: [
    { value: "cinematic_wide", label: "시네마틱 와이드" },
    { value: "portrait_shallow", label: "인물 보케" },
    { value: "macro_detail", label: "매크로 디테일" },
    { value: "handheld_raw", label: "핸드헬드 로우" },
    { value: "drone_aerial", label: "드론/에어리얼" },
  ]},
  { id: "motion", label: "움직임 성향", choices: [
    { value: "static_stable", label: "정적/안정" },
    { value: "slow_smooth", label: "슬로우 부드러움" },
    { value: "dynamic_fast", label: "다이내믹 빠름" },
    { value: "parallax_subtle", label: "미세 패럴랙스" },
  ]},
];

/* ═══════════════════════════════════════════════════════
   Style Wizard (3-step)
   ═══════════════════════════════════════════════════════ */

interface WizardState {
  genre: string | null;
  visualLook: string | null;
  tones: Record<string, string>;
}

function StyleWizard({ onApply, onApplyStarter, current }: {
  onApply: (state: WizardState, presetData: Record<string, string>) => void;
  onApplyStarter: (template: StarterTemplate) => void;
  current: WizardState;
}) {
  const [genre, setGenre] = useState(current.genre);
  const [look, setLook] = useState(current.visualLook);
  const [tones, setTones] = useState<Record<string, string>>(current.tones);
  const [step, setStep] = useState(1);
  const [starterPreview, setStarterPreview] = useState<string | null>(null);

  const genreDef = GENRES.find(g => g.id === genre);
  const lookDef = VISUAL_LOOKS.find(l => l.id === look);

  const filteredLooks = useMemo(() => {
    if (!genre) return VISUAL_LOOKS;
    return [...VISUAL_LOOKS].sort((a, b) => {
      const aRec = a.recommended.includes(genre) ? 0 : 1;
      const bRec = b.recommended.includes(genre) ? 0 : 1;
      return aRec - bRec;
    });
  }, [genre]);

  const promptPreview = useMemo(() => {
    const parts: string[] = [];
    if (lookDef) parts.push(lookDef.keywords);
    if (genreDef) {
      parts.push(`camera: ${genreDef.defaults.camera}`);
      parts.push(`lighting: ${genreDef.defaults.lighting}`);
    }
    for (const axis of TONE_AXES) {
      const val = tones[axis.id];
      if (val) {
        const ch = axis.choices.find(c => c.value === val);
        if (ch) parts.push(`${axis.label}: ${ch.label}`);
      }
    }
    return parts.join(" · ");
  }, [lookDef, genreDef, tones]);

  const buildPresetData = (): Record<string, string> => {
    const data: Record<string, string> = {};
    data.name = `${genreDef?.label || "커스텀"} — ${lookDef?.label || "기본"}`;
    data.description = `${genreDef?.desc || ""} + ${lookDef?.desc || ""}`;
    if (lookDef) data.style_keywords = lookDef.keywords;
    if (lookDef) data.rendering_style = lookDef.id;
    if (genreDef) {
      data.camera_language = genreDef.defaults.camera;
      data.lighting_rules = genreDef.defaults.lighting;
      data.color_palette = genreDef.defaults.color;
    }
    const toneLabel = tones.color_temp;
    if (toneLabel) data.color_temperature = toneLabel.replace(/_/g, " ");
    const lightTone = tones.lighting;
    if (lightTone) data.lighting_rules = (data.lighting_rules || "") + `, ${lightTone.replace(/_/g, " ")}`;
    const camTone = tones.camera_style;
    if (camTone) data.camera_language = (data.camera_language || "") + `, ${camTone.replace(/_/g, " ")}`;
    data.style_anchor = `${lookDef?.label || ""} style for ${genreDef?.label || ""} content. ${lookDef?.keywords || ""}`;
    return data;
  };

  const handleApply = () => {
    const state: WizardState = { genre, visualLook: look, tones };
    onApply(state, buildPresetData());
  };

  return (
    <div className="space-y-5">
      {/* Step indicators */}
      <div className="flex items-center gap-2">
        {[1, 2, 3].map(s => (
          <button key={s} onClick={() => setStep(s)} className="flex items-center gap-1.5">
            <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition ${
              step === s ? "bg-blue-600 text-white" : s < step || (s === 1 && genre) || (s === 2 && look) ? "bg-emerald-600/20 text-emerald-400 border border-emerald-600/30" : "bg-neutral-800 text-neutral-600"
            }`}>{s < step || (s === 1 && genre) || (s === 2 && look) ? "✓" : s}</span>
            <span className={`text-xs font-medium ${step === s ? "text-neutral-200" : "text-neutral-500"}`}>
              {s === 1 ? "장르" : s === 2 ? "비주얼 룩" : "톤 설정"}
            </span>
            {s < 3 ? <span className="text-neutral-700 mx-1">→</span> : null}
          </button>
        ))}
      </div>

      {/* Step 1: Genre + Starter Templates */}
      {step === 1 ? (
        <div className="space-y-5">
          {/* Starter templates — quick start */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <p className="text-sm font-bold text-neutral-300">원클릭 스타터 템플릿</p>
              <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-emerald-900/30 text-emerald-400 font-medium border border-emerald-800/30">추천</span>
            </div>
            <p className="text-[10px] text-neutral-500">
              장르에 최적화된 완성형 템플릿입니다. 클릭 한 번으로 스타일·색감·조명·카메라·Continuity 규칙이 모두 설정됩니다.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {STARTER_TEMPLATES.map(t => {
                const isPreview = starterPreview === t.id;
                return (
                  <div key={t.id} className={`rounded-xl border overflow-hidden transition-all ${
                    isPreview ? "border-blue-600 ring-1 ring-blue-500/20" : "border-neutral-800 hover:border-neutral-700"
                  }`}>
                    {/* Gradient header */}
                    <div className={`h-20 bg-gradient-to-br ${t.gradient} relative p-3 flex flex-col justify-end`}>
                      <span className="absolute top-2 right-2 text-2xl">{t.icon}</span>
                      <p className="text-sm font-bold text-white drop-shadow-lg">{t.name}</p>
                      <p className="text-[10px] text-white/70">{t.tagline}</p>
                    </div>

                    <div className="p-3 space-y-2">
                      {/* Use cases */}
                      <div className="flex flex-wrap gap-1">
                        {t.useCases.map(u => (
                          <span key={u} className="text-[8px] px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-400">{u}</span>
                        ))}
                      </div>

                      {/* Key specs */}
                      <div className="grid grid-cols-3 gap-1 text-[8px]">
                        <div className="rounded bg-neutral-800/50 px-1.5 py-1 text-center">
                          <p className="text-neutral-600">색감</p>
                          <p className="text-neutral-400 font-medium">{t.preset.color_temperature || "자동"}</p>
                        </div>
                        <div className="rounded bg-neutral-800/50 px-1.5 py-1 text-center">
                          <p className="text-neutral-600">컷 리듬</p>
                          <p className="text-neutral-400 font-medium">{t.shotRhythm.cutsPerMinute}컷/분</p>
                        </div>
                        <div className="rounded bg-neutral-800/50 px-1.5 py-1 text-center">
                          <p className="text-neutral-600">캐릭터 고정</p>
                          <p className={`font-medium ${t.characterConsistency === "high" ? "text-emerald-400" : t.characterConsistency === "medium" ? "text-amber-400" : "text-neutral-500"}`}>
                            {t.characterConsistency === "high" ? "강함" : t.characterConsistency === "medium" ? "보통" : "약함"}
                          </p>
                        </div>
                      </div>

                      {/* Preview toggle */}
                      {isPreview ? (
                        <div className="rounded-lg bg-emerald-950/10 border border-emerald-800/20 p-2.5 space-y-1.5">
                          <p className="text-[9px] font-bold text-emerald-400">이 템플릿이 설정하는 항목</p>
                          <div className="text-[9px] space-y-0.5">
                            <p className="text-neutral-400"><span className="text-emerald-500">✓</span> 조명: {t.preset.lighting_rules?.slice(0, 60)}...</p>
                            <p className="text-neutral-400"><span className="text-emerald-500">✓</span> 카메라: {t.preset.camera_language?.slice(0, 60)}...</p>
                            <p className="text-neutral-400"><span className="text-emerald-500">✓</span> Continuity Bible {Object.keys(t.bible).length}개 규칙 자동 설정</p>
                            <p className="text-neutral-400"><span className="text-emerald-500">✓</span> 네거티브 프롬프트 포함</p>
                            <p className="text-neutral-400"><span className="text-emerald-500">✓</span> 평균 {t.shotRhythm.avgDurationSec}초/컷, 핵심 프레임 {Math.round(t.shotRhythm.keyFrameRatio * 100)}%</p>
                          </div>
                        </div>
                      ) : null}

                      {/* Actions */}
                      <div className="flex gap-2">
                        <button
                          onClick={() => onApplyStarter(t)}
                          className="flex-1 rounded-lg bg-blue-600 py-2 text-[11px] font-medium text-white hover:bg-blue-500 transition"
                        >
                          이 템플릿 적용
                        </button>
                        <button
                          onClick={() => setStarterPreview(isPreview ? null : t.id)}
                          className="rounded-lg bg-neutral-800 border border-neutral-700/50 px-3 py-2 text-[11px] font-medium text-neutral-400 hover:text-neutral-200 transition"
                        >
                          {isPreview ? "닫기" : "상세"}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3">
            <div className="flex-1 border-t border-neutral-800" />
            <span className="text-[10px] text-neutral-600 font-medium">또는 직접 선택</span>
            <div className="flex-1 border-t border-neutral-800" />
          </div>

          {/* Manual genre selection */}
          <div className="space-y-2">
            <p className="text-sm text-neutral-400">장르를 직접 선택하고 단계별로 설정하기</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {GENRES.map(g => (
                <button
                  key={g.id}
                  onClick={() => { setGenre(g.id); setStep(2); }}
                  className={`rounded-xl border p-4 text-left transition-all ${
                    genre === g.id
                      ? "border-blue-600 bg-blue-950/20 ring-1 ring-blue-500/20"
                      : "border-neutral-800 bg-neutral-900/50 hover:border-neutral-700"
                  }`}
                >
                  <span className="text-2xl">{g.icon}</span>
                  <p className="text-sm font-bold text-neutral-200 mt-2">{g.label}</p>
                  <p className="text-[10px] text-neutral-500 mt-1">{g.desc}</p>
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      {/* Step 2: Visual look */}
      {step === 2 ? (
        <div className="space-y-3">
          <p className="text-sm text-neutral-400">어떤 비주얼 느낌을 원하시나요?</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {filteredLooks.map(l => {
              const isRecommended = genre ? l.recommended.includes(genre) : false;
              return (
                <button
                  key={l.id}
                  onClick={() => { setLook(l.id); setStep(3); }}
                  className={`rounded-xl border overflow-hidden text-left transition-all ${
                    look === l.id
                      ? "border-blue-600 ring-1 ring-blue-500/20"
                      : "border-neutral-800 hover:border-neutral-700"
                  }`}
                >
                  <div className={`h-16 bg-gradient-to-br ${l.color} relative`}>
                    {isRecommended ? (
                      <span className="absolute top-1.5 right-1.5 text-[8px] px-1.5 py-0.5 rounded-full bg-emerald-600/30 text-emerald-400 font-medium border border-emerald-700/30">
                        추천
                      </span>
                    ) : null}
                  </div>
                  <div className="p-3">
                    <p className="text-sm font-bold text-neutral-200">{l.label}</p>
                    <p className="text-[10px] text-neutral-500 mt-0.5">{l.desc}</p>
                    <p className="text-[9px] text-neutral-600 mt-1 line-clamp-1">{l.keywords}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      {/* Step 3: Tone */}
      {step === 3 ? (
        <div className="space-y-4">
          <p className="text-sm text-neutral-400">세부 톤을 선택하세요 (선택 사항)</p>
          {TONE_AXES.map(axis => (
            <div key={axis.id} className="space-y-1.5">
              <p className="text-xs font-medium text-neutral-400">{axis.label}</p>
              <div className="flex flex-wrap gap-2">
                {axis.choices.map(ch => (
                  <button
                    key={ch.value}
                    onClick={() => setTones(prev => ({
                      ...prev,
                      [axis.id]: prev[axis.id] === ch.value ? "" : ch.value,
                    }))}
                    className={`rounded-lg px-3 py-1.5 text-[11px] font-medium border transition ${
                      tones[axis.id] === ch.value
                        ? "bg-blue-600/20 border-blue-700/40 text-blue-400"
                        : "bg-neutral-800/50 border-neutral-700/50 text-neutral-400 hover:text-neutral-200"
                    }`}
                  >
                    {ch.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {/* Preview & apply */}
      {(genre || look) ? (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-bold text-neutral-500 uppercase">선택 요약</p>
            {genre && look ? (
              <button
                onClick={handleApply}
                className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-500 transition"
              >
                이 스타일 적용
              </button>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2">
            {genreDef ? (
              <span className="text-[10px] px-2 py-1 rounded-lg bg-blue-900/20 text-blue-400 border border-blue-800/30">
                {genreDef.icon} {genreDef.label}
              </span>
            ) : null}
            {lookDef ? (
              <span className="text-[10px] px-2 py-1 rounded-lg bg-violet-900/20 text-violet-400 border border-violet-800/30">
                {lookDef.label}
              </span>
            ) : null}
            {Object.entries(tones).filter(([, v]) => v).map(([k, v]) => {
              const axis = TONE_AXES.find(a => a.id === k);
              const ch = axis?.choices.find(c => c.value === v);
              return ch ? (
                <span key={k} className="text-[10px] px-2 py-1 rounded-lg bg-neutral-800 text-neutral-400 border border-neutral-700/50">
                  {axis?.label}: {ch.label}
                </span>
              ) : null;
            })}
          </div>
          {promptPreview ? (
            <div className="rounded-lg bg-emerald-950/10 border border-emerald-800/20 p-3">
              <p className="text-[9px] font-bold text-emerald-400 mb-1">프롬프트에 반영되는 내용</p>
              <p className="text-[10px] text-emerald-300/80 leading-relaxed">{promptPreview}</p>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Simplified Character Form
   ═══════════════════════════════════════════════════════ */

const CHAR_SIMPLE_FIELDS: { key: keyof CharacterProfile; label: string; placeholder: string; multi?: boolean }[] = [
  { key: "name", label: "이름/명칭", placeholder: "주인공, 제품명, 브랜드 등" },
  { key: "role", label: "역할", placeholder: "주인공, 조연, 내레이터 등" },
  { key: "appearance", label: "외형 유지 (핵심)", placeholder: "예: 긴 흑발, 흰 셔츠, 날씬한 체형", multi: true },
  { key: "outfit", label: "의상/소품 유지", placeholder: "예: 항상 빨간 재킷, 안경 착용", multi: true },
  { key: "forbidden_drift", label: "절대 변하면 안 되는 것", placeholder: "예: 머리색 변경 금지, 나이 변화 금지", multi: true },
];

const CHAR_ADVANCED_FIELDS: { key: keyof CharacterProfile; label: string; placeholder: string; multi?: boolean }[] = [
  { key: "age_impression", label: "나이 인상", placeholder: "예: 20대 초반" },
  { key: "body_type", label: "체형", placeholder: "예: slim athletic, 170cm" },
  { key: "skin_tone", label: "피부톤", placeholder: "예: fair warm undertones" },
  { key: "hair_description", label: "머리카락 상세", placeholder: "색상, 길이, 스타일", multi: true },
  { key: "facial_traits", label: "얼굴 특징 (영어)", placeholder: "예: sharp jawline, big eyes", multi: true },
  { key: "signature_props", label: "시그니처 소품", placeholder: "항상 착용하는 아이템", multi: true },
  { key: "personality", label: "성격/특성", placeholder: "예: cheerful, bold", multi: true },
  { key: "pose_rules", label: "포즈 규칙 (영어)", placeholder: "자세/동작 규칙", multi: true },
  { key: "visual_prompt", label: "Visual Prompt (자동 생성)", placeholder: "컴파일러가 자동 조합", multi: true },
  { key: "voice_id", label: "TTS Voice ID", placeholder: "ElevenLabs Voice ID" },
];

function SimpleCharacterForm({
  initial,
  onSave,
  onCancel,
  saving,
}: {
  initial: Partial<CharacterProfile>;
  onSave: (data: Record<string, string>) => void;
  onCancel: () => void;
  saving: boolean;
}) {
  const [form, setForm] = useState<Record<string, string>>({});
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    const f: Record<string, string> = {};
    for (const { key } of [...CHAR_SIMPLE_FIELDS, ...CHAR_ADVANCED_FIELDS]) {
      f[key] = (initial[key] as string) ?? "";
    }
    setForm(f);
  }, [initial]);

  const renderField = (field: { key: string; label: string; placeholder: string; multi?: boolean }) => (
    <div key={field.key} className="space-y-1">
      <label className="text-xs font-medium text-neutral-400">{field.label}</label>
      {field.multi ? (
        <textarea
          value={form[field.key] ?? ""}
          onChange={e => setForm(p => ({ ...p, [field.key]: e.target.value }))}
          rows={2}
          placeholder={field.placeholder}
          className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 placeholder-neutral-600 focus:border-blue-500 focus:outline-none resize-none"
        />
      ) : (
        <input
          type="text"
          value={form[field.key] ?? ""}
          onChange={e => setForm(p => ({ ...p, [field.key]: e.target.value }))}
          placeholder={field.placeholder}
          className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 placeholder-neutral-600 focus:border-blue-500 focus:outline-none"
        />
      )}
    </div>
  );

  return (
    <div className="space-y-3">
      <p className="text-[10px] text-neutral-500">
        핵심 필드만 채우면 됩니다. 나머지는 AI가 자동 보완합니다.
      </p>
      {CHAR_SIMPLE_FIELDS.map(renderField)}

      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="text-[10px] font-medium text-neutral-500 hover:text-neutral-300 transition"
      >
        {showAdvanced ? "▾ 고급 필드 닫기" : "▸ 고급 필드 열기 (선택 사항)"}
      </button>
      {showAdvanced ? CHAR_ADVANCED_FIELDS.map(renderField) : null}

      <div className="flex gap-2 pt-2">
        <button onClick={() => onSave(form)} disabled={saving || !form.name?.trim()} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition">
          {saving ? "저장 중..." : "저장"}
        </button>
        <button onClick={onCancel} className="rounded-lg bg-neutral-700 px-4 py-2 text-sm font-medium hover:bg-neutral-600 transition">취소</button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Character Card (simplified)
   ═══════════════════════════════════════════════════════ */

function CharacterCard({ char, onEdit, onDelete }: { char: CharacterProfile; onEdit: () => void; onDelete: () => void }) {
  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 flex items-start gap-4">
      <div className="w-12 h-12 rounded-full bg-purple-900/30 border border-purple-800/30 flex items-center justify-center shrink-0">
        <span className="text-lg">{char.name.charAt(0)}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-bold text-neutral-200">{char.name}</span>
          {char.role ? <span className="text-[9px] bg-purple-900/40 text-purple-400 px-1.5 py-0.5 rounded-full">{char.role}</span> : null}
        </div>
        {char.appearance ? <p className="text-[10px] text-neutral-500 line-clamp-1">{char.appearance}</p> : null}
        {char.forbidden_drift ? (
          <p className="text-[9px] text-red-400/70 mt-0.5 line-clamp-1">고정: {char.forbidden_drift}</p>
        ) : null}
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        <button onClick={onEdit} className="rounded bg-neutral-700 px-2.5 py-1 text-[10px] font-medium hover:bg-neutral-600 transition">수정</button>
        <button onClick={onDelete} className="rounded bg-red-900/30 px-2.5 py-1 text-[10px] font-medium text-red-400 hover:bg-red-800/30 transition">삭제</button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Style Preset Card (improved)
   ═══════════════════════════════════════════════════════ */

function PresetCard({ preset, isActive, onActivate, onEdit, onDelete }: {
  preset: StylePreset; isActive: boolean; onActivate: () => void; onEdit: () => void; onDelete: () => void;
}) {
  const lookDef = VISUAL_LOOKS.find(l => l.id === preset.rendering_style);

  return (
    <div className={`rounded-xl border overflow-hidden transition-all ${
      isActive ? "border-blue-600 bg-blue-950/15 ring-1 ring-blue-500/20" : "border-neutral-800 bg-neutral-900/50 hover:border-neutral-700"
    }`}>
      {/* Gradient thumbnail */}
      <div className={`h-20 bg-gradient-to-br ${lookDef?.color || "from-neutral-800 to-neutral-900"} relative flex items-end p-3`}>
        {isActive ? (
          <span className="absolute top-2 right-2 text-[9px] px-2 py-0.5 rounded-full bg-blue-600 text-white font-bold">사용 중</span>
        ) : null}
        <p className="text-sm font-bold text-white drop-shadow-lg">{preset.name}</p>
      </div>

      <div className="p-3 space-y-2">
        {preset.description ? <p className="text-[10px] text-neutral-500 line-clamp-2">{preset.description}</p> : null}

        {/* Key info pills */}
        <div className="flex flex-wrap gap-1">
          {preset.rendering_style ? <span className="text-[8px] px-1.5 py-0.5 rounded bg-violet-900/20 text-violet-400">{lookDef?.label || preset.rendering_style}</span> : null}
          {preset.color_temperature ? <span className="text-[8px] px-1.5 py-0.5 rounded bg-amber-900/20 text-amber-400">{preset.color_temperature}</span> : null}
          {preset.lighting_rules ? <span className="text-[8px] px-1.5 py-0.5 rounded bg-yellow-900/20 text-yellow-400 line-clamp-1">{preset.lighting_rules.slice(0, 30)}</span> : null}
        </div>

        {/* Prompt impact */}
        {preset.style_anchor ? (
          <div className="rounded-lg bg-emerald-950/10 border border-emerald-800/20 p-2">
            <p className="text-[8px] font-bold text-emerald-400 mb-0.5">프롬프트 영향</p>
            <p className="text-[9px] text-emerald-300/70 line-clamp-2">{preset.style_anchor}</p>
          </div>
        ) : null}

        {/* Actions */}
        <div className="flex gap-1.5 pt-1">
          {!isActive ? (
            <button onClick={onActivate} className="rounded bg-blue-600 px-3 py-1 text-[10px] font-medium text-white hover:bg-blue-500 transition">적용</button>
          ) : null}
          {!preset.is_global ? (
            <>
              <button onClick={onEdit} className="rounded bg-neutral-700 px-2.5 py-1 text-[10px] font-medium hover:bg-neutral-600 transition">수정</button>
              <button onClick={onDelete} className="rounded bg-red-900/30 px-2.5 py-1 text-[10px] font-medium text-red-400 hover:bg-red-800/30 transition">삭제</button>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Style Form (existing advanced editor)
   ═══════════════════════════════════════════════════════ */

const STYLE_FIELDS: { key: keyof StylePreset; label: string; multi?: boolean }[] = [
  { key: "name", label: "이름" },
  { key: "description", label: "설명", multi: true },
  { key: "style_anchor", label: "스타일 앵커", multi: true },
  { key: "style_keywords", label: "스타일 키워드", multi: true },
  { key: "color_palette", label: "색상 팔레트", multi: true },
  { key: "color_temperature", label: "색온도" },
  { key: "rendering_style", label: "렌더링 스타일", multi: true },
  { key: "texture_quality", label: "텍스처 품질" },
  { key: "depth_style", label: "피사계 심도" },
  { key: "camera_language", label: "카메라 언어", multi: true },
  { key: "lighting_rules", label: "조명 규칙", multi: true },
  { key: "environment_rules", label: "환경 규칙", multi: true },
  { key: "negative_rules", label: "네거티브 규칙", multi: true },
  { key: "prompt_prefix", label: "프롬프트 접두사", multi: true },
  { key: "negative_prompt", label: "네거티브 프롬프트", multi: true },
];

function AdvancedStyleForm({ initial, onSave, onCancel, saving }: {
  initial: Partial<StylePreset>;
  onSave: (data: Record<string, string>) => void;
  onCancel: () => void;
  saving: boolean;
}) {
  const [form, setForm] = useState<Record<string, string>>({});

  useEffect(() => {
    const f: Record<string, string> = {};
    for (const { key } of STYLE_FIELDS) f[key] = (initial[key] as string) ?? "";
    setForm(f);
  }, [initial]);

  return (
    <div className="space-y-3">
      {STYLE_FIELDS.map(({ key, label, multi }) => (
        <div key={key}>
          <label className="block text-xs font-medium text-neutral-400 mb-1">{label}</label>
          {multi ? (
            <textarea value={form[key] ?? ""} onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))} rows={2}
              className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none resize-none" />
          ) : (
            <input type="text" value={form[key] ?? ""} onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
              className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none" />
          )}
        </div>
      ))}
      <div className="flex gap-2 pt-2">
        <button onClick={() => onSave(form)} disabled={saving || !form.name?.trim()} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition">
          {saving ? "저장 중..." : "저장"}
        </button>
        <button onClick={onCancel} className="rounded-lg bg-neutral-700 px-4 py-2 text-sm font-medium hover:bg-neutral-600 transition">취소</button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Continuity Advanced Section (collapsible)
   ═══════════════════════════════════════════════════════ */

const CONTINUITY_FIELDS: { key: keyof ContinuityProfile; label: string; multi?: boolean; hint: string }[] = [
  { key: "color_palette_lock", label: "색상 팔레트 잠금", multi: true, hint: "모든 샷에서 유지할 색상" },
  { key: "lighting_anchor", label: "조명 앵커", multi: true, hint: "기준 조명 방향/스타일" },
  { key: "color_temperature_range", label: "색온도 범위", hint: "허용 범위 (예: 3000K-4500K)" },
  { key: "environment_consistency", label: "환경 일관성", multi: true, hint: "반복될 환경 요소" },
  { key: "style_anchor_summary", label: "스타일 앵커 요약", multi: true, hint: "프로젝트 전체 스타일 DNA" },
  { key: "character_lock_notes", label: "캐릭터 잠금 노트", multi: true, hint: "전체 캐릭터 공통 잠금" },
  { key: "forbidden_global_drift", label: "글로벌 Forbidden Drift", multi: true, hint: "절대 변하면 안 되는 것들" },
  { key: "temporal_rules", label: "시간적 규칙", multi: true, hint: "시간 흐름에 따른 변화 규칙" },
];

function ContinuitySection({ projectId }: { projectId: string }) {
  const [expanded, setExpanded] = useState(false);
  const [profile, setProfile] = useState<ContinuityProfile | null>(null);
  const [preview, setPreview] = useState<ContinuityPreview | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);

  const fetchProfile = useCallback(async () => {
    try {
      const r = await fetch(apiUrl(`/api/projects/${projectId}/continuity`));
      if (r.ok) {
        const data = await r.json();
        setProfile(data);
        const f: Record<string, string> = {};
        for (const { key } of CONTINUITY_FIELDS) f[key] = (data[key] as string) ?? "";
        f.enabled = data.enabled ? "true" : "false";
        setForm(f);
      }
    } catch { /* skip */ }
  }, [projectId]);

  const fetchPreview = useCallback(async () => {
    try {
      const r = await fetch(apiUrl(`/api/projects/${projectId}/continuity/preview`));
      if (r.ok) setPreview(await r.json());
    } catch { /* skip */ }
  }, [projectId]);

  useEffect(() => { fetchProfile(); fetchPreview(); }, [fetchProfile, fetchPreview]);

  const saveProfile = async () => {
    setSaving(true);
    try {
      const body: Record<string, unknown> = {};
      for (const { key } of CONTINUITY_FIELDS) {
        if (form[key] !== undefined) body[key] = form[key] || null;
      }
      body.enabled = form.enabled !== "false";
      const r = await fetch(apiUrl(`/api/projects/${projectId}/continuity`), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (r.ok) {
        await fetchProfile();
        await fetchPreview();
        setEditing(false);
      }
    } finally { setSaving(false); }
  };

  const hasData = preview && (preview.style_anchor || preview.color_rules || preview.forbidden_drift.length > 0);

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/30">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-neutral-400">고급 설정: Continuity 시스템</span>
          {profile?.enabled ? (
            <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-emerald-900/30 text-emerald-400 font-medium">활성</span>
          ) : (
            <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-neutral-800 text-neutral-600 font-medium">비활성</span>
          )}
          {hasData ? (
            <span className="text-[8px] text-neutral-600">설정됨</span>
          ) : null}
        </div>
        <span className="text-xs text-neutral-600">{expanded ? "▾" : "▸"}</span>
      </button>

      {expanded ? (
        <div className="border-t border-neutral-800 px-4 py-4 space-y-4">
          <p className="text-[10px] text-neutral-500">
            이 설정은 스타일 위자드와 프리셋에서 처리하지 못하는 세밀한 일관성 규칙을 직접 작성할 때 사용합니다.
            대부분의 경우 위의 스타일 선택만으로 충분합니다.
          </p>

          {/* Preview */}
          {preview && !editing ? (
            <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-3 space-y-2 text-xs">
              {preview.style_anchor ? <p className="text-blue-400"><span className="font-bold">앵커:</span> {preview.style_anchor}</p> : null}
              {preview.color_rules ? <p className="text-amber-400/80"><span className="font-bold text-neutral-500">색상:</span> {preview.color_rules}</p> : null}
              {preview.lighting_rules ? <p className="text-yellow-400/80"><span className="font-bold text-neutral-500">조명:</span> {preview.lighting_rules}</p> : null}
              {preview.forbidden_drift.length > 0 ? (
                <p className="text-red-400/80"><span className="font-bold text-neutral-500">금지:</span> {preview.forbidden_drift.join(", ")}</p>
              ) : null}
            </div>
          ) : null}

          {!editing ? (
            <button onClick={() => setEditing(true)} className="rounded-lg bg-neutral-800 px-3 py-1.5 text-xs font-medium text-neutral-400 hover:text-neutral-200 transition">
              Continuity 규칙 편집
            </button>
          ) : (
            <div className="space-y-3">
              {CONTINUITY_FIELDS.map(({ key, label, multi, hint }) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-neutral-400 mb-1">{label}</label>
                  <p className="text-[9px] text-neutral-600 mb-1">{hint}</p>
                  {multi ? (
                    <textarea value={form[key] ?? ""} onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))} rows={2}
                      className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none resize-none" />
                  ) : (
                    <input type="text" value={form[key] ?? ""} onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
                      className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none" />
                  )}
                </div>
              ))}
              <div className="flex gap-2">
                <button onClick={saveProfile} disabled={saving} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition">
                  {saving ? "저장 중..." : "저장"}
                </button>
                <button onClick={() => setEditing(false)} className="rounded-lg bg-neutral-700 px-4 py-2 text-sm font-medium hover:bg-neutral-600 transition">취소</button>
              </div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Main Panel
   ═══════════════════════════════════════════════════════ */

export default function StyleCharacterPanel({
  projectId,
  activeStylePresetId,
  onActiveStyleChange,
}: {
  projectId: string;
  activeStylePresetId: string | null;
  onActiveStyleChange: (id: string | null) => void;
}) {
  const [view, setView] = useState<"wizard" | "presets" | "characters">("wizard");
  const [presets, setPresets] = useState<StylePreset[]>([]);
  const [characters, setCharacters] = useState<CharacterProfile[]>([]);
  const [editingStyle, setEditingStyle] = useState<StylePreset | null>(null);
  const [editingChar, setEditingChar] = useState<CharacterProfile | null>(null);
  const [creatingChar, setCreatingChar] = useState(false);
  const [saving, setSaving] = useState(false);
  const [wizardState, setWizardState] = useState<WizardState>({ genre: null, visualLook: null, tones: {} });

  const fetchPresets = useCallback(async () => {
    try {
      const r = await fetch(apiUrl(`/api/projects/${projectId}/styles`));
      if (r.ok) setPresets((await r.json()).presets || []);
    } catch { /* skip */ }
  }, [projectId]);

  const fetchCharacters = useCallback(async () => {
    try {
      const r = await fetch(apiUrl(`/api/projects/${projectId}/characters`));
      if (r.ok) setCharacters((await r.json()).characters || []);
    } catch { /* skip */ }
  }, [projectId]);

  useEffect(() => { fetchPresets(); fetchCharacters(); }, [fetchPresets, fetchCharacters]);

  const saveStyle = async (data: Record<string, string>, id?: string) => {
    setSaving(true);
    try {
      const url = id ? `/api/projects/${projectId}/styles/${id}` : `/api/projects/${projectId}/styles`;
      const r = await fetch(apiUrl(url), {
        method: id ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (r.ok) {
        const saved = await r.json();
        await fetchPresets();
        setEditingStyle(null);
        if (!id && saved.id) {
          await fetch(apiUrl(`/api/projects/${projectId}/active-style/${saved.id}`), { method: "POST" });
          onActiveStyleChange(saved.id);
        }
      }
    } finally { setSaving(false); }
  };

  const activateStyle = async (presetId: string) => {
    const r = await fetch(apiUrl(`/api/projects/${projectId}/active-style/${presetId}`), { method: "POST" });
    if (r.ok) onActiveStyleChange(presetId);
  };

  const deleteStyle = async (presetId: string) => {
    await fetch(apiUrl(`/api/projects/${projectId}/styles/${presetId}`), { method: "DELETE" });
    fetchPresets();
    if (activeStylePresetId === presetId) onActiveStyleChange(null);
  };

  const saveChar = async (data: Record<string, string>, id?: string) => {
    setSaving(true);
    try {
      const url = id ? `/api/projects/${projectId}/characters/${id}` : `/api/projects/${projectId}/characters`;
      const r = await fetch(apiUrl(url), {
        method: id ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (r.ok) {
        await fetchCharacters();
        setEditingChar(null);
        setCreatingChar(false);
      }
    } finally { setSaving(false); }
  };

  const deleteChar = async (charId: string) => {
    await fetch(apiUrl(`/api/projects/${projectId}/characters/${charId}`), { method: "DELETE" });
    fetchCharacters();
  };

  const handleWizardApply = (state: WizardState, presetData: Record<string, string>) => {
    setWizardState(state);
    saveStyle(presetData);
  };

  const handleStarterApply = async (template: StarterTemplate) => {
    setSaving(true);
    try {
      const presetUrl = `/api/projects/${projectId}/styles`;
      const r = await fetch(apiUrl(presetUrl), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(template.preset),
      });
      if (r.ok) {
        const saved = await r.json();
        await fetchPresets();
        if (saved.id) {
          await fetch(apiUrl(`/api/projects/${projectId}/active-style/${saved.id}`), { method: "POST" });
          onActiveStyleChange(saved.id);
        }
      }
      if (Object.keys(template.bible).length > 0) {
        await fetch(apiUrl(`/api/projects/${projectId}/bible`), {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ bible: template.bible }),
        });
      }
      setWizardState({ genre: template.genreId, visualLook: template.preset.rendering_style || null, tones: {} });
    } finally {
      setSaving(false);
    }
  };

  const activePreset = presets.find(p => p.id === activeStylePresetId);

  return (
    <div className="space-y-5">
      {/* Current style summary */}
      {activePreset ? (
        <div className="rounded-xl border border-blue-800/30 bg-blue-950/10 p-4 flex items-center gap-4">
          <div className={`w-14 h-14 rounded-lg bg-gradient-to-br ${
            VISUAL_LOOKS.find(l => l.id === activePreset.rendering_style)?.color || "from-neutral-800 to-neutral-900"
          } shrink-0`} />
          <div className="flex-1 min-w-0">
            <p className="text-[9px] text-blue-400 font-medium">현재 적용된 스타일</p>
            <p className="text-sm font-bold text-neutral-200">{activePreset.name}</p>
            {activePreset.style_anchor ? <p className="text-[10px] text-neutral-500 line-clamp-1">{activePreset.style_anchor}</p> : null}
          </div>
          <button
            onClick={() => setView("wizard")}
            className="rounded-lg bg-neutral-800 border border-neutral-700/50 px-3 py-1.5 text-xs font-medium text-neutral-400 hover:text-neutral-200 transition shrink-0"
          >
            변경
          </button>
        </div>
      ) : null}

      {/* View tabs */}
      <div className="flex gap-1 border-b border-neutral-800">
        {([
          { key: "wizard" as const, label: "스타일 선택", desc: "빠른 설정" },
          { key: "presets" as const, label: `프리셋 (${presets.length})`, desc: "상세 관리" },
          { key: "characters" as const, label: `캐릭터 (${characters.length})`, desc: "인물/주체" },
        ]).map(t => (
          <button
            key={t.key}
            onClick={() => setView(t.key)}
            className={`px-4 py-2 text-sm font-medium transition border-b-2 -mb-px ${
              view === t.key
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-neutral-500 hover:text-neutral-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Wizard view ─── */}
      {view === "wizard" ? (
        <StyleWizard onApply={handleWizardApply} onApplyStarter={handleStarterApply} current={wizardState} />
      ) : null}

      {/* ── Presets view ─── */}
      {view === "presets" ? (
        <div className="space-y-3">
          {editingStyle ? (
            <div className="rounded-xl border border-blue-900/50 bg-blue-950/10 p-4">
              <h3 className="text-sm font-semibold mb-3">프리셋 수정: {editingStyle.name}</h3>
              <AdvancedStyleForm
                initial={editingStyle}
                onSave={data => saveStyle(data, editingStyle.id)}
                onCancel={() => setEditingStyle(null)}
                saving={saving}
              />
            </div>
          ) : null}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {presets.map(p => (
              <PresetCard
                key={p.id}
                preset={p}
                isActive={activeStylePresetId === p.id}
                onActivate={() => activateStyle(p.id)}
                onEdit={() => setEditingStyle(p)}
                onDelete={() => deleteStyle(p.id)}
              />
            ))}
          </div>
          {presets.length === 0 ? <p className="text-sm text-neutral-500 text-center py-6">스타일 프리셋이 없습니다. 위자드로 빠르게 생성하세요.</p> : null}
        </div>
      ) : null}

      {/* ── Characters view ─── */}
      {view === "characters" ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs text-neutral-500">
              핵심 필드만 채우세요. 나머지는 AI가 자동으로 보완합니다.
            </p>
            <button
              onClick={() => { setCreatingChar(true); setEditingChar(null); }}
              className="rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium hover:bg-purple-500 transition"
            >
              새 캐릭터/주체
            </button>
          </div>

          {(creatingChar || editingChar) ? (
            <div className="rounded-xl border border-purple-900/50 bg-purple-950/10 p-4">
              <h3 className="text-sm font-semibold mb-3">{editingChar ? "캐릭터 수정" : "새 캐릭터/주체"}</h3>
              <SimpleCharacterForm
                initial={editingChar ?? {}}
                onSave={data => saveChar(data, editingChar?.id)}
                onCancel={() => { setCreatingChar(false); setEditingChar(null); }}
                saving={saving}
              />
            </div>
          ) : null}

          {characters.map(c => (
            <CharacterCard
              key={c.id}
              char={c}
              onEdit={() => { setEditingChar(c); setCreatingChar(false); }}
              onDelete={() => deleteChar(c.id)}
            />
          ))}
          {characters.length === 0 && !creatingChar ? (
            <p className="text-sm text-neutral-500 text-center py-6">등록된 캐릭터/주체가 없습니다.</p>
          ) : null}
        </div>
      ) : null}

      {/* ── Continuity (always at bottom, collapsed) ─── */}
      <ContinuitySection projectId={projectId} />
    </div>
  );
}
