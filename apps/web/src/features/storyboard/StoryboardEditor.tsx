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

/* ── API helper ─────────────────────────────────────── */

async function api(path: string, opts?: RequestInit) {
  const res = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.json();
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

  // Build flat cut list from the hierarchy: scene → shot → frame
  const cuts: CutItem[] = useMemo(() => {
    const result: CutItem[] = [];
    let cutIdx = 0;

    const sortedScenes = [...scenes].sort((a, b) => a.order_index - b.order_index);
    for (const scene of sortedScenes) {
      const sceneShots = shots
        .filter((s) => s.scene_id === scene.id)
        .sort((a, b) => a.order_index - b.order_index);

      for (const shot of sceneShots) {
        const shotFrames = frames
          .filter((f) => f.shot_id === shot.id)
          .sort((a, b) => a.order_index - b.order_index);

        for (const frame of shotFrames) {
          const frameAssets = assets.get(frame.id) || [];
          const imageAssets = frameAssets.filter((a) => a.asset_type === "image");
          const selectedImage = imageAssets.find((a) => a.is_selected) || imageAssets[0];

          let imageStatus: CutItem["imageStatus"] = "none";
          if (selectedImage) {
            if (selectedImage.status === "approved") imageStatus = "approved";
            else if (selectedImage.status === "rejected") imageStatus = "rejected";
            else imageStatus = "ready";
          }

          const shotVideoAssets = frameAssets.filter((a) => a.asset_type === "video");
          const videoStatus: CutItem["videoStatus"] =
            shotVideoAssets.some((a) => a.status === "ready") ? "ready" : "none";

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

  // Load assets for all frames
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
          } catch {
            // Skip frames with no assets
          }
        }
        if (!cancelled) setAssets(map);
      } catch (e) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : "에셋 로딩 실패");
      }
    };
    if (frames.length > 0) loadAssets();
    return () => { cancelled = true; };
  }, [projectId, frames]);

  // Get selected cut
  const selectedCut = cuts[selectedIndex] || null;

  // Frame detail for inspector
  const frameDetail: FrameDetail | null = useMemo(() => {
    if (!selectedCut) return null;
    const f = frames.find((fr) => fr.id === selectedCut.frameId);
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

  // Shot detail for inspector
  const shotDetail: ShotDetail | null = useMemo(() => {
    if (!selectedCut) return null;
    const s = shots.find((sh) => sh.id === selectedCut.shotId);
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

  // Save frame
  const handleFrameSave = useCallback(async (payload: FrameSavePayload) => {
    setSaving(true);
    try {
      const { frameId, ...fields } = payload;
      await api(`/api/projects/${projectId}/frames/${frameId}`, {
        method: "PATCH",
        body: JSON.stringify(fields),
      });
    } finally {
      setSaving(false);
    }
  }, [projectId]);

  // Save shot
  const handleShotSave = useCallback(async (payload: ShotSavePayload) => {
    setSaving(true);
    try {
      const { shotId, ...fields } = payload;
      await api(`/api/projects/${projectId}/shots/${shotId}/edit`, {
        method: "PATCH",
        body: JSON.stringify(fields),
      });
    } finally {
      setSaving(false);
    }
  }, [projectId]);

  // Regenerate image
  const handleRegenerateImage = useCallback(async (frameId: string) => {
    try {
      await api(`/api/projects/${projectId}/frames/${frameId}/images/generate`, {
        method: "POST",
        body: JSON.stringify({ num_variants: 2 }),
      });
    } catch {
      // Handled in the UI
    }
  }, [projectId]);

  // Reorder (local only for now)
  const handleReorder = useCallback((_from: number, _to: number) => {
    // Placeholder for future drag-and-drop
  }, []);

  if (frames.length === 0) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-8 text-center">
        <p className="text-sm text-neutral-500">프레임이 없습니다</p>
        <p className="text-xs text-neutral-600 mt-1">장면 구성 → 샷 계획 → 프레임 생성을 먼저 실행하세요.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/30 overflow-hidden">
      {/* Error banner */}
      {loadError && (
        <div className="border-b border-red-800/40 bg-red-950/20 px-3 py-2">
          <p className="text-[10px] text-red-400">{loadError}</p>
        </div>
      )}

      {/* 3-panel layout */}
      <div className="flex h-[700px]">
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
              {/* Cut number header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="rounded-md bg-blue-600 px-2 py-0.5 text-xs font-bold text-white">
                    #{selectedCut.cutIndex + 1}
                  </span>
                  <span className="text-xs text-neutral-400">
                    Scene {selectedCut.sceneIndex + 1} · Shot {selectedCut.shotIndex + 1}
                  </span>
                </div>
                <span className="text-[10px] text-neutral-600">
                  {(selectedCut.durationMs / 1000).toFixed(1)}s
                </span>
              </div>

              {/* Image preview */}
              <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden">
                {selectedCut.thumbnailUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={selectedCut.thumbnailUrl}
                    alt={`Cut ${selectedCut.cutIndex + 1}`}
                    className="w-full aspect-[9/16] object-cover"
                  />
                ) : (
                  <div className="w-full aspect-[9/16] flex items-center justify-center bg-neutral-900">
                    <div className="text-center">
                      <div className="text-3xl text-neutral-700 mb-2">🖼</div>
                      <p className="text-xs text-neutral-600">이미지 없음</p>
                      <p className="text-[10px] text-neutral-700 mt-1">
                        인스펙터에서 프롬프트를 작성 후 이미지를 생성하세요
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Status bar */}
              <div className="flex items-center justify-between text-[9px] text-neutral-500">
                <div className="flex gap-3">
                  <span className="flex items-center gap-1">
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      selectedCut.imageStatus === "approved" ? "bg-emerald-400"
                        : selectedCut.imageStatus === "ready" ? "bg-amber-400"
                          : "bg-neutral-700"
                    }`} />
                    IMG {selectedCut.imageStatus}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      selectedCut.videoStatus === "ready" ? "bg-emerald-400" : "bg-neutral-700"
                    }`} />
                    VID {selectedCut.videoStatus}
                  </span>
                </div>
                {selectedCut.hasPrompt ? (
                  <span className="text-emerald-500">프롬프트 있음</span>
                ) : (
                  <span className="text-amber-500">프롬프트 없음</span>
                )}
              </div>

              {/* Narration preview */}
              {selectedCut.narration && (
                <div className="rounded-lg bg-neutral-800/40 p-3 border border-neutral-800/50">
                  <p className="text-[9px] text-neutral-500 font-medium mb-1">내레이션</p>
                  <p className="text-[11px] text-neutral-300 leading-relaxed">
                    {selectedCut.narration}
                  </p>
                </div>
              )}

              {/* Nav buttons */}
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
  );
}
