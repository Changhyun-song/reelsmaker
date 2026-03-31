"use client";

import { useEffect, useState, useCallback, use } from "react";
import { apiUrl } from "@/lib/api";
import StyleCharacterPanel from "./style-character-panel";
import NextStepGuide from "./next-step-guide";
import AutoPilot from "./auto-pilot";
import WorkspaceLayout, {
  type WorkspaceSection,
  type StepStatus,
  WORKSPACE_STEPS,
} from "./workspace-layout";

import type {
  Project,
  ScriptSection,
  ScriptPlan,
  ScriptVersion,
  SceneData,
  ShotData,
  FrameData,
  AssetData,
  SubtitleSegmentData,
  SubtitleTrackData,
  TimelineSummaryData,
  TimelineListItem,
  Job,
  QAResultData,
  QASummaryData,
  CompiledPromptData,
  StylePreset,
} from "@/lib/types";
import { FORMAT_OPTIONS, TONE_SUGGESTIONS } from "@/lib/types";

import StudioPage from "@/features/studio/StudioPage";
import StylePickerModal from "@/features/style/StylePickerModal";
import VoicePicker from "@/features/voice/VoicePicker";
import TimelineEditor from "@/features/timeline/TimelineEditor";
import RenderPanel from "@/features/render/RenderPanel";
import CostDashboard from "@/features/studio/CostDashboard";
import PipelineInspector from "./pipeline-inspector";
import Badge from "@/components/ui/badge";
import Button from "@/components/ui/button";

const SCENE_STATUS_STYLES: Record<string, string> = {
  drafted: "bg-neutral-800 text-neutral-300",
  approved: "bg-emerald-900/50 text-emerald-400",
  needs_revision: "bg-orange-900/50 text-orange-400",
};

const STRATEGY_LABELS: Record<string, string> = {
  image_to_video: "I→V",
  direct_video: "Video",
  still_image: "Still",
  mixed: "Mixed",
};

const STRATEGY_COLORS: Record<string, string> = {
  image_to_video: "text-blue-400",
  direct_video: "text-purple-400",
  still_image: "text-amber-400",
  mixed: "text-cyan-400",
};

const FRAME_ROLE_STYLES: Record<string, { bg: string; border: string; label: string }> = {
  start: { bg: "bg-emerald-950/30", border: "border-emerald-700/50", label: "START" },
  middle: { bg: "bg-amber-950/30", border: "border-amber-700/50", label: "MIDDLE" },
  end: { bg: "bg-rose-950/30", border: "border-rose-700/50", label: "END" },
};

const FRAME_ROLE_BADGE: Record<string, string> = {
  start: "bg-emerald-900/60 text-emerald-300",
  middle: "bg-amber-900/60 text-amber-300",
  end: "bg-rose-900/60 text-rose-300",
};

/* ── Helpers ───────────────────────────────────────── */

function LockedSection({
  message,
  target,
  onNavigate,
}: {
  message: string;
  target: WorkspaceSection;
  onNavigate: (s: WorkspaceSection) => void;
}) {
  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-8 text-center">
      <p className="text-neutral-400">{message}</p>
      <button
        onClick={() => onNavigate(target)}
        className="mt-3 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium transition hover:bg-blue-500"
      >
        이전 단계로 이동
      </button>
    </div>
  );
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function StatusBadge({ status, styles }: { status: string; styles?: Record<string, string> }) {
  const map = styles ?? {
    draft: "bg-neutral-800 text-neutral-300",
    drafted: "bg-neutral-800 text-neutral-300",
    structuring: "bg-blue-900/50 text-blue-400",
    structured: "bg-emerald-900/50 text-emerald-400",
    approved: "bg-purple-900/50 text-purple-400",
    needs_revision: "bg-orange-900/50 text-orange-400",
  };
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${map[status] ?? "bg-neutral-800 text-neutral-400"}`}>
      {status}
    </span>
  );
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-2 w-full rounded-full bg-neutral-800">
      <div className="h-full rounded-full bg-blue-500 transition-all duration-500" style={{ width: `${Math.min(value, 100)}%` }} />
    </div>
  );
}

function JobStatusPanel({ job, label }: { job: Job; label: string }) {
  const isRunning = job.status === "running" || job.status === "queued";
  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-neutral-300">{label}</h2>
        <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${
          job.status === "completed" ? "bg-emerald-900/50 text-emerald-400"
          : job.status === "failed" ? "bg-red-900/50 text-red-400"
          : job.status === "running" ? "bg-blue-900/50 text-blue-400"
          : "bg-yellow-900/50 text-yellow-400"
        }`}>{job.status}</span>
      </div>
      {isRunning && (
        <div className="space-y-2">
          <ProgressBar value={job.progress} />
          <p className="text-xs text-neutral-500">{job.progress}%</p>
        </div>
      )}
      {job.status === "failed" && job.error_message && (
        <p className="text-sm text-red-300">{job.error_message}</p>
      )}
    </div>
  );
}

/* ── Script Plan Display ──────────────────────────── */

