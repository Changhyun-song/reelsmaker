"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { apiUrl } from "@/lib/api";
import type { SceneData, ShotData, FrameData, AssetData } from "@/lib/types";
import CutListPanel, { type CutItem, type ShotImportance } from "./CutListPanel";
import CutInspector, {
  type FrameDetail,
  type ShotDetail,
  type FrameSavePayload,
  type ShotSavePayload,
} from "./CutInspector";

/* ── Types ──────────────────────────────────────────── */

interface StoryboardEditorProps {
  projectId: string;
  scenes: SceneData[];
  shots: ShotData[];
  frames: FrameData[];
}

type FilterMode = "all" | "key_cuts" | "no_image" | "needs_review" | "manual_review";

interface BatchJob {
  frameId: string;
  cutIndex: number;
  status: "queued" | "running" | "done" | "error";
  error?: string;
}

/* ── API helper ─────────────────────────────────────── */

async function api(path: string, opts?: RequestInit) {
  const res = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.json();
}

/* ── Shot importance classification ─────────────────── */

const EMOTION_PEAK_KEYWORDS = [
  "dramatic", "intense", "climax", "reveal", "shock", "surprise",
  "emotional", "cry", "scream", "rage", "joy", "explosion",
  "절정", "클라이맥스", "감동", "충격", "반전", "눈물",
  "분노", "환희", "폭발", "비명",
];

const ACTION_PEAK_KEYWORDS = [
  "fight", "chase", "crash", "explosion", "battle", "run",
  "jump", "attack", "escape", "collision", "transform",
  "전투", "추격", "폭발", "싸움", "도주", "변신", "충돌",
];

const CLOSE_UP_TYPES = [
  "close-up", "close_up", "closeup", "extreme_close", "extreme close",
  "클로즈업", "익스트림", "clo",
];

interface ClassificationResult {
  importance: ShotImportance;
  reasons: string[];
  needsManualReview: boolean;
}

function classifyCut(
  cut: { sceneIndex: number; shotIndex: number; frameRole: string },
  shot: ShotData | undefined,
  allSceneCuts: { sceneIndex: number; shotIndex: number }[],
): ClassificationResult {
  const reasons: string[] = [];

  const sceneCuts = allSceneCuts.filter(c => c.sceneIndex === cut.sceneIndex);
  const isFirst = sceneCuts.length > 0 && cut.shotIndex <= (sceneCuts[0]?.shotIndex ?? 0);
  const isLast = sceneCuts.length > 0 && cut.shotIndex >= (sceneCuts[sceneCuts.length - 1]?.shotIndex ?? 0);

  if (isFirst) reasons.push("씬 오프너");
  if (isLast && sceneCuts.length > 1) reasons.push("씬 엔딩");

  const desc = (shot?.description || "").toLowerCase();
  const emotion = (shot?.emotion || "").toLowerCase();
  const purpose = (shot?.purpose || "").toLowerCase();
  const shotType = (shot?.shot_type || "").toLowerCase();
  const framing = (shot?.camera_framing || "").toLowerCase();
  const narration = (shot?.narration_segment || "").toLowerCase();

  if (CLOSE_UP_TYPES.some(kw => shotType.includes(kw) || framing.includes(kw))) {
    reasons.push("클로즈업/히어로");
  }

  const allText = `${desc} ${emotion} ${purpose} ${narration}`;
  if (EMOTION_PEAK_KEYWORDS.some(kw => allText.includes(kw))) {
    reasons.push("감정 절정");
  }
  if (ACTION_PEAK_KEYWORDS.some(kw => allText.includes(kw))) {
    reasons.push("액션 피크");
  }

  if (purpose.includes("reveal") || purpose.includes("intro") || desc.includes("first appear") || desc.includes("첫 등장")) {
    reasons.push("캐릭터 등장");
  }

  if (purpose.includes("hero") || purpose.includes("iconic") || purpose.includes("signature")) {
    reasons.push("히어로 샷");
  }

  let importance: ShotImportance;
  if (reasons.length >= 2 || reasons.some(r => ["씬 오프너", "감정 절정", "액션 피크", "캐릭터 등장", "히어로 샷"].includes(r))) {
    importance = "key";
  } else if (reasons.length === 1) {
    importance = "normal";
  } else {
    const isMidScene = !isFirst && !isLast;
    const isTransitionShot = shotType.includes("transition") || shotType.includes("establishing") || shotType.includes("cutaway");
    importance = (isMidScene && isTransitionShot) ? "filler" : "normal";
  }

  const needsManualReview = importance === "key" ||
    (importance === "normal" && reasons.length > 0);

  return { importance, reasons, needsManualReview };
}

