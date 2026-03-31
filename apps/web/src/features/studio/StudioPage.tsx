"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { apiUrl } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import type { ShotData, SceneData, FrameData, AssetData, Job } from "@/lib/types";
import CutCard, { type CutInfo, type CutStatus } from "@/features/generation/CutCard";
import CutDetail from "@/features/generation/CutDetail";
import GenerationProgress from "@/features/generation/GenerationProgress";
import SystemLog, { type LogEntry } from "@/features/generation/SystemLog";
import Button from "@/components/ui/button";

type StudioStage =
  | "idle"
  | "preparing"
  | "generating_images"
  | "generating_videos"
  | "generating_audio"
  | "assembling"
  | "done"
  | "error";

interface StudioPageProps {
  projectId: string;
  scenes: SceneData[];
  shots: ShotData[];
  frames: FrameData[];
  versionId: string;
  onComplete?: () => void;
}

export default function StudioPage({
  projectId,
  scenes,
  shots,
  frames,
  versionId,
  onComplete,
}: StudioPageProps) {
  const { apiFetch } = useApi();
  const [stage, setStage] = useState<StudioStage>("idle");
  const [selectedCut, setSelectedCut] = useState(0);
  const [cuts, setCuts] = useState<CutInfo[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [overallProgress, setOverallProgress] = useState(0);
  const [completedCuts, setCompletedCuts] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const abortRef = useRef(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const addLog = useCallback((level: LogEntry["level"], message: string) => {
    setLogs((prev) => [...prev, { timestamp: Date.now(), level, message }]);
  }, []);

  const pollJobProgress = useCallback(
    async (jobId: string, maxWait = 600): Promise<Job> => {
      const start = Date.now();
      while (Date.now() - start < maxWait * 1000) {
        if (abortRef.current) throw new Error("중단됨");
        await new Promise((r) => setTimeout(r, 2500));
        const res = await fetch(apiUrl(`/api/jobs/${jobId}`));
        if (!res.ok) continue;
        const job: Job = await res.json();
        if (job.status === "completed") return job;
        if (job.status === "failed")
          throw new Error(job.error_message || "작업 실패");
      }
      throw new Error("시간 초과");
    },
    [],
  );

  // Initialize cuts from shots
  useEffect(() => {
    const cutList: CutInfo[] = shots.map((shot, i) => ({
      index: i,
      shot,
      imageAsset: null,
      videoAsset: null,
      status: "pending" as CutStatus,
      imageProgress: 0,
      videoProgress: 0,
      prompt: shot.description || "",
    }));
    setCuts(cutList);
    if (cutList.length > 0) setSelectedCut(0);
  }, [shots]);

  const updateCut = useCallback(
    (index: number, update: Partial<CutInfo>) => {
      setCuts((prev) =>
        prev.map((c, i) => (i === index ? { ...c, ...update } : c)),
      );
    },
    [],
  );

  // Timer
  useEffect(() => {
    if (stage !== "idle" && stage !== "done" && stage !== "error") {
      const start = Date.now();
      timerRef.current = setInterval(() => {
        setElapsedSec(Math.floor((Date.now() - start) / 1000));
      }, 1000);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [stage]);

  const fetchAssetUrl = useCallback(
    async (assetId: string): Promise<string | null> => {
      try {
        const data = await apiFetch<{ url: string }>(
          `/api/projects/${projectId}/assets/${assetId}/url`,
        );
        return data.url;
      } catch {
        return null;
      }
    },
    [apiFetch, projectId],
  );

  /* ── Main Generation Flow ─────────────────────────── */

  const startGeneration = async () => {
    abortRef.current = false;
    setStage("preparing");
    setLogs([]);
    setCompletedCuts(0);
    setOverallProgress(0);
    setErrorMsg("");

    addLog("info", "생성 준비 중...");

    try {
      // Phase 1: Generate images for all frames
      setStage("generating_images");
      addLog("info", "이미지 생성을 시작합니다.");

      const shotFrameMap = new Map<string, FrameData[]>();
      for (const f of frames) {
        const existing = shotFrameMap.get(f.shot_id) || [];
        existing.push(f);
        shotFrameMap.set(f.shot_id, existing);
      }

      let imagesDone = 0;
      const totalImages = frames.length;

      for (let ci = 0; ci < cuts.length; ci++) {
        if (abortRef.current) throw new Error("중단됨");

        const shot = cuts[ci].shot;
        const shotFrames = shotFrameMap.get(shot.id) || [];

        updateCut(ci, { status: "generating_image" });
        setSelectedCut(ci);
        addLog("info", `Cut ${ci + 1}: 이미지 생성 시작`);

        for (const frame of shotFrames) {
          if (abortRef.current) throw new Error("중단됨");

          const job = await apiFetch<Job>(
            `/api/projects/${projectId}/frames/${frame.id}/images/generate`,
            { method: "POST", body: JSON.stringify({ num_variants: 1 }) },
          );

          // Poll with progress updates
          const start = Date.now();
          let lastProgress = 0;
          while (true) {
            if (abortRef.current) throw new Error("중단됨");
            await new Promise((r) => setTimeout(r, 2000));
            const res = await fetch(apiUrl(`/api/jobs/${job.id}`));
            if (!res.ok) continue;
            const j: Job = await res.json();

            if (j.progress > lastProgress) {
              lastProgress = j.progress;
              updateCut(ci, { imageProgress: j.progress });
            }

            if (j.status === "completed") break;
            if (j.status === "failed")
              throw new Error(j.error_message || `Cut ${ci + 1} 이미지 생성 실패`);
            if (Date.now() - start > 120000) throw new Error("이미지 생성 시간 초과");
          }

          imagesDone++;
          setOverallProgress((imagesDone / totalImages) * 50);
        }

        // Fetch generated image asset
        try {
          const frameId = shotFrames[0]?.id;
          if (frameId) {
            const assets = await apiFetch<{ assets: AssetData[] }>(
              `/api/projects/${projectId}/frames/${frameId}/assets`,
            );
            const img = assets.assets?.find(
              (a) => a.asset_type === "image" && a.status === "ready",
            );
            if (img) {
              const url = await fetchAssetUrl(img.id);
              updateCut(ci, {
                imageAsset: { ...img, url },
                status: "image_done",
                imageProgress: 100,
              });
            }
          }
        } catch {
          /* continue */
        }

        addLog("success", `Cut ${ci + 1}: 이미지 완료`);
        setCompletedCuts((p) => p + 1);
      }

      // Phase 2: Generate videos
      setStage("generating_videos");
      addLog("info", "비디오 생성을 시작합니다.");

      let videosDone = 0;
      for (let ci = 0; ci < cuts.length; ci++) {
        if (abortRef.current) throw new Error("중단됨");

        const shot = cuts[ci].shot;
        updateCut(ci, { status: "generating_video", videoProgress: 0 });
        setSelectedCut(ci);
        addLog("info", `Cut ${ci + 1}: 비디오 생성 시작`);

        const job = await apiFetch<Job>(
          `/api/projects/${projectId}/shots/${shot.id}/video/generate`,
          {
            method: "POST",
            body: JSON.stringify({ mode: "image_to_video", num_variants: 1 }),
          },
        );

        const start = Date.now();
        let lastProgress = 0;
        while (true) {
          if (abortRef.current) throw new Error("중단됨");
          await new Promise((r) => setTimeout(r, 3000));
          const res = await fetch(apiUrl(`/api/jobs/${job.id}`));
          if (!res.ok) continue;
          const j: Job = await res.json();

          if (j.progress > lastProgress) {
            lastProgress = j.progress;
            updateCut(ci, { videoProgress: j.progress });
          }

          if (j.status === "completed") break;
          if (j.status === "failed")
            throw new Error(j.error_message || `Cut ${ci + 1} 비디오 생성 실패`);
          if (Date.now() - start > 600000) throw new Error("비디오 생성 시간 초과");
        }

        // Fetch video asset
        try {
          const videoAssets = await apiFetch<{ assets: AssetData[] }>(
            `/api/projects/${projectId}/shots/${shot.id}/video/assets`,
          );
          const vid = videoAssets.assets?.find(
            (a) => a.asset_type === "video" && a.status === "ready",
          );
          if (vid) {
            const url = await fetchAssetUrl(vid.id);
            updateCut(ci, {
              videoAsset: { ...vid, url },
              status: "complete",
              videoProgress: 100,
            });
          }
        } catch {
          updateCut(ci, { status: "complete", videoProgress: 100 });
        }

        videosDone++;
        setOverallProgress(50 + (videosDone / cuts.length) * 50);
        addLog("success", `Cut ${ci + 1}: 비디오 완료`);
      }

      setStage("done");
      setOverallProgress(100);
      addLog("success", "모든 생성이 완료되었습니다!");
      onComplete?.();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "알 수 없는 오류";
      setErrorMsg(msg);
      setStage("error");
      addLog("error", msg);
    }
  };

  const stageLabel =
    stage === "generating_images"
      ? "이미지 생성 중"
      : stage === "generating_videos"
        ? "비디오 생성 중"
        : stage === "assembling"
          ? "합성 중"
          : stage === "done"
            ? "완료"
            : "준비";

  /* ── Idle Screen ──────────────────────────────────── */
  if (stage === "idle" && cuts.length > 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-6">
        <div className="text-center space-y-2">
          <h2 className="text-xl font-bold text-neutral-100">영상 생성 준비 완료</h2>
          <p className="text-sm text-neutral-400">
            {cuts.length}개 컷의 이미지와 비디오를 생성합니다.
          </p>
        </div>
        <Button size="lg" onClick={startGeneration}>
          전체 생성 시작
        </Button>
      </div>
    );
  }

  if (cuts.length === 0) {
    return (
      <div className="flex items-center justify-center py-16 text-neutral-500">
        <p>장면 구조를 먼저 생성해주세요.</p>
      </div>
    );
  }

  /* ── Main Studio Layout ───────────────────────────── */
  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Top: Progress bar */}
      <GenerationProgress
        stage={stageLabel}
        currentStep={completedCuts}
        totalSteps={cuts.length}
        elapsedSec={elapsedSec}
      />

      {/* Main: Cut list + Detail */}
      <div className="flex gap-4 flex-1 min-h-0">
        {/* Left: Cut list */}
        <div className="w-[340px] shrink-0 flex flex-col gap-2 overflow-y-auto pr-1">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-neutral-500">
              {completedCuts}/{cuts.length} 완료
            </span>
            {stage !== "done" && stage !== "idle" && (
              <button
                onClick={() => { abortRef.current = true; }}
                className="text-[10px] text-neutral-500 hover:text-red-400 transition"
              >
                중단
              </button>
            )}
          </div>
          {cuts.map((cut, i) => (
            <CutCard
              key={cut.shot.id}
              cut={cut}
              selected={selectedCut === i}
              onClick={() => setSelectedCut(i)}
            />
          ))}
        </div>

        {/* Right: Detail */}
        <div className="flex-1 min-w-0">
          {cuts[selectedCut] && (
            <CutDetail cut={cuts[selectedCut]} />
          )}
        </div>
      </div>

      {/* Bottom: System log */}
      <SystemLog logs={logs} />

      {/* Error */}
      {stage === "error" && (
        <div className="rounded-xl border border-red-800/50 bg-red-950/20 p-4 text-center">
          <p className="text-sm text-red-300 mb-3">{errorMsg}</p>
          <Button variant="danger" size="sm" onClick={startGeneration}>
            다시 시도
          </Button>
        </div>
      )}

      {/* Done */}
      {stage === "done" && (
        <div className="rounded-xl border border-emerald-800/50 bg-emerald-950/20 p-5 text-center space-y-3">
          <p className="text-lg font-bold text-emerald-400">모든 생성이 완료되었습니다!</p>
          <p className="text-sm text-neutral-400">
            {cuts.length}개 컷 | 총 {elapsedSec}초 소요
          </p>
          <Button onClick={onComplete}>다음 단계로</Button>
        </div>
      )}
    </div>
  );
}