function ScriptPlanView({ plan }: { plan: ScriptPlan }) {
  const [showFull, setShowFull] = useState(false);
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-bold">{plan.title}</h3>
        <p className="mt-1 text-sm text-neutral-400">{plan.summary}</p>
        <div className="mt-2 flex gap-3 text-xs text-neutral-500">
          <span>약 {Math.round(plan.estimated_duration_sec)}초</span>
          <span>{plan.sections.length}개 섹션</span>
        </div>
      </div>
      <div className="rounded-lg border border-amber-900/50 bg-amber-950/20 p-4">
        <p className="text-xs font-semibold text-amber-400 mb-1">Hook (첫 3초)</p>
        <p className="text-sm text-neutral-200">{plan.hook}</p>
      </div>
      <div>
        <p className="text-xs font-semibold text-neutral-400 mb-2">내러티브 흐름</p>
        <ol className="space-y-1 pl-4 text-sm text-neutral-300 list-decimal">
          {plan.narrative_flow.map((beat, i) => <li key={i}>{beat}</li>)}
        </ol>
      </div>
      <div>
        <p className="text-xs font-semibold text-neutral-400 mb-3">섹션 구성</p>
        <div className="space-y-3">
          {plan.sections.map((sec, i) => (
            <div key={i} className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-neutral-200">{i + 1}. {sec.title}</span>
                <span className="text-xs text-neutral-500">~{sec.duration_sec}초</span>
              </div>
              {sec.description && <p className="text-xs text-neutral-500 mb-2">{sec.description}</p>}
              <div className="rounded bg-neutral-800 p-3 text-sm text-neutral-200 leading-relaxed">{sec.narration}</div>
              {sec.visual_notes && <p className="mt-2 text-xs text-blue-400/80"><span className="font-medium">Visual:</span> {sec.visual_notes}</p>}
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-lg border border-emerald-900/50 bg-emerald-950/20 p-4">
        <p className="text-xs font-semibold text-emerald-400 mb-1">엔딩 / CTA</p>
        <p className="text-sm text-neutral-200">{plan.ending_cta}</p>
      </div>
      <div>
        <button onClick={() => setShowFull(!showFull)} className="text-xs font-medium text-blue-400 hover:text-blue-300 transition">
          {showFull ? "▲ 전체 나레이션 숨기기" : "▼ 전체 나레이션 보기"}
        </button>
        {showFull && (
          <div className="mt-2 rounded-lg border border-neutral-800 bg-neutral-900/50 p-4 text-sm text-neutral-200 leading-relaxed whitespace-pre-wrap">{plan.narration_draft}</div>
        )}
      </div>
    </div>
  );
}

/* ── Prompt Preview Modal ─────────────────────────── */

function PromptPreviewModal({
  prompt,
  onClose,
}: {
  prompt: CompiledPromptData;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<"image" | "video" | "negative">("image");

  const tabs = [
    { key: "image" as const, label: "Image Prompt" },
    { key: "video" as const, label: "Video Prompt" },
    { key: "negative" as const, label: "Negative" },
  ];

  const content: Record<string, string> = {
    image: prompt.detailed_prompt,
    video: prompt.video_prompt,
    negative: prompt.negative_prompt,
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-2xl mx-4 rounded-xl border border-neutral-700 bg-neutral-900 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 pt-4 pb-2">
          <h3 className="text-sm font-bold text-neutral-100">Prompt Preview</h3>
          <button onClick={onClose} className="text-neutral-500 hover:text-neutral-200 text-lg">&times;</button>
        </div>

        <div className="px-5 pb-2">
          <p className="text-[11px] text-neutral-400 leading-relaxed mb-3 px-3 py-2 rounded bg-neutral-800/80 border border-neutral-700/50">
            <span className="font-semibold text-neutral-300">Concise:</span> {prompt.concise_prompt || "—"}
          </p>
        </div>

        <div className="px-5">
          <div className="flex gap-1 border-b border-neutral-700/50">
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`px-3 py-1.5 text-[11px] font-medium border-b-2 transition ${
                  tab === t.key
                    ? "border-blue-500 text-blue-400"
                    : "border-transparent text-neutral-500 hover:text-neutral-300"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="px-5 py-4">
          <div className="rounded-lg bg-neutral-800/60 border border-neutral-700/40 p-4 max-h-64 overflow-y-auto">
            <p className="text-xs text-neutral-200 leading-relaxed whitespace-pre-wrap font-mono">
              {content[tab] || "(비어있음)"}
            </p>
          </div>
        </div>

        {prompt.continuity_notes && (
          <div className="px-5 pb-3">
            <div className="rounded bg-cyan-950/30 border border-cyan-800/30 p-3">
              <p className="text-[10px] font-semibold text-cyan-400 mb-0.5">Continuity Notes</p>
              <p className="text-[11px] text-cyan-300/70">{prompt.continuity_notes}</p>
            </div>
          </div>
        )}

        {Object.keys(prompt.provider_options).length > 0 && (
          <div className="px-5 pb-4">
            <p className="text-[10px] font-semibold text-neutral-500 mb-1">Provider Options</p>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(prompt.provider_options).map(([k, v]) => (
                <span key={k} className="rounded bg-neutral-800 px-2 py-0.5 text-[10px] text-neutral-400">
                  <span className="text-neutral-500">{k}:</span> {String(v)}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Inline quality note editor ───────────────────── */

function QualityNoteEditor({ projectId, asset, onSaved }: { projectId: string; asset: AssetData; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(asset.quality_note || "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await fetch(apiUrl(`/api/projects/${projectId}/assets/${asset.id}/note`), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quality_note: val || null }),
      });
      onSaved();
      setEditing(false);
    } catch {} finally { setSaving(false); }
  };

  if (!editing) {
    return (
      <button
        onClick={(e) => { e.stopPropagation(); setEditing(true); }}
        className="text-[8px] text-neutral-500 hover:text-neutral-300 truncate max-w-[120px] text-left"
        title={asset.quality_note || "메모 추가"}
      >
        {asset.quality_note || "메모"}
      </button>
    );
  }
  return (
    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
      <input
        value={val}
        onChange={(e) => setVal(e.target.value)}
        placeholder="품질 메모..."
        maxLength={500}
        className="bg-neutral-900 border border-neutral-700 rounded px-1.5 py-0.5 text-[9px] text-neutral-200 w-24 focus:outline-none focus:border-blue-600"
        autoFocus
        onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setEditing(false); }}
      />
      <button onClick={save} disabled={saving} className="text-[8px] text-blue-400 hover:text-blue-300">
        {saving ? "..." : "OK"}
      </button>
    </div>
  );
}

/* ── Frame Spec Card ──────────────────────────────── */

function FrameSpecCard({
  frame,
  projectId,
  onRegenerate,
  busyId,
  pollJob,
}: {
  frame: FrameData;
  projectId: string;
  onRegenerate: (id: string) => void;
  busyId: string | null;
  pollJob: (job: Job | null, set: (j: Job | null) => void, done: () => void) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [promptPreview, setPromptPreview] = useState<CompiledPromptData | null>(null);
  const [loadingPrompt, setLoadingPrompt] = useState(false);
  const [imageJob, setImageJob] = useState<Job | null>(null);
  const [assets, setAssets] = useState<AssetData[]>([]);
  const [assetsLoaded, setAssetsLoaded] = useState(false);
  const [comparingIds, setComparingIds] = useState<string[]>([]);
  const [numVariants, setNumVariants] = useState(2);
  const [showBatchView, setShowBatchView] = useState(false);

  const isBusy = busyId === frame.id;
  const role = frame.frame_role || "start";
  const style = FRAME_ROLE_STYLES[role] || FRAME_ROLE_STYLES.start;
  const badge = FRAME_ROLE_BADGE[role] || FRAME_ROLE_BADGE.start;

  const isImageJobRunning = imageJob && imageJob.status !== "completed" && imageJob.status !== "failed";

  const fetchAssets = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/frames/${frame.id}/assets`));
      if (res.ok) {
        const data = await res.json();
        setAssets(data.assets);
      }
    } catch {} finally { setAssetsLoaded(true); }
  }, [projectId, frame.id]);

  useEffect(() => {
    if (open && !assetsLoaded) fetchAssets();
  }, [open, assetsLoaded, fetchAssets]);

  useEffect(() => {
    if (!imageJob || imageJob.status === "completed" || imageJob.status === "failed") return;
    const id = setInterval(() =>
      pollJob(imageJob, setImageJob, () => { fetchAssets(); }),
    2000);
    return () => clearInterval(id);
  }, [imageJob, pollJob, fetchAssets]);

  const fetchPromptPreview = async () => {
    setLoadingPrompt(true);
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/frames/${frame.id}/prompt-preview`));
      if (res.ok) setPromptPreview(await res.json());
    } catch {} finally { setLoadingPrompt(false); }
  };

  const generateImages = async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/frames/${frame.id}/images/generate`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ num_variants: numVariants }),
      });
      if (res.ok) setImageJob(await res.json());
    } catch {}
  };

  const readyAssets = assets.filter((a) => a.status === "ready" && a.url);
  const selectedAsset = readyAssets.find((a) => a.is_selected);

  const batches: Map<string, AssetData[]> = new Map();
  for (const a of readyAssets) {
    const key = a.generation_batch || `single-${a.id}`;
    if (!batches.has(key)) batches.set(key, []);
    batches.get(key)!.push(a);
  }

  const toggleCompare = (id: string) => {
    setComparingIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 4 ? [...prev, id] : prev
    );
  };

  return (
    <>
      {promptPreview && <PromptPreviewModal prompt={promptPreview} onClose={() => setPromptPreview(null)} />}
      <div className={`rounded ${style.border} border ${style.bg} overflow-hidden`}>
        <button onClick={() => setOpen(!open)} className="w-full px-2.5 py-1.5 text-left">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <span className={`inline-block rounded px-1.5 py-px text-[9px] font-bold tracking-wider ${badge}`}>
                {style.label}
              </span>
              <span className="text-[11px] text-neutral-300 truncate">
                {frame.composition ? frame.composition.slice(0, 60) + (frame.composition.length > 60 ? "..." : "") : "—"}
              </span>
              {readyAssets.length > 0 && (
                <span className="text-[8px] text-emerald-400 font-semibold">
                  IMG{readyAssets.length > 1 ? `×${readyAssets.length}` : ""}
                  {selectedAsset ? " ✓" : ""}
                </span>
              )}
              {frame.status === "generating" && (
                <span className="text-[8px] text-amber-400 font-semibold animate-pulse">GEN...</span>
              )}
            </div>
            <span className="text-neutral-600 text-[10px] shrink-0">{open ? "▲" : "▼"}</span>
          </div>
        </button>

        {open && (
          <div className="border-t border-neutral-700/30 px-2.5 py-2.5 space-y-1.5 text-[11px]">
            <div className="grid grid-cols-2 gap-x-3 gap-y-1">
              {frame.subject_position && (
                <div><span className="font-semibold text-neutral-500">Subject pos:</span> <span className="text-neutral-300">{frame.subject_position}</span></div>
              )}
              {frame.camera_angle && (
                <div><span className="font-semibold text-neutral-500">Camera:</span> <span className="text-neutral-300">{frame.camera_angle}</span></div>
              )}
              {frame.lens_feel && (
                <div><span className="font-semibold text-neutral-500">Lens:</span> <span className="text-neutral-300">{frame.lens_feel}</span></div>
              )}
              {frame.mood && (
                <div><span className="font-semibold text-neutral-500">Mood:</span> <span className="text-purple-400/80">{frame.mood}</span></div>
              )}
            </div>
            {frame.lighting && (
              <div><span className="font-semibold text-neutral-500">Lighting:</span> <span className="text-amber-300/70">{frame.lighting}</span></div>
            )}
            {frame.action_pose && (
              <div><span className="font-semibold text-neutral-500">Action:</span> <span className="text-neutral-300">{frame.action_pose}</span></div>
            )}
            {frame.background_description && (
              <div><span className="font-semibold text-neutral-500">Background:</span> <span className="text-neutral-400">{frame.background_description}</span></div>
            )}
            {frame.continuity_notes && (
              <div className="rounded bg-neutral-900/60 p-1.5 text-[10px]">
                <span className="font-semibold text-cyan-500/80">Continuity:</span> <span className="text-cyan-400/60">{frame.continuity_notes}</span>
              </div>
            )}
            {frame.forbidden_elements && (
              <div className="text-[10px]"><span className="font-semibold text-red-500/80">Forbidden:</span> <span className="text-red-400/60">{frame.forbidden_elements}</span></div>
            )}

            {/* ── Image variant gallery ── */}
            {readyAssets.length > 0 && (
              <div className="pt-1 space-y-1.5">
                <div className="flex items-center justify-between">
                  <p className="text-[9px] font-semibold text-neutral-500">
                    이미지 ({readyAssets.length}개{batches.size > 1 ? ` · ${batches.size}배치` : ""})
                    {!selectedAsset && readyAssets.length > 1 && <span className="text-amber-400 ml-1">선택 필요</span>}
                  </p>
                  {batches.size > 1 && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setShowBatchView(!showBatchView); }}
                      className="text-[8px] text-neutral-500 hover:text-neutral-300"
                    >
                      {showBatchView ? "그리드 보기" : "배치별 보기"}
                    </button>
                  )}
                </div>

                {/* Grid view: all variants flat */}
                {!showBatchView && (
                  <div className="grid grid-cols-3 gap-1.5">
                    {readyAssets.map((asset, idx) => {
                      const isSelected = asset.is_selected;
                      const isComparing = comparingIds.includes(asset.id);
                      return (
                        <div key={asset.id} className="relative group">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              fetch(apiUrl(`/api/projects/${projectId}/assets/${asset.id}/select`), { method: "PATCH" })
                                .then(() => fetchAssets());
                            }}
                            className={`relative w-full rounded overflow-hidden border-2 transition ${
                              isSelected ? "border-blue-500 ring-1 ring-blue-500/30" : "border-neutral-700 hover:border-neutral-500"
                            }`}
                          >
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={asset.url!} alt={`V${asset.version}`} className="w-full aspect-[16/9] object-cover" />
                            <span className={`absolute top-0.5 left-0.5 rounded px-1 py-px text-[7px] font-bold ${
                              isSelected ? "bg-blue-500 text-white" : "bg-neutral-900/80 text-neutral-400"
                            }`}>
                              {isSelected ? "✓ BEST" : `V${asset.version}`}
                            </span>
                          </button>
                          <div className="mt-0.5 flex items-center justify-between gap-0.5">
                            <QualityNoteEditor projectId={projectId} asset={asset} onSaved={fetchAssets} />
                            <button
                              onClick={(e) => { e.stopPropagation(); toggleCompare(asset.id); }}
                              className={`text-[7px] px-1 rounded ${isComparing ? "bg-yellow-700/60 text-yellow-200" : "text-neutral-600 hover:text-neutral-400"}`}
                              title="비교"
                            >비교</button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Batch view: grouped by generation_batch */}
                {showBatchView && (
                  <div className="space-y-2">
                    {Array.from(batches.entries()).map(([batchKey, items]) => (
                      <div key={batchKey} className="rounded border border-neutral-700/40 bg-neutral-900/30 p-1.5">
                        <p className="text-[8px] text-neutral-600 mb-1">
                          배치 {batchKey.slice(0, 16)}... · {items.length}개 · {formatDate(items[0].created_at)}
                        </p>
                        <div className="flex gap-1.5 overflow-x-auto">
                          {items.map((asset) => {
                            const isSelected = asset.is_selected;
                            return (
                              <div key={asset.id} className="relative shrink-0 group">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    fetch(apiUrl(`/api/projects/${projectId}/assets/${asset.id}/select`), { method: "PATCH" })
                                      .then(() => fetchAssets());
                                  }}
                                  className={`relative rounded overflow-hidden border-2 transition ${
                                    isSelected ? "border-blue-500 ring-1 ring-blue-500/30" : "border-neutral-700 hover:border-neutral-500"
                                  }`}
                                >
                                  {/* eslint-disable-next-line @next/next/no-img-element */}
                                  <img src={asset.url!} alt={`V${asset.version}`} className="w-20 h-12 object-cover" />
                                  <span className={`absolute bottom-0 right-0 rounded-tl px-1 py-px text-[7px] font-bold ${
                                    isSelected ? "bg-blue-500 text-white" : "bg-neutral-900/80 text-neutral-400"
                                  }`}>
                                    {isSelected ? "✓" : `V${asset.version}`}
                                  </span>
                                </button>
                                <div className="mt-0.5">
                                  <QualityNoteEditor projectId={projectId} asset={asset} onSaved={fetchAssets} />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Comparison overlay: side-by-side up to 4 */}
                {comparingIds.length >= 2 && (
                  <div className="rounded border border-yellow-700/40 bg-neutral-900/80 p-1.5">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-[8px] font-semibold text-yellow-400">비교 뷰 ({comparingIds.length}개)</p>
                      <button onClick={(e) => { e.stopPropagation(); setComparingIds([]); }} className="text-[8px] text-neutral-500 hover:text-neutral-300">닫기</button>
                    </div>
                    <div className={`grid gap-1 ${comparingIds.length <= 2 ? "grid-cols-2" : "grid-cols-2"}`}>
                      {comparingIds.map((cid) => {
                        const a = readyAssets.find((x) => x.id === cid);
                        if (!a) return null;
                        return (
                          <div key={cid} className="relative rounded overflow-hidden border border-neutral-700">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={a.url!} alt={`compare V${a.version}`} className="w-full object-contain bg-black max-h-32" />
                            <div className="absolute top-0.5 left-0.5 flex items-center gap-1">
                              <span className={`rounded px-1 py-px text-[7px] font-bold ${a.is_selected ? "bg-blue-500 text-white" : "bg-neutral-900/80 text-neutral-300"}`}>
                                V{a.version}{a.is_selected ? " ✓" : ""}
                              </span>
                            </div>
                            <div className="px-1.5 py-0.5 text-[8px] text-neutral-500 bg-neutral-900/60">
                              {a.quality_note || "—"}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {isImageJobRunning && imageJob && (
              <div className="pt-1">
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-neutral-700 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-green-500 h-full rounded-full transition-all" style={{ width: `${imageJob.progress}%` }} />
                  </div>
                  <span className="text-[9px] text-neutral-500">{imageJob.progress}%</span>
                </div>
              </div>
            )}
            {imageJob?.status === "failed" && (
              <p className="text-[9px] text-red-400">{imageJob.error_message || "이미지 생성 실패"}</p>
            )}

            <div className="flex items-center gap-2 pt-0.5 flex-wrap">
              <button
                onClick={(e) => { e.stopPropagation(); onRegenerate(frame.id); }}
                disabled={!!busyId}
                className="rounded bg-blue-700/80 px-2 py-0.5 text-[9px] font-medium hover:bg-blue-600 disabled:opacity-50 transition"
              >
                {isBusy ? "재생성 중..." : "Frame 재생성"}
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); fetchPromptPreview(); }}
                disabled={loadingPrompt}
                className="rounded bg-violet-700/80 px-2 py-0.5 text-[9px] font-medium hover:bg-violet-600 disabled:opacity-50 transition"
              >
                {loadingPrompt ? "로딩..." : "Prompt"}
              </button>
              <div className="flex items-center gap-1">
                <select
                  value={numVariants}
                  onChange={(e) => setNumVariants(Number(e.target.value))}
                  onClick={(e) => e.stopPropagation()}
                  className="bg-neutral-800 border border-neutral-700 rounded text-[9px] text-neutral-300 px-1 py-0.5"
                >
                  <option value={2}>2개</option>
                  <option value={3}>3개</option>
                  <option value={4}>4개</option>
                </select>
                <button
                  onClick={(e) => { e.stopPropagation(); generateImages(); }}
                  disabled={!!isImageJobRunning}
                  className="rounded bg-green-700/80 px-2 py-0.5 text-[9px] font-medium hover:bg-green-600 disabled:opacity-50 transition"
                >
                  {isImageJobRunning ? "생성 중..." : readyAssets.length > 0 ? "추가 생성" : "이미지 생성"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

/* ── Voice track type ─────────────────────────────── */

interface VoiceTrackData {
  id: string;
  shot_id: string | null;
  text: string;
  voice_id: string;
  speaker_name: string | null;
  language: string;
  speed: number;
  emotion: string | null;
  duration_ms: number | null;
  timestamps: Record<string, unknown> | null;
  tts_metadata: Record<string, unknown> | null;
  asset_id: string | null;
  status: string;
  is_selected: boolean;
  created_at: string;
}

interface VoicePresetOption {
  id: string;
  name: string;
  language: string;
}

/* ── Shot Card (with nested frames + video + TTS) ── */

const VIDEO_MODE_LABELS: Record<string, { label: string; desc: string }> = {
  auto: { label: "Auto", desc: "프레임 이미지가 있으면 I→V, 없으면 T→V" },
  image_to_video: { label: "Image → Video", desc: "start/end 프레임 이미지 기반" },
  text_to_video: { label: "Text → Video", desc: "프롬프트 텍스트 기반" },
};

function ShotCard({
  shot,
  projectId,
  onRegenerate,
  busyId,
  pollJob,
}: {
  shot: ShotData;
  projectId: string;
  onRegenerate: (id: string) => void;
  busyId: string | null;
  pollJob: (job: Job | null, set: (j: Job | null) => void, done: () => void) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const isBusy = busyId === shot.id;

  /* ── Frame state ── */
  const [frames, setFrames] = useState<FrameData[]>([]);
  const [frameJob, setFrameJob] = useState<Job | null>(null);
  const [regenFrameId, setRegenFrameId] = useState<string | null>(null);
  const [framesLoaded, setFramesLoaded] = useState(false);

  /* ── Video state ── */
  const [videoJob, setVideoJob] = useState<Job | null>(null);
  const [videoAssets, setVideoAssets] = useState<AssetData[]>([]);
  const [videoAssetsLoaded, setVideoAssetsLoaded] = useState(false);
  const [videoMode, setVideoMode] = useState<string>("auto");
  const [videoNumVariants, setVideoNumVariants] = useState(1);
  const [videoComparingIds, setVideoComparingIds] = useState<string[]>([]);

  /* ── TTS state ── */
  const [ttsJob, setTtsJob] = useState<Job | null>(null);
  const [voiceTracks, setVoiceTracks] = useState<VoiceTrackData[]>([]);
  const [voiceTracksLoaded, setVoiceTracksLoaded] = useState(false);
  const [voices, setVoices] = useState<VoicePresetOption[]>([]);
  const [selectedVoice, setSelectedVoice] = useState("narrator-ko-male");
  const [ttsSpeed, setTtsSpeed] = useState(1.0);
  const [ttsAudioUrl, setTtsAudioUrl] = useState<string | null>(null);

  const isFrameJobRunning = frameJob && frameJob.status !== "completed" && frameJob.status !== "failed";
  const isVideoJobRunning = videoJob && videoJob.status !== "completed" && videoJob.status !== "failed";
  const isTtsJobRunning = ttsJob && ttsJob.status !== "completed" && ttsJob.status !== "failed";

  const fetchFrames = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/shots/${shot.id}/frames`));
      if (res.ok) { setFrames((await res.json()).frames); }
    } catch {} finally { setFramesLoaded(true); }
  }, [projectId, shot.id]);

  const fetchVideoAssets = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/shots/${shot.id}/video/assets`));
      if (res.ok) { setVideoAssets((await res.json()).assets); }
    } catch {} finally { setVideoAssetsLoaded(true); }
  }, [projectId, shot.id]);

  const fetchVoiceTracks = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/shots/${shot.id}/tts`));
      if (res.ok) {
        const data = await res.json();
        setVoiceTracks(data.voice_tracks);
      }
    } catch {} finally { setVoiceTracksLoaded(true); }
  }, [projectId, shot.id]);

  const fetchAudioUrl = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/shots/${shot.id}/tts/audio-url`));
      if (res.ok) {
        const data = await res.json();
        setTtsAudioUrl(data.url);
      }
    } catch {}
  }, [projectId, shot.id]);

  const fetchVoices = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/voices`));
      if (res.ok) setVoices(await res.json());
    } catch {}
  }, [projectId]);

  useEffect(() => {
    if (open && !framesLoaded) fetchFrames();
    if (open && !videoAssetsLoaded) fetchVideoAssets();
    if (open && !voiceTracksLoaded) { fetchVoiceTracks(); fetchAudioUrl(); fetchVoices(); }
  }, [open, framesLoaded, fetchFrames, videoAssetsLoaded, fetchVideoAssets, voiceTracksLoaded, fetchVoiceTracks, fetchAudioUrl, fetchVoices]);

  useEffect(() => {
    if (!frameJob || frameJob.status === "completed" || frameJob.status === "failed") return;
    const id = setInterval(() =>
      pollJob(frameJob, setFrameJob, () => { fetchFrames(); setRegenFrameId(null); }),
    2000);
    return () => clearInterval(id);
  }, [frameJob, pollJob, fetchFrames]);

  useEffect(() => {
    if (!videoJob || videoJob.status === "completed" || videoJob.status === "failed") return;
    const id = setInterval(() =>
      pollJob(videoJob, setVideoJob, () => { fetchVideoAssets(); }),
    2500);
    return () => clearInterval(id);
  }, [videoJob, pollJob, fetchVideoAssets]);

  useEffect(() => {
    if (!ttsJob || ttsJob.status === "completed" || ttsJob.status === "failed") return;
    const id = setInterval(() =>
      pollJob(ttsJob, setTtsJob, () => { fetchVoiceTracks(); fetchAudioUrl(); }),
    2000);
    return () => clearInterval(id);
  }, [ttsJob, pollJob, fetchVoiceTracks, fetchAudioUrl]);

  const generateFrames = async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/shots/${shot.id}/frames/generate`), { method: "POST" });
      if (res.ok) setFrameJob(await res.json());
    } catch {}
  };

  const regenerateFrame = async (frameId: string) => {
    setRegenFrameId(frameId);
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/frames/${frameId}/regenerate`), { method: "POST" });
      if (res.ok) setFrameJob(await res.json());
      else setRegenFrameId(null);
    } catch { setRegenFrameId(null); }
  };

  const generateVideo = async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/shots/${shot.id}/video/generate`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: videoMode, num_variants: videoNumVariants }),
      });
      if (res.ok) setVideoJob(await res.json());
    } catch {}
  };

  const toggleVideoCompare = (id: string) => {
    setVideoComparingIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 3 ? [...prev, id] : prev
    );
  };

  const generateTts = async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/shots/${shot.id}/tts/generate`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          voice_id: selectedVoice,
          speed: ttsSpeed,
          language: voices.find((v) => v.id === selectedVoice)?.language || "ko",
        }),
      });
      if (res.ok) setTtsJob(await res.json());
    } catch {}
  };

  const readyVideos = videoAssets.filter((a) => a.status === "ready" && a.url);
  const selectedVideo = readyVideos.find((v) => v.is_selected) || readyVideos[0] || null;
  const selectedTrack = voiceTracks.find((t) => t.is_selected && t.status === "ready") || voiceTracks.find((t) => t.status === "ready") || null;

  const selectAsset = async (assetId: string) => {
    try {
      await fetch(apiUrl(`/api/projects/${projectId}/assets/${assetId}/select`), { method: "PATCH" });
      fetchVideoAssets();
    } catch {}
  };

  const selectVoiceTrack = async (trackId: string) => {
    try {
      await fetch(apiUrl(`/api/projects/${projectId}/voice-tracks/${trackId}/select`), { method: "PATCH" });
      fetchVoiceTracks();
      fetchAudioUrl();
    } catch {}
  };

  return (
    <div className="rounded border border-neutral-700/60 bg-neutral-800/40 overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full px-3 py-2 text-left">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="shrink-0 text-[10px] font-mono text-neutral-500 w-4 text-right">
              {shot.order_index + 1}
            </span>
            <span className="text-xs font-semibold text-neutral-300 truncate">
              {shot.shot_type || "shot"} · {shot.camera_framing || "—"}
            </span>
            {shot.camera_movement && shot.camera_movement !== "static" && (
              <span className="text-[10px] text-cyan-400/70">{shot.camera_movement}</span>
            )}
            {(shot.status === "video_ready" || readyVideos.length > 0) && (
              <span className="text-[8px] font-bold text-emerald-400">VID{readyVideos.length > 1 ? `×${readyVideos.length}` : ""}</span>
            )}
            {shot.status === "generating_video" && (
              <span className="text-[8px] font-bold text-amber-400 animate-pulse">VID...</span>
            )}
            {selectedTrack && <span className="text-[8px] font-bold text-pink-400">TTS{voiceTracks.filter(t => t.status === "ready").length > 1 ? `×${voiceTracks.filter(t => t.status === "ready").length}` : ""}</span>}
            {isTtsJobRunning && <span className="text-[8px] font-bold text-pink-300 animate-pulse">TTS...</span>}
          </div>
          <div className="flex items-center gap-2 shrink-0 text-[10px]">
            {shot.asset_strategy && (
              <span className={`font-medium ${STRATEGY_COLORS[shot.asset_strategy] ?? "text-neutral-400"}`}>
                {STRATEGY_LABELS[shot.asset_strategy] ?? shot.asset_strategy}
              </span>
            )}
            <span className="text-neutral-500">
              {shot.duration_sec ? `${shot.duration_sec}s` : ""}
            </span>
            <span className="text-neutral-600">{open ? "▲" : "▼"}</span>
          </div>
        </div>
        {!open && shot.subject && (
          <p className="mt-0.5 ml-6 text-[11px] text-neutral-500 truncate">{shot.subject}</p>
        )}
      </button>

      {open && (
        <div className="border-t border-neutral-700/40 px-3 py-3 space-y-2 text-xs">
          {shot.purpose && (
            <div><span className="font-semibold text-neutral-400">Purpose:</span> <span className="text-neutral-300">{shot.purpose}</span></div>
          )}
          {shot.subject && (
            <div><span className="font-semibold text-neutral-400">Subject:</span> <span className="text-neutral-300">{shot.subject}</span></div>
          )}
          {shot.environment && (
            <div><span className="font-semibold text-neutral-400">Environment:</span> <span className="text-neutral-300">{shot.environment}</span></div>
          )}
          {shot.emotion && (
            <div><span className="font-semibold text-neutral-400">Emotion:</span> <span className="text-purple-400">{shot.emotion}</span></div>
          )}
          {shot.narration_segment && (
            <div className="rounded bg-neutral-900/80 p-2 text-neutral-300 leading-relaxed">
              {shot.narration_segment}
            </div>
          )}
          {shot.description && (
            <div><span className="font-semibold text-blue-400/80">Prompt:</span> <span className="text-blue-300/70">{shot.description}</span></div>
          )}
          <div className="flex items-center gap-3 text-[10px] text-neutral-500">
            <span>{shot.transition_in} → {shot.transition_out}</span>
            <span>{shot.camera_framing} / {shot.camera_movement}</span>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); onRegenerate(shot.id); }}
            disabled={!!busyId}
            className="rounded bg-blue-700/80 px-2.5 py-1 text-[10px] font-medium hover:bg-blue-600 disabled:opacity-50 transition"
          >
            {isBusy ? "재생성 중..." : "Shot 재생성"}
          </button>

          {/* ── Video section ──────────────────── */}
          <div className="border-t border-neutral-700/30 pt-3 mt-2">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-semibold text-neutral-400">
                Video Clip
                {readyVideos.length > 0 && (
                  <span className="ml-1 text-emerald-400">
                    ({readyVideos.length}개{selectedVideo?.is_selected ? " · 선택됨" : ""})
                  </span>
                )}
              </p>
              <div className="flex items-center gap-1.5">
                <select
                  value={videoMode}
                  onChange={(e) => setVideoMode(e.target.value)}
                  className="bg-neutral-800 border border-neutral-700 rounded text-[9px] text-neutral-300 px-1.5 py-0.5"
                >
                  {Object.entries(VIDEO_MODE_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>{v.label}</option>
                  ))}
                </select>
                <select
                  value={videoNumVariants}
                  onChange={(e) => setVideoNumVariants(Number(e.target.value))}
                  className="bg-neutral-800 border border-neutral-700 rounded text-[9px] text-neutral-300 px-1 py-0.5"
                >
                  <option value={1}>1개</option>
                  <option value={2}>2개</option>
                  <option value={3}>3개</option>
                </select>
                <button
                  onClick={generateVideo}
                  disabled={!!isVideoJobRunning}
                  className="rounded bg-teal-700 px-2.5 py-0.5 text-[9px] font-medium hover:bg-teal-600 disabled:opacity-50 transition"
                >
                  {isVideoJobRunning ? "생성 중..." : readyVideos.length > 0 ? "추가 생성" : "비디오 생성"}
                </button>
              </div>
            </div>
            <p className="text-[9px] text-neutral-600 mb-2">{VIDEO_MODE_LABELS[videoMode]?.desc}</p>

            {isVideoJobRunning && videoJob && (
              <div className="mb-2">
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-neutral-700 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-teal-500 h-full rounded-full transition-all" style={{ width: `${videoJob.progress}%` }} />
                  </div>
                  <span className="text-[9px] text-neutral-500">{videoJob.progress}%</span>
                </div>
              </div>
            )}
            {videoJob?.status === "failed" && (
              <p className="text-[10px] text-red-400 mb-2">{videoJob.error_message || "비디오 생성 실패"}</p>
            )}

            {/* Selected video preview */}
            {selectedVideo && (
              <div className="rounded border border-neutral-700/50 overflow-hidden mb-2">
                {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                <video
                  key={selectedVideo.id}
                  src={selectedVideo.url!}
                  controls
                  className="w-full max-h-48 bg-black"
                  preload="metadata"
                />
                <div className="px-2 py-1 flex items-center justify-between text-[9px] text-neutral-500 bg-neutral-900/60">
                  <div className="flex items-center gap-2">
                    {selectedVideo.metadata_ && (
                      <>
                        <span>{String(selectedVideo.metadata_.duration_sec || "")}s</span>
                        <span>{String(selectedVideo.metadata_.width || "")}×{String(selectedVideo.metadata_.height || "")}</span>
                        <span className={`font-medium ${
                          selectedVideo.metadata_.mode === "image_to_video" ? "text-blue-400" : "text-amber-400"
                        }`}>
                          {selectedVideo.metadata_.mode === "image_to_video" ? "I→V" : "T→V"}
                        </span>
                      </>
                    )}
                    {selectedVideo.is_selected && <span className="text-teal-400 font-bold">BEST</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    {selectedVideo.quality_note && <span className="text-neutral-600 truncate max-w-[80px]">{selectedVideo.quality_note}</span>}
                    <span className="text-neutral-700">V{selectedVideo.version}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Video variant list with comparison */}
            {readyVideos.length > 0 && (
              <div className="mb-2 space-y-1.5">
                <div className="flex items-center justify-between">
                  <p className="text-[9px] font-semibold text-neutral-500">
                    비디오 variant ({readyVideos.length}개)
                    {!selectedVideo?.is_selected && readyVideos.length > 1 && <span className="text-amber-400 ml-1">선택 필요</span>}
                  </p>
                  {readyVideos.length > 1 && (
                    <span className="text-[8px] text-neutral-600">클릭=선택 · 비교=나란히 보기</span>
                  )}
                </div>
                <div className="space-y-1">
                  {readyVideos.map((v) => {
                    const meta = v.metadata_ || {};
                    const isComparing = videoComparingIds.includes(v.id);
                    return (
                      <div key={v.id} className={`flex items-center gap-2 rounded px-2 py-1.5 text-[9px] transition border ${
                        v.is_selected ? "bg-teal-900/40 border-teal-600/50 text-teal-300" : "bg-neutral-900/30 border-neutral-700/30 text-neutral-400 hover:border-neutral-600"
                      }`}>
                        <button
                          onClick={(e) => { e.stopPropagation(); selectAsset(v.id); }}
                          className="flex items-center gap-2 flex-1 min-w-0 text-left"
                        >
                          <span className={`font-mono font-bold w-6 shrink-0 ${v.is_selected ? "text-teal-300" : "text-neutral-500"}`}>
                            {v.is_selected ? "✓" : `V${v.version}`}
                          </span>
                          <span>{String(meta.duration_sec || "?")}s</span>
                          <span className={meta.mode === "image_to_video" ? "text-blue-400" : "text-amber-400"}>
                            {meta.mode === "image_to_video" ? "I→V" : "T→V"}
                          </span>
                          <span className="text-neutral-600">{formatDate(v.created_at)}</span>
                          {v.generation_batch && <span className="text-neutral-700 text-[7px]">{v.generation_batch.slice(0, 12)}</span>}
                        </button>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <QualityNoteEditor projectId={projectId} asset={v} onSaved={fetchVideoAssets} />
                          {readyVideos.length > 1 && (
                            <button
                              onClick={(e) => { e.stopPropagation(); toggleVideoCompare(v.id); }}
                              className={`px-1 py-0.5 rounded text-[7px] ${isComparing ? "bg-yellow-700/60 text-yellow-200" : "text-neutral-600 hover:text-neutral-400"}`}
                            >비교</button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Side-by-side video comparison */}
            {videoComparingIds.length >= 2 && (
              <div className="rounded border border-yellow-700/40 bg-neutral-900/80 p-2 mb-2">
                <div className="flex items-center justify-between mb-1.5">
                  <p className="text-[8px] font-semibold text-yellow-400">비디오 비교 ({videoComparingIds.length}개)</p>
                  <button onClick={(e) => { e.stopPropagation(); setVideoComparingIds([]); }} className="text-[8px] text-neutral-500 hover:text-neutral-300">닫기</button>
                </div>
                <div className={`grid gap-2 ${videoComparingIds.length === 2 ? "grid-cols-2" : "grid-cols-1"}`}>
                  {videoComparingIds.map((cid) => {
                    const va = readyVideos.find((x) => x.id === cid);
                    if (!va) return null;
                    const meta = va.metadata_ || {};
                    return (
                      <div key={cid} className="rounded border border-neutral-700 overflow-hidden">
                        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                        <video src={va.url!} controls className="w-full max-h-36 bg-black" preload="metadata" />
                        <div className="px-1.5 py-1 bg-neutral-900/60 flex items-center justify-between text-[8px]">
                          <div className="flex items-center gap-1.5 text-neutral-400">
                            <span className={`font-bold ${va.is_selected ? "text-teal-400" : "text-neutral-500"}`}>
                              V{va.version}{va.is_selected ? " ✓" : ""}
                            </span>
                            <span>{String(meta.duration_sec || "?")}s</span>
                            <span className={meta.mode === "image_to_video" ? "text-blue-400" : "text-amber-400"}>
                              {meta.mode === "image_to_video" ? "I→V" : "T→V"}
                            </span>
                          </div>
                          <button
                            onClick={(e) => { e.stopPropagation(); selectAsset(va.id); }}
                            className="text-[8px] text-teal-500 hover:text-teal-300 font-medium"
                          >이걸로 선택</button>
                        </div>
                        {va.quality_note && <p className="px-1.5 py-0.5 text-[7px] text-neutral-600 bg-neutral-950/40">{va.quality_note}</p>}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* ── TTS section ───────────────────── */}
          <div className="border-t border-neutral-700/30 pt-3 mt-2">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-semibold text-neutral-400">Narration TTS</p>
              <div className="flex items-center gap-1.5">
                {voices.length > 0 && (
                  <select
                    value={selectedVoice}
                    onChange={(e) => setSelectedVoice(e.target.value)}
                    className="bg-neutral-800 border border-neutral-700 rounded text-[9px] text-neutral-300 px-1.5 py-0.5"
                  >
                    {voices.map((v) => (
                      <option key={v.id} value={v.id}>{v.name}</option>
                    ))}
                  </select>
                )}
                <select
                  value={ttsSpeed}
                  onChange={(e) => setTtsSpeed(parseFloat(e.target.value))}
                  className="bg-neutral-800 border border-neutral-700 rounded text-[9px] text-neutral-300 px-1.5 py-0.5 w-16"
                >
                  <option value={0.75}>0.75x</option>
                  <option value={1.0}>1.0x</option>
                  <option value={1.25}>1.25x</option>
                  <option value={1.5}>1.5x</option>
                </select>
                <button
                  onClick={generateTts}
                  disabled={!!isTtsJobRunning || !shot.narration_segment}
                  className="rounded bg-pink-700 px-2.5 py-0.5 text-[9px] font-medium hover:bg-pink-600 disabled:opacity-50 transition"
                >
                  {isTtsJobRunning ? "생성 중..." : selectedTrack ? "TTS 재생성" : "TTS 생성"}
                </button>
              </div>
            </div>
            {!shot.narration_segment && (
              <p className="text-[9px] text-neutral-500 mb-2">나레이션 텍스트가 없습니다.</p>
            )}

            {isTtsJobRunning && ttsJob && (
              <div className="mb-2">
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-neutral-700 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-pink-500 h-full rounded-full transition-all" style={{ width: `${ttsJob.progress}%` }} />
                  </div>
                  <span className="text-[9px] text-neutral-500">{ttsJob.progress}%</span>
                </div>
              </div>
            )}
            {ttsJob?.status === "failed" && (
              <p className="text-[10px] text-red-400 mb-2">{ttsJob.error_message || "TTS 생성 실패"}</p>
            )}

            {ttsAudioUrl && selectedTrack && (
              <div className="rounded border border-neutral-700/50 overflow-hidden mb-2 bg-neutral-900/60">
                {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                <audio
                  src={ttsAudioUrl}
                  controls
                  className="w-full h-8"
                  preload="metadata"
                />
                <div className="px-2 py-1 flex items-center justify-between text-[9px] text-neutral-500">
                  <div className="flex items-center gap-2">
                    <span>{selectedTrack.voice_id}</span>
                    {selectedTrack.duration_ms && <span>{(selectedTrack.duration_ms / 1000).toFixed(1)}s</span>}
                    <span>speed: {selectedTrack.speed}x</span>
                    {selectedTrack.is_selected && <span className="text-pink-400 font-medium">선택됨</span>}
                  </div>
                  <span className="text-neutral-600">{selectedTrack.language}</span>
                </div>
              </div>
            )}

            {voiceTracks.filter(t => t.status === "ready").length > 1 && (
              <div className="mb-1">
                <p className="text-[9px] font-semibold text-neutral-500 mb-1">
                  TTS variant ({voiceTracks.filter(t => t.status === "ready").length}개) · 클릭하여 선택
                </p>
                <div className="space-y-0.5">
                  {voiceTracks.filter(t => t.status === "ready").map((t, idx) => {
                    const isActive = t.is_selected || (!voiceTracks.some(vt => vt.is_selected && vt.status === "ready") && idx === 0);
                    return (
                      <button
                        key={t.id}
                        onClick={(e) => { e.stopPropagation(); selectVoiceTrack(t.id); }}
                        className={`w-full flex items-center justify-between rounded px-2 py-1 text-[9px] transition ${
                          t.is_selected ? "bg-pink-900/40 border border-pink-600/50 text-pink-300" : isActive ? "bg-neutral-800/60 border border-neutral-700/40 text-neutral-300" : "bg-neutral-900/30 border border-transparent text-neutral-500 hover:border-neutral-700/40"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-mono">V{idx + 1}</span>
                          <span>{t.voice_id}</span>
                          <span>{t.duration_ms ? `${(t.duration_ms / 1000).toFixed(1)}s` : "—"}</span>
                          <span>{t.speed}x</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-neutral-600">{formatDate(t.created_at)}</span>
                          {t.is_selected && <span className="text-pink-400 font-bold">✓</span>}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* ── Frames section ─────────────────── */}
          <div className="border-t border-neutral-700/30 pt-3 mt-2">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-semibold text-neutral-400">Frame Specs</p>
              <button
                onClick={generateFrames}
                disabled={!!isFrameJobRunning}
                className="rounded bg-indigo-700 px-2.5 py-0.5 text-[9px] font-medium hover:bg-indigo-600 disabled:opacity-50 transition"
              >
                {isFrameJobRunning ? "생성 중..." : frames.length > 0 ? "Frame 재생성" : "Frame 생성"}
              </button>
            </div>

            {isFrameJobRunning && frameJob && (
              <div className="mb-2">
                <ProgressBar value={frameJob.progress} />
                <p className="text-[9px] text-neutral-500 mt-0.5">{frameJob.progress}%</p>
              </div>
            )}
            {frameJob?.status === "failed" && (
              <p className="text-[10px] text-red-400 mb-2">{frameJob.error_message || "Frame 생성 실패"}</p>
            )}

            {frames.length > 0 ? (
              <div className="space-y-1">
                {frames.map((f) => (
                  <FrameSpecCard key={f.id} frame={f} projectId={projectId} onRegenerate={regenerateFrame} busyId={regenFrameId} pollJob={pollJob} />
                ))}
              </div>
            ) : (
              framesLoaded && !isFrameJobRunning && (
                <p className="text-[10px] text-neutral-500 text-center py-2">Frame 스펙이 없습니다.</p>
              )
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Subtitle Panel ─────────────────────────────────── */

function SubtitlePanel({
  projectId,
  scriptVersionId,
  pollJob,
}: {
  projectId: string;
  scriptVersionId: string;
  pollJob: (job: Job | null, set: (j: Job | null) => void, done: () => void) => Promise<void>;
}) {
  const [subJob, setSubJob] = useState<Job | null>(null);
  const [tracks, setTracks] = useState<SubtitleTrackData[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [srtPreview, setSrtPreview] = useState<string | null>(null);
  const [previewTrackId, setPreviewTrackId] = useState<string | null>(null);

  const [maxChars, setMaxChars] = useState(35);
  const [maxLines, setMaxLines] = useState(2);
  const [gapMs, setGapMs] = useState(100);
  const [subFormat, setSubFormat] = useState("srt");

  const isRunning = subJob && subJob.status !== "completed" && subJob.status !== "failed";

  const fetchTracks = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/subtitles?script_version_id=${scriptVersionId}`));
      if (res.ok) {
        const data = await res.json();
        setTracks(data.tracks);
      }
    } catch {} finally { setLoaded(true); }
  }, [projectId, scriptVersionId]);

  useEffect(() => { fetchTracks(); }, [fetchTracks]);

  useEffect(() => {
    if (!subJob || subJob.status === "completed" || subJob.status === "failed") return;
    const id = setInterval(() =>
      pollJob(subJob, setSubJob, () => { fetchTracks(); }),
    2000);
    return () => clearInterval(id);
  }, [subJob, pollJob, fetchTracks]);

  const generateSubtitles = async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/subtitles/generate`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          script_version_id: scriptVersionId,
          format: subFormat,
          language: "ko",
          style: {
            max_chars_per_line: maxChars,
            max_lines: maxLines,
            gap_ms: gapMs,
          },
        }),
      });
      if (res.ok) setSubJob(await res.json());
    } catch {}
  };

  const loadPreview = async (trackId: string) => {
    if (previewTrackId === trackId) { setSrtPreview(null); setPreviewTrackId(null); return; }
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/subtitles/${trackId}/content`));
      if (res.ok) {
        setSrtPreview(await res.text());
        setPreviewTrackId(trackId);
      }
    } catch {}
  };

  const latestTrack = tracks.find((t) => t.status === "ready") || null;

  function fmtMs(ms: number): string {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    const sec = s % 60;
    const milli = ms % 1000;
    return `${m}:${String(sec).padStart(2, "0")}.${String(milli).padStart(3, "0")}`;
  }

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold">자막 생성</h2>
          {latestTrack && (
            <p className="text-xs text-neutral-500 mt-1">
              {latestTrack.total_segments}개 세그먼트 ·{" "}
              {latestTrack.total_duration_ms ? fmtMs(latestTrack.total_duration_ms) : "—"} ·{" "}
              타이밍: {latestTrack.timing_source}
            </p>
          )}
        </div>
        <button
          onClick={generateSubtitles}
          disabled={!!isRunning}
          className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium transition hover:bg-amber-500 disabled:opacity-50"
        >
          {isRunning ? "생성 중..." : latestTrack ? "자막 재생성" : "자막 생성"}
        </button>
      </div>

      {/* Style settings */}
      <div className="grid grid-cols-4 gap-3 mb-4">
        <div>
          <label className="block text-[10px] text-neutral-500 mb-0.5">줄당 최대 글자</label>
          <input type="number" value={maxChars} onChange={(e) => setMaxChars(Number(e.target.value))} min={10} max={80}
            className="w-full rounded border border-neutral-700 bg-neutral-800 px-2 py-1 text-xs text-neutral-200 focus:border-amber-500 focus:outline-none" />
        </div>
        <div>
          <label className="block text-[10px] text-neutral-500 mb-0.5">최대 줄 수</label>
          <select value={maxLines} onChange={(e) => setMaxLines(Number(e.target.value))}
            className="w-full rounded border border-neutral-700 bg-neutral-800 px-2 py-1 text-xs text-neutral-200 focus:border-amber-500 focus:outline-none">
            <option value={1}>1줄</option>
            <option value={2}>2줄</option>
            <option value={3}>3줄</option>
          </select>
        </div>
        <div>
          <label className="block text-[10px] text-neutral-500 mb-0.5">세그먼트 간격(ms)</label>
          <input type="number" value={gapMs} onChange={(e) => setGapMs(Number(e.target.value))} min={0} max={2000} step={50}
            className="w-full rounded border border-neutral-700 bg-neutral-800 px-2 py-1 text-xs text-neutral-200 focus:border-amber-500 focus:outline-none" />
        </div>
        <div>
          <label className="block text-[10px] text-neutral-500 mb-0.5">포맷</label>
          <select value={subFormat} onChange={(e) => setSubFormat(e.target.value)}
            className="w-full rounded border border-neutral-700 bg-neutral-800 px-2 py-1 text-xs text-neutral-200 focus:border-amber-500 focus:outline-none">
            <option value="srt">SRT</option>
            <option value="vtt">VTT</option>
          </select>
        </div>
      </div>

      {/* Job progress */}
      {isRunning && subJob && (
        <div className="mb-4">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-neutral-700 rounded-full h-1.5 overflow-hidden">
              <div className="bg-amber-500 h-full rounded-full transition-all" style={{ width: `${subJob.progress}%` }} />
            </div>
            <span className="text-[10px] text-neutral-500">{subJob.progress}%</span>
          </div>
        </div>
      )}
      {subJob?.status === "failed" && (
        <p className="text-sm text-red-300 mb-4">{subJob.error_message || "자막 생성 실패"}</p>
      )}

      {/* Track list */}
      {tracks.length > 0 && (
        <div className="space-y-2">
          {tracks.map((t) => (
            <div key={t.id} className="rounded border border-neutral-700/50 bg-neutral-800/30 overflow-hidden">
              <div className="px-3 py-2 flex items-center justify-between">
                <div className="flex items-center gap-3 text-xs">
                  <span className={`font-semibold ${t.status === "ready" ? "text-emerald-400" : "text-neutral-400"}`}>
                    {t.format.toUpperCase()}
                  </span>
                  <span className="text-neutral-500">{t.total_segments ?? 0}개</span>
                  <span className="text-neutral-500">{t.total_duration_ms ? fmtMs(t.total_duration_ms) : "—"}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                    t.timing_source === "tts" ? "bg-emerald-900/40 text-emerald-400" :
                    t.timing_source === "mixed" ? "bg-blue-900/40 text-blue-400" :
                    "bg-neutral-700 text-neutral-400"
                  }`}>
                    {t.timing_source}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => loadPreview(t.id)}
                    className="text-[10px] text-amber-400 hover:text-amber-300 transition"
                  >
                    {previewTrackId === t.id ? "닫기" : "미리보기"}
                  </button>
                  {t.asset_id && (
                    <a
                      href={`/api/projects/${projectId}/subtitles/${t.id}/download-url`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-blue-400 hover:text-blue-300 transition"
                    >
                      다운로드
                    </a>
                  )}
                </div>
              </div>

              {/* SRT preview */}
              {previewTrackId === t.id && srtPreview && (
                <div className="border-t border-neutral-700/30 px-3 py-2">
                  <pre className="text-[10px] text-neutral-300 font-mono leading-relaxed max-h-64 overflow-y-auto whitespace-pre-wrap">
                    {srtPreview}
                  </pre>
                </div>
              )}

              {/* Segment timeline preview */}
              {previewTrackId === t.id && t.segments && t.segments.length > 0 && (
                <div className="border-t border-neutral-700/30 px-3 py-2">
                  <p className="text-[10px] font-semibold text-neutral-500 mb-1.5">세그먼트 타임라인</p>
                  <div className="space-y-0.5 max-h-48 overflow-y-auto">
                    {t.segments.map((seg) => (
                      <div key={seg.index} className="flex items-start gap-2 text-[10px] text-neutral-400">
                        <span className="shrink-0 text-neutral-600 font-mono w-24">
                          {fmtMs(seg.start_ms)} → {fmtMs(seg.end_ms)}
                        </span>
                        <span className="text-neutral-300">{seg.text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {!loaded && <p className="text-sm text-neutral-500 text-center py-4">불러오는 중...</p>}
      {loaded && tracks.length === 0 && !isRunning && (
        <p className="text-sm text-neutral-500 text-center py-4">아직 자막이 생성되지 않았습니다.</p>
      )}
    </div>
  );
}

/* ── Timeline Panel ─────────────────────────────────── */

function TimelinePanel({
  projectId,
  scriptVersionId,
  pollJob,
}: {
  projectId: string;
  scriptVersionId: string;
  pollJob: (job: Job | null, set: (j: Job | null) => void, done: () => void) => Promise<void>;
}) {
  const [composeJob, setComposeJob] = useState<Job | null>(null);
  const [timelines, setTimelines] = useState<TimelineListItem[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [summary, setSummary] = useState<TimelineSummaryData | null>(null);
  const [showWarnings, setShowWarnings] = useState(false);

  /* ── Render state ── */
  const [renderJob, setRenderJob] = useState<Job | null>(null);
  const [renderOutput, setRenderOutput] = useState<{
    render_job_id: string; status: string; output_url: string | null;
    duration_sec: number | null; file_size_bytes: number | null; width: number | null; height: number | null;
  } | null>(null);
  const [burnSubs, setBurnSubs] = useState(false);

  const isRunning = composeJob && composeJob.status !== "completed" && composeJob.status !== "failed";
  const isRendering = renderJob && renderJob.status !== "completed" && renderJob.status !== "failed";
  const latestTlId = timelines.length > 0 ? timelines[0].id : null;

  const fetchTimelines = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/timelines?script_version_id=${scriptVersionId}`));
      if (res.ok) {
        const data = await res.json();
        setTimelines(data.timelines);
        if (data.timelines.length > 0) {
          const latest = data.timelines[0];
          const sRes = await fetch(apiUrl(`/api/projects/${projectId}/timelines/${latest.id}/summary`));
          if (sRes.ok) setSummary(await sRes.json());
        }
      }
    } catch {} finally { setLoaded(true); }
  }, [projectId, scriptVersionId]);

  const fetchRenderOutput = useCallback(async () => {
    if (!latestTlId) return;
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/render-jobs?timeline_id=${latestTlId}`));
      if (res.ok) {
        const data = await res.json();
        const completed = data.render_jobs?.find((r: Record<string, unknown>) => r.status === "completed");
        if (completed) {
          const oRes = await fetch(apiUrl(`/api/projects/${projectId}/render-jobs/${completed.id}/output`));
          if (oRes.ok) setRenderOutput(await oRes.json());
        }
      }
    } catch {}
  }, [projectId, latestTlId]);

  useEffect(() => { fetchTimelines(); }, [fetchTimelines]);
  useEffect(() => { if (latestTlId) fetchRenderOutput(); }, [latestTlId, fetchRenderOutput]);

  useEffect(() => {
    if (!composeJob || composeJob.status === "completed" || composeJob.status === "failed") return;
    const id = setInterval(() =>
      pollJob(composeJob, setComposeJob, () => { fetchTimelines(); }),
    2000);
    return () => clearInterval(id);
  }, [composeJob, pollJob, fetchTimelines]);

  useEffect(() => {
    if (!renderJob || renderJob.status === "completed" || renderJob.status === "failed") return;
    const id = setInterval(() =>
      pollJob(renderJob, setRenderJob, () => { fetchRenderOutput(); }),
    3000);
    return () => clearInterval(id);
  }, [renderJob, pollJob, fetchRenderOutput]);

  const composeTimeline = async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/timelines/compose`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ script_version_id: scriptVersionId }),
      });
      if (res.ok) setComposeJob(await res.json());
    } catch {}
  };

  const startRender = async () => {
    if (!latestTlId) return;
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/render`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ timeline_id: latestTlId, burn_subtitles: burnSubs }),
      });
      if (res.ok) {
        setRenderJob(await res.json());
        setRenderOutput(null);
      }
    } catch {}
  };

  function fmtDur(ms: number): string {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}분 ${sec}초` : `${sec}초`;
  }

  function fmtSize(bytes: number): string {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold">타임라인 & 렌더</h2>
          {summary && (
            <p className="text-xs text-neutral-500 mt-1">
              {summary.total_shots}개 shot · {fmtDur(summary.total_duration_ms)}
            </p>
          )}
        </div>
        <button
          onClick={composeTimeline}
          disabled={!!isRunning}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium transition hover:bg-violet-500 disabled:opacity-50"
        >
          {isRunning ? "조립 중..." : summary ? "타임라인 재조립" : "타임라인 조립"}
        </button>
      </div>

      {/* Compose job progress */}
      {isRunning && composeJob && (
        <div className="mb-4">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-neutral-700 rounded-full h-1.5 overflow-hidden">
              <div className="bg-violet-500 h-full rounded-full transition-all" style={{ width: `${composeJob.progress}%` }} />
            </div>
            <span className="text-[10px] text-neutral-500">{composeJob.progress}%</span>
          </div>
        </div>
      )}
      {composeJob?.status === "failed" && (
        <p className="text-sm text-red-300 mb-4">{composeJob.error_message || "타임라인 조립 실패"}</p>
      )}

      {/* Summary dashboard */}
      {summary && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded border border-neutral-700/50 bg-neutral-800/30 p-2.5 text-center">
              <p className="text-lg font-bold text-neutral-200">{summary.shots_with_video}</p>
              <p className="text-[10px] text-emerald-400">비디오 있음</p>
            </div>
            <div className="rounded border border-neutral-700/50 bg-neutral-800/30 p-2.5 text-center">
              <p className="text-lg font-bold text-neutral-200">{summary.shots_with_image_only}</p>
              <p className="text-[10px] text-amber-400">이미지만</p>
            </div>
            <div className={`rounded border p-2.5 text-center ${
              summary.shots_missing_visual > 0
                ? "border-red-700/50 bg-red-950/20"
                : "border-neutral-700/50 bg-neutral-800/30"
            }`}>
              <p className={`text-lg font-bold ${summary.shots_missing_visual > 0 ? "text-red-400" : "text-neutral-200"}`}>
                {summary.shots_missing_visual}
              </p>
              <p className="text-[10px] text-red-400">비주얼 누락</p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div className="rounded border border-neutral-700/50 bg-neutral-800/30 p-2.5 text-center">
              <p className="text-lg font-bold text-neutral-200">{summary.shots_with_audio}</p>
              <p className="text-[10px] text-pink-400">TTS 있음</p>
            </div>
            <div className={`rounded border p-2.5 text-center ${
              summary.shots_missing_audio > 0
                ? "border-orange-700/50 bg-orange-950/20"
                : "border-neutral-700/50 bg-neutral-800/30"
            }`}>
              <p className={`text-lg font-bold ${summary.shots_missing_audio > 0 ? "text-orange-400" : "text-neutral-200"}`}>
                {summary.shots_missing_audio}
              </p>
              <p className="text-[10px] text-orange-400">TTS 누락</p>
            </div>
            <div className="rounded border border-neutral-700/50 bg-neutral-800/30 p-2.5 text-center">
              <div className="flex items-center justify-center gap-1.5">
                <span className={`inline-block w-2 h-2 rounded-full ${summary.has_subtitle ? "bg-emerald-400" : "bg-neutral-600"}`} />
                <span className={`inline-block w-2 h-2 rounded-full ${summary.has_bgm ? "bg-blue-400" : "bg-neutral-600"}`} />
              </div>
              <p className="text-[10px] text-neutral-400 mt-1">
                자막 {summary.has_subtitle ? "O" : "X"} · BGM {summary.has_bgm ? "O" : "X"}
              </p>
            </div>
          </div>

          {summary.warnings.length > 0 && (
            <div>
              <button
                onClick={() => setShowWarnings(!showWarnings)}
                className="text-[11px] text-amber-400 hover:text-amber-300 transition"
              >
                {showWarnings ? "경고 숨기기" : `${summary.warnings.length}개 경고 보기`}
              </button>
              {showWarnings && (
                <div className="mt-1.5 rounded border border-amber-800/40 bg-amber-950/20 p-2.5 space-y-0.5 max-h-40 overflow-y-auto">
                  {summary.warnings.map((w, i) => (
                    <p key={i} className="text-[10px] text-amber-300/80">{w}</p>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── Render section ── */}
          <div className="border-t border-neutral-700/30 pt-3 mt-1">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-semibold text-neutral-300">최종 렌더</p>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-1 text-[10px] text-neutral-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={burnSubs}
                    onChange={(e) => setBurnSubs(e.target.checked)}
                    className="rounded border-neutral-600 bg-neutral-800 text-red-500 focus:ring-0 w-3 h-3"
                  />
                  자막 번인
                </label>
                <button
                  onClick={startRender}
                  disabled={!!isRendering || !latestTlId}
                  className="rounded-lg bg-red-600 px-4 py-1.5 text-xs font-medium transition hover:bg-red-500 disabled:opacity-50"
                >
                  {isRendering ? "렌더 중..." : renderOutput?.output_url ? "재렌더" : "렌더 시작"}
                </button>
              </div>
            </div>

            {/* Render progress */}
            {isRendering && renderJob && (
              <div className="mb-3">
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-neutral-700 rounded-full h-2 overflow-hidden">
                    <div className="bg-red-500 h-full rounded-full transition-all" style={{ width: `${renderJob.progress}%` }} />
                  </div>
                  <span className="text-[10px] text-neutral-500">{renderJob.progress}%</span>
                </div>
                <p className="text-[10px] text-neutral-600 mt-0.5">FFmpeg로 영상을 합성하고 있습니다...</p>
              </div>
            )}
            {renderJob?.status === "failed" && (
              <p className="text-[11px] text-red-400 mb-2">{renderJob.error_message || "렌더 실패"}</p>
            )}

            {/* Render output */}
            {renderOutput?.output_url && (
              <div className="space-y-2">
                <div className="rounded border border-neutral-700/50 overflow-hidden">
                  {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                  <video
                    src={renderOutput.output_url}
                    controls
                    className="w-full max-h-80 bg-black"
                    preload="metadata"
                  />
                </div>
                <div className="flex items-center justify-between text-[10px] text-neutral-500">
                  <div className="flex items-center gap-3">
                    {renderOutput.duration_sec && <span>{renderOutput.duration_sec.toFixed(1)}s</span>}
                    {renderOutput.width && renderOutput.height && (
                      <span>{renderOutput.width}×{renderOutput.height}</span>
                    )}
                    {renderOutput.file_size_bytes && <span>{fmtSize(renderOutput.file_size_bytes)}</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    <a
                      href={renderOutput.output_url}
                      download
                      className="text-blue-400 hover:text-blue-300 transition font-medium"
                    >
                      MP4 다운로드
                    </a>
                  </div>
                </div>
              </div>
            )}

            {!renderOutput?.output_url && !isRendering && latestTlId && (
              <p className="text-[10px] text-neutral-500 text-center py-2">렌더를 시작하면 최종 영상이 여기에 표시됩니다.</p>
            )}
          </div>
        </div>
      )}

      {!loaded && <p className="text-sm text-neutral-500 text-center py-4">불러오는 중...</p>}
      {loaded && timelines.length === 0 && !isRunning && (
        <p className="text-sm text-neutral-500 text-center py-4">아직 타임라인이 조립되지 않았습니다.</p>
      )}
    </div>
  );
}

/* ── QA Panel ───────────────────────────────────────── */

const SEVERITY_CONFIG: Record<string, { bg: string; text: string; icon: string; label: string }> = {
  error: { bg: "bg-red-900/40 border-red-700/50", text: "text-red-400", icon: "✕", label: "오류" },
  warning: { bg: "bg-amber-900/40 border-amber-700/50", text: "text-amber-400", icon: "⚠", label: "경고" },
  info: { bg: "bg-blue-900/40 border-blue-700/50", text: "text-blue-400", icon: "ℹ", label: "정보" },
};

const CHECK_TYPE_LABELS: Record<string, string> = {
  missing_frame_specs: "Frame Spec 누락",
  missing_start_frame: "Start Frame 누락",
  missing_end_frame: "End Frame 누락",
  missing_images: "이미지 누락",
  missing_video_clip: "비디오 클립 누락",
  no_voice_track: "TTS 누락",
  no_shots: "Shot 누락",
  no_scenes: "Scene 누락",
  missing_narration: "나레이션 누락",
  duration_conflict: "길이 불일치",
  subtitle_missing: "자막 누락",
  subtitle_duration_mismatch: "자막 길이 불일치",
  render_not_ready: "렌더 미준비",
  no_timeline: "타임라인 없음",
  failed_jobs: "작업 실패",
  provider_failures: "프로바이더 실패",
};

function QAPanel({
  projectId,
  scriptVersionId,
}: {
  projectId: string;
  scriptVersionId: string;
}) {
  const [summary, setSummary] = useState<QASummaryData | null>(null);
  const [results, setResults] = useState<QAResultData[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [running, setRunning] = useState(false);
  const [filterSeverity, setFilterSeverity] = useState<string | null>(null);
  const [filterScope, setFilterScope] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/qa/summary`));
      if (res.ok) setSummary(await res.json());
    } catch {}
  }, [projectId]);

  const fetchResults = useCallback(async () => {
    const params = new URLSearchParams();
    params.set("resolved", "false");
    if (filterSeverity) params.set("severity", filterSeverity);
    if (filterScope) params.set("scope", filterScope);
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/qa?${params}`));
      if (res.ok) {
        const data = await res.json();
        setResults(data.results);
      }
    } catch {} finally { setLoaded(true); }
  }, [projectId, filterSeverity, filterScope]);

  useEffect(() => { fetchSummary(); fetchResults(); }, [fetchSummary, fetchResults]);

  const runQA = async () => {
    setRunning(true);
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/qa/run`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ script_version_id: scriptVersionId }),
      });
      if (res.ok) {
        await fetchSummary();
        await fetchResults();
      }
    } catch {} finally { setRunning(false); }
  };

  const resolveIssue = async (qaId: string) => {
    try {
      await fetch(apiUrl(`/api/projects/${projectId}/qa/${qaId}/resolve`), { method: "PATCH" });
      setResults((prev) => prev.filter((r) => r.id !== qaId));
      fetchSummary();
    } catch {}
  };

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <button onClick={() => setExpanded(!expanded)} className="text-neutral-500 hover:text-neutral-300 transition">
            {expanded ? "▼" : "▶"}
          </button>
          <div>
            <h2 className="text-lg font-semibold">QA 점검</h2>
            {summary && (
              <div className="flex items-center gap-2 mt-0.5">
                {summary.render_ready ? (
                  <span className="text-xs text-emerald-400 font-medium">렌더 준비 완료</span>
                ) : (
                  <span className="text-xs text-red-400 font-medium">렌더 차단 이슈 있음</span>
                )}
                <span className="text-xs text-neutral-500">·</span>
                {summary.errors > 0 && <span className="text-xs text-red-400">{summary.errors} 오류</span>}
                {summary.warnings > 0 && <span className="text-xs text-amber-400">{summary.warnings} 경고</span>}
                {summary.infos > 0 && <span className="text-xs text-blue-400">{summary.infos} 정보</span>}
                {summary.total === 0 && <span className="text-xs text-emerald-400">이슈 없음</span>}
              </div>
            )}
          </div>
        </div>
        <button
          onClick={runQA}
          disabled={running}
          className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium transition hover:bg-cyan-500 disabled:opacity-50"
        >
          {running ? "점검 중..." : "QA 실행"}
        </button>
      </div>

      {expanded && (
        <>
          {/* Summary cards */}
          {summary && summary.total > 0 && (
            <div className="grid grid-cols-4 gap-2 mb-4">
              <button
                onClick={() => setFilterSeverity(filterSeverity === "error" ? null : "error")}
                className={`rounded border p-2 text-center transition ${
                  filterSeverity === "error" ? "bg-red-900/40 border-red-600" : "bg-neutral-800/40 border-neutral-700/50 hover:border-neutral-600"
                }`}
              >
                <p className="text-lg font-bold text-red-400">{summary.errors}</p>
                <p className="text-[10px] text-red-400/80">오류</p>
              </button>
              <button
                onClick={() => setFilterSeverity(filterSeverity === "warning" ? null : "warning")}
                className={`rounded border p-2 text-center transition ${
                  filterSeverity === "warning" ? "bg-amber-900/40 border-amber-600" : "bg-neutral-800/40 border-neutral-700/50 hover:border-neutral-600"
                }`}
              >
                <p className="text-lg font-bold text-amber-400">{summary.warnings}</p>
                <p className="text-[10px] text-amber-400/80">경고</p>
              </button>
              <button
                onClick={() => setFilterSeverity(filterSeverity === "info" ? null : "info")}
                className={`rounded border p-2 text-center transition ${
                  filterSeverity === "info" ? "bg-blue-900/40 border-blue-600" : "bg-neutral-800/40 border-neutral-700/50 hover:border-neutral-600"
                }`}
              >
                <p className="text-lg font-bold text-blue-400">{summary.infos}</p>
                <p className="text-[10px] text-blue-400/80">정보</p>
              </button>
              <div className={`rounded border p-2 text-center ${
                summary.render_ready ? "border-emerald-700/50 bg-emerald-950/20" : "border-red-700/50 bg-red-950/20"
              }`}>
                <p className={`text-lg font-bold ${summary.render_ready ? "text-emerald-400" : "text-red-400"}`}>
                  {summary.render_ready ? "OK" : "NO"}
                </p>
                <p className="text-[10px] text-neutral-400">렌더 준비</p>
              </div>
            </div>
          )}

          {/* Scope filter */}
          {summary && summary.total > 0 && (
            <div className="flex items-center gap-1.5 mb-3">
              <span className="text-[10px] text-neutral-500">범위:</span>
              {["project", "scene", "shot", "frame"].map((s) => {
                const count = summary.by_scope[s] || 0;
                if (count === 0 && filterScope !== s) return null;
                return (
                  <button
                    key={s}
                    onClick={() => setFilterScope(filterScope === s ? null : s)}
                    className={`rounded px-2 py-0.5 text-[10px] transition ${
                      filterScope === s ? "bg-cyan-800 text-cyan-200" : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
                    }`}
                  >
                    {s} ({count})
                  </button>
                );
              })}
              {(filterSeverity || filterScope) && (
                <button
                  onClick={() => { setFilterSeverity(null); setFilterScope(null); }}
                  className="text-[10px] text-neutral-500 hover:text-neutral-300 ml-1"
                >
                  초기화
                </button>
              )}
            </div>
          )}

          {/* Issue list */}
          {results.length > 0 && (
            <div className="space-y-1.5 max-h-96 overflow-y-auto">
              {results.map((r) => {
                const sev = SEVERITY_CONFIG[r.severity] || SEVERITY_CONFIG.info;
                return (
                  <div key={r.id} className={`rounded border ${sev.bg} p-3`}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2 min-w-0">
                        <span className={`shrink-0 text-sm ${sev.text}`}>{sev.icon}</span>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className={`text-xs font-semibold ${sev.text}`}>{sev.label}</span>
                            <span className="text-[10px] text-neutral-500 bg-neutral-800 rounded px-1.5 py-px">
                              {CHECK_TYPE_LABELS[r.check_type] || r.check_type}
                            </span>
                            <span className="text-[10px] text-neutral-600">{r.scope}</span>
                            {r.target_id && (
                              <span className="text-[10px] text-neutral-600 font-mono">{r.target_id.slice(0, 8)}</span>
                            )}
                          </div>
                          <p className="text-xs text-neutral-300 mt-1">{r.message}</p>
                          {r.suggestion && (
                            <p className="text-[11px] text-cyan-400/80 mt-1">
                              <span className="font-semibold">수정 방법:</span> {r.suggestion}
                            </p>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => resolveIssue(r.id)}
                        className="shrink-0 rounded bg-neutral-700/50 px-2 py-0.5 text-[9px] text-neutral-400 hover:bg-neutral-600 hover:text-neutral-200 transition"
                        title="해결됨으로 표시"
                      >
                        해결
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {loaded && results.length === 0 && !running && (
            <div className="text-center py-6">
              {summary && summary.total === 0 ? (
                <div>
                  <p className="text-emerald-400 font-medium">모든 점검을 통과했습니다</p>
                  <p className="text-xs text-neutral-500 mt-1">프로젝트가 렌더할 준비가 되었습니다</p>
                </div>
              ) : (
                <p className="text-sm text-neutral-500">QA를 실행하면 점검 결과가 여기에 표시됩니다</p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ── Quality Evaluation Panel ──────────────────────── */

interface CriterionDef {
  key: string;
  label: string;
  description: string;
  scopes: string[];
  weight: number;
}

interface EvalData {
  id: string;
  project_id: string;
  target_type: string;
  target_id: string | null;
  source: string;
  scores: Record<string, number>;
  overall_score: number | null;
  comment: string | null;
  reviewer: string;
  run_label: string | null;
  created_at: string;
  updated_at: string;
}

interface EvalSummaryData {
  total_reviews: number;
  manual_count: number;
  auto_count: number;
  latest_auto_score: number | null;
  latest_manual_score: number | null;
  latest_auto_scores: Record<string, number> | null;
  latest_manual_scores: Record<string, number> | null;
  score_history: {
    id: string;
    source: string;
    overall_score: number | null;
    reviewer: string;
    run_label: string | null;
    created_at: string | null;
  }[];
}

const SCORE_COLORS: Record<number, string> = {
  1: "bg-red-600",
  2: "bg-orange-500",
  3: "bg-amber-500",
  4: "bg-lime-500",
  5: "bg-emerald-500",
};

const SCORE_LABELS: Record<number, string> = {
  1: "매우 낮음",
  2: "낮음",
  3: "보통",
  4: "좋음",
  5: "매우 좋음",
};

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((v) => (
          <div
            key={v}
            className={`w-3 h-3 rounded-sm ${v <= score ? SCORE_COLORS[score] : "bg-neutral-700"}`}
          />
        ))}
      </div>
      <span className="text-[10px] text-neutral-400">{SCORE_LABELS[score] || ""}</span>
    </div>
  );
}

function QualityEvaluationPanel({
  projectId,
  scriptVersionId,
}: {
  projectId: string;
  scriptVersionId: string;
}) {
  const [criteria, setCriteria] = useState<CriterionDef[]>([]);
  const [summary, setSummary] = useState<EvalSummaryData | null>(null);
  const [history, setHistory] = useState<EvalData[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [running, setRunning] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [formScores, setFormScores] = useState<Record<string, number>>({});
  const [formComment, setFormComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [selectedReview, setSelectedReview] = useState<EvalData | null>(null);

  const API = `/api/projects/${projectId}/evaluations`;

  const fetchCriteria = useCallback(async () => {
    try {
      const res = await fetch(`${API}/criteria?scope=project`);
      if (res.ok) setCriteria(await res.json());
    } catch {}
  }, [API]);

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch(`${API}/summary`);
      if (res.ok) setSummary(await res.json());
    } catch {}
  }, [API]);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API}?limit=20`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.reviews);
      }
    } catch {} finally { setLoaded(true); }
  }, [API]);

  useEffect(() => {
    fetchCriteria();
    fetchSummary();
    fetchHistory();
  }, [fetchCriteria, fetchSummary, fetchHistory]);

  const runAutoEval = async () => {
    setRunning(true);
    try {
      const res = await fetch(`${API}/auto`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ script_version_id: scriptVersionId }),
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedReview(data);
        await fetchSummary();
        await fetchHistory();
      }
    } catch {} finally { setRunning(false); }
  };

  const submitManualEval = async () => {
    const filled = Object.keys(formScores).length;
    if (filled === 0) return;
    setSubmitting(true);
    try {
      const res = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_type: "project",
          scores: formScores,
          comment: formComment || null,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedReview(data);
        setShowForm(false);
        setFormScores({});
        setFormComment("");
        await fetchSummary();
        await fetchHistory();
      }
    } catch {} finally { setSubmitting(false); }
  };

  const openForm = () => {
    setShowForm(true);
    const defaults: Record<string, number> = {};
    criteria.forEach((c) => { defaults[c.key] = 3; });
    setFormScores(defaults);
  };

  const ScoreOverview = ({ label, score, scores }: { label: string; score: number | null; scores: Record<string, number> | null }) => (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-neutral-400 font-medium">{label}</span>
        {score !== null && (
          <span className={`text-2xl font-bold ${score >= 4 ? "text-emerald-400" : score >= 3 ? "text-amber-400" : "text-red-400"}`}>
            {score.toFixed(1)}
          </span>
        )}
        {score === null && <span className="text-sm text-neutral-600">—</span>}
      </div>
      {scores && (
        <div className="space-y-1.5">
          {criteria.map((c) => {
            const s = scores[c.key];
            if (s === undefined) return null;
            return (
              <div key={c.key} className="flex items-center justify-between gap-2">
                <span className="text-[11px] text-neutral-400 truncate flex-1">{c.label}</span>
                <ScoreBar score={s} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <button onClick={() => setExpanded(!expanded)} className="text-neutral-500 hover:text-neutral-300 transition">
            {expanded ? "▼" : "▶"}
          </button>
          <div>
            <h2 className="text-lg font-semibold">품질 평가</h2>
            {summary && summary.total_reviews > 0 && (
              <p className="text-[11px] text-neutral-500 mt-0.5">
                자동 {summary.auto_count}회 · 수동 {summary.manual_count}회
                {summary.latest_auto_score !== null && (
                  <> · 최근 자동 점수 <span className="text-amber-400 font-medium">{summary.latest_auto_score.toFixed(1)}</span></>
                )}
              </p>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={openForm}
            className="rounded-lg bg-neutral-700 px-3 py-1.5 text-xs font-medium transition hover:bg-neutral-600"
          >
            수동 평가
          </button>
          <button
            onClick={runAutoEval}
            disabled={running}
            className="rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-medium transition hover:bg-cyan-500 disabled:opacity-50"
          >
            {running ? "평가 중..." : "자동 평가"}
          </button>
        </div>
      </div>

      {expanded && (
        <>
          {/* Score overview cards */}
          {summary && (summary.latest_auto_scores || summary.latest_manual_scores) && (
            <div className="grid grid-cols-2 gap-3 mb-5">
              <ScoreOverview label="자동 평가 (최근)" score={summary.latest_auto_score} scores={summary.latest_auto_scores} />
              <ScoreOverview label="수동 평가 (최근)" score={summary.latest_manual_score} scores={summary.latest_manual_scores} />
            </div>
          )}

          {/* Manual evaluation form */}
          {showForm && (
            <div className="rounded-lg border border-blue-800/50 bg-blue-950/20 p-4 mb-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-blue-300">수동 품질 평가</h3>
                <button onClick={() => setShowForm(false)} className="text-neutral-500 hover:text-neutral-300 text-xs">닫기</button>
              </div>
              <div className="space-y-3">
                {criteria.map((c) => (
                  <div key={c.key}>
                    <div className="flex items-center justify-between mb-1">
                      <div>
                        <span className="text-xs font-medium text-neutral-300">{c.label}</span>
                        <p className="text-[10px] text-neutral-500">{c.description}</p>
                      </div>
                      <div className="flex gap-1">
                        {[1, 2, 3, 4, 5].map((v) => (
                          <button
                            key={v}
                            onClick={() => setFormScores((p) => ({ ...p, [c.key]: v }))}
                            className={`w-8 h-8 rounded text-xs font-bold transition ${
                              formScores[c.key] === v
                                ? `${SCORE_COLORS[v]} text-white`
                                : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
                            }`}
                          >
                            {v}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
                <div>
                  <label className="text-xs text-neutral-400 block mb-1">코멘트 (선택)</label>
                  <textarea
                    value={formComment}
                    onChange={(e) => setFormComment(e.target.value)}
                    rows={2}
                    className="w-full rounded border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none resize-none"
                    placeholder="전체적인 평가, 개선 포인트 등..."
                  />
                </div>
                <div className="flex justify-end">
                  <button
                    onClick={submitManualEval}
                    disabled={submitting}
                    className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium transition hover:bg-blue-500 disabled:opacity-50"
                  >
                    {submitting ? "저장 중..." : "평가 제출"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Selected review detail */}
          {selectedReview && (
            <div className="rounded-lg border border-neutral-700 bg-neutral-800/50 p-4 mb-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] px-2 py-0.5 rounded font-medium ${
                    selectedReview.source === "auto" ? "bg-cyan-900/40 text-cyan-400" : "bg-purple-900/40 text-purple-400"
                  }`}>
                    {selectedReview.source === "auto" ? "자동" : "수동"}
                  </span>
                  <span className="text-xs text-neutral-400">
                    {new Date(selectedReview.created_at).toLocaleString("ko-KR")}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {selectedReview.overall_score !== null && (
                    <span className={`text-lg font-bold ${
                      selectedReview.overall_score >= 4 ? "text-emerald-400" :
                      selectedReview.overall_score >= 3 ? "text-amber-400" : "text-red-400"
                    }`}>
                      {selectedReview.overall_score.toFixed(1)}
                    </span>
                  )}
                  <button onClick={() => setSelectedReview(null)} className="text-neutral-500 hover:text-neutral-300 text-xs">닫기</button>
                </div>
              </div>
              <div className="space-y-1.5">
                {criteria.map((c) => {
                  const s = selectedReview.scores[c.key];
                  if (s === undefined) return null;
                  return (
                    <div key={c.key} className="flex items-center justify-between gap-2">
                      <span className="text-[11px] text-neutral-400 truncate flex-1">{c.label}</span>
                      <ScoreBar score={s} />
                    </div>
                  );
                })}
              </div>
              {selectedReview.comment && (
                <p className="text-xs text-neutral-300 mt-3 border-t border-neutral-700 pt-2">{selectedReview.comment}</p>
              )}
            </div>
          )}

          {/* History */}
          {history.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-neutral-400 mb-2">평가 이력</h3>
              <div className="space-y-1">
                {history.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => setSelectedReview(r)}
                    className={`w-full flex items-center justify-between rounded px-3 py-2 text-left transition ${
                      selectedReview?.id === r.id ? "bg-neutral-800 border border-neutral-600" : "bg-neutral-800/30 hover:bg-neutral-800/60 border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className={`text-[9px] px-1.5 py-px rounded font-medium ${
                        r.source === "auto" ? "bg-cyan-900/30 text-cyan-400" : "bg-purple-900/30 text-purple-400"
                      }`}>
                        {r.source === "auto" ? "자동" : "수동"}
                      </span>
                      <span className="text-[11px] text-neutral-400">
                        {new Date(r.created_at).toLocaleDateString("ko-KR")}
                      </span>
                      {r.run_label && <span className="text-[10px] text-neutral-600">{r.run_label}</span>}
                    </div>
                    <span className={`text-sm font-bold ${
                      (r.overall_score ?? 0) >= 4 ? "text-emerald-400" :
                      (r.overall_score ?? 0) >= 3 ? "text-amber-400" : "text-red-400"
                    }`}>
                      {r.overall_score?.toFixed(1) ?? "—"}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {loaded && !summary?.total_reviews && !showForm && (
            <div className="text-center py-8">
              <p className="text-sm text-neutral-500">아직 품질 평가가 없습니다</p>
              <p className="text-xs text-neutral-600 mt-1">'자동 평가'로 시스템 점수를 확인하거나 '수동 평가'로 직접 점수를 매기세요</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ── Export Panel ───────────────────────────────────── */

interface ExportManifestSummary {
  total_assets: number;
  total_size_bytes: number;
  by_type: Record<string, number>;
}

function ExportPanel({ projectId }: { projectId: string }) {
  const [saving, setSaving] = useState(false);
  const [savedAssetId, setSavedAssetId] = useState<string | null>(null);
  const [manifest, setManifest] = useState<ExportManifestSummary | null>(null);
  const [manifestLoaded, setManifestLoaded] = useState(false);
  const [mp4Info, setMp4Info] = useState<{ url: string; filename: string; file_size_bytes: number | null } | null>(null);
  const [srtAvailable, setSrtAvailable] = useState(false);
  const [jsonUrl, setJsonUrl] = useState<string | null>(null);

  const fetchExportInfo = useCallback(async () => {
    try {
      const [manifestRes, mp4Res, srtRes] = await Promise.allSettled([
        fetch(apiUrl(`/api/projects/${projectId}/export/manifest`)),
        fetch(apiUrl(`/api/projects/${projectId}/export/mp4`)),
        fetch(apiUrl(`/api/projects/${projectId}/export/srt`)),
      ]);

      if (manifestRes.status === "fulfilled" && manifestRes.value.ok) {
        const data = await manifestRes.value.json();
        setManifest(data.summary);
      }
      if (mp4Res.status === "fulfilled" && mp4Res.value.ok) {
        setMp4Info(await mp4Res.value.json());
      }
      if (srtRes.status === "fulfilled" && srtRes.value.ok) {
        setSrtAvailable(true);
      }
    } catch {} finally { setManifestLoaded(true); }
  }, [projectId]);

  useEffect(() => { fetchExportInfo(); }, [fetchExportInfo]);

  const saveProjectJson = async () => {
    setSaving(true);
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/export/json?save_as_asset=true`));
      if (res.ok) {
        const data = await res.json();
        setSavedAssetId(data._export_meta?.asset_id || null);
      }
    } catch {} finally { setSaving(false); }
  };

  const downloadProjectJson = async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/export/json`));
      if (res.ok) {
        const data = await res.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${data.project?.title || "project"}_export.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch {}
  };

  function fmtSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
      <h2 className="text-lg font-semibold mb-4">내보내기</h2>

      {/* Asset summary */}
      {manifest && (
        <div className="rounded border border-neutral-700/50 bg-neutral-800/30 p-3 mb-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-neutral-300">프로젝트 자산 현황</p>
            <span className="text-[10px] text-neutral-500">{fmtSize(manifest.total_size_bytes)}</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(manifest.by_type).map(([type, count]) => (
              <span key={type} className="rounded bg-neutral-700 px-2 py-0.5 text-[10px] text-neutral-300">
                {type}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Download buttons */}
      <div className="space-y-2">
        {/* MP4 */}
        <div className={`rounded border p-3 flex items-center justify-between ${
          mp4Info ? "border-emerald-700/50 bg-emerald-950/10" : "border-neutral-700/50 bg-neutral-800/20"
        }`}>
          <div>
            <p className="text-sm font-medium text-neutral-200">최종 영상 (MP4)</p>
            <p className="text-[10px] text-neutral-500">
              {mp4Info
                ? `렌더 완료 · ${mp4Info.file_size_bytes ? fmtSize(mp4Info.file_size_bytes) : ""}`
                : "렌더가 완료되면 다운로드할 수 있습니다"}
            </p>
          </div>
          {mp4Info ? (
            <a
              href={mp4Info.url}
              download={mp4Info.filename}
              className="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-medium text-white transition hover:bg-emerald-500"
            >
              MP4 다운로드
            </a>
          ) : (
            <span className="rounded-lg bg-neutral-700 px-4 py-1.5 text-xs font-medium text-neutral-500 cursor-not-allowed">
              MP4 없음
            </span>
          )}
        </div>

        {/* SRT */}
        <div className={`rounded border p-3 flex items-center justify-between ${
          srtAvailable ? "border-amber-700/50 bg-amber-950/10" : "border-neutral-700/50 bg-neutral-800/20"
        }`}>
          <div>
            <p className="text-sm font-medium text-neutral-200">자막 (SRT)</p>
            <p className="text-[10px] text-neutral-500">
              {srtAvailable
                ? "자막 트랙 준비 완료"
                : "자막이 생성되면 다운로드할 수 있습니다"}
            </p>
          </div>
          {srtAvailable ? (
            <a
              href={`/api/projects/${projectId}/export/srt`}
              download="subtitles.srt"
              className="rounded-lg bg-amber-600 px-4 py-1.5 text-xs font-medium text-white transition hover:bg-amber-500"
            >
              SRT 다운로드
            </a>
          ) : (
            <span className="rounded-lg bg-neutral-700 px-4 py-1.5 text-xs font-medium text-neutral-500 cursor-not-allowed">
              SRT 없음
            </span>
          )}
        </div>

        {/* Project JSON */}
        <div className="rounded border border-blue-700/50 bg-blue-950/10 p-3 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-neutral-200">프로젝트 JSON</p>
            <p className="text-[10px] text-neutral-500">
              대본, Scene, Shot, Frame, 타임라인, 렌더 메타데이터 포함
            </p>
            {savedAssetId && (
              <p className="text-[10px] text-blue-400 mt-0.5">S3에 저장됨</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={downloadProjectJson}
              className="rounded-lg bg-blue-600 px-4 py-1.5 text-xs font-medium text-white transition hover:bg-blue-500"
            >
              JSON 다운로드
            </button>
            <button
              onClick={saveProjectJson}
              disabled={saving}
              className="rounded-lg bg-neutral-700 px-3 py-1.5 text-xs font-medium text-neutral-300 transition hover:bg-neutral-600 disabled:opacity-50"
              title="S3에 프로젝트 JSON을 저장합니다"
            >
              {saving ? "저장 중..." : "S3 저장"}
            </button>
          </div>
        </div>

        {/* Asset Manifest */}
        <div className="rounded border border-violet-700/50 bg-violet-950/10 p-3 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-neutral-200">자산 매니페스트</p>
            <p className="text-[10px] text-neutral-500">
              모든 생성 자산의 목록, 메타데이터, 다운로드 URL 포함
              {manifest && ` · ${manifest.total_assets}개 자산`}
            </p>
          </div>
          <a
            href={`/api/projects/${projectId}/export/manifest`}
            download="asset_manifest.json"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg bg-violet-600 px-4 py-1.5 text-xs font-medium text-white transition hover:bg-violet-500"
          >
            매니페스트 다운로드
          </a>
        </div>
      </div>

      {!manifestLoaded && <p className="text-sm text-neutral-500 text-center py-4 mt-2">불러오는 중...</p>}
    </div>
  );
}

/* ── Scene Card (with nested shots) ──────────────── */

function SceneCard({
  scene,
  projectId,
  onSceneRegenerate,
  sceneRegeneratingId,
  pollJob,
}: {
  scene: SceneData;
  projectId: string;
  onSceneRegenerate: (id: string) => void;
  sceneRegeneratingId: string | null;
  pollJob: (job: Job | null, set: (j: Job | null) => void, done: () => void) => Promise<void>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [shots, setShots] = useState<ShotData[]>([]);
  const [shotJob, setShotJob] = useState<Job | null>(null);
  const [regenShotId, setRegenShotId] = useState<string | null>(null);
  const [shotsLoaded, setShotsLoaded] = useState(false);

  const isSceneRegen = sceneRegeneratingId === scene.id;
  const isShotJobRunning = shotJob && shotJob.status !== "completed" && shotJob.status !== "failed";

  const fetchShots = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/scenes/${scene.id}/shots`));
      if (res.ok) {
        const data = await res.json();
        setShots(data.shots);
      }
    } catch { /* silent */ }
    finally { setShotsLoaded(true); }
  }, [projectId, scene.id]);

  useEffect(() => {
    if (expanded && !shotsLoaded) fetchShots();
  }, [expanded, shotsLoaded, fetchShots]);

  useEffect(() => {
    if (!shotJob) return;
    if (shotJob.status === "completed" || shotJob.status === "failed") return;
    const id = setInterval(() =>
      pollJob(shotJob, setShotJob, () => { fetchShots(); setRegenShotId(null); }),
    2000);
    return () => clearInterval(id);
  }, [shotJob, pollJob, fetchShots]);

  const generateShots = async () => {
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/scenes/${scene.id}/shots/generate`), { method: "POST" });
      if (res.ok) setShotJob(await res.json());
    } catch { /* silent */ }
  };

  const regenerateShot = async (shotId: string) => {
    setRegenShotId(shotId);
    try {
      const res = await fetch(apiUrl(`/api/projects/${projectId}/shots/${shotId}/regenerate`), { method: "POST" });
      if (res.ok) setShotJob(await res.json());
      else setRegenShotId(null);
    } catch { setRegenShotId(null); }
  };

  const totalShotDur = shots.reduce((s, sh) => s + (sh.duration_sec || 0), 0);

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 overflow-hidden">
      {/* Scene header */}
      <button onClick={() => setExpanded(!expanded)} className="w-full px-4 py-3 text-left">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="shrink-0 text-xs font-mono text-neutral-500 w-6 text-right">{scene.order_index + 1}</span>
            <StatusBadge status={scene.status} styles={SCENE_STATUS_STYLES} />
            <span className="text-sm font-semibold text-neutral-200 truncate">{scene.title || `Scene ${scene.order_index + 1}`}</span>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className="text-xs text-neutral-500">{scene.duration_estimate_sec ? `${Math.round(scene.duration_estimate_sec)}초` : ""}</span>
            {scene.emotional_tone && <span className="text-xs text-purple-400/80">{scene.emotional_tone}</span>}
            <span className="text-neutral-600 text-xs">{expanded ? "▲" : "▼"}</span>
          </div>
        </div>
        {scene.purpose && !expanded && <p className="mt-1 ml-8 text-xs text-neutral-500 truncate">{scene.purpose}</p>}
      </button>

      {expanded && (
        <div className="border-t border-neutral-800 px-4 py-4 space-y-4 text-sm">
          {/* Scene details */}
          {scene.purpose && <div><p className="text-xs font-semibold text-neutral-400 mb-1">목적</p><p className="text-neutral-300">{scene.purpose}</p></div>}
          {scene.narration_text && (
            <div>
              <p className="text-xs font-semibold text-neutral-400 mb-1">나레이션</p>
              <div className="rounded bg-neutral-800 p-3 text-neutral-200 leading-relaxed whitespace-pre-wrap">{scene.narration_text}</div>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            {scene.setting && <div><p className="text-xs font-semibold text-neutral-400 mb-1">배경</p><p className="text-xs text-neutral-300">{scene.setting}</p></div>}
            {scene.mood && <div><p className="text-xs font-semibold text-neutral-400 mb-1">분위기</p><p className="text-xs text-neutral-300">{scene.mood}</p></div>}
            {scene.emotional_tone && <div><p className="text-xs font-semibold text-neutral-400 mb-1">감정 톤</p><p className="text-xs text-purple-400">{scene.emotional_tone}</p></div>}
            {scene.transition_hint && <div><p className="text-xs font-semibold text-neutral-400 mb-1">전환</p><p className="text-xs text-neutral-300">{scene.transition_hint}</p></div>}
          </div>
          {scene.visual_intent && <div><p className="text-xs font-semibold text-neutral-400 mb-1">Visual Intent</p><p className="text-xs text-blue-400/80">{scene.visual_intent}</p></div>}

          <div className="flex gap-2 pt-1">
            <button
              onClick={(e) => { e.stopPropagation(); onSceneRegenerate(scene.id); }}
              disabled={!!sceneRegeneratingId}
              className="rounded bg-blue-700 px-3 py-1.5 text-xs font-medium hover:bg-blue-600 disabled:opacity-50 transition"
            >{isSceneRegen ? "재생성 중..." : "Scene 재생성"}</button>
          </div>

          {/* ── Shots section ─────────────────────── */}
          <div className="border-t border-neutral-700/50 pt-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="text-xs font-semibold text-neutral-300">Shots</p>
                {shots.length > 0 && (
                  <p className="text-[10px] text-neutral-500">{shots.length}개 · {totalShotDur.toFixed(1)}초</p>
                )}
              </div>
              <button
                onClick={generateShots}
                disabled={!!isShotJobRunning}
                className="rounded bg-teal-700 px-3 py-1 text-[11px] font-medium hover:bg-teal-600 disabled:opacity-50 transition"
              >
                {isShotJobRunning ? "생성 중..." : shots.length > 0 ? "Shot 재생성" : "Shot 분해"}
              </button>
            </div>

            {isShotJobRunning && shotJob && (
              <div className="mb-3">
                <ProgressBar value={shotJob.progress} />
                <p className="text-[10px] text-neutral-500 mt-1">{shotJob.progress}%</p>
              </div>
            )}

            {shotJob?.status === "failed" && (
              <p className="text-xs text-red-400 mb-3">{shotJob.error_message || "Shot 생성 실패"}</p>
            )}

            {shots.length > 0 ? (
              <div className="space-y-1.5">
                {shots.map((shot) => (
                  <ShotCard key={shot.id} shot={shot} projectId={projectId} onRegenerate={regenerateShot} busyId={regenShotId} pollJob={pollJob} />
                ))}
              </div>
            ) : (
              shotsLoaded && !isShotJobRunning && (
                <p className="text-[11px] text-neutral-500 text-center py-3">
                  Shot이 없습니다. 위 버튼으로 분해하세요.
                </p>
              )
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Main Page ─────────────────────────────────────── */

export default function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: projectId } = use(params);

  const [project, setProject] = useState<Project | null>(null);
  const [versions, setVersions] = useState<ScriptVersion[]>([]);
  const [activeVersion, setActiveVersion] = useState<ScriptVersion | null>(null);
  const [scenes, setScenes] = useState<SceneData[]>([]);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [sceneJob, setSceneJob] = useState<Job | null>(null);
  const [regeneratingSceneId, setRegeneratingSceneId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [hasApiKey, setHasApiKey] = useState(true);
  const [easyMode, setEasyMode] = useState(true);
  const [progress, setProgress] = useState<{
    script: boolean; scenes: number; shots: number; frames: number;
    images: number; videos: number; voices: number; subtitles: number;
    timelines: number; renders: number; active_jobs: { id: string; job_type: string; status: string; progress: number }[];
  } | null>(null);

  const [topic, setTopic] = useState("");
  const [audience, setAudience] = useState("");
  const [tone, setTone] = useState("");
  const [duration, setDuration] = useState(60);
  const [format, setFormat] = useState("youtube_short");
  const [language, setLanguage] = useState("ko");
  const [constraints, setConstraints] = useState("");

  const [showStylePicker, setShowStylePicker] = useState(false);
  const [showVoicePicker, setShowVoicePicker] = useState(false);
  const [selectedVoiceId, setSelectedVoiceId] = useState<string | null>(null);
  const [allShots, setAllShots] = useState<ShotData[]>([]);
  const [allFrames, setAllFrames] = useState<FrameData[]>([]);
  const [allAssets, setAllAssets] = useState<AssetData[]>([]);

  const fetchProject = useCallback(async () => {
    try { const r = await fetch(apiUrl(`/api/projects/${projectId}`)); if (r.ok) setProject(await r.json()); } catch {}
  }, [projectId]);

  const fetchVersions = useCallback(async () => {
    try {
      const r = await fetch(apiUrl(`/api/projects/${projectId}/scripts`));
      if (r.ok) { const d = await r.json(); setVersions(d.versions); if (d.versions.length > 0 && !activeVersion) setActiveVersion(d.versions[0]); }
    } catch {} finally { setLoading(false); }
  }, [projectId, activeVersion]);

  const fetchScenes = useCallback(async (vId: string) => {
    try {
      const r = await fetch(apiUrl(`/api/projects/${projectId}/scripts/${vId}/scenes`));
      if (r.ok) {
        const data = await r.json();
        setScenes(data.scenes);
        const shotsList: ShotData[] = [];
        const framesList: FrameData[] = [];
        for (const sc of data.scenes) {
          try {
            const sr = await fetch(apiUrl(`/api/projects/${projectId}/scenes/${sc.id}/shots`));
            if (sr.ok) {
              const sd = await sr.json();
              const shots = sd.shots || [];
              shotsList.push(...shots);
              for (const shot of shots) {
                try {
                  const fr = await fetch(apiUrl(`/api/projects/${projectId}/shots/${shot.id}/frames`));
                  if (fr.ok) { const fd = await fr.json(); framesList.push(...(fd.frame_specs || [])); }
                } catch {}
              }
            }
          } catch {}
        }
        setAllShots(shotsList);
        setAllFrames(framesList);
      }
    } catch {}
  }, [projectId]);

  const pollJob = useCallback(async (job: Job | null, setJob: (j: Job | null) => void, done: () => void) => {
    if (!job || job.status === "completed" || job.status === "failed") return;
    try { const r = await fetch(apiUrl(`/api/jobs/${job.id}`)); if (r.ok) { const u: Job = await r.json(); setJob(u); if (u.status === "completed" || u.status === "failed") done(); } } catch {}
  }, []);

  const fetchProgress = useCallback(async () => {
    try {
      const r = await fetch(apiUrl(`/api/projects/${projectId}/progress`));
      if (r.ok) setProgress(await r.json());
    } catch {}
  }, [projectId]);

  useEffect(() => { fetchProject(); fetchVersions(); fetchProgress(); }, [fetchProject, fetchVersions, fetchProgress]);
  useEffect(() => { if (activeVersion) fetchScenes(activeVersion.id); else setScenes([]); }, [activeVersion, fetchScenes]);
  useEffect(() => {
    fetch(apiUrl("/api/health")).then(r => r.json()).then(d => {
      const text = d?.services?.providers?.text;
      setHasApiKey(text !== "none");
    }).catch(() => {});
  }, []);
  useEffect(() => {
    const id = setInterval(fetchProgress, 3000);
    return () => clearInterval(id);
  }, [fetchProgress]);

  useEffect(() => {
    if (!activeJob || activeJob.status === "completed" || activeJob.status === "failed") return;
    const id = setInterval(() => pollJob(activeJob, setActiveJob, () => fetchVersions()), 2000);
    return () => clearInterval(id);
  }, [activeJob, pollJob, fetchVersions]);

  useEffect(() => {
    if (!sceneJob || sceneJob.status === "completed" || sceneJob.status === "failed") return;
    const id = setInterval(() => pollJob(sceneJob, setSceneJob, () => { if (activeVersion) fetchScenes(activeVersion.id); setRegeneratingSceneId(null); }), 2000);
    return () => clearInterval(id);
  }, [sceneJob, pollJob, activeVersion, fetchScenes]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    setSubmitting(true);
    try {
      const r = await fetch(apiUrl(`/api/projects/${projectId}/scripts/generate`), {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic.trim(), target_audience: audience.trim(), tone: tone.trim(), duration_sec: duration, format, language, constraints: constraints.trim() }),
      });
      if (r.ok) { setActiveJob(await r.json()); setActiveVersion(null); setScenes([]); }
    } finally { setSubmitting(false); }
  };

  const generateScenes = async () => {
    if (!activeVersion) return;
    try { const r = await fetch(apiUrl(`/api/projects/${projectId}/scripts/${activeVersion.id}/scenes/generate`), { method: "POST" }); if (r.ok) setSceneJob(await r.json()); } catch {}
  };

  const regenerateScene = async (id: string) => {
    setRegeneratingSceneId(id);
    try { const r = await fetch(apiUrl(`/api/projects/${projectId}/scenes/${id}/regenerate`), { method: "POST" }); if (r.ok) setSceneJob(await r.json()); else setRegeneratingSceneId(null); } catch { setRegeneratingSceneId(null); }
  };

  const selectVersion = (v: ScriptVersion) => { setActiveVersion(v); setActiveJob(null); setSceneJob(null); setRegeneratingSceneId(null); };

  const [section, setSection] = useState<WorkspaceSection>("overview");

  if (loading && !project) return <p className="text-neutral-500">불러오는 중...</p>;
  if (!project) return <p className="text-red-400">프로젝트를 찾을 수 없습니다.</p>;

  const isScriptJobRunning = activeJob && activeJob.status !== "completed" && activeJob.status !== "failed";
  const isSceneJobRunning = sceneJob && sceneJob.status !== "completed" && sceneJob.status !== "failed";
  const totalSceneDur = scenes.reduce((s, sc) => s + (sc.duration_estimate_sec || 0), 0);

  const hasScript = !!activeVersion?.plan_json || !!progress?.script;
  const hasScenes = scenes.length > 0 || (progress?.scenes ?? 0) > 0;
  const hasShots = (progress?.shots ?? 0) > 0;
  const hasFrames = (progress?.frames ?? 0) > 0;
  const hasImages = (progress?.images ?? 0) > 0;
  const hasVideos = (progress?.videos ?? 0) > 0;
  const hasVoices = (progress?.voices ?? 0) > 0;
  const hasSubtitles = (progress?.subtitles ?? 0) > 0;
  const hasTimelines = (progress?.timelines ?? 0) > 0;
  const hasRenders = (progress?.renders ?? 0) > 0;

  const activeJobTypes = new Set((progress?.active_jobs ?? []).map(j => j.job_type));
  const isAnyJobRunning = (types: string[]) => types.some(t => activeJobTypes.has(t));

  const stepStatuses: Record<WorkspaceSection, StepStatus> = {
    overview: "complete",
    script: isScriptJobRunning || isAnyJobRunning(["generate_script"])
      ? "in_progress" : hasScript ? "complete" : "available",
    structure: isSceneJobRunning || isAnyJobRunning(["plan_scenes", "plan_shots", "plan_frames"])
      ? "in_progress" : (hasShots && hasFrames) ? "complete" : hasScenes ? "available" : hasScript ? "available" : "locked",
    style: hasScenes ? "available" : "locked",
    images: isAnyJobRunning(["generate_image", "generate_images"])
      ? "in_progress" : hasImages ? "complete" : hasFrames ? "available" : "locked",
    videos: isAnyJobRunning(["generate_video", "generate_videos"])
      ? "in_progress" : hasVideos ? "complete" : hasImages ? "available" : "locked",
    "tts-subtitle": isAnyJobRunning(["generate_tts", "generate_subtitles"])
      ? "in_progress" : (hasVoices && hasSubtitles) ? "complete" : hasVoices ? "available" : hasScenes ? "available" : "locked",
    timeline: isAnyJobRunning(["compose_timeline"])
      ? "in_progress" : hasTimelines ? "complete" : (hasVideos || hasImages) ? "available" : "locked",
    render: isAnyJobRunning(["render"])
      ? "in_progress" : hasRenders ? "complete" : hasTimelines ? "available" : "locked",
    qa: activeVersion ? "available" : "locked",
    export: hasRenders ? "complete" : "available",
  };

  const sidebarVersionList = (
    <div>
      <p className="text-[11px] font-semibold text-neutral-500 mb-2">대본 버전</p>
      <div className="space-y-1 max-h-48 overflow-y-auto">
        {versions.slice(0, 8).map((v) => {
          const isVActive = activeVersion?.id === v.id;
          const plan = v.plan_json as ScriptPlan | null;
          return (
            <button
              key={v.id}
              onClick={() => selectVersion(v)}
              className={`w-full rounded px-2 py-1.5 text-left text-[11px] transition ${
                isVActive
                  ? "bg-blue-900/30 text-blue-300"
                  : "text-neutral-500 hover:bg-neutral-800 hover:text-neutral-300"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">v{v.version}</span>
                <span className={`text-[9px] ${v.status === "structured" ? "text-emerald-400" : "text-neutral-600"}`}>
                  {v.status}
                </span>
              </div>
              {plan?.title && (
                <p className="text-[10px] text-neutral-600 truncate mt-0.5">{plan.title}</p>
              )}
            </button>
          );
        })}
        {versions.length === 0 && (
          <p className="text-[10px] text-neutral-600">아직 대본 없음</p>
        )}
      </div>
    </div>
  );

  return (
    <WorkspaceLayout
      projectTitle={project.title}
      projectDescription={project.description}
      section={section}
      onSectionChange={setSection}
      stepStatuses={stepStatuses}
      sidebarFooter={sidebarVersionList}
    >
      {/* ═══ Overview ═══ */}
      {section === "overview" && (
        <div className="space-y-6">
          {/* Mode Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">{project.title}</h1>
              {project.description && (
                <p className="mt-1 text-sm text-neutral-400">{project.description}</p>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setEasyMode(true)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  easyMode ? "bg-blue-600 text-white" : "bg-neutral-800 text-neutral-400 hover:text-neutral-200"
                }`}
              >
                간편 모드
              </button>
              <button
                onClick={() => setEasyMode(false)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  !easyMode ? "bg-blue-600 text-white" : "bg-neutral-800 text-neutral-400 hover:text-neutral-200"
                }`}
              >
                전문가 모드
              </button>
            </div>
          </div>

          {!hasApiKey && (
            <div className="rounded-lg border border-amber-700/50 bg-amber-950/30 px-4 py-3">
              <p className="text-sm font-semibold text-amber-400">
                AI 기능을 사용하려면 API 키가 필요합니다
              </p>
              <p className="text-xs text-amber-400/70 mt-1">
                <code className="bg-amber-900/40 px-1 rounded">.env</code> 파일에 API 키를 설정한 뒤
                컨테이너를 재시작하세요.
              </p>
            </div>
          )}

          {easyMode ? (
            <AutoPilot
              projectId={projectId}
              onComplete={() => fetchVersions()}
              onSwitchToExpert={() => { setEasyMode(false); setSection("script"); }}
            />
          ) : (
            <NextStepGuide
              currentSection={section}
              stepStatuses={stepStatuses}
              onNavigate={setSection}
              hasApiKey={hasApiKey}
            />
          )}

          {/* Pipeline Inspector */}
          <PipelineInspector projectId={projectId} />

          {/* Cost summary */}
          {(hasImages || hasVideos || hasVoices) && (
            <div className="border-t border-neutral-800 pt-4">
              <CostDashboard projectId={projectId} />
            </div>
          )}
        </div>
      )}

      {/* ═══ Script ═══ */}
      {section === "script" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
            <h2 className="text-lg font-semibold mb-4">대본 생성</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-1">
                  주제 / 목표 *
                </label>
                <textarea
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="영상의 주제나 목표를 구체적으로 작성하세요..."
                  rows={2}
                  className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 placeholder-neutral-500 focus:border-blue-500 focus:outline-none resize-none"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-1">
                    타깃 시청자
                  </label>
                  <input
                    type="text"
                    value={audience}
                    onChange={(e) => setAudience(e.target.value)}
                    placeholder="20~30대 직장인"
                    className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 placeholder-neutral-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-1">
                    톤 / 분위기
                  </label>
                  <input
                    type="text"
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                    placeholder="감성적, 편안한"
                    className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 placeholder-neutral-500 focus:border-blue-500 focus:outline-none"
                  />
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    {TONE_SUGGESTIONS.map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setTone((p) => (p ? `${p}, ${t}` : t))}
                        className="rounded-full bg-neutral-800 px-2 py-0.5 text-[11px] text-neutral-400 hover:bg-neutral-700 hover:text-neutral-200 transition"
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-1">
                    영상 길이
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      value={duration}
                      onChange={(e) =>
                        setDuration(Math.max(10, Math.min(600, Number(e.target.value))))
                      }
                      min={10}
                      max={600}
                      className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none"
                    />
                    <span className="text-xs text-neutral-500 shrink-0">초</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-1">포맷</label>
                  <select
                    value={format}
                    onChange={(e) => setFormat(e.target.value)}
                    className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none"
                  >
                    {FORMAT_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-1">언어</label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none"
                  >
                    <option value="ko">한국어</option>
                    <option value="en">English</option>
                    <option value="ja">日本語</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-1">
                  추가 제약 조건 (선택)
                </label>
                <textarea
                  value={constraints}
                  onChange={(e) => setConstraints(e.target.value)}
                  placeholder="예: 배경음악은 로파이, 실사 배경 금지..."
                  rows={2}
                  className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 placeholder-neutral-500 focus:border-blue-500 focus:outline-none resize-none"
                />
              </div>
              <button
                type="submit"
                disabled={submitting || !topic.trim() || !!isScriptJobRunning}
                className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium transition hover:bg-blue-500 disabled:opacity-50"
              >
                {isScriptJobRunning ? "생성 중..." : submitting ? "제출 중..." : "대본 생성"}
              </button>
            </form>
          </div>

          {activeJob && <JobStatusPanel job={activeJob} label="대본 생성 작업" />}

          {activeVersion?.plan_json && (
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">
                  대본 플랜 v{activeVersion.version}
                </h2>
                <StatusBadge status={activeVersion.status} />
              </div>
              <ScriptPlanView plan={activeVersion.plan_json as ScriptPlan} />
            </div>
          )}
        </div>
      )}

      {/* ═══ Structure (Scene/Shot/Frame) ═══ */}
      {section === "structure" && (
        <div className="space-y-6">
          {!activeVersion && (
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-8 text-center">
              <p className="text-neutral-400">먼저 대본을 생성하세요.</p>
              <button
                onClick={() => setSection("script")}
                className="mt-3 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium transition hover:bg-blue-500"
              >
                대본 생성으로 이동
              </button>
            </div>
          )}
          {activeVersion && (
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-semibold">Scene 구성</h2>
                  {hasScenes && (
                    <p className="text-xs text-neutral-500 mt-1">
                      {scenes.length}개 장면 · 총 {Math.round(totalSceneDur)}초
                    </p>
                  )}
                </div>
                <button
                  onClick={generateScenes}
                  disabled={!!isSceneJobRunning || !activeVersion.raw_text}
                  className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium transition hover:bg-purple-500 disabled:opacity-50"
                >
                  {isSceneJobRunning
                    ? "생성 중..."
                    : hasScenes
                      ? "Scene 재생성"
                      : "Scene 분해"}
                </button>
              </div>

              {sceneJob &&
                sceneJob.status !== "completed" &&
                sceneJob.status !== "failed" && (
                  <div className="mb-4">
                    <JobStatusPanel job={sceneJob} label="Scene 계획 작업" />
                  </div>
                )}
              {sceneJob?.status === "failed" && (
                <p className="text-sm text-red-300 mb-4">
                  {sceneJob.error_message || "Scene 생성 실패"}
                </p>
              )}

              {hasScenes ? (
                <div className="space-y-2">
                  {scenes.map((sc) => (
                    <SceneCard
                      key={sc.id}
                      scene={sc}
                      projectId={projectId}
                      onSceneRegenerate={regenerateScene}
                      sceneRegeneratingId={regeneratingSceneId}
                      pollJob={pollJob}
                    />
                  ))}
                </div>
              ) : (
                !isSceneJobRunning && (
                  <p className="text-sm text-neutral-500 text-center py-6">
                    아직 Scene이 생성되지 않았습니다.
                  </p>
                )
              )}
            </div>
          )}
        </div>
      )}

      {/* ═══ Style & Character ═══ */}
      {section === "style" && (
        <>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">스타일 설정</h2>
              <p className="text-sm text-neutral-400 mt-1">영상의 비주얼 스타일을 선택합니다.</p>
            </div>
            <Button onClick={() => setShowStylePicker(true)}>
              스타일 선택
            </Button>
          </div>
          <StyleCharacterPanel
            projectId={projectId}
            activeStylePresetId={project.active_style_preset_id}
            onActiveStyleChange={(id) => {
              setProject((prev) =>
                prev ? { ...prev, active_style_preset_id: id } : prev,
              );
            }}
          />
          <StylePickerModal
            open={showStylePicker}
            onClose={() => setShowStylePicker(false)}
            projectId={projectId}
            activeStyleId={project.active_style_preset_id}
            onSelect={(preset) => {
              setProject((prev) =>
                prev ? { ...prev, active_style_preset_id: preset.id } : prev,
              );
            }}
          />
        </>
      )}

      {/* ═══ Images (Studio) ═══ */}
      {section === "images" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">AI 스튜디오</h2>
              <p className="text-sm text-neutral-400 mt-1">
                컷별 이미지/비디오 실시간 생성 · 진행률 확인
              </p>
            </div>
            {allShots.length > 0 && (
              <div className="flex items-center gap-2">
                <Button variant="secondary" size="sm" onClick={() => setShowVoicePicker(true)}>
                  보이스 선택
                </Button>
                <Button variant="secondary" size="sm" onClick={() => setShowStylePicker(true)}>
                  스타일
                </Button>
              </div>
            )}
          </div>
          {!hasScenes ? (
            <LockedSection message="Scene/Shot 구조를 먼저 생성하세요." target="structure" onNavigate={setSection} />
          ) : allShots.length > 0 && activeVersion ? (
            <StudioPage
              projectId={projectId}
              scenes={scenes}
              shots={allShots}
              frames={allFrames}
              versionId={activeVersion.id}
              onComplete={() => fetchProgress()}
            />
          ) : (
            <>
              <div className="rounded-lg border border-blue-900/40 bg-blue-950/20 p-4 space-y-1">
                <p className="text-xs text-blue-300 font-medium">Best-of-N 이미지 생성 워크플로우</p>
                <p className="text-[11px] text-blue-300/70">
                  1. Shot을 펼치고 Frame Spec에서 variant 수(2~4개)를 선택한 뒤 <strong>이미지 생성</strong> 클릭
                </p>
                <p className="text-[11px] text-blue-300/70">
                  2. 그리드에서 각 이미지를 비교하고 <strong>클릭으로 BEST 선택</strong> · 메모를 남겨 기록
                </p>
                <p className="text-[11px] text-blue-300/70">
                  3. 만족스럽지 않으면 <strong>추가 생성</strong>으로 기존 결과를 보존한 채 새 후보 추가
                </p>
              </div>
              <div className="space-y-2">
                {scenes.map((sc) => (
                  <SceneCard
                    key={sc.id}
                    scene={sc}
                    projectId={projectId}
                    onSceneRegenerate={regenerateScene}
                    sceneRegeneratingId={regeneratingSceneId}
                    pollJob={pollJob}
                  />
                ))}
              </div>
            </>
          )}

          <VoicePicker
            open={showVoicePicker}
            onClose={() => setShowVoicePicker(false)}
            projectId={projectId}
            selectedVoiceId={selectedVoiceId}
            onSelect={(v) => setSelectedVoiceId(v.id)}
          />
          <StylePickerModal
            open={showStylePicker}
            onClose={() => setShowStylePicker(false)}
            projectId={projectId}
            activeStyleId={project.active_style_preset_id}
            onSelect={(preset) => {
              setProject((prev) =>
                prev ? { ...prev, active_style_preset_id: preset.id } : prev,
              );
            }}
          />
        </div>
      )}

      {/* ═══ Videos ═══ */}
      {section === "videos" && (
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-semibold">비디오 생성</h2>
            <p className="text-sm text-neutral-400 mt-1">
              Shot 단위로 2~8초 영상 클립을 생성합니다.
            </p>
          </div>
          {!hasScenes ? (
            <LockedSection message="Scene/Shot 구조를 먼저 생성하세요." target="structure" onNavigate={setSection} />
          ) : (
            <>
              <div className="rounded-lg border border-teal-900/40 bg-teal-950/20 p-4 space-y-1">
                <p className="text-xs text-teal-300 font-medium">Best-of-N 비디오 생성 워크플로우</p>
                <p className="text-[11px] text-teal-300/70">
                  1. Shot을 펼치고 모드(Auto/I→V/T→V)와 variant 수(1~3개)를 선택한 뒤 <strong>비디오 생성</strong> 클릭
                </p>
                <p className="text-[11px] text-teal-300/70">
                  2. variant 목록에서 <strong>비교</strong> 버튼으로 나란히 재생 비교 · BEST 선택은 <strong>클릭</strong>
                </p>
                <p className="text-[11px] text-teal-300/70">
                  3. <strong>추가 생성</strong>은 기존 클립을 보존하며 새 후보를 추가합니다. 선택된 것만 타임라인에 반영
                </p>
              </div>
              <div className="space-y-2">
                {scenes.map((sc) => (
                  <SceneCard
                    key={sc.id}
                    scene={sc}
                    projectId={projectId}
                    onSceneRegenerate={regenerateScene}
                    sceneRegeneratingId={regeneratingSceneId}
                    pollJob={pollJob}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ═══ TTS / Subtitle ═══ */}
      {section === "tts-subtitle" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">TTS / 자막</h2>
              <p className="text-sm text-neutral-400 mt-1">
                나레이션 음성과 자막 트랙을 생성합니다.
              </p>
            </div>
            <Button variant="secondary" size="sm" onClick={() => setShowVoicePicker(true)}>
              보이스 선택
            </Button>
          </div>
          {!hasScenes ? (
            <LockedSection message="Scene/Shot 구조를 먼저 생성하세요." target="structure" onNavigate={setSection} />
          ) : (
            <>
              {selectedVoiceId && (
                <div className="rounded-lg border border-violet-900/40 bg-violet-950/20 p-3 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center text-xs font-bold text-white">V</div>
                  <div>
                    <p className="text-xs text-violet-300 font-medium">선택된 보이스</p>
                    <p className="text-[11px] text-neutral-400">{selectedVoiceId}</p>
                  </div>
                </div>
              )}
              <div className="rounded-lg border border-pink-900/40 bg-pink-950/20 p-4">
                <p className="text-xs text-pink-300">
                  Shot별 TTS는 각 Shot 카드 안에서 개별 생성합니다.
                  아래에서 프로젝트 전체 자막을 생성할 수 있습니다.
                </p>
                <button
                  onClick={() => setSection("structure")}
                  className="mt-2 rounded bg-pink-800/50 px-3 py-1 text-[11px] text-pink-300 font-medium hover:bg-pink-800 transition"
                >
                  Shot별 TTS 생성 → 구조 탭
                </button>
              </div>
              <VoicePicker
                open={showVoicePicker}
                onClose={() => setShowVoicePicker(false)}
                projectId={projectId}
                selectedVoiceId={selectedVoiceId}
                onSelect={(v) => setSelectedVoiceId(v.id)}
              />

              {activeVersion && (
                <SubtitlePanel
                  projectId={projectId}
                  scriptVersionId={activeVersion.id}
                  pollJob={pollJob}
                />
              )}
            </>
          )}
        </div>
      )}

      {/* ═══ Timeline ═══ */}
      {section === "timeline" && (
        <div className="space-y-6">
          {!hasScenes || !activeVersion ? (
            <LockedSection message="Scene/Shot 구조를 먼저 생성하세요." target="structure" onNavigate={setSection} />
          ) : (
            <TimelinePanel
              projectId={projectId}
              scriptVersionId={activeVersion.id}
              pollJob={pollJob}
            />
          )}
        </div>
      )}

      {/* ═══ Render ═══ */}
      {section === "render" && (
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-semibold">최종 렌더</h2>
            <p className="text-sm text-neutral-400 mt-1">
              타임라인 데이터를 FFmpeg로 합성하여 최종 MP4를 생성합니다.
            </p>
          </div>
          {!hasScenes || !activeVersion ? (
            <LockedSection message="타임라인을 먼저 조립하세요." target="timeline" onNavigate={setSection} />
          ) : (
            <TimelinePanel
              projectId={projectId}
              scriptVersionId={activeVersion.id}
              pollJob={pollJob}
            />
          )}
        </div>
      )}

      {/* ═══ QA ═══ */}
      {section === "qa" && (
        <div className="space-y-6">
          {!activeVersion ? (
            <LockedSection message="대본을 먼저 생성하세요." target="script" onNavigate={setSection} />
          ) : (
            <>
              <QAPanel projectId={projectId} scriptVersionId={activeVersion.id} />
              <QualityEvaluationPanel projectId={projectId} scriptVersionId={activeVersion.id} />
            </>
          )}
        </div>
      )}

      {/* ═══ Export ═══ */}
      {section === "export" && (
        <div className="space-y-6">
          <ExportPanel projectId={projectId} />
          <div className="border-t border-neutral-800 pt-6">
            <h2 className="text-lg font-semibold mb-4">비용 분석</h2>
            <CostDashboard projectId={projectId} />
          </div>
        </div>
      )}
    </WorkspaceLayout>
  );
}
