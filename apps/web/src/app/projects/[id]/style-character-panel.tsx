"use client";

import { useEffect, useState, useCallback } from "react";
import { apiUrl } from "@/lib/api";

/* ── Types ─────────────────────────────────────────── */

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

/* ── Style Form ───────────────────────────────────── */

const STYLE_FIELDS: { key: keyof StylePreset; label: string; multi?: boolean; group?: string }[] = [
  { key: "name", label: "이름", group: "기본" },
  { key: "description", label: "설명", multi: true, group: "기본" },
  { key: "style_anchor", label: "스타일 앵커 (핵심 DNA)", multi: true, group: "앵커" },
  { key: "style_keywords", label: "스타일 키워드", multi: true, group: "앵커" },
  { key: "color_palette", label: "색상 팔레트", multi: true, group: "앵커" },
  { key: "color_temperature", label: "색온도 (예: warm 3200K)", group: "앵커" },
  { key: "rendering_style", label: "렌더링 스타일", multi: true, group: "렌더" },
  { key: "texture_quality", label: "텍스처 품질 (예: photorealistic 8k)", group: "렌더" },
  { key: "depth_style", label: "피사계 심도 (예: shallow DOF f/1.4)", group: "렌더" },
  { key: "camera_language", label: "카메라 언어", multi: true, group: "렌더" },
  { key: "lighting_rules", label: "조명 규칙", multi: true, group: "조명" },
  { key: "environment_rules", label: "환경 일관성 규칙", multi: true, group: "환경" },
  { key: "negative_rules", label: "네거티브 규칙", multi: true, group: "네거티브" },
  { key: "prompt_prefix", label: "프롬프트 접두사", multi: true, group: "프롬프트" },
  { key: "negative_prompt", label: "네거티브 프롬프트", multi: true, group: "네거티브" },
];

function StyleForm({
  initial,
  onSave,
  onCancel,
  saving,
}: {
  initial: Partial<StylePreset>;
  onSave: (data: Record<string, string>) => void;
  onCancel: () => void;
  saving: boolean;
}) {
  const [form, setForm] = useState<Record<string, string>>({});

  useEffect(() => {
    const f: Record<string, string> = {};
    for (const { key } of STYLE_FIELDS) {
      f[key] = (initial[key] as string) ?? "";
    }
    setForm(f);
  }, [initial]);

  let lastGroup = "";

  return (
    <div className="space-y-3">
      {STYLE_FIELDS.map(({ key, label, multi, group }) => {
        const showGroup = group && group !== lastGroup;
        if (group) lastGroup = group;
        return (
          <div key={key}>
            {showGroup && (
              <p className="text-[10px] font-bold text-neutral-600 uppercase tracking-wider pt-3 pb-1">{group}</p>
            )}
            <label className="block text-xs font-medium text-neutral-400 mb-1">{label}</label>
            {multi ? (
              <textarea
                value={form[key] ?? ""}
                onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                rows={2}
                className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none resize-none"
              />
            ) : (
              <input
                type="text"
                value={form[key] ?? ""}
                onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none"
              />
            )}
          </div>
        );
      })}
      <div className="flex gap-2 pt-2">
        <button onClick={() => onSave(form)} disabled={saving || !form.name?.trim()} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition">
          {saving ? "저장 중..." : "저장"}
        </button>
        <button onClick={onCancel} className="rounded-lg bg-neutral-700 px-4 py-2 text-sm font-medium hover:bg-neutral-600 transition">취소</button>
      </div>
    </div>
  );
}

/* ── Character Form ───────────────────────────────── */

