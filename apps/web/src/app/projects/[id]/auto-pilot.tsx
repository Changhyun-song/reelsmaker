"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { apiUrl } from "@/lib/api";

type Stage =
  | "idle"
  | "script"
  | "structure"
  | "images"
  | "videos"
  | "audio"
  | "assembly"
  | "done"
  | "error";

interface StageInfo {
  key: Stage;
  label: string;
  emoji: string;
  detail?: string;
}

const STAGES: StageInfo[] = [
  { key: "script", label: "대본 작성", emoji: "📝" },
  { key: "structure", label: "장면 구성", emoji: "🎬" },
  { key: "images", label: "이미지 생성", emoji: "🖼️" },
  { key: "videos", label: "비디오 생성", emoji: "🎥" },
  { key: "audio", label: "음성 · 자막", emoji: "🎙️" },
  { key: "assembly", label: "최종 합성", emoji: "✨" },
];

const DURATION_OPTIONS = [
  { value: 30, label: "30초 (숏폼)" },
  { value: 60, label: "60초 (릴스/숏츠)" },
];

const STYLE_OPTIONS = [
  { value: "cinematic", label: "🎬 시네마틱" },
  { value: "cute", label: "🐱 귀여운" },
  { value: "educational", label: "📚 교육적" },
  { value: "funny", label: "😄 유머러스" },
  { value: "dramatic", label: "🔥 드라마틱" },
  { value: "calm", label: "🌿 차분한" },
];

interface AutoPilotProps {
  projectId: string;
  onComplete?: () => void;
  onSwitchToExpert?: () => void;
}

