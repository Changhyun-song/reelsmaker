"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { apiUrl } from "@/lib/api";

/* ── Types ─────────────────────────────────────────── */

type Stage =
  | "idle"
  | "script_running" | "script_review"
  | "structure_running" | "structure_review"
  | "images_running" | "images_review"
  | "videos_running" | "videos_review"
  | "audio_running" | "audio_review"
  | "assembly_running"
  | "done"
  | "error";

interface ScriptPlan {
  title: string;
  summary: string;
  hook: string;
  narrative_flow: string[];
  sections: { title: string; description: string; narration: string; visual_notes: string; duration_sec: number }[];
  ending_cta: string;
  narration_draft: string;
  estimated_duration_sec: number;
}

interface SceneInfo {
  id: string; order_index: number; title: string | null; description: string | null;
  setting: string | null; mood: string | null; duration_estimate_sec: number | null;
  narration_text: string | null; emotional_tone: string | null;
}

interface ShotInfo {
  id: string; scene_id: string; order_index: number; shot_type: string | null;
  description: string | null; camera_movement: string | null; duration_sec: number | null;
  subject: string | null; emotion: string | null;
}

interface FrameInfo {
  id: string; shot_id: string; order_index: number; frame_role: string | null;
  visual_prompt: string | null; mood: string | null;
}

interface AssetInfo {
  id: string; parent_id: string; asset_type: string; url: string | null;
  status: string; is_selected: boolean; version: number;
}

interface VoiceInfo {
  id: string; shot_id: string; duration_sec: number | null;
}

const STAGE_LABELS: Record<string, { label: string; num: number }> = {
  script: { label: "대본 작성", num: 1 },
  structure: { label: "장면 구성", num: 2 },
  images: { label: "이미지 생성", num: 3 },
  videos: { label: "비디오 생성", num: 4 },
  audio: { label: "음성/자막", num: 5 },
  assembly: { label: "최종 합성", num: 6 },
};

const DURATION_OPTIONS = [
  { value: 30, label: "30초 (숏폼)" },
  { value: 60, label: "60초 (릴스/숏츠)" },
];

const STYLE_OPTIONS = [
  { value: "cinematic", label: "시네마틱" },
  { value: "cute", label: "귀여운" },
  { value: "educational", label: "교육적" },
  { value: "funny", label: "유머러스" },
  { value: "dramatic", label: "드라마틱" },
  { value: "calm", label: "차분한" },
];

/* ── Helpers ────────────────────────────────────────── */