/* ── Batch progress bar ─────────────────────────────── */

function BatchProgress({ jobs, onCancel }: { jobs: BatchJob[]; onCancel: () => void }) {
  const done = jobs.filter(j => j.status === "done").length;
  const errored = jobs.filter(j => j.status === "error").length;
  const total = jobs.length;
  const running = jobs.filter(j => j.status === "running").length;
  const pct = total > 0 ? Math.round(((done + errored) / total) * 100) : 0;

  return (
    <div className="rounded-lg border border-blue-800/30 bg-blue-950/10 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-medium text-blue-400">
            일괄 생성 진행 중 ({done + errored}/{total})
          </span>
        </div>
        <button onClick={onCancel} className="text-[9px] text-neutral-500 hover:text-neutral-300">중단</button>
      </div>
      <div className="h-1.5 rounded-full bg-neutral-800 overflow-hidden">
        <div className="h-full flex">
          <div className="bg-emerald-500 transition-all" style={{ width: `${(done / total) * 100}%` }} />
          <div className="bg-red-500 transition-all" style={{ width: `${(errored / total) * 100}%` }} />
          <div className="bg-blue-500 transition-all" style={{ width: `${(running / total) * 100}%` }} />
        </div>
      </div>
      <div className="flex items-center gap-3 text-[9px]">
        <span className="text-emerald-400">{done} 완료</span>
        {errored > 0 ? <span className="text-red-400">{errored} 실패</span> : null}
        <span className="text-neutral-600">{pct}%</span>
      </div>
      {errored > 0 ? (
        <div className="space-y-1">
          {jobs.filter(j => j.status === "error").slice(0, 3).map(j => (
            <p key={j.frameId} className="text-[9px] text-red-400/80">
              컷 {j.cutIndex + 1}: {j.error || "실패"}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

/* ── Workflow guide ──────────────────────────────────── */

function WorkflowGuide({ onClose, manualRatio }: { onClose: () => void; manualRatio: number }) {
  const steps = [
    { num: 1, label: "Continuity Bible 저장", desc: "스타일 섹션에서 전체 영상 규칙을 먼저 설정하세요" },
    { num: 2, label: "전체 이미지 자동 생성", desc: "'전체 이미지 생성' 버튼으로 한번에 실행" },
    { num: 3, label: "핵심 컷만 검토", desc: "핵심 컷 필터 → 수동 검토 권장 컷만 확인" },
    { num: 4, label: "문제 컷만 재생성", desc: "프롬프트 수정 후 개별 재생성 (전체의 20~30%)" },
    { num: 5, label: "승인 → 비디오", desc: "이미지 승인 후 비디오 단계로 진행" },
  ];

  return (
    <div className="rounded-xl border border-blue-800/20 bg-blue-950/5 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-blue-400">권장 워크플로</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
            manualRatio <= 30 ? "bg-emerald-900/30 text-emerald-400" : "bg-amber-900/30 text-amber-400"
          }`}>
            수동 검토 권장 {manualRatio}%
          </span>
        </div>
        <button onClick={onClose} className="text-neutral-600 hover:text-neutral-400 text-xs">✕</button>
      </div>
      <p className="text-[10px] text-neutral-500">
        이 화면은 모든 프레임을 수동으로 작성하는 곳이 아닙니다.
        자동 생성 결과를 검토하고, <strong className="text-neutral-400">수동 검토가 권장된 핵심 컷</strong>만 수정하세요.
        나머지는 자동 결과를 그대로 사용해도 충분합니다.
      </p>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {steps.map(s => (
          <div key={s.num} className="shrink-0 w-36 rounded-lg bg-neutral-800/40 border border-neutral-800/60 p-2.5">
            <div className="flex items-center gap-1.5 mb-1">
              <span className="w-5 h-5 rounded-full bg-blue-600/20 text-blue-400 text-[10px] font-bold flex items-center justify-center">
                {s.num}
              </span>
              <span className="text-[10px] font-medium text-neutral-300">{s.label}</span>
            </div>
            <p className="text-[9px] text-neutral-500 leading-snug">{s.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Review ratio meter ─────────────────────────────── */

function ReviewRatioMeter({ total, keyCount, normalCount, fillerCount, manualCount }: {
  total: number; keyCount: number; normalCount: number; fillerCount: number; manualCount: number;
}) {
  if (total === 0) return null;
  const pctKey = (keyCount / total) * 100;
  const pctNormal = (normalCount / total) * 100;
  const pctFiller = (fillerCount / total) * 100;
  const manualPct = Math.round((manualCount / total) * 100);

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-2.5 space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-bold text-neutral-500">Shot 중요도 분포</span>
        <span className={`text-[9px] font-medium ${
          manualPct <= 30 ? "text-emerald-400" : manualPct <= 50 ? "text-amber-400" : "text-red-400"
        }`}>
          수동 보정 {manualPct}% {manualPct <= 30 ? "(최적)" : manualPct <= 50 ? "(적정)" : "(과다 — 권장 20~30%)"}
        </span>
      </div>
      <div className="h-2 rounded-full bg-neutral-800 overflow-hidden flex">
        <div className="bg-violet-500 transition-all" style={{ width: `${pctKey}%` }} title={`핵심 ${keyCount}`} />
        <div className="bg-blue-500 transition-all" style={{ width: `${pctNormal}%` }} title={`일반 ${normalCount}`} />
        <div className="bg-neutral-600 transition-all" style={{ width: `${pctFiller}%` }} title={`연결 ${fillerCount}`} />
      </div>
      <div className="flex items-center gap-3 text-[8px]">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-violet-500" />핵심 {keyCount}</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500" />일반 {normalCount}</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-neutral-600" />연결 {fillerCount}</span>
      </div>
    </div>
  );
}

/* ── Main component ─────────────────────────────────── */

export default function StoryboardEditor({
  projectId,
  scenes,
  shots,
  frames,
}: StoryboardEditorProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [assets, setAssets] = useState<Map<string, AssetData[]>>(new Map());
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filterMode, setFilterMode] = useState<FilterMode>("all");
  const [showGuide, setShowGuide] = useState(true);
  const [batchJobs, setBatchJobs] = useState<BatchJob[]>([]);
  const [batchRunning, setBatchRunning] = useState(false);
  const batchCancelRef = useState({ cancelled: false })[0];

  // Build shot lookup
  const shotMap = useMemo(() => {
    const map = new Map<string, ShotData>();
    for (const s of shots) map.set(s.id, s);
    return map;
  }, [shots]);

  // Build flat cut list with importance classification
  const allCuts: CutItem[] = useMemo(() => {
    const result: CutItem[] = [];
    let cutIdx = 0;
    const sortedScenes = [...scenes].sort((a, b) => a.order_index - b.order_index);

    // Pre-collect all scene/shot indices for scene boundary detection
    const allSceneShotIndices: { sceneIndex: number; shotIndex: number }[] = [];
    for (const scene of sortedScenes) {
      const sceneShots = shots.filter(s => s.scene_id === scene.id).sort((a, b) => a.order_index - b.order_index);
      for (const shot of sceneShots) {
        allSceneShotIndices.push({ sceneIndex: scene.order_index, shotIndex: shot.order_index });
      }
    }

    for (const scene of sortedScenes) {
      const sceneShots = shots.filter(s => s.scene_id === scene.id).sort((a, b) => a.order_index - b.order_index);
      for (const shot of sceneShots) {
        const shotFrames = frames.filter(f => f.shot_id === shot.id).sort((a, b) => a.order_index - b.order_index);
        for (const frame of shotFrames) {
          const frameAssets = assets.get(frame.id) || [];
          const imageAssets = frameAssets.filter(a => a.asset_type === "image");
          const selectedImage = imageAssets.find(a => a.is_selected) || imageAssets[0];
          let imageStatus: CutItem["imageStatus"] = "none";
          if (selectedImage) {
            if (selectedImage.status === "approved") imageStatus = "approved";
            else if (selectedImage.status === "rejected") imageStatus = "rejected";
            else imageStatus = "ready";
          }
          const videoAssets = frameAssets.filter(a => a.asset_type === "video");
          const videoStatus: CutItem["videoStatus"] = videoAssets.some(a => a.status === "ready") ? "ready" : "none";

          const classification = classifyCut(
            { sceneIndex: scene.order_index, shotIndex: shot.order_index, frameRole: frame.frame_role || "start" },
            shotMap.get(shot.id),
            allSceneShotIndices,
          );

          result.push({
            cutIndex: cutIdx++,
            frameId: frame.id,
            shotId: shot.id,
            shotIndex: shot.order_index,
            sceneIndex: scene.order_index,
            frameRole: frame.frame_role || "start",
            narration: shot.narration_segment,
            durationMs: frame.duration_ms || 3000,
            imageStatus,
            videoStatus,
            hasPrompt: !!frame.visual_prompt,
            thumbnailUrl: selectedImage?.url || null,
            importance: classification.importance,
            importanceReasons: classification.reasons,
            needsManualReview: classification.needsManualReview,
          });
        }
      }
    }
    return result;
  }, [scenes, shots, frames, assets, shotMap]);

  // Filter cuts
  const cuts = useMemo(() => {
    if (filterMode === "all") return allCuts;
    if (filterMode === "key_cuts") return allCuts.filter(c => c.importance === "key");
    if (filterMode === "no_image") return allCuts.filter(c => c.imageStatus === "none");
    if (filterMode === "needs_review") return allCuts.filter(c => c.imageStatus === "ready" || c.imageStatus === "rejected");
    if (filterMode === "manual_review") return allCuts.filter(c => c.needsManualReview);
    return allCuts;
  }, [allCuts, filterMode]);

  // Stats
  const stats = useMemo(() => {
    const total = allCuts.length;
    const withImage = allCuts.filter(c => c.imageStatus !== "none").length;
    const approved = allCuts.filter(c => c.imageStatus === "approved").length;
    const noImage = allCuts.filter(c => c.imageStatus === "none").length;
    const withPrompt = allCuts.filter(c => c.hasPrompt).length;
    const keyCuts = allCuts.filter(c => c.importance === "key").length;
    const normalCuts = allCuts.filter(c => c.importance === "normal").length;
    const fillerCuts = allCuts.filter(c => c.importance === "filler").length;
    const manualReview = allCuts.filter(c => c.needsManualReview).length;
    return { total, withImage, approved, noImage, withPrompt, keyCuts, normalCuts, fillerCuts, manualReview };
  }, [allCuts]);

  const manualRatio = stats.total > 0 ? Math.round((stats.manualReview / stats.total) * 100) : 0;

  // Load assets
  useEffect(() => {
    let cancelled = false;
    const loadAssets = async () => {
      try {
        setLoadError(null);
        const map = new Map<string, AssetData[]>();
        for (const frame of frames) {
          try {
            const res = await api(`/api/projects/${projectId}/frames/${frame.id}/assets`);
            if (!cancelled) map.set(frame.id, res.assets || []);
          } catch { /* skip */ }
        }
        if (!cancelled) setAssets(map);
      } catch (e) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : "에셋 로딩 실패");
      }
    };
    if (frames.length > 0) loadAssets();
    return () => { cancelled = true; };
  }, [projectId, frames]);

  const selectedCut = cuts[selectedIndex] || null;

  const frameDetail: FrameDetail | null = useMemo(() => {
    if (!selectedCut) return null;
    const f = frames.find(fr => fr.id === selectedCut.frameId);
    if (!f) return null;
    return {
      id: f.id,
      visual_prompt: f.visual_prompt,
      negative_prompt: f.negative_prompt,
      dialogue: f.dialogue ?? null,
      duration_ms: f.duration_ms ?? 3000,
      composition: f.composition,
      mood: f.mood,
      action_pose: f.action_pose,
      background_description: f.background_description,
      continuity_notes: f.continuity_notes,
      forbidden_elements: f.forbidden_elements,
    };
  }, [selectedCut, frames]);

  const shotDetail: ShotDetail | null = useMemo(() => {
    if (!selectedCut) return null;
    const s = shots.find(sh => sh.id === selectedCut.shotId);
    if (!s) return null;
    return {
      id: s.id,
      narration_segment: s.narration_segment,
      description: s.description,
      duration_sec: s.duration_sec,
      camera_movement: s.camera_movement,
      emotion: s.emotion,
    };
  }, [selectedCut, shots]);

  const handleFrameSave = useCallback(async (payload: FrameSavePayload) => {
    setSaving(true);
    try {
      const { frameId, ...fields } = payload;
      await api(`/api/projects/${projectId}/frames/${frameId}`, { method: "PATCH", body: JSON.stringify(fields) });
    } finally { setSaving(false); }
  }, [projectId]);

  const handleShotSave = useCallback(async (payload: ShotSavePayload) => {
    setSaving(true);
    try {
      const { shotId, ...fields } = payload;
      await api(`/api/projects/${projectId}/shots/${shotId}/edit`, { method: "PATCH", body: JSON.stringify(fields) });
    } finally { setSaving(false); }
  }, [projectId]);

  const handleRegenerateImage = useCallback(async (frameId: string) => {
    try {
      await api(`/api/projects/${projectId}/frames/${frameId}/images/generate`, {
        method: "POST",
        body: JSON.stringify({ num_variants: 2 }),
      });
    } catch { /* handled in UI */ }
  }, [projectId]);

  // Batch execution
  const runBatch = useCallback(async (targetCuts: CutItem[]) => {
    if (batchRunning || targetCuts.length === 0) return;
    setBatchRunning(true);
    batchCancelRef.cancelled = false;

    const jobs: BatchJob[] = targetCuts.map(c => ({
      frameId: c.frameId,
      cutIndex: c.cutIndex,
      status: "queued" as const,
    }));
    setBatchJobs([...jobs]);

    const CONCURRENCY = 3;
    let idx = 0;

    const runNext = async (): Promise<void> => {
      while (idx < jobs.length) {
        if (batchCancelRef.cancelled) return;
        const i = idx++;
        const job = jobs[i];
        job.status = "running";
        setBatchJobs([...jobs]);

        try {
          await api(`/api/projects/${projectId}/frames/${job.frameId}/images/generate`, {
            method: "POST",
            body: JSON.stringify({ num_variants: 2 }),
          });
          job.status = "done";
        } catch (e) {
          job.status = "error";
          job.error = e instanceof Error ? e.message : "실패";
        }
        setBatchJobs([...jobs]);
      }
    };

    const workers = Array.from({ length: Math.min(CONCURRENCY, jobs.length) }, () => runNext());
    await Promise.all(workers);
    setBatchRunning(false);
  }, [projectId, batchRunning, batchCancelRef]);

  const cancelBatch = useCallback(() => {
    batchCancelRef.cancelled = true;
    setBatchRunning(false);
  }, [batchCancelRef]);

  const handleReorder = useCallback((_from: number, _to: number) => {}, []);

  if (frames.length === 0) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-8 text-center">
        <p className="text-sm text-neutral-500">프레임이 없습니다</p>
        <p className="text-xs text-neutral-600 mt-1">장면 구성 → 샷 계획 → 프레임 생성을 먼저 실행하세요.</p>
      </div>
    );
  }

  const impStyle = selectedCut ? {
    key: { badge: "bg-violet-900/40 text-violet-400 border-violet-700/30", label: "핵심 컷" },
    normal: { badge: "bg-blue-900/30 text-blue-400 border-blue-800/30", label: "일반 컷" },
    filler: { badge: "bg-neutral-800 text-neutral-500 border-neutral-700/30", label: "연결 컷" },
  }[selectedCut.importance] : null;

  return (
    <div className="space-y-3">
      {/* Workflow guide */}
      {showGuide ? <WorkflowGuide onClose={() => setShowGuide(false)} manualRatio={manualRatio} /> : null}

      {/* Review ratio meter */}
      <ReviewRatioMeter
        total={stats.total}
        keyCount={stats.keyCuts}
        normalCount={stats.normalCuts}
        fillerCount={stats.fillerCuts}
        manualCount={stats.manualReview}
      />

      {/* Action bar */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-4 text-[10px]">
            <span className="text-neutral-500">{stats.total}컷</span>
            <span className="text-violet-400">{stats.keyCuts} 핵심</span>
            <span className="text-emerald-400">{stats.approved} 승인</span>
            <span className="text-neutral-600">{stats.noImage} 미생성</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => runBatch(allCuts.filter(c => c.imageStatus === "none"))}
              disabled={batchRunning || stats.noImage === 0}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-[10px] font-medium text-white hover:bg-blue-500 transition disabled:opacity-40"
            >
              미생성 일괄 생성 ({stats.noImage})
            </button>
            <button
              onClick={() => runBatch(allCuts)}
              disabled={batchRunning}
              className="rounded-md bg-blue-600/80 px-3 py-1.5 text-[10px] font-medium text-white hover:bg-blue-500 transition disabled:opacity-40"
            >
              전체 이미지 생성
            </button>
            <button
              onClick={() => runBatch(allCuts.filter(c => c.importance === "key" && c.imageStatus === "none"))}
              disabled={batchRunning}
              className="rounded-md bg-violet-600/20 border border-violet-700/40 px-3 py-1.5 text-[10px] font-medium text-violet-400 hover:bg-violet-600/30 transition disabled:opacity-40"
            >
              핵심 컷만 ({stats.keyCuts})
            </button>
          </div>
        </div>

        {/* Filter buttons */}
        <div className="flex items-center gap-1.5 mt-2">
          {([
            ["all", `전체 (${allCuts.length})`],
            ["key_cuts", `핵심 (${stats.keyCuts})`],
            ["manual_review", `검토 권장 (${stats.manualReview})`],
            ["no_image", `미생성 (${stats.noImage})`],
            ["needs_review", `이미지 확인 (${allCuts.filter(c => c.imageStatus === "ready" || c.imageStatus === "rejected").length})`],
          ] as [FilterMode, string][]).map(([mode, label]) => (
            <button
              key={mode}
              onClick={() => { setFilterMode(mode); setSelectedIndex(0); }}
              className={`rounded-md px-2.5 py-1 text-[9px] font-medium border transition ${
                filterMode === mode
                  ? mode === "key_cuts" ? "bg-violet-600/20 border-violet-700/40 text-violet-400"
                    : "bg-blue-600/20 border-blue-700/40 text-blue-400"
                  : "bg-transparent border-neutral-800 text-neutral-500 hover:text-neutral-300"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Batch progress */}
      {batchJobs.length > 0 ? <BatchProgress jobs={batchJobs} onCancel={cancelBatch} /> : null}

      {/* Error banner */}
      {loadError ? (
        <div className="rounded-lg border border-red-800/40 bg-red-950/20 px-3 py-2">
          <p className="text-[10px] text-red-400">{loadError}</p>
        </div>
      ) : null}

      {/* 3-panel layout */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/30 overflow-hidden">
        <div className="flex h-[650px]">
          {/* Left: Cut list */}
          <div className="w-64 border-r border-neutral-800 shrink-0">
            <CutListPanel
              cuts={cuts}
              selectedIndex={selectedIndex}
              onSelect={setSelectedIndex}
              onReorder={handleReorder}
            />
          </div>

          {/* Center: Cut preview */}
          <div className="flex-1 flex flex-col items-center justify-center p-4 bg-neutral-950/30">
            {selectedCut ? (
              <div className="w-full max-w-md space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-blue-600 px-2 py-0.5 text-xs font-bold text-white">
                      #{selectedCut.cutIndex + 1}
                    </span>
                    <span className="text-xs text-neutral-400">
                      Scene {selectedCut.sceneIndex + 1} · Shot {selectedCut.shotIndex + 1}
                    </span>
                    {impStyle ? (
                      <span className={`text-[8px] px-1.5 py-0.5 rounded border font-medium ${impStyle.badge}`}>
                        {impStyle.label}
                      </span>
                    ) : null}
                    {selectedCut.needsManualReview ? (
                      <span className="text-[8px] px-1.5 py-0.5 rounded bg-orange-900/30 text-orange-400 border border-orange-800/30 font-medium">
                        수동 검토 권장
                      </span>
                    ) : null}
                  </div>
                  <span className="text-[10px] text-neutral-600">
                    {(selectedCut.durationMs / 1000).toFixed(1)}s
                  </span>
                </div>

                {/* Importance reasons */}
                {selectedCut.importanceReasons.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {selectedCut.importanceReasons.map(r => (
                      <span key={r} className="text-[8px] px-1.5 py-0.5 rounded bg-violet-900/20 text-violet-400/80 font-medium">
                        {r}
                      </span>
                    ))}
                  </div>
                ) : null}

                <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden">
                  {selectedCut.thumbnailUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={selectedCut.thumbnailUrl} alt={`Cut ${selectedCut.cutIndex + 1}`} className="w-full aspect-[9/16] object-cover" />
                  ) : (
                    <div className="w-full aspect-[9/16] flex items-center justify-center bg-neutral-900">
                      <div className="text-center">
                        <div className="text-3xl text-neutral-700 mb-2">🖼</div>
                        <p className="text-xs text-neutral-600">이미지 없음</p>
                        <p className="text-[10px] text-neutral-700 mt-1">
                          위의 일괄 생성 버튼을 사용하거나,<br/>인스펙터에서 개별 재생성하세요
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Status badges */}
                <div className="flex items-center justify-between text-[9px] text-neutral-500">
                  <div className="flex gap-3">
                    <ShotBadge label="프레임" ok={true} detail="생성됨" />
                    <ShotBadge
                      label="이미지"
                      ok={selectedCut.imageStatus !== "none"}
                      detail={selectedCut.imageStatus === "approved" ? "승인됨" : selectedCut.imageStatus === "ready" ? "검토 대기" : selectedCut.imageStatus === "rejected" ? "거절됨" : "미생성"}
                      warn={selectedCut.imageStatus === "ready"}
                    />
                    <ShotBadge
                      label="비디오"
                      ok={selectedCut.videoStatus === "ready"}
                      detail={selectedCut.videoStatus === "ready" ? "생성됨" : "미생성"}
                    />
                  </div>
                  {selectedCut.hasPrompt ? (
                    <span className="text-emerald-500">프롬프트 있음</span>
                  ) : (
                    <span className="text-amber-500">프롬프트 없음</span>
                  )}
                </div>

                {selectedCut.narration ? (
                  <div className="rounded-lg bg-neutral-800/40 p-3 border border-neutral-800/50">
                    <p className="text-[9px] text-neutral-500 font-medium mb-1">내레이션</p>
                    <p className="text-[11px] text-neutral-300 leading-relaxed">{selectedCut.narration}</p>
                  </div>
                ) : null}

                <div className="flex justify-between">
                  <button
                    onClick={() => setSelectedIndex(Math.max(0, selectedIndex - 1))}
                    disabled={selectedIndex === 0}
                    className="rounded-md bg-neutral-800 border border-neutral-700/50 px-3 py-1.5 text-[10px] text-neutral-400 hover:text-neutral-200 transition disabled:opacity-30"
                  >
                    ← 이전 컷
                  </button>
                  <button
                    onClick={() => setSelectedIndex(Math.min(cuts.length - 1, selectedIndex + 1))}
                    disabled={selectedIndex >= cuts.length - 1}
                    className="rounded-md bg-neutral-800 border border-neutral-700/50 px-3 py-1.5 text-[10px] text-neutral-400 hover:text-neutral-200 transition disabled:opacity-30"
                  >
                    다음 컷 →
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-xs text-neutral-600">컷을 선택하세요</p>
            )}
          </div>

          {/* Right: Inspector */}
          <div className="w-80 border-l border-neutral-800 shrink-0">
            <CutInspector
              cut={selectedCut}
              projectId={projectId}
              frameDetail={frameDetail}
              shotDetail={shotDetail}
              onSave={handleFrameSave}
              onShotSave={handleShotSave}
              onRegenerateImage={handleRegenerateImage}
              saving={saving}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Shot status badge ──────────────────────────────── */

function ShotBadge({ label, ok, detail, warn }: { label: string; ok: boolean; detail: string; warn?: boolean }) {
  return (
    <span className="flex items-center gap-1">
      <span className={`w-1.5 h-1.5 rounded-full ${
        ok ? (warn ? "bg-amber-400" : "bg-emerald-400") : "bg-neutral-700"
      }`} />
      <span className="text-[8px] uppercase">{label}</span>
      <span className={`text-[8px] ${ok ? (warn ? "text-amber-400" : "text-emerald-400") : "text-neutral-600"}`}>
        {detail}
      </span>
    </span>
  );
}
