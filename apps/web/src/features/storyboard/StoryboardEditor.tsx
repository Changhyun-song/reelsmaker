"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { apiUrl } from "@/lib/api";
import type { SceneData, ShotData, FrameData, AssetData } from "@/lib/types";
import CutListPanel, { type CutItem } from "./CutListPanel";
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

type FilterMode = "all" | "key_cuts" | "no_image" | "needs_review";

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

/* ── Key cut detection ──────────────────────────────── */

function isKeyCut(cut: CutItem, allCuts: CutItem[]): boolean {
  const sceneCuts = allCuts.filter(c => c.sceneIndex === cut.sceneIndex);
  if (sceneCuts.length === 0) return false;
  const first = sceneCuts[0];
  const last = sceneCuts[sceneCuts.length - 1];
  if (cut.cutIndex === first.cutIndex || cut.cutIndex === last.cutIndex) return true;
  if (cut.frameRole === "start" && cut.shotIndex === 0) return true;
  return false;
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
        <button onClick={onCancel} className="text-[9px] text-neutral-500 hover:text-neutral-300">
          중단
        </button>
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

function WorkflowGuide({ onClose }: { onClose: () => void }) {
  const steps = [
    { num: 1, label: "Continuity Bible 저장", desc: "스타일 섹션에서 전체 영상 규칙을 먼저 설정하세요" },
    { num: 2, label: "전체 프레임 자동 생성", desc: "아래 '전체 이미지 생성' 버튼으로 한번에 실행" },
    { num: 3, label: "핵심 컷만 검토", desc: "'핵심 컷' 필터로 중요한 장면만 빠르게 확인" },
    { num: 4, label: "이상한 컷만 재생성", desc: "인스펙터에서 프롬프트 수정 후 개별 재생성" },
    { num: 5, label: "승인 후 비디오 생성", desc: "이미지 승인 → 비디오 단계로 진행" },
  ];

  return (
    <div className="rounded-xl border border-blue-800/20 bg-blue-950/5 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-blue-400 text-sm">💡</span>
          <span className="text-xs font-bold text-blue-400">권장 워크플로</span>
        </div>
        <button onClick={onClose} className="text-neutral-600 hover:text-neutral-400 text-xs">✕</button>
      </div>
      <p className="text-[10px] text-neutral-500">
        이 화면은 모든 프레임을 수동으로 작성하는 곳이 아닙니다.
        자동 생성된 결과를 검토하고, 문제가 있는 컷만 수정하세요.
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

  // Build flat cut list
  const allCuts: CutItem[] = useMemo(() => {
    const result: CutItem[] = [];
    let cutIdx = 0;
    const sortedScenes = [...scenes].sort((a, b) => a.order_index - b.order_index);
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
          });
        }
      }
    }
    return result;
  }, [scenes, shots, frames, assets]);

  // Filter cuts
  const cuts = useMemo(() => {
    if (filterMode === "all") return allCuts;
    if (filterMode === "key_cuts") return allCuts.filter(c => isKeyCut(c, allCuts));
    if (filterMode === "no_image") return allCuts.filter(c => c.imageStatus === "none");
    if (filterMode === "needs_review") return allCuts.filter(c => c.imageStatus === "ready" || c.imageStatus === "rejected");
    return allCuts;
  }, [allCuts, filterMode]);

  // Stats
  const stats = useMemo(() => {
    const total = allCuts.length;
    const withImage = allCuts.filter(c => c.imageStatus !== "none").length;
    const approved = allCuts.filter(c => c.imageStatus === "approved").length;
    const noImage = allCuts.filter(c => c.imageStatus === "none").length;
    const withPrompt = allCuts.filter(c => c.hasPrompt).length;
    const keyCuts = allCuts.filter(c => isKeyCut(c, allCuts)).length;
    return { total, withImage, approved, noImage, withPrompt, keyCuts };
  }, [allCuts]);

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

  // ── Batch execution ──────────────────────────────
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

  return (
    <div className="space-y-3">
      {/* Workflow guide */}
      {showGuide ? <WorkflowGuide onClose={() => setShowGuide(false)} /> : null}

      {/* Action bar */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          {/* Stats */}
          <div className="flex items-center gap-4 text-[10px]">
            <span className="text-neutral-500">{stats.total}컷</span>
            <span className="text-emerald-400">{stats.withImage} 이미지</span>
            <span className="text-blue-400">{stats.approved} 승인</span>
            <span className="text-neutral-600">{stats.noImage} 미생성</span>
            <span className="text-neutral-500">{stats.withPrompt}/{stats.total} 프롬프트</span>
          </div>

          {/* Batch action buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => runBatch(allCuts.filter(c => c.imageStatus === "none"))}
              disabled={batchRunning || stats.noImage === 0}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-[10px] font-medium text-white hover:bg-blue-500 transition disabled:opacity-40"
            >
              미생성 컷 일괄 생성 ({stats.noImage})
            </button>
            <button
              onClick={() => runBatch(allCuts)}
              disabled={batchRunning}
              className="rounded-md bg-blue-600/80 px-3 py-1.5 text-[10px] font-medium text-white hover:bg-blue-500 transition disabled:opacity-40"
            >
              전체 이미지 생성
            </button>
            <button
              onClick={() => runBatch(allCuts.filter(c => isKeyCut(c, allCuts) && c.imageStatus === "none"))}
              disabled={batchRunning}
              className="rounded-md bg-neutral-800 border border-neutral-700/50 px-3 py-1.5 text-[10px] font-medium text-neutral-400 hover:text-neutral-200 transition disabled:opacity-40"
            >
              핵심 컷만 생성 ({stats.keyCuts})
            </button>
          </div>
        </div>

        {/* Filter buttons */}
        <div className="flex items-center gap-1.5 mt-2">
          {([
            ["all", `전체 (${allCuts.length})`],
            ["key_cuts", `핵심 컷 (${stats.keyCuts})`],
            ["no_image", `미생성 (${stats.noImage})`],
            ["needs_review", `검토 필요 (${allCuts.filter(c => c.imageStatus === "ready" || c.imageStatus === "rejected").length})`],
          ] as [FilterMode, string][]).map(([mode, label]) => (
            <button
              key={mode}
              onClick={() => { setFilterMode(mode); setSelectedIndex(0); }}
              className={`rounded-md px-2.5 py-1 text-[9px] font-medium border transition ${
                filterMode === mode
                  ? "bg-blue-600/20 border-blue-700/40 text-blue-400"
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
                    {isKeyCut(selectedCut, allCuts) ? (
                      <span className="text-[8px] px-1.5 py-0.5 rounded bg-violet-900/40 text-violet-400 font-medium">
                        핵심 컷
                      </span>
                    ) : null}
                  </div>
                  <span className="text-[10px] text-neutral-600">
                    {(selectedCut.durationMs / 1000).toFixed(1)}s
                  </span>
                </div>

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