const CHAR_FIELDS: { key: keyof CharacterProfile; label: string; multi?: boolean; group?: string }[] = [
  { key: "name", label: "이름", group: "기본" },
  { key: "role", label: "역할", group: "기본" },
  { key: "age_impression", label: "나이 인상", group: "기본" },
  { key: "description", label: "설명", multi: true, group: "기본" },
  { key: "body_type", label: "체형 (예: slim athletic, 170cm)", group: "외형" },
  { key: "skin_tone", label: "피부톤 (예: fair warm undertones)", group: "외형" },
  { key: "hair_description", label: "머리카락 상세 (색상, 길이, 스타일)", multi: true, group: "외형" },
  { key: "appearance", label: "전체 외형 (영어)", multi: true, group: "외형" },
  { key: "outfit", label: "의상 (영어)", multi: true, group: "외형" },
  { key: "facial_traits", label: "얼굴 특징 (영어)", multi: true, group: "외형" },
  { key: "signature_props", label: "시그니처 소품 (항상 착용)", multi: true, group: "일관성" },
  { key: "personality", label: "성격/특성", multi: true, group: "일관성" },
  { key: "pose_rules", label: "포즈 규칙 (영어)", multi: true, group: "일관성" },
  { key: "forbidden_changes", label: "변경 금지 사항 (레거시)", multi: true, group: "드리프트 방지" },
  { key: "forbidden_drift", label: "Forbidden Drift (구조화)", multi: true, group: "드리프트 방지" },
  { key: "visual_prompt", label: "Visual Prompt (컴파일 결과)", multi: true, group: "프롬프트" },
  { key: "voice_id", label: "TTS Voice ID", group: "오디오" },
];

