"use client";

import { useState, useCallback } from "react";
import { apiUrl } from "@/lib/api";

/* ── Types ──────────────────────────────────────────── */

interface ProgressData {
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

type StepState = "done" | "active" | "ready" | "locked" | "running" | "error";

interface GuidedStep {
  id: string;
  num: number;
  title: string;
  description: string;
  state: StepState;
  action: string | null;
  detail: string | null;
  errorMsg: string | null;
  doneCondition: string;
  nextCondition: string;
  counts?: string;
}

/* ── Error Toast ─────────────────────────────────────── */

function ErrorToast({ message, onRetry, onDismiss }: {
  message: string;
  onRetry?: () => void;
  onDismiss: () => void;
}) {
  return (
    <div className="rounded-lg border border-red-800/50 bg-red-950/30 p-3 flex items-start gap-3 animate-in slide-in-from-top">
      <span className="text-red-400 mt-0.5">✖</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-red-300">{message}</p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {onRetry && (
          <button
            onClick={onRetry}
            className="text-xs text-red-400 hover:text-red-300 font-medium transition"
          >
            다시 시도
          </button>
        )}
        <button onClick={onDismiss} className="text-neutral-600 hover:text-neutral-400 text-xs">✕</button>
      </div>
    </div>
  );
}

/* ── Step Card ───────────────────────────────────────── */