export default function AutoPilot({ projectId, onComplete, onSwitchToExpert }: AutoPilotProps) {
  const [stage, setStage] = useState<Stage>("idle");
  const [topic, setTopic] = useState("");
  const [duration, setDuration] = useState(30);
  const [style, setStyle] = useState("cinematic");
  const [stageDetail, setStageDetail] = useState("");
  const [stageProgress, setStageProgress] = useState<Record<string, "pending" | "running" | "done" | "error">>({});
  const [errorMsg, setErrorMsg] = useState("");
  const [renderOutputUrl, setRenderOutputUrl] = useState<string | null>(null);
  const abortRef = useRef(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  const api = useCallback(async (path: string, opts?: RequestInit) => {
    const res = await fetch(apiUrl(path), {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`API error ${res.status}: ${text}`);
    }
    return res.json();
  }, []);

  const pollJob = useCallback(async (jobId: string, maxWait = 600): Promise<Record<string, unknown>> => {
    const start = Date.now();
    while (Date.now() - start < maxWait * 1000) {
      if (abortRef.current) throw new Error("중단됨");
      await new Promise((r) => setTimeout(r, 3000));
      const job = await api(`/api/jobs/${jobId}`);
      if (job.status === "completed") return job;
      if (job.status === "failed") throw new Error(job.error_message || "작업 실패");
    }
    throw new Error("시간 초과");
  }, [api]);

  const updateStage = (s: Stage, detail = "") => {
    setStage(s);
    setStageDetail(detail);
    setStageProgress((prev) => {
      const next = { ...prev };
      for (const st of STAGES) {
        if (st.key === s) next[st.key] = "running";
        else if (STAGES.findIndex((x) => x.key === st.key) < STAGES.findIndex((x) => x.key === s))
          next[st.key] = "done";
      }
      return next;
    });
  };

  const markStageDone = (s: Stage) => {
    setStageProgress((prev) => ({ ...prev, [s]: "done" }));
  };

  const runAutoPilot = async () => {
    abortRef.current = false;
    setErrorMsg("");
    setRenderOutputUrl(null);
    setElapsedSec(0);

    const startTime = Date.now();
    timerRef.current = setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    const initProgress: Record<string, "pending"> = {};
    for (const s of STAGES) initProgress[s.key] = "pending";
    setStageProgress(initProgress);

    try {
      // ── Stage 1: Script ──
      updateStage("script", "AI가 대본을 작성하고 있어요...");
      const scriptJob = await api(`/api/projects/${projectId}/scripts/generate`, {
        method: "POST",
        body: JSON.stringify({
          topic: topic.trim(),
          tone: style,
          duration_sec: duration,
          format: duration <= 60 ? "youtube_short" : "youtube_standard",
          language: "ko",
        }),
      });
      await pollJob(scriptJob.id);
      markStageDone("script");

      const versions = await api(`/api/projects/${projectId}/scripts`);
      const version = versions.versions?.[0];
      if (!version) throw new Error("대본이 생성되지 않았습니다");
      const versionId = version.id;

      // ── Stage 2: Structure ──
      updateStage("structure", "장면과 샷을 구성하고 있어요...");

      setStageDetail("장면(Scene)을 나누는 중...");
      const sceneJob = await api(`/api/projects/${projectId}/scripts/${versionId}/scenes/generate`, { method: "POST" });
      await pollJob(sceneJob.id);

      const scenesData = await api(`/api/projects/${projectId}/scripts/${versionId}/scenes`);
      const scenes: Array<{ id: string }> = scenesData.scenes || [];

      for (let i = 0; i < scenes.length; i++) {
        if (abortRef.current) throw new Error("중단됨");
        setStageDetail(`샷(Shot) 구성 중... (${i + 1}/${scenes.length})`);
        const shotJob = await api(`/api/projects/${projectId}/scenes/${scenes[i].id}/shots/generate`, { method: "POST" });
        await pollJob(shotJob.id);
      }

      const allShots: Array<{ id: string; scene_id: string }> = [];
      for (const sc of scenes) {
        const sd = await api(`/api/projects/${projectId}/scenes/${sc.id}/shots`);
        allShots.push(...(sd.shots || []));
      }

      for (let i = 0; i < allShots.length; i++) {
        if (abortRef.current) throw new Error("중단됨");
        setStageDetail(`프레임 구성 중... (${i + 1}/${allShots.length})`);
        const fJob = await api(`/api/projects/${projectId}/shots/${allShots[i].id}/frames/generate`, { method: "POST" });
        await pollJob(fJob.id);
      }
      markStageDone("structure");

      // Collect all frames
      const allFrames: Array<{ id: string; shot_id: string }> = [];
      for (const shot of allShots) {
        const fd = await api(`/api/projects/${projectId}/shots/${shot.id}/frames`);
        allFrames.push(...(fd.frames || []));
      }

      // ── Stage 3: Images ──
      updateStage("images", "이미지를 생성하고 있어요...");
      const imgJobs: string[] = [];
      for (const frame of allFrames) {
        if (abortRef.current) throw new Error("중단됨");
        const ij = await api(`/api/projects/${projectId}/frames/${frame.id}/images/generate`, {
          method: "POST",
          body: JSON.stringify({ num_variants: 1 }),
        });
        imgJobs.push(ij.id);
      }
      for (let i = 0; i < imgJobs.length; i++) {
        if (abortRef.current) throw new Error("중단됨");
        setStageDetail(`이미지 생성 중... (${i + 1}/${imgJobs.length})`);
        await pollJob(imgJobs[i]);
      }
      markStageDone("images");

      // ── Stage 4: Videos ──
      updateStage("videos", "비디오 클립을 생성하고 있어요...");
      const vidJobs: string[] = [];
      for (const shot of allShots) {
        if (abortRef.current) throw new Error("중단됨");
        const vj = await api(`/api/projects/${projectId}/shots/${shot.id}/video/generate`, {
          method: "POST",
          body: JSON.stringify({ mode: "image_to_video", num_variants: 1 }),
        });
        vidJobs.push(vj.id);
      }
      for (let i = 0; i < vidJobs.length; i++) {
        if (abortRef.current) throw new Error("중단됨");
        setStageDetail(`비디오 생성 중... (${i + 1}/${vidJobs.length})`);
        await pollJob(vidJobs[i], 600);
      }
      markStageDone("videos");

      // ── Stage 5: Audio ──
      updateStage("audio", "음성과 자막을 만들고 있어요...");
      const ttsJobs: string[] = [];
      for (const shot of allShots) {
        if (abortRef.current) throw new Error("중단됨");
        const tj = await api(`/api/projects/${projectId}/shots/${shot.id}/tts/generate`, {
          method: "POST",
          body: JSON.stringify({}),
        });
        ttsJobs.push(tj.id);
      }
      for (let i = 0; i < ttsJobs.length; i++) {
        setStageDetail(`음성 생성 중... (${i + 1}/${ttsJobs.length})`);
        await pollJob(ttsJobs[i]);
      }

      setStageDetail("자막 생성 중...");
      const subJob = await api(`/api/projects/${projectId}/subtitles/generate`, {
        method: "POST",
        body: JSON.stringify({ script_version_id: versionId }),
      });
      await pollJob(subJob.id);
      markStageDone("audio");

      // ── Stage 6: Assembly ──
      updateStage("assembly", "타임라인을 합성하고 있어요...");
      setStageDetail("타임라인 조립 중...");
      const tlJob = await api(`/api/projects/${projectId}/timelines/compose`, {
        method: "POST",
        body: JSON.stringify({ script_version_id: versionId }),
      });
      await pollJob(tlJob.id);

      const tlData = await api(`/api/projects/${projectId}/timelines?script_version_id=${versionId}`);
      const timeline = tlData.timelines?.[0];
      if (!timeline) throw new Error("타임라인이 생성되지 않았습니다");

      setStageDetail("최종 영상 렌더링 중...");
      const renderJob = await api(`/api/projects/${projectId}/render`, {
        method: "POST",
        body: JSON.stringify({ timeline_id: timeline.id, burn_subtitles: true }),
      });
      await pollJob(renderJob.id, 600);

      const renderJobs = await api(`/api/projects/${projectId}/render-jobs?timeline_id=${timeline.id}`);
      const completed = renderJobs.render_jobs?.find((r: Record<string, unknown>) => r.status === "completed");
      if (completed) {
        const output = await api(`/api/projects/${projectId}/render-jobs/${completed.id}/output`);
        setRenderOutputUrl(output.url || null);
      }

      markStageDone("assembly");
      setStage("done");
      if (timerRef.current) clearInterval(timerRef.current);
      onComplete?.();
    } catch (err: unknown) {
      if (timerRef.current) clearInterval(timerRef.current);
      const msg = err instanceof Error ? err.message : "알 수 없는 오류";
      setErrorMsg(msg);
      setStage("error");
      setStageProgress((prev) => {
        const next = { ...prev };
        for (const key of Object.keys(next)) {
          if (next[key] === "running") next[key] = "error";
        }
        return next;
      });
    }
  };

  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return m > 0 ? `${m}분 ${s}초` : `${s}초`;
  };

  const completedStages = STAGES.filter((s) => stageProgress[s.key] === "done").length;
  const progressPct = stage === "done" ? 100 : Math.round((completedStages / STAGES.length) * 100);

  // ── Idle: Input Form ──
  if (stage === "idle") {
    return (
      <div className="max-w-xl mx-auto space-y-6">
        <div className="text-center pt-4">
          <h2 className="text-2xl font-bold">어떤 영상을 만들까요?</h2>
          <p className="text-sm text-neutral-400 mt-1">
            주제만 입력하면 AI가 알아서 영상을 만들어드려요
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <textarea
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="예: 우주를 탐험하는 고양이 루나의 모험&#10;예: 3분 요리! 초간단 계란볶음밥&#10;예: 직장인을 위한 5가지 시간관리 팁"
              rows={3}
              className="w-full rounded-xl border border-neutral-700 bg-neutral-800/80 px-4 py-3 text-base text-neutral-100 placeholder-neutral-500 focus:border-blue-500 focus:outline-none resize-none"
              autoFocus
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-neutral-400 mb-1.5">
                영상 길이
              </label>
              <div className="flex gap-2">
                {DURATION_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setDuration(opt.value)}
                    className={`flex-1 rounded-lg border px-3 py-2 text-sm transition ${
                      duration === opt.value
                        ? "border-blue-500 bg-blue-600/20 text-blue-300"
                        : "border-neutral-700 bg-neutral-800/50 text-neutral-400 hover:border-neutral-600"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-neutral-400 mb-1.5">
                영상 분위기
              </label>
              <select
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                className="w-full rounded-lg border border-neutral-700 bg-neutral-800/80 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none"
              >
                {STYLE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button
            onClick={runAutoPilot}
            disabled={!topic.trim()}
            className="w-full rounded-xl bg-blue-600 py-3.5 text-base font-bold transition hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            영상 만들기
          </button>
        </div>

        {onSwitchToExpert && (
          <div className="text-center">
            <button
              onClick={onSwitchToExpert}
              className="text-xs text-neutral-500 hover:text-neutral-300 transition underline underline-offset-2"
            >
              세부 단계별로 직접 조정하기 (전문가 모드)
            </button>
          </div>
        )}
      </div>
    );
  }

  // ── Running / Done / Error ──
  return (
    <div className="max-w-xl mx-auto space-y-6">
      {/* Header */}
      <div className="text-center pt-2">
        {stage === "done" ? (
          <>
            <h2 className="text-2xl font-bold">영상이 완성되었어요!</h2>
            <p className="text-sm text-neutral-400 mt-1">
              총 {formatTime(elapsedSec)} 소요
            </p>
          </>
        ) : stage === "error" ? (
          <>
            <h2 className="text-2xl font-bold text-red-400">문제가 발생했어요</h2>
            <p className="text-sm text-neutral-400 mt-1">
              아래에서 오류를 확인해주세요
            </p>
          </>
        ) : (
          <>
            <h2 className="text-2xl font-bold">영상을 만들고 있어요</h2>
            <p className="text-sm text-neutral-400 mt-1">
              {formatTime(elapsedSec)} 경과 · 잠시만 기다려주세요
            </p>
          </>
        )}
      </div>

      {/* Progress Bar */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-neutral-300">진행률</span>
          <span className="text-sm text-neutral-500">{progressPct}%</span>
        </div>
        <div className="h-3 w-full rounded-full bg-neutral-800 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              stage === "error" ? "bg-red-500" : stage === "done" ? "bg-emerald-500" : "bg-blue-500"
            }`}
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Stage List */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-1">
        {STAGES.map((s) => {
          const status = stageProgress[s.key] || "pending";
          return (
            <div
              key={s.key}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition ${
                status === "running" ? "bg-blue-950/30 border border-blue-800/40" : ""
              }`}
            >
              <div className="w-8 h-8 flex items-center justify-center text-lg shrink-0">
                {status === "done" ? (
                  <span className="text-emerald-400">✅</span>
                ) : status === "running" ? (
                  <span className="animate-spin text-blue-400">⏳</span>
                ) : status === "error" ? (
                  <span className="text-red-400">❌</span>
                ) : (
                  <span className="text-neutral-600">{s.emoji}</span>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p
                  className={`text-sm font-medium ${
                    status === "done"
                      ? "text-emerald-300"
                      : status === "running"
                        ? "text-blue-300"
                        : status === "error"
                          ? "text-red-300"
                          : "text-neutral-500"
                  }`}
                >
                  {s.label}
                </p>
                {status === "running" && stageDetail && (
                  <p className="text-xs text-neutral-500 mt-0.5">{stageDetail}</p>
                )}
              </div>
              {status === "done" && (
                <span className="text-xs text-emerald-600 shrink-0">완료</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Result: Video Player */}
      {stage === "done" && renderOutputUrl && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 overflow-hidden">
          <video
            src={renderOutputUrl}
            controls
            className="w-full aspect-video bg-black"
          />
          <div className="p-4 flex gap-3">
            <a
              href={renderOutputUrl}
              download
              className="flex-1 text-center rounded-lg bg-blue-600 py-2.5 text-sm font-medium hover:bg-blue-500 transition"
            >
              영상 다운로드
            </a>
            {onSwitchToExpert && (
              <button
                onClick={onSwitchToExpert}
                className="flex-1 rounded-lg border border-neutral-700 py-2.5 text-sm font-medium text-neutral-300 hover:bg-neutral-800 transition"
              >
                세부 조정하기
              </button>
            )}
          </div>
        </div>
      )}

      {stage === "done" && !renderOutputUrl && (
        <div className="rounded-xl border border-emerald-800/50 bg-emerald-950/20 p-5 text-center">
          <p className="text-sm text-emerald-300">
            파이프라인이 완료되었습니다. 세부 조정에서 결과를 확인하세요.
          </p>
          {onSwitchToExpert && (
            <button
              onClick={onSwitchToExpert}
              className="mt-3 rounded-lg bg-emerald-600 px-5 py-2 text-sm font-medium hover:bg-emerald-500 transition"
            >
              결과 확인하기
            </button>
          )}
        </div>
      )}

      {/* Error */}
      {stage === "error" && (
        <div className="rounded-xl border border-red-800/50 bg-red-950/20 p-5 space-y-3">
          <p className="text-sm text-red-300">{errorMsg}</p>
          <div className="flex gap-3">
            <button
              onClick={() => { setStage("idle"); setStageProgress({}); }}
              className="flex-1 rounded-lg bg-red-600/80 py-2.5 text-sm font-medium hover:bg-red-500 transition"
            >
              처음부터 다시
            </button>
            {onSwitchToExpert && (
              <button
                onClick={onSwitchToExpert}
                className="flex-1 rounded-lg border border-neutral-700 py-2.5 text-sm font-medium text-neutral-300 hover:bg-neutral-800 transition"
              >
                전문가 모드에서 확인
              </button>
            )}
          </div>
        </div>
      )}

      {/* Cancel */}
      {stage !== "done" && stage !== "error" && (
        <div className="text-center">
          <button
            onClick={() => { abortRef.current = true; }}
            className="text-xs text-neutral-500 hover:text-red-400 transition"
          >
            제작 중단
          </button>
        </div>
      )}
    </div>
  );
}
