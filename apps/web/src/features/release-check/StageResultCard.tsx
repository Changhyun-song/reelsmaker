"use client";

/* ── Types ──────────────────────────────────────────── */

export type StageStatus = "success" | "fail" | "not_run" | "partial";

export interface StageResult {
  key: string;
  label: string;
  status: StageStatus;
  detail: string;
  error: string | null;
  lastRun: string | null;
  counts: string | null;
}

interface Props {
  stage: StageResult;
  checked: boolean;
  onToggle: () => void;
}

/* ── Helpers ─────────────────────────────────────────── */

const STATUS_STYLES: Record<StageStatus, { bg: string; border: string; badge: string; badgeBg: string; icon: string }> = {
  success: {
    bg: "bg-emerald-950/10",
    border: "border-emerald-800/40",
    badge: "text-emerald-400",
    badgeBg: "bg-emerald-600/20",
    icon: "✓",
  },
  fail: {
    bg: "bg-red-950/10",
    border: "border-red-800/40",
    badge: "text-red-400",
    badgeBg: "bg-red-600/20",
    icon: "✗",
  },
  partial: {
    bg: "bg-amber-950/10",
    border: "border-amber-800/40",
    badge: "text-amber-400",
    badgeBg: "bg-amber-600/20",
    icon: "△",
  },
  not_run: {
    bg: "bg-neutral-900/30",
    border: "border-neutral-800",
    badge: "text-neutral-500",
    badgeBg: "bg-neutral-800",
    icon: "–",
  },
};

const STATUS_LABELS: Record<StageStatus, string> = {
  success: "성공",
  fail: "실패",
  partial: "일부 완료",
  not_run: "미실행",
};

function relTime(iso: string | null): string {
  if (!iso) return "";
  const sec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (sec < 0) return "방금 전";
  if (sec < 60) return `${sec}초 전`;
  if (sec < 3600) return `${Math.floor(sec / 60)}분 전`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}시간 전`;
  return `${Math.floor(sec / 86400)}일 전`;
}

/* ── Component ───────────────────────────────────────── */

export default function StageResultCard({ stage, checked, onToggle }: Props) {
  const s = STATUS_STYLES[stage.status];

  return (
    <div className={`rounded-xl border ${s.border} ${s.bg} p-4 transition-all`}>
      <div className="flex items-start gap-3">
        {/* Status icon */}
        <div className={`w-7 h-7 rounded-lg ${s.badgeBg} flex items-center justify-center shrink-0`}>
          <span className={`text-sm font-bold ${s.badge}`}>{s.icon}</span>
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-sm font-medium text-neutral-200">{stage.label}</span>
            <span className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${s.badgeBg} ${s.badge}`}>
              {STATUS_LABELS[stage.status]}
            </span>
            {stage.counts ? (
              <span className="text-[9px] text-neutral-600 font-mono">{stage.counts}</span>
            ) : null}
          </div>

          <p className="text-[11px] text-neutral-500 leading-snug">{stage.detail}</p>

          {stage.error ? (
            <p className="text-[10px] text-red-400/80 mt-1 line-clamp-2">{stage.error}</p>
          ) : null}

          {stage.lastRun ? (
            <p className="text-[9px] text-neutral-600 mt-1">마지막 실행: {relTime(stage.lastRun)}</p>
          ) : null}
        </div>

        {/* Manual check toggle */}
        <button
          onClick={(e) => { e.stopPropagation(); onToggle(); }}
          className={`w-5 h-5 rounded border-2 shrink-0 mt-0.5 transition ${
            checked
              ? "bg-blue-600 border-blue-500"
              : "bg-transparent border-neutral-700 hover:border-neutral-500"
          } flex items-center justify-center`}
          title="검수 완료 체크"
        >
          {checked ? <span className="text-white text-[10px] font-bold">✓</span> : null}
        </button>
      </div>
    </div>
  );
}