function CharacterForm({
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

  useEffect(() => {
    const f: Record<string, string> = {};
    for (const { key } of CHAR_FIELDS) {
      f[key] = (initial[key] as string) ?? "";
    }
    setForm(f);
  }, [initial]);

  let lastGroup = "";

  return (
    <div className="space-y-3">
      {CHAR_FIELDS.map(({ key, label, multi, group }) => {
        const showGroup = group && group !== lastGroup;
        if (group) lastGroup = group;
        return (
          <div key={key}>
            {showGroup && (
              <p className="text-[10px] font-bold text-neutral-600 uppercase tracking-wider pt-3 pb-1">{group}</p>
            )}
            <label className="block text-xs font-medium text-neutral-400 mb-1">{label}</label>
            {multi ? (
              <textarea
                value={form[key] ?? ""}
                onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                rows={2}
                className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none resize-none"
              />
            ) : (
              <input
                type="text"
                value={form[key] ?? ""}
                onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none"
              />
            )}
          </div>
        );
      })}
      <div className="flex gap-2 pt-2">
        <button onClick={() => onSave(form)} disabled={saving || !form.name?.trim()} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition">
          {saving ? "저장 중..." : "저장"}
        </button>
        <button onClick={onCancel} className="rounded-lg bg-neutral-700 px-4 py-2 text-sm font-medium hover:bg-neutral-600 transition">취소</button>
      </div>
    </div>
  );
}

/* ── Style Preset Card ────────────────────────────── */

function StylePresetCard({
  preset,
  isActive,
  onActivate,
  onEdit,
  onDuplicate,
  onDelete,
}: {
  preset: StylePreset;
  isActive: boolean;
  onActivate: () => void;
  onEdit: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`rounded-lg border overflow-hidden ${isActive ? "border-blue-600 bg-blue-950/20" : "border-neutral-800 bg-neutral-900/50"}`}>
      <button onClick={() => setExpanded(!expanded)} className="w-full px-4 py-3 text-left">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            {isActive && <span className="shrink-0 w-2 h-2 rounded-full bg-blue-500" />}
            <span className="text-sm font-semibold text-neutral-200 truncate">{preset.name}</span>
            {preset.is_global && <span className="text-[10px] bg-neutral-700 text-neutral-400 px-1.5 py-px rounded-full">Global</span>}
          </div>
          <span className="text-xs text-neutral-600">{expanded ? "▲" : "▼"}</span>
        </div>
        {!expanded && (
          <p className="mt-1 text-xs text-neutral-500 truncate">
            {preset.style_anchor || preset.rendering_style || "No anchor set"}
          </p>
        )}
      </button>

      {expanded && (
        <div className="border-t border-neutral-800 px-4 py-3 space-y-2 text-xs">
          {preset.description && <p className="text-neutral-400">{preset.description}</p>}
          {preset.style_anchor && (
            <div className="rounded bg-blue-950/30 border border-blue-900/30 px-3 py-2">
              <span className="font-semibold text-blue-400">앵커: </span>
              <span className="text-blue-300">{preset.style_anchor}</span>
            </div>
          )}
          <div className="grid grid-cols-1 gap-2">
            {preset.style_keywords && <Field label="키워드" value={preset.style_keywords} />}
            {preset.color_palette && <Field label="색상 팔레트" value={preset.color_palette} color="text-amber-400/80" />}
            {preset.color_temperature && <Field label="색온도" value={preset.color_temperature} color="text-orange-400/80" />}
            {preset.rendering_style && <Field label="렌더링" value={preset.rendering_style} />}
            {preset.texture_quality && <Field label="텍스처" value={preset.texture_quality} />}
            {preset.depth_style && <Field label="심도" value={preset.depth_style} />}
            {preset.camera_language && <Field label="카메라" value={preset.camera_language} color="text-cyan-400/80" />}
            {preset.lighting_rules && <Field label="조명" value={preset.lighting_rules} color="text-yellow-400/80" />}
            {preset.environment_rules && <Field label="환경 규칙" value={preset.environment_rules} color="text-green-400/80" />}
            {preset.negative_rules && <Field label="네거티브" value={preset.negative_rules} color="text-red-400/80" />}
            {preset.prompt_prefix && <Field label="접두사" value={preset.prompt_prefix} color="text-blue-400/80" />}
            {preset.negative_prompt && <Field label="네거티브 프롬프트" value={preset.negative_prompt} color="text-red-400/60" />}
          </div>
          <div className="flex flex-wrap gap-2 pt-2">
            {!isActive && (
              <button onClick={onActivate} className="rounded bg-blue-700 px-3 py-1 text-[11px] font-medium hover:bg-blue-600 transition">적용</button>
            )}
            {!preset.is_global && (
              <button onClick={onEdit} className="rounded bg-neutral-700 px-3 py-1 text-[11px] font-medium hover:bg-neutral-600 transition">수정</button>
            )}
            <button onClick={onDuplicate} className="rounded bg-neutral-700 px-3 py-1 text-[11px] font-medium hover:bg-neutral-600 transition">복제</button>
            {!preset.is_global && (
              <button onClick={onDelete} className="rounded bg-red-900/50 px-3 py-1 text-[11px] font-medium text-red-400 hover:bg-red-800/50 transition">삭제</button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <span className="font-semibold text-neutral-500">{label}: </span>
      <span className={color || "text-neutral-300"}>{value}</span>
    </div>
  );
}

/* ── Character Card ───────────────────────────────── */

function CharacterCard({
  char,
  onEdit,
  onDelete,
}: {
  char: CharacterProfile;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 overflow-hidden">
      <button onClick={() => setExpanded(!expanded)} className="w-full px-4 py-3 text-left">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-sm font-semibold text-neutral-200 truncate">{char.name}</span>
            {char.role && <span className="text-[10px] bg-purple-900/50 text-purple-400 px-1.5 py-px rounded-full">{char.role}</span>}
            {char.age_impression && <span className="text-[10px] text-neutral-500">{char.age_impression}</span>}
          </div>
          <span className="text-xs text-neutral-600">{expanded ? "▲" : "▼"}</span>
        </div>
        {!expanded && <p className="mt-1 text-xs text-neutral-500 truncate">{char.body_type || char.description || "No details"}</p>}
      </button>

      {expanded && (
        <div className="border-t border-neutral-800 px-4 py-3 space-y-2 text-xs">
          {char.description && <p className="text-neutral-400">{char.description}</p>}
          <div className="grid grid-cols-1 gap-2">
            {char.body_type && <Field label="체형" value={char.body_type} />}
            {char.skin_tone && <Field label="피부톤" value={char.skin_tone} />}
            {char.hair_description && <Field label="머리카락" value={char.hair_description} />}
            {char.appearance && <Field label="외형" value={char.appearance} />}
            {char.outfit && <Field label="의상" value={char.outfit} />}
            {char.facial_traits && <Field label="얼굴" value={char.facial_traits} />}
            {char.signature_props && <Field label="시그니처 소품" value={char.signature_props} color="text-amber-400/80" />}
            {char.personality && <Field label="성격" value={char.personality} color="text-purple-400/80" />}
            {char.pose_rules && <Field label="포즈 규칙" value={char.pose_rules} color="text-cyan-400/80" />}
            {char.forbidden_drift && (
              <div className="rounded bg-red-950/20 border border-red-900/30 px-2 py-1">
                <span className="font-semibold text-red-400">Forbidden Drift: </span>
                <span className="text-red-300">{char.forbidden_drift}</span>
              </div>
            )}
            {!char.forbidden_drift && char.forbidden_changes && (
              <Field label="변경 금지" value={char.forbidden_changes} color="text-red-400/80" />
            )}
            {char.visual_prompt && <Field label="Visual Prompt" value={char.visual_prompt} color="text-blue-400/80" />}
            {char.voice_id && <Field label="Voice ID" value={char.voice_id} />}
          </div>
          <div className="flex gap-2 pt-2">
            <button onClick={onEdit} className="rounded bg-neutral-700 px-3 py-1 text-[11px] font-medium hover:bg-neutral-600 transition">수정</button>
            <button onClick={onDelete} className="rounded bg-red-900/50 px-3 py-1 text-[11px] font-medium text-red-400 hover:bg-red-800/50 transition">삭제</button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Continuity Panel ─────────────────────────────── */

const CONTINUITY_FIELDS: { key: keyof ContinuityProfile; label: string; multi?: boolean; hint?: string }[] = [
  { key: "color_palette_lock", label: "색상 팔레트 잠금", multi: true, hint: "모든 샷에서 유지할 색상 (예: deep navy, teal accent, warm gold highlights)" },
  { key: "lighting_anchor", label: "조명 앵커", multi: true, hint: "기준 조명 방향/스타일 (예: warm key from left 45°, cool fill, thin rim)" },
  { key: "color_temperature_range", label: "색온도 범위", hint: "허용 범위 (예: 3000K-4500K warm dominant)" },
  { key: "environment_consistency", label: "환경 일관성", multi: true, hint: "반복될 환경 요소 (예: always modern minimalist, clean surfaces, glass/metal)" },
  { key: "style_anchor_summary", label: "스타일 앵커 요약", multi: true, hint: "프로젝트 전체 스타일 DNA (활성 프리셋에서 자동 생성 가능)" },
  { key: "character_lock_notes", label: "캐릭터 잠금 노트", multi: true, hint: "전체 캐릭터 공통 잠금 규칙" },
  { key: "forbidden_global_drift", label: "글로벌 Forbidden Drift", multi: true, hint: "절대 변하면 안 되는 것들 (예: no cartoon style, no warm-to-cold shift)" },
  { key: "temporal_rules", label: "시간적 규칙", multi: true, hint: "시간 흐름에 따른 변화 규칙 (예: lighting gets warmer toward ending)" },
];

function ContinuityPanel({ projectId }: { projectId: string }) {
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
        for (const { key } of CONTINUITY_FIELDS) {
          f[key] = (data[key] as string) ?? "";
        }
        f.enabled = data.enabled ? "true" : "false";
        setForm(f);
      }
    } catch {}
  }, [projectId]);

  const fetchPreview = useCallback(async () => {
    try {
      const r = await fetch(apiUrl(`/api/projects/${projectId}/continuity/preview`));
      if (r.ok) setPreview(await r.json());
    } catch {}
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

  return (
    <div className="space-y-4">
      {/* Toggle + Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-neutral-200">Continuity 시스템</h3>
          {profile && (
            <button
              onClick={async () => {
                await fetch(apiUrl(`/api/projects/${projectId}/continuity`), {
                  method: "PUT",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ enabled: !profile.enabled }),
                });
                fetchProfile();
                fetchPreview();
              }}
              className={`text-[10px] px-2 py-0.5 rounded-full font-medium transition ${
                profile.enabled
                  ? "bg-emerald-900/40 text-emerald-400 border border-emerald-800"
                  : "bg-neutral-800 text-neutral-500 border border-neutral-700"
              }`}
            >
              {profile.enabled ? "활성" : "비활성"}
            </button>
          )}
        </div>
        {!editing && (
          <button onClick={() => setEditing(true)} className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium hover:bg-blue-500 transition">
            설정 편집
          </button>
        )}
      </div>

      {/* Preview (compiled context) */}
      {preview && !editing && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-3">
          <h4 className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">컴파일된 Continuity Context (프롬프트에 주입됨)</h4>
          {preview.style_anchor && (
            <div className="rounded bg-blue-950/30 border border-blue-900/30 px-3 py-2">
              <span className="text-[11px] font-semibold text-blue-400">STYLE ANCHOR: </span>
              <span className="text-xs text-blue-300">{preview.style_anchor}</span>
            </div>
          )}
          {preview.color_rules && <Field label="COLOR" value={preview.color_rules} color="text-amber-400/80" />}
          {preview.lighting_rules && <Field label="LIGHTING" value={preview.lighting_rules} color="text-yellow-400/80" />}
          {preview.environment_rules && <Field label="ENVIRONMENT" value={preview.environment_rules} color="text-green-400/80" />}
          {preview.character_anchors.length > 0 && (
            <div>
              <span className="text-[11px] font-semibold text-purple-400">CHARACTERS:</span>
              {preview.character_anchors.map((a, i) => (
                <p key={i} className="text-xs text-purple-300 ml-2">• {a}</p>
              ))}
            </div>
          )}
          {preview.forbidden_drift.length > 0 && (
            <div>
              <span className="text-[11px] font-semibold text-red-400">FORBIDDEN DRIFT:</span>
              {preview.forbidden_drift.map((d, i) => (
                <p key={i} className="text-xs text-red-300 ml-2">• {d}</p>
              ))}
            </div>
          )}
          <p className="text-[10px] text-neutral-600">Reference assets: {preview.reference_count}개</p>
        </div>
      )}

      {/* Edit form */}
      {editing && (
        <div className="rounded-xl border border-blue-900/30 bg-blue-950/10 p-4 space-y-3">
          {CONTINUITY_FIELDS.map(({ key, label, multi, hint }) => (
            <div key={key}>
              <label className="block text-xs font-medium text-neutral-400 mb-1">{label}</label>
              {hint && <p className="text-[10px] text-neutral-600 mb-1">{hint}</p>}
              {multi ? (
                <textarea
                  value={form[key] ?? ""}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                  rows={2}
                  className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none resize-none"
                />
              ) : (
                <input
                  type="text"
                  value={form[key] ?? ""}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none"
                />
              )}
            </div>
          ))}
          <div className="flex gap-2 pt-2">
            <button onClick={saveProfile} disabled={saving} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition">
              {saving ? "저장 중..." : "저장"}
            </button>
            <button onClick={() => setEditing(false)} className="rounded-lg bg-neutral-700 px-4 py-2 text-sm font-medium hover:bg-neutral-600 transition">취소</button>
          </div>
        </div>
      )}

      {!preview && !editing && (
        <p className="text-xs text-neutral-500 text-center py-4">Continuity 프로필을 설정하면 모든 Shot/Frame 생성에 일관성 규칙이 자동 주입됩니다.</p>
      )}
    </div>
  );
}

/* ── Main Panel ───────────────────────────────────── */

export default function StyleCharacterPanel({
  projectId,
  activeStylePresetId,
  onActiveStyleChange,
}: {
  projectId: string;
  activeStylePresetId: string | null;
  onActiveStyleChange: (id: string | null) => void;
}) {
  const [subTab, setSubTab] = useState<"style" | "character" | "continuity">("style");

  const [presets, setPresets] = useState<StylePreset[]>([]);
  const [characters, setCharacters] = useState<CharacterProfile[]>([]);
  const [editingStyle, setEditingStyle] = useState<StylePreset | null>(null);
  const [editingChar, setEditingChar] = useState<CharacterProfile | null>(null);
  const [creatingStyle, setCreatingStyle] = useState(false);
  const [creatingChar, setCreatingChar] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchPresets = useCallback(async () => {
    try {
      const r = await fetch(apiUrl(`/api/projects/${projectId}/styles`));
      if (r.ok) setPresets((await r.json()).presets);
    } catch {}
  }, [projectId]);

  const fetchCharacters = useCallback(async () => {
    try {
      const r = await fetch(apiUrl(`/api/projects/${projectId}/characters`));
      if (r.ok) setCharacters((await r.json()).characters);
    } catch {}
  }, [projectId]);

  useEffect(() => { fetchPresets(); fetchCharacters(); }, [fetchPresets, fetchCharacters]);

  /* ── Style actions ─────────────────────────────── */

  const saveStyle = async (data: Record<string, string>, id?: string) => {
    setSaving(true);
    try {
      const url = id
        ? `/api/projects/${projectId}/styles/${id}`
        : `/api/projects/${projectId}/styles`;
      const r = await fetch(url, {
        method: id ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (r.ok) {
        await fetchPresets();
        setEditingStyle(null);
        setCreatingStyle(false);
      }
    } finally { setSaving(false); }
  };

  const activateStyle = async (presetId: string) => {
    const r = await fetch(apiUrl(`/api/projects/${projectId}/active-style/${presetId}`), { method: "POST" });
    if (r.ok) onActiveStyleChange(presetId);
  };

  const duplicateStyle = async (presetId: string) => {
    const r = await fetch(apiUrl(`/api/projects/${projectId}/styles/${presetId}/duplicate`), { method: "POST" });
    if (r.ok) fetchPresets();
  };

  const deleteStyle = async (presetId: string) => {
    await fetch(apiUrl(`/api/projects/${projectId}/styles/${presetId}`), { method: "DELETE" });
    fetchPresets();
    if (activeStylePresetId === presetId) onActiveStyleChange(null);
  };

  /* ── Character actions ─────────────────────────── */

  const saveChar = async (data: Record<string, string>, id?: string) => {
    setSaving(true);
    try {
      const url = id
        ? `/api/projects/${projectId}/characters/${id}`
        : `/api/projects/${projectId}/characters`;
      const r = await fetch(url, {
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

  /* ── Render ────────────────────────────────────── */

  return (
    <div className="space-y-4">
      {/* Sub-tabs */}
      <div className="flex gap-1 border-b border-neutral-800">
        {([
          { key: "style" as const, label: "스타일 프리셋" },
          { key: "character" as const, label: "캐릭터 프로필" },
          { key: "continuity" as const, label: "Continuity" },
        ]).map((t) => (
          <button
            key={t.key}
            onClick={() => setSubTab(t.key)}
            className={`px-4 py-2 text-sm font-medium transition border-b-2 -mb-px ${
              subTab === t.key
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-neutral-500 hover:text-neutral-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {subTab === "style" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs text-neutral-500">{presets.length}개 프리셋 (Global 포함)</p>
            <button
              onClick={() => { setCreatingStyle(true); setEditingStyle(null); }}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium hover:bg-blue-500 transition"
            >
              새 프리셋
            </button>
          </div>

          {(creatingStyle || editingStyle) && (
            <div className="rounded-xl border border-blue-900/50 bg-blue-950/10 p-4">
              <h3 className="text-sm font-semibold mb-3">{editingStyle ? "프리셋 수정" : "새 프리셋"}</h3>
              <StyleForm
                initial={editingStyle ?? {}}
                onSave={(data) => saveStyle(data, editingStyle?.id)}
                onCancel={() => { setCreatingStyle(false); setEditingStyle(null); }}
                saving={saving}
              />
            </div>
          )}

          {presets.map((p) => (
            <StylePresetCard
              key={p.id}
              preset={p}
              isActive={activeStylePresetId === p.id}
              onActivate={() => activateStyle(p.id)}
              onEdit={() => { setEditingStyle(p); setCreatingStyle(false); }}
              onDuplicate={() => duplicateStyle(p.id)}
              onDelete={() => deleteStyle(p.id)}
            />
          ))}
          {presets.length === 0 && <p className="text-sm text-neutral-500 text-center py-6">스타일 프리셋이 없습니다.</p>}
        </div>
      )}

      {subTab === "character" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs text-neutral-500">{characters.length}개 캐릭터</p>
            <button
              onClick={() => { setCreatingChar(true); setEditingChar(null); }}
              className="rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium hover:bg-purple-500 transition"
            >
              새 캐릭터
            </button>
          </div>

          {(creatingChar || editingChar) && (
            <div className="rounded-xl border border-purple-900/50 bg-purple-950/10 p-4">
              <h3 className="text-sm font-semibold mb-3">{editingChar ? "캐릭터 수정" : "새 캐릭터"}</h3>
              <CharacterForm
                initial={editingChar ?? {}}
                onSave={(data) => saveChar(data, editingChar?.id)}
                onCancel={() => { setCreatingChar(false); setEditingChar(null); }}
                saving={saving}
              />
            </div>
          )}

          {characters.map((c) => (
            <CharacterCard
              key={c.id}
              char={c}
              onEdit={() => { setEditingChar(c); setCreatingChar(false); }}
              onDelete={() => deleteChar(c.id)}
            />
          ))}
          {characters.length === 0 && !creatingChar && (
            <p className="text-sm text-neutral-500 text-center py-6">등록된 캐릭터가 없습니다.</p>
          )}
        </div>
      )}

      {subTab === "continuity" && (
        <ContinuityPanel projectId={projectId} />
      )}
    </div>
  );
}
