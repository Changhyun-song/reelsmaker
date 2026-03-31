"use client";

import { LinearProgress } from "@/components/ui/progress";

interface GenerationProgressProps {
  stage: string;
  currentStep: number;
  totalSteps: number;
  modelName?: string;
  aspectRatio?: string;
  elapsedSec?: number;
}

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function GenerationProgress({
  stage,
  currentStep,
  totalSteps,
  modelName = "Seedance 1.0 Lite",
  aspectRatio = "9:16",
  elapsedSec,
}: GenerationProgressProps) {
  const pct = totalSteps > 0 ? (currentStep / totalSteps) * 100 : 0;

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 px-5 py-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          {/* Model badge */}
          <span className="inline-flex items-center gap-1.5 rounded-full bg-violet-900/40 border border-violet-700/40 px-3 py-1 text-[11px] font-semibold text-violet-300">
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
            {modelName}
          </span>
          <span className="text-[11px] text-neutral-500">
            비율 <span className="text-neutral-300 font-medium">{aspectRatio}</span>
          </span>
          <span className="text-[11px] text-neutral-500">
            컷 <span className="text-neutral-300 font-medium">{totalSteps}</span>개
          </span>
        </div>

        <div className="flex items-center gap-3">
          {elapsedSec != null && (
            <span className="text-[11px] text-neutral-500">{formatTime(elapsedSec)}</span>
          )}
          <span className="text-xs font-bold text-violet-400">
            {stage} {Math.round(pct)}%
          </span>
        </div>
      </div>
      <LinearProgress value={pct} color="bg-violet-500" size="sm" />
      <p className="mt-1.5 text-[11px] text-neutral-500">
        {currentStep}/{totalSteps} 완료
      </p>
    </div>
  );
}