function StageIndicator({ current }: { current: Stage }) {
  const stageKeys = ["script", "structure", "images", "videos", "audio", "assembly"];
  const currentBase = current.replace("_running", "").replace("_review", "");
  const currentIdx = stageKeys.indexOf(currentBase);

  return (
    <div className="flex items-center gap-1 mb-6">
      {stageKeys.map((key, idx) => {
        const info = STAGE_LABELS[key];
        const isDone = idx < currentIdx || current === "done";
        const isActive = idx === currentIdx;
        const isRunning = isActive && current.endsWith("_running");
        return (
          <div key={key} className="flex items-center gap-1 flex-1">
            <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold shrink-0 ${
              isDone ? "bg-emerald-600 text-white"
              : isRunning ? "bg-blue-600 text-white animate-pulse"
              : isActive ? "bg-blue-600 text-white"
              : "bg-neutral-800 text-neutral-500"
            }`}>
              {isDone ? "✓" : info.num}
            </div>
            <span className={`text-[11px] truncate hidden sm:inline ${
              isDone ? "text-emerald-400" : isActive ? "text-blue-300 font-medium" : "text-neutral-600"
            }`}>{info.label}</span>
            {idx < stageKeys.length - 1 && (
              <div className={`flex-1 h-px mx-1 ${isDone ? "bg-emerald-700" : "bg-neutral-800"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function RunningSpinner({ message, detail }: { message: string; detail?: string }) {
  return (
    <div className="rounded-xl border border-blue-800/40 bg-blue-950/20 p-8 text-center space-y-3">
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-600/20 mb-2">
        <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
      </div>
      <p className="text-base font-semibold text-blue-300">{message}</p>
      {detail && <p className="text-sm text-neutral-400">{detail}</p>}
    </div>
  );
}

function ReviewActions({ onApprove, onRegenerate, approveLabel, regenerateLabel }: {
  onApprove: () => void; onRegenerate: () => void;
  approveLabel?: string; regenerateLabel?: string;
}) {
  return (
    <div className="flex gap-3 mt-6">
      <button
        onClick={onApprove}
        className="flex-1 rounded-xl bg-emerald-600 py-3 text-sm font-bold transition hover:bg-emerald-500"
      >
        {approveLabel || "승인하고 다음 단계로"} →
      </button>
      <button
        onClick={onRegenerate}
        className="rounded-xl border border-neutral-700 px-5 py-3 text-sm font-medium text-neutral-300 hover:bg-neutral-800 transition"
      >
        {regenerateLabel || "다시 생성"}
      </button>
    </div>
  );
}

/* ── Main Component ─────────────────────────────────── */

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
  const [errorMsg, setErrorMsg] = useState("");
  const [runningDetail, setRunningDetail] = useState("");
  const abortRef = useRef(false);

  // Accumulated data across stages
  const [scriptPlan, setScriptPlan] = useState<ScriptPlan | null>(null);
  const [versionId, setVersionId] = useState<string | null>(null);
  const [scenesData, setScenesData] = useState<SceneInfo[]>([]);
  const [shotsData, setShotsData] = useState<ShotInfo[]>([]);
  const [framesData, setFramesData] = useState<FrameInfo[]>([]);
  const [imageAssets, setImageAssets] = useState<AssetInfo[]>([]);
  const [videoAssets, setVideoAssets] = useState<AssetInfo[]>([]);
  const [voiceTracks, setVoiceTracks] = useState<VoiceInfo[]>([]);
  const [subtitleSegments, setSubtitleSegments] = useState<{ index: number; start_ms: number; end_ms: number; text: string }[]>([]);
  const [renderOutputUrl, setRenderOutputUrl] = useState<string | null>(null);

  const api = useCallback(async (path: string, opts?: RequestInit) => {
    const res = await fetch(apiUrl(path), {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`API ${res.status}: ${text}`);
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

  const handleError = (err: unknown) => {
    const msg = err instanceof Error ? err.message : "알 수 없는 오류";
    setErrorMsg(msg);
    setStage("error");
  };

  /* ── Stage Runners ─────────────────────────────────── */

  const runScript = async () => {
    try {
      setStage("script_running");
      setRunningDetail("AI가 대본을 작성하고 있어요...");
      abortRef.current = false;

      const scriptJob = await api(`/api/projects/${projectId}/scripts/generate`, {
        method: "POST",
        body: JSON.stringify({
          topic: topic.trim(), tone: style, duration_sec: duration,
          format: duration <= 60 ? "youtube_short" : "youtube_standard",
          language: "ko",
        }),
      });
      await pollJob(scriptJob.id);

      const versions = await api(`/api/projects/${projectId}/scripts`);
      const version = versions.versions?.[0];
      if (!version) throw new Error("대본이 생성되지 않았습니다");

      setVersionId(version.id);
      setScriptPlan(version.plan_json as ScriptPlan);
      setStage("script_review");
    } catch (err) { handleError(err); }
  };

  const runStructure = async () => {
    if (!versionId) return;
    try {
      setStage("structure_running");

      setRunningDetail("장면(Scene)을 나누는 중...");
      const sceneJob = await api(`/api/projects/${projectId}/scripts/${versionId}/scenes/generate`, { method: "POST" });
      await pollJob(sceneJob.id);

      const sd = await api(`/api/projects/${projectId}/scripts/${versionId}/scenes`);
      const scenes: SceneInfo[] = sd.scenes || [];
      setScenesData(scenes);

      const allShots: ShotInfo[] = [];
      for (let i = 0; i < scenes.length; i++) {
        if (abortRef.current) throw new Error("중단됨");
        setRunningDetail(`샷(Shot) 구성 중... (${i + 1}/${scenes.length})`);
        const shotJob = await api(`/api/projects/${projectId}/scenes/${scenes[i].id}/shots/generate`, { method: "POST" });
        await pollJob(shotJob.id);
        const shotData = await api(`/api/projects/${projectId}/scenes/${scenes[i].id}/shots`);
        allShots.push(...(shotData.shots || []));
      }
      setShotsData(allShots);

      const allFrames: FrameInfo[] = [];
      for (let i = 0; i < allShots.length; i++) {
        if (abortRef.current) throw new Error("중단됨");
        setRunningDetail(`프레임 구성 중... (${i + 1}/${allShots.length})`);
        const fJob = await api(`/api/projects/${projectId}/shots/${allShots[i].id}/frames/generate`, { method: "POST" });
        await pollJob(fJob.id);
        const fd = await api(`/api/projects/${projectId}/shots/${allShots[i].id}/frames`);
        allFrames.push(...(fd.frames || []));
      }
      setFramesData(allFrames);

      setStage("structure_review");
    } catch (err) { handleError(err); }
  };

  const runImages = async () => {
    try {
      setStage("images_running");
      const frames = framesData.length > 0 ? framesData : [];
      const jobs: string[] = [];
      for (const frame of frames) {
        if (abortRef.current) throw new Error("중단됨");
        const ij = await api(`/api/projects/${projectId}/frames/${frame.id}/images/generate`, {
          method: "POST", body: JSON.stringify({ num_variants: 1 }),
        });
        jobs.push(ij.id);
      }
      for (let i = 0; i < jobs.length; i++) {
        if (abortRef.current) throw new Error("중단됨");
        setRunningDetail(`이미지 생성 중... (${i + 1}/${jobs.length})`);
        await pollJob(jobs[i]);
      }

      // Fetch all image assets
      const assets: AssetInfo[] = [];
      for (const shot of shotsData) {
        try {
          const res = await api(`/api/projects/${projectId}/shots/${shot.id}/frames`);
          for (const f of (res.frames || [])) {
            const ar = await api(`/api/projects/${projectId}/frames/${f.id}/assets`);
            assets.push(...(ar.assets || []));
          }
        } catch { /* skip */ }
      }
      setImageAssets(assets);

      setStage("images_review");
    } catch (err) { handleError(err); }
  };

  const runVideos = async () => {
    try {
      setStage("videos_running");
      const jobs: string[] = [];
      for (const shot of shotsData) {
        if (abortRef.current) throw new Error("중단됨");
        const vj = await api(`/api/projects/${projectId}/shots/${shot.id}/video/generate`, {
          method: "POST", body: JSON.stringify({ mode: "image_to_video", num_variants: 1 }),
        });
        jobs.push(vj.id);
      }
      for (let i = 0; i < jobs.length; i++) {
        if (abortRef.current) throw new Error("중단됨");
        setRunningDetail(`비디오 생성 중... (${i + 1}/${jobs.length})`);
        await pollJob(jobs[i], 600);
      }

      const assets: AssetInfo[] = [];
      for (const shot of shotsData) {
        try {
          const res = await api(`/api/projects/${projectId}/shots/${shot.id}/video/assets`);
          assets.push(...(res.assets || []));
        } catch { /* skip */ }
      }
      setVideoAssets(assets);

      setStage("videos_review");
    } catch (err) { handleError(err); }
  };

  const runAudio = async () => {
    if (!versionId) return;
    try {
      setStage("audio_running");
      const ttsJobs: string[] = [];
      for (const shot of shotsData) {
        if (abortRef.current) throw new Error("중단됨");
        const tj = await api(`/api/projects/${projectId}/shots/${shot.id}/tts/generate`, {
          method: "POST", body: JSON.stringify({}),
        });
        ttsJobs.push(tj.id);
      }
      for (let i = 0; i < ttsJobs.length; i++) {
        setRunningDetail(`음성 생성 중... (${i + 1}/${ttsJobs.length})`);
        await pollJob(ttsJobs[i]);
      }

      setRunningDetail("자막 생성 중...");
      const subJob = await api(`/api/projects/${projectId}/subtitles/generate`, {
        method: "POST", body: JSON.stringify({ script_version_id: versionId }),
      });
      await pollJob(subJob.id);

      // Fetch voice tracks
      const voices: VoiceInfo[] = [];
      for (const shot of shotsData) {
        try {
          const res = await api(`/api/projects/${projectId}/shots/${shot.id}/tts`);
          if (res.voice_tracks?.length) voices.push(...res.voice_tracks.map((v: Record<string, unknown>) => ({
            id: v.id as string, shot_id: shot.id, duration_sec: v.duration_sec as number | null,
          })));
        } catch { /* skip */ }
      }
      setVoiceTracks(voices);

      // Fetch subtitle segments
      try {
        const subRes = await api(`/api/projects/${projectId}/subtitles`);
        const track = subRes.tracks?.[0];
        if (track?.segments) setSubtitleSegments(track.segments);
      } catch { /* skip */ }

      setStage("audio_review");
    } catch (err) { handleError(err); }
  };

  const runAssembly = async () => {
    if (!versionId) return;
    try {
      setStage("assembly_running");
      setRunningDetail("타임라인 조립 중...");

      const tlJob = await api(`/api/projects/${projectId}/timelines/compose`, {
        method: "POST", body: JSON.stringify({ script_version_id: versionId }),
      });
      await pollJob(tlJob.id);

      const tlData = await api(`/api/projects/${projectId}/timelines?script_version_id=${versionId}`);
      const timeline = tlData.timelines?.[0];
      if (!timeline) throw new Error("타임라인이 생성되지 않았습니다");

      setRunningDetail("최종 영상 렌더링 중...");
      const renderJob = await api(`/api/projects/${projectId}/render`, {
        method: "POST", body: JSON.stringify({ timeline_id: timeline.id, burn_subtitles: true }),
      });
      await pollJob(renderJob.id, 600);

      const renderJobs = await api(`/api/projects/${projectId}/render-jobs?timeline_id=${timeline.id}`);
      const completed = renderJobs.render_jobs?.find((r: Record<string, unknown>) => r.status === "completed");
      if (completed) {
        const output = await api(`/api/projects/${projectId}/render-jobs/${completed.id}/output`);
        setRenderOutputUrl(output.output_url || null);
      }

      setStage("done");
      onComplete?.();
    } catch (err) { handleError(err); }
  };

  /* ── Scroll to top on stage change ─────────────────── */
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    containerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [stage]);

  /* ── Render ────────────────────────────────────────── */

  if (stage === "idle") {
    return (
      <div ref={containerRef} className="max-w-xl mx-auto space-y-6">
        <div className="text-center pt-4">
          <h2 className="text-2xl font-bold">어떤 영상을 만들까요?</h2>
          <p className="text-sm text-neutral-400 mt-1">
            주제를 입력하면 단계별로 결과를 확인하며 영상을 만들 수 있어요
          </p>
        </div>

        <div className="space-y-4">
          <textarea
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder={"예: 우주를 탐험하는 고양이 루나의 모험\n예: 3분 요리! 초간단 계란볶음밥\n예: 직장인을 위한 5가지 시간관리 팁"}
            rows={3}
            className="w-full rounded-xl border border-neutral-700 bg-neutral-800/80 px-4 py-3 text-base text-neutral-100 placeholder-neutral-500 focus:border-blue-500 focus:outline-none resize-none"
            autoFocus
          />

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-neutral-400 mb-1.5">영상 길이</label>
              <div className="flex gap-2">
                {DURATION_OPTIONS.map((opt) => (
                  <button key={opt.value} onClick={() => setDuration(opt.value)}
                    className={`flex-1 rounded-lg border px-3 py-2 text-sm transition ${
                      duration === opt.value
                        ? "border-blue-500 bg-blue-600/20 text-blue-300"
                        : "border-neutral-700 bg-neutral-800/50 text-neutral-400 hover:border-neutral-600"
                    }`}
                  >{opt.label}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-400 mb-1.5">영상 분위기</label>
              <select value={style} onChange={(e) => setStyle(e.target.value)}
                className="w-full rounded-lg border border-neutral-700 bg-neutral-800/80 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none"
              >
                {STYLE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>

          <button onClick={runScript} disabled={!topic.trim()}
            className="w-full rounded-xl bg-blue-600 py-3.5 text-base font-bold transition hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Step 1: 대본 만들기
          </button>
        </div>

        {onSwitchToExpert && (
          <div className="text-center">
            <button onClick={onSwitchToExpert}
              className="text-xs text-neutral-500 hover:text-neutral-300 transition underline underline-offset-2"
            >세부 단계별로 직접 조정하기 (전문가 모드)</button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div ref={containerRef} className="max-w-3xl mx-auto space-y-4">
      <StageIndicator current={stage} />

      {/* ═══ Error ═══ */}
      {stage === "error" && (
        <div className="rounded-xl border border-red-800/50 bg-red-950/20 p-6 space-y-4">
          <h3 className="text-lg font-bold text-red-400">오류가 발생했습니다</h3>
          <p className="text-sm text-red-300">{errorMsg}</p>
          <div className="flex gap-3">
            <button onClick={() => { setStage("idle"); }}
              className="flex-1 rounded-lg bg-red-600/80 py-2.5 text-sm font-medium hover:bg-red-500 transition"
            >처음부터 다시</button>
            {onSwitchToExpert && (
              <button onClick={onSwitchToExpert}
                className="flex-1 rounded-lg border border-neutral-700 py-2.5 text-sm text-neutral-300 hover:bg-neutral-800 transition"
              >전문가 모드에서 확인</button>
            )}
          </div>
        </div>
      )}

      {/* ═══ Script Running ═══ */}
      {stage === "script_running" && (
        <RunningSpinner message="대본을 작성하고 있어요" detail={runningDetail} />
      )}

      {/* ═══ Script Review ═══ */}
      {stage === "script_review" && scriptPlan && (
        <div className="space-y-4">
          <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs text-blue-400 font-medium">Step 1 완료</span>
                <h3 className="text-xl font-bold mt-1">{scriptPlan.title}</h3>
              </div>
              <span className="text-xs text-neutral-500 bg-neutral-800 px-2 py-1 rounded-full">
                약 {scriptPlan.estimated_duration_sec}초
              </span>
            </div>

            <p className="text-sm text-neutral-300">{scriptPlan.summary}</p>

            {scriptPlan.hook && (
              <div className="rounded-lg bg-amber-950/20 border border-amber-800/30 p-3">
                <span className="text-[10px] text-amber-400 font-bold uppercase">Hook</span>
                <p className="text-sm text-amber-200 mt-1">&ldquo;{scriptPlan.hook}&rdquo;</p>
              </div>
            )}

            <div>
              <h4 className="text-sm font-semibold text-neutral-300 mb-2">섹션 구성 ({scriptPlan.sections.length}개)</h4>
              <div className="space-y-2">
                {scriptPlan.sections.map((sec, i) => (
                  <div key={i} className="rounded-lg border border-neutral-800 bg-neutral-800/30 p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-neutral-200">
                        {i + 1}. {sec.title}
                      </span>
                      <span className="text-[10px] text-neutral-500">{sec.duration_sec}초</span>
                    </div>
                    <p className="text-xs text-neutral-400">{sec.description}</p>
                    {sec.narration && (
                      <p className="text-xs text-neutral-500 mt-1.5 italic border-l-2 border-neutral-700 pl-2">
                        &ldquo;{sec.narration.slice(0, 120)}{sec.narration.length > 120 ? "..." : ""}&rdquo;
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {scriptPlan.narration_draft && (
              <details className="group">
                <summary className="text-xs text-neutral-500 cursor-pointer hover:text-neutral-300 transition">
                  전체 나레이션 미리보기 ▸
                </summary>
                <p className="text-xs text-neutral-400 mt-2 leading-relaxed whitespace-pre-wrap bg-neutral-800/50 rounded-lg p-3">
                  {scriptPlan.narration_draft}
                </p>
              </details>
            )}

            {scriptPlan.ending_cta && (
              <div className="rounded-lg bg-emerald-950/20 border border-emerald-800/30 p-3">
                <span className="text-[10px] text-emerald-400 font-bold uppercase">CTA</span>
                <p className="text-sm text-emerald-200 mt-1">&ldquo;{scriptPlan.ending_cta}&rdquo;</p>
              </div>
            )}
          </div>

          <ReviewActions
            onApprove={runStructure}
            onRegenerate={runScript}
            approveLabel="승인 → 장면 구성으로"
          />
        </div>
      )}

      {/* ═══ Structure Running ═══ */}
      {stage === "structure_running" && (
        <RunningSpinner message="장면과 샷을 구성하고 있어요" detail={runningDetail} />
      )}

      {/* ═══ Structure Review ═══ */}
      {stage === "structure_review" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs text-blue-400 font-medium">Step 2 완료</span>
                <h3 className="text-lg font-bold mt-1">장면 구성</h3>
              </div>
              <span className="text-xs text-neutral-500 bg-neutral-800 px-2 py-1 rounded-full">
                {scenesData.length} Scene / {shotsData.length} Shot / {framesData.length} Frame
              </span>
            </div>

            <div className="space-y-3">
              {scenesData.map((scene, si) => {
                const sceneShots = shotsData.filter(s => s.scene_id === scene.id);
                return (
                  <div key={scene.id} className="rounded-lg border border-neutral-800 bg-neutral-800/20 p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-neutral-200">
                        Scene {si + 1}: {scene.title || "무제"}
                      </span>
                      <div className="flex items-center gap-2">
                        {scene.mood && <span className="text-[10px] text-purple-400 bg-purple-900/30 px-1.5 py-0.5 rounded">{scene.mood}</span>}
                        <span className="text-[10px] text-neutral-500">{scene.duration_estimate_sec || "?"}초</span>
                      </div>
                    </div>
                    {scene.description && <p className="text-xs text-neutral-400">{scene.description}</p>}
                    {scene.narration_text && (
                      <p className="text-xs text-neutral-500 italic border-l-2 border-neutral-700 pl-2">
                        &ldquo;{scene.narration_text.slice(0, 80)}{scene.narration_text.length > 80 ? "..." : ""}&rdquo;
                      </p>
                    )}
                    <div className="pl-3 space-y-1">
                      {sceneShots.map((shot, shi) => {
                        const shotFrames = framesData.filter(f => f.shot_id === shot.id);
                        return (
                          <div key={shot.id} className="flex items-center gap-2 text-xs text-neutral-400">
                            <span className="text-neutral-600">└</span>
                            <span className="font-medium text-neutral-300">Shot {si + 1}-{shi + 1}</span>
                            {shot.shot_type && <span className="text-blue-400">{shot.shot_type}</span>}
                            {shot.description && <span className="truncate flex-1">{shot.description.slice(0, 60)}</span>}
                            <span className="text-neutral-600 shrink-0">{shot.duration_sec || "?"}초</span>
                            <span className="text-neutral-600 shrink-0">{shotFrames.length}F</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <ReviewActions
            onApprove={runImages}
            onRegenerate={runStructure}
            approveLabel="승인 → 이미지 생성으로"
          />
        </div>
      )}

      {/* ═══ Images Running ═══ */}
      {stage === "images_running" && (
        <RunningSpinner message="이미지를 생성하고 있어요" detail={runningDetail} />
      )}

      {/* ═══ Images Review ═══ */}
      {stage === "images_review" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5 space-y-4">
            <div>
              <span className="text-xs text-blue-400 font-medium">Step 3 완료</span>
              <h3 className="text-lg font-bold mt-1">생성된 이미지 ({imageAssets.length}개)</h3>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {imageAssets.map((asset) => {
                const frame = framesData.find(f => f.id === asset.parent_id);
                return (
                  <div key={asset.id} className="rounded-lg border border-neutral-800 overflow-hidden bg-neutral-900">
                    {asset.url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={asset.url} alt="frame" className="w-full aspect-[16/9] object-cover" />
                    ) : (
                      <div className="w-full aspect-[16/9] bg-neutral-800 flex items-center justify-center text-neutral-600 text-xs">
                        로딩 중
                      </div>
                    )}
                    <div className="px-2 py-1">
                      <span className={`text-[9px] font-bold uppercase ${
                        frame?.frame_role === "start" ? "text-emerald-400"
                        : frame?.frame_role === "end" ? "text-rose-400"
                        : "text-amber-400"
                      }`}>{frame?.frame_role || "frame"}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {imageAssets.length === 0 && (
              <p className="text-sm text-neutral-500 text-center py-4">
                생성된 이미지가 없습니다. 프레임 설정을 확인해주세요.
              </p>
            )}
          </div>

          <ReviewActions
            onApprove={runVideos}
            onRegenerate={runImages}
            approveLabel="승인 → 비디오 생성으로"
          />
        </div>
      )}

      {/* ═══ Videos Running ═══ */}
      {stage === "videos_running" && (
        <RunningSpinner message="비디오 클립을 생성하고 있어요" detail={runningDetail} />
      )}

      {/* ═══ Videos Review ═══ */}
      {stage === "videos_review" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5 space-y-4">
            <div>
              <span className="text-xs text-blue-400 font-medium">Step 4 완료</span>
              <h3 className="text-lg font-bold mt-1">생성된 비디오 클립 ({videoAssets.length}개)</h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {videoAssets.map((asset, idx) => {
                const shot = shotsData.find(s => s.id === asset.parent_id);
                return (
                  <div key={asset.id} className="rounded-lg border border-neutral-800 overflow-hidden bg-neutral-900">
                    {asset.url ? (
                      // eslint-disable-next-line jsx-a11y/media-has-caption
                      <video src={asset.url} controls className="w-full aspect-video bg-black" preload="metadata" />
                    ) : (
                      <div className="w-full aspect-video bg-neutral-800 flex items-center justify-center text-neutral-600 text-xs">
                        로딩 중
                      </div>
                    )}
                    <div className="px-3 py-2 flex items-center justify-between">
                      <span className="text-xs text-neutral-300 font-medium">
                        Shot {idx + 1}
                        {shot?.shot_type && <span className="text-neutral-500 ml-1">({shot.shot_type})</span>}
                      </span>
                      {shot?.duration_sec && <span className="text-[10px] text-neutral-500">{shot.duration_sec}초</span>}
                    </div>
                  </div>
                );
              })}
            </div>

            {videoAssets.length === 0 && (
              <p className="text-sm text-neutral-500 text-center py-4">
                생성된 비디오가 없습니다.
              </p>
            )}
          </div>

          <ReviewActions
            onApprove={runAudio}
            onRegenerate={runVideos}
            approveLabel="승인 → 음성/자막 생성으로"
          />
        </div>
      )}

      {/* ═══ Audio Running ═══ */}
      {stage === "audio_running" && (
        <RunningSpinner message="음성과 자막을 만들고 있어요" detail={runningDetail} />
      )}

      {/* ═══ Audio Review ═══ */}
      {stage === "audio_review" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5 space-y-4">
            <div>
              <span className="text-xs text-blue-400 font-medium">Step 5 완료</span>
              <h3 className="text-lg font-bold mt-1">음성 & 자막</h3>
            </div>

            <div className="rounded-lg border border-neutral-800 bg-neutral-800/30 p-3 space-y-2">
              <h4 className="text-sm font-semibold text-neutral-300">
                TTS 음성 ({voiceTracks.length}개 트랙)
              </h4>
              {voiceTracks.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {voiceTracks.map((vt, i) => (
                    <span key={vt.id} className="text-xs bg-neutral-700/50 text-neutral-300 px-2 py-1 rounded">
                      Shot {i + 1}: {vt.duration_sec ? `${vt.duration_sec.toFixed(1)}초` : "생성됨"}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-neutral-500">음성 트랙이 생성되지 않았습니다.</p>
              )}
            </div>

            {subtitleSegments.length > 0 && (
              <div className="rounded-lg border border-neutral-800 bg-neutral-800/30 p-3 space-y-2">
                <h4 className="text-sm font-semibold text-neutral-300">
                  자막 미리보기 ({subtitleSegments.length}개 세그먼트)
                </h4>
                <div className="max-h-48 overflow-y-auto space-y-1">
                  {subtitleSegments.map((seg) => (
                    <div key={seg.index} className="flex items-start gap-2 text-xs">
                      <span className="text-neutral-600 shrink-0 font-mono w-20">
                        {(seg.start_ms / 1000).toFixed(1)}s~{(seg.end_ms / 1000).toFixed(1)}s
                      </span>
                      <span className="text-neutral-300">{seg.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <ReviewActions
            onApprove={runAssembly}
            onRegenerate={runAudio}
            approveLabel="승인 → 최종 합성으로"
          />
        </div>
      )}

      {/* ═══ Assembly Running ═══ */}
      {stage === "assembly_running" && (
        <RunningSpinner message="최종 영상을 합성하고 있어요" detail={runningDetail} />
      )}

      {/* ═══ Done ═══ */}
      {stage === "done" && (
        <div className="space-y-4">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-emerald-400">영상이 완성되었어요!</h2>
          </div>

          {renderOutputUrl ? (
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 overflow-hidden">
              {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
              <video src={renderOutputUrl} controls className="w-full aspect-video bg-black" />
              <div className="p-4 flex gap-3">
                <a href={renderOutputUrl} download
                  className="flex-1 text-center rounded-lg bg-blue-600 py-2.5 text-sm font-medium hover:bg-blue-500 transition"
                >영상 다운로드</a>
                {onSwitchToExpert && (
                  <button onClick={onSwitchToExpert}
                    className="flex-1 rounded-lg border border-neutral-700 py-2.5 text-sm text-neutral-300 hover:bg-neutral-800 transition"
                  >세부 조정하기</button>
                )}
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-emerald-800/50 bg-emerald-950/20 p-5 text-center">
              <p className="text-sm text-emerald-300">파이프라인 완료. 전문가 모드에서 결과를 확인하세요.</p>
              {onSwitchToExpert && (
                <button onClick={onSwitchToExpert}
                  className="mt-3 rounded-lg bg-emerald-600 px-5 py-2 text-sm font-medium hover:bg-emerald-500 transition"
                >결과 확인하기</button>
              )}
            </div>
          )}

          <div className="text-center">
            <button onClick={() => { setStage("idle"); setScriptPlan(null); setVersionId(null); setScenesData([]); setShotsData([]); setFramesData([]); setImageAssets([]); setVideoAssets([]); setVoiceTracks([]); setSubtitleSegments([]); setRenderOutputUrl(null); }}
              className="text-xs text-neutral-500 hover:text-neutral-300 transition underline underline-offset-2"
            >새 영상 만들기</button>
          </div>
        </div>
      )}

      {/* Cancel button for running stages */}
      {stage.endsWith("_running") && (
        <div className="text-center">
          <button onClick={() => { abortRef.current = true; }}
            className="text-xs text-neutral-500 hover:text-red-400 transition"
          >제작 중단</button>
        </div>
      )}
    </div>
  );
}