function StepCard({ step, isFirst, onAction }: {
  step: GuidedStep;
  isFirst: boolean;
  onAction: () => void;
}) {
  const isActive = step.state === "active" || step.state === "ready";
  const isRunning = step.state === "running";
  const isDone = step.state === "done";
  const isError = step.state === "error";
  const isLocked = step.state === "locked";

  const borderColor = isDone ? "border-emerald-800/40"
    : isActive && isFirst ? "border-blue-600/60 ring-1 ring-blue-500/20"
    : isActive ? "border-blue-800/40"
    : isRunning ? "border-blue-700/50"
    : isError ? "border-red-800/40"
    : "border-neutral-800";

  const bgColor = isDone ? "bg-emerald-950/5"
    : isActive && isFirst ? "bg-blue-950/15"
    : isRunning ? "bg-blue-950/10"
    : isError ? "bg-red-950/10"
    : "bg-neutral-900/30";

  return (
    <div className={`rounded-xl border ${borderColor} ${bgColor} p-5 transition-all`}>
      <div className="flex items-start gap-4">
        {/* Step number circle */}
        <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${
          isDone ? "bg-emerald-600/20 text-emerald-400 border border-emerald-600/30"
          : isRunning ? "bg-blue-600/20 text-blue-400 border border-blue-600/30 animate-pulse"
          : isActive && isFirst ? "bg-blue-600 text-white border border-blue-500"
          : isActive ? "bg-blue-600/20 text-blue-400 border border-blue-600/30"
          : isError ? "bg-red-600/20 text-red-400 border border-red-600/30"
          : "bg-neutral-800 text-neutral-600 border border-neutral-700"
        }`}>
          {isDone ? "✓" : step.num}
        </div>

        <div className="flex-1 min-w-0">
          {/* Title + status */}
          <div className="flex items-center gap-2 mb-1">
            <h3 className={`text-base font-bold ${
              isDone ? "text-emerald-400/80"
              : isActive && isFirst ? "text-white"
              : isActive ? "text-neutral-200"
              : isLocked ? "text-neutral-600"
              : "text-neutral-300"
            }`}>{step.title}</h3>
            {isDone && <span className="text-[10px] text-emerald-400 bg-emerald-900/30 px-1.5 py-0.5 rounded font-medium">완료</span>}
            {isRunning && <span className="text-[10px] text-blue-400 bg-blue-900/30 px-1.5 py-0.5 rounded font-medium animate-pulse">진행 중</span>}
            {isError && <span className="text-[10px] text-red-400 bg-red-900/30 px-1.5 py-0.5 rounded font-medium">실패</span>}
          </div>

          {/* Description */}
          <p className={`text-sm mb-2 ${isLocked ? "text-neutral-700" : "text-neutral-500"}`}>
            {step.description}
          </p>

          {/* Counts */}
          {step.counts && !isLocked && (
            <p className="text-xs text-neutral-500 mb-2">{step.counts}</p>
          )}

          {/* Detail */}
          {step.detail && !isLocked && (
            <p className="text-xs text-neutral-400 mb-2">{step.detail}</p>
          )}

          {/* Error */}
          {step.errorMsg && (
            <div className="rounded-md bg-red-950/30 border border-red-900/30 px-3 py-2 mb-2">
              <p className="text-xs text-red-400">{step.errorMsg}</p>
            </div>
          )}

          {/* Action button */}
          {step.action && !isLocked && !isDone && (
            <button
              onClick={onAction}
              disabled={isRunning}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                isActive && isFirst
                  ? "bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-600/20"
                  : isError
                    ? "bg-red-600/20 text-red-300 border border-red-700/50 hover:bg-red-600/30"
                    : isRunning
                      ? "bg-neutral-800 text-neutral-500 cursor-wait"
                      : "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
              }`}
            >
              {isRunning ? "처리 중..." : step.action}
            </button>
          )}

          {/* Completion / next conditions — small text */}
          {!isLocked && !isDone && (
            <div className="mt-3 text-[10px] text-neutral-600 space-y-0.5">
              <p>완료 조건: {step.doneCondition}</p>
              <p>다음 단계 조건: {step.nextCondition}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Main Component ──────────────────────────────────── */

interface GuidedWorkflowProps {
  projectId: string;
  progress: ProgressData | null;
  hasApiKey: boolean;
  onSwitchToAdvanced: () => void;
  onSwitchToAutoPilot: () => void;
  onRefresh: () => void;
}

export default function GuidedWorkflow({
  projectId,
  progress,
  hasApiKey,
  onSwitchToAdvanced,
  onSwitchToAutoPilot,
  onRefresh,
}: GuidedWorkflowProps) {
  const [errors, setErrors] = useState<{ id: string; msg: string; retry?: () => void }[]>([]);
  const [runningStep, setRunningStep] = useState<string | null>(null);

  const addError = (id: string, msg: string, retry?: () => void) => {
    setErrors(prev => [...prev.filter(e => e.id !== id), { id, msg, retry }]);
  };
  const removeError = (id: string) => {
    setErrors(prev => prev.filter(e => e.id !== id));
  };

  const apiCall = useCallback(async (path: string, opts?: RequestInit) => {
    const res = await fetch(apiUrl(path), {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status}: ${text.slice(0, 200)}`);
    }
    return res.json();
  }, []);

  // Derive step states from progress
  const p = progress;
  const hasScript = p?.script ?? false;
  const hasScenes = (p?.scenes ?? 0) > 0;
  const hasShots = (p?.shots ?? 0) > 0;
  const hasFrames = (p?.frames ?? 0) > 0;
  const hasImages = (p?.images ?? 0) > 0;
  const hasVideos = (p?.videos ?? 0) > 0;
  const hasVoices = (p?.voices ?? 0) > 0;
  const hasSubtitles = (p?.subtitles ?? 0) > 0;
  const hasTimelines = (p?.timelines ?? 0) > 0;
  const hasRenders = (p?.renders ?? 0) > 0;

  const activeJobs = new Set((p?.active_jobs ?? []).map(j => j.job_type));
  const hasActiveJob = (types: string[]) => types.some(t => activeJobs.has(t));
  const latestError = (p?.active_jobs ?? []).find(j => j.status === "failed");

  function stepState(done: boolean, ready: boolean, jobTypes: string[]): StepState {
    if (runningStep && jobTypes.some(t => runningStep === t)) return "running";
    if (hasActiveJob(jobTypes)) return "running";
    if (done) return "done";
    if (ready) return "ready";
    return "locked";
  }

  // Find the first non-done step for "active" highlighting
  const stepDefs: { id: string; done: boolean }[] = [
    { id: "script", done: hasScript },
    { id: "structure", done: hasShots && hasFrames },
    { id: "style", done: hasScenes },
    { id: "storyboard", done: hasFrames },
    { id: "generate", done: hasImages },
    { id: "audio", done: hasVoices && hasSubtitles && hasTimelines },
    { id: "render", done: hasRenders },
  ];
  const firstIncomplete = stepDefs.find(s => !s.done)?.id || null;

  function getState(id: string, done: boolean, ready: boolean, jobTypes: string[]): StepState {
    const base = stepState(done, ready, jobTypes);
    if (base === "ready" && id === firstIncomplete) return "active";
    if (base === "ready") return "ready";
    return base;
  }

  const steps: GuidedStep[] = [
    {
      id: "script",
      num: 1,
      title: "대본 생성",
      description: "영상 주제를 입력하면 AI가 대본을 작성합니다",
      state: getState("script", hasScript, true, ["script_generate", "script_structure"]),
      action: hasScript ? null : "대본 생성하러 가기",
      detail: hasScript ? `대본 v${p?.script ? "✓" : "?"} 생성됨` : null,
      errorMsg: null,
      counts: undefined,
      doneCondition: "대본이 1개 이상 생성됨",
      nextCondition: "대본을 승인하면 장면 구조 생성 가능",
    },
    {
      id: "structure",
      num: 2,
      title: "장면 구조 확인",
      description: "대본을 바탕으로 씬, 샷, 프레임 구조를 생성합니다",
      state: getState("structure", hasShots && hasFrames, hasScript, ["scene_plan", "shot_plan", "frame_plan"]),
      action: hasShots && hasFrames ? null : hasScript ? "장면 구조 생성하러 가기" : null,
      detail: null,
      errorMsg: null,
      counts: (hasScenes || hasShots || hasFrames)
        ? `씬 ${p?.scenes ?? 0} · 샷 ${p?.shots ?? 0} · 프레임 ${p?.frames ?? 0}`
        : undefined,
      doneCondition: "씬 + 샷 + 프레임이 모두 존재",
      nextCondition: "프레임이 생성되면 이미지 생성 가능",
    },
    {
      id: "style",
      num: 3,
      title: "스타일 · 캐릭터 설정",
      description: "영상의 비주얼 스타일과 등장 캐릭터를 설정합니다",
      state: getState("style", hasScenes, hasScript, []),
      action: hasScenes ? "스타일 설정하러 가기" : null,
      detail: hasScenes ? "선택사항 — 설정하지 않아도 다음 단계 진행 가능" : null,
      errorMsg: null,
      counts: undefined,
      doneCondition: "스타일 프리셋 또는 캐릭터 1개 이상 등록 (선택)",
      nextCondition: "프레임이 존재하면 스토리보드 편집 가능",
    },
    {
      id: "storyboard",
      num: 4,
      title: "스토리보드 편집",
      description: "컷 단위로 프롬프트, 길이, 내레이션을 세밀하게 수정합니다",
      state: getState("storyboard", hasImages, hasFrames, []),
      action: hasFrames ? "스토리보드 편집하기" : null,
      detail: hasFrames ? "선택사항 — 직접 수정 없이 이미지 생성도 가능" : null,
      errorMsg: null,
      counts: hasFrames ? `프레임 ${p?.frames ?? 0}개` : undefined,
      doneCondition: "컷별 프롬프트 확인 · 수정 완료 (선택)",
      nextCondition: "프레임이 존재하면 이미지 생성 가능",
    },
    {
      id: "generate",
      num: 5,
      title: "이미지 · 비디오 생성",
      description: "각 프레임의 이미지를 생성하고 승인 후 비디오 클립을 생성합니다",
      state: getState("generate", hasImages, hasFrames, ["story_prompts", "image_generate", "video_generate"]),
      action: hasImages ? (hasVideos ? null : "이미지 승인 · 비디오 생성하기") : hasFrames ? "이미지 생성하러 가기" : null,
      detail: hasImages && !hasVideos ? "이미지 검토/승인 후 비디오 생성을 권장합니다" : null,
      errorMsg: null,
      counts: (hasImages || hasVideos)
        ? `이미지 ${p?.images ?? 0}개 · 비디오 ${p?.videos ?? 0}개`
        : undefined,
      doneCondition: "이미지 승인 및 비디오가 각 프레임/샷에 대해 생성됨",
      nextCondition: "승인된 이미지 기반으로 비디오 생성 → 오디오/자막 생성 가능",
    },
    {
      id: "audio",
      num: 6,
      title: "오디오 · 자막 · 타임라인",
      description: "TTS 음성, 자막, 타임라인을 생성하고 조립합니다",
      state: getState("audio", hasVoices && hasSubtitles && hasTimelines, hasImages, ["tts_generate", "subtitle_generate", "timeline_compose"]),
      action: !hasVoices && hasImages ? "오디오 생성하러 가기" : (!hasTimelines && hasVoices) ? "타임라인 조립하러 가기" : null,
      detail: null,
      errorMsg: null,
      counts: (hasVoices || hasSubtitles || hasTimelines)
        ? `음성 ${p?.voices ?? 0} · 자막 ${p?.subtitles ?? 0} · 타임라인 ${p?.timelines ?? 0}`
        : undefined,
      doneCondition: "TTS + 자막 + 타임라인이 모두 생성됨",
      nextCondition: "타임라인이 있으면 최종 렌더 가능",
    },
    {
      id: "render",
      num: 7,
      title: "최종 렌더",
      description: "모든 소스를 합쳐 최종 영상 파일을 만듭니다",
      state: getState("render", hasRenders, hasTimelines, ["render_final"]),
      action: hasRenders ? "영상 다운로드" : hasTimelines ? "렌더 시작하러 가기" : null,
      detail: hasRenders ? "렌더 완료! 내보내기 탭에서 다운로드하세요." : null,
      errorMsg: null,
      counts: hasRenders ? `완성된 영상 ${p?.renders ?? 0}개` : undefined,
      doneCondition: "렌더 작업이 성공적으로 완료됨",
      nextCondition: "완성! 내보내기에서 다운로드 가능",
    },
  ];

  // Action handlers — navigate to the appropriate advanced section
  const handleAction = (stepId: string) => {
    const sectionMap: Record<string, string> = {
      script: "script",
      structure: "structure",
      style: "style",
      storyboard: "storyboard",
      generate: "images",
      audio: "tts-subtitle",
      render: "render",
    };
    const target = sectionMap[stepId];
    if (target) {
      onSwitchToAdvanced();
      // A small delay so the advanced view renders first
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent("navigate-section", { detail: target }));
      }, 50);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold">영상 제작 진행 상황</h2>
          <p className="text-xs text-neutral-500 mt-0.5">
            위에서 아래로 순서대로 진행하세요
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onSwitchToAutoPilot}
            className="rounded-lg bg-violet-600/20 border border-violet-700/40 px-3 py-1.5 text-xs font-medium text-violet-300 hover:bg-violet-600/30 transition"
          >
            자동 파일럿
          </button>
          <button
            onClick={onSwitchToAdvanced}
            className="rounded-lg bg-neutral-800 px-3 py-1.5 text-xs font-medium text-neutral-400 hover:text-neutral-200 transition"
          >
            전문가 모드
          </button>
        </div>
      </div>

      {/* API key warning */}
      {!hasApiKey && (
        <div className="rounded-lg border border-amber-700/50 bg-amber-950/30 px-4 py-3">
          <p className="text-sm font-semibold text-amber-400">AI 기능을 사용하려면 API 키가 필요합니다</p>
          <p className="text-xs text-amber-400/70 mt-1">
            시스템 진단 페이지에서 누락된 키를 확인하세요.
            <a href="/status" className="underline ml-1">진단 페이지 →</a>
          </p>
        </div>
      )}

      {/* Error toasts */}
      {errors.length > 0 && (
        <div className="space-y-2">
          {errors.map(e => (
            <ErrorToast
              key={e.id}
              message={e.msg}
              onRetry={e.retry}
              onDismiss={() => removeError(e.id)}
            />
          ))}
        </div>
      )}

      {/* Progress summary bar */}
      {progress && (
        <div className="rounded-lg bg-neutral-800/50 px-4 py-2.5 flex items-center gap-3">
          <div className="flex-1 h-1.5 rounded-full bg-neutral-700">
            <div
              className="h-full rounded-full bg-blue-500 transition-all duration-700"
              style={{ width: `${Math.round((stepDefs.filter(s => s.done).length / stepDefs.length) * 100)}%` }}
            />
          </div>
          <span className="text-xs text-neutral-400 shrink-0">
            {stepDefs.filter(s => s.done).length}/{stepDefs.length} 완료
          </span>
        </div>
      )}

      {/* Step cards */}
      <div className="space-y-3">
        {steps.map((step, i) => (
          <StepCard
            key={step.id}
            step={step}
            isFirst={step.id === firstIncomplete}
            onAction={() => handleAction(step.id)}
          />
        ))}
      </div>
    </div>
  );
}
