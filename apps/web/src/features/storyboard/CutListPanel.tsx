"use client";

import { useCallback } from "react";

/* ── Types ──────────────────────────────────────────── */

export interface CutItem {
  cutIndex: number;
  frameId: string;
  shotId: string;
  shotIndex: number;
  sceneIndex: number;
  frameRole: string;
  narration: string | null;
  durationMs: number;
  imageStatus: "none" | "ready" | "approved" | "rejected";
  videoStatus: "none" | "ready";
  hasPrompt: boolean;
  thumbnailUrl: string | null;
}

interface CutListPanelProps {
  cuts: CutItem[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  onReorder: (from: number, to: number) => void;
}

/* ── Status badge ────────────────────────────────────── */

function StatusBadge({ status, label }: { status: string; label: string }) {
  const cfg: Record<string, { bg: string; text: string; ring?: string }> = {
    none: { bg: "bg-neutral-800", text: "text-neutral-600" },
    ready: { bg: "bg-amber-900/30", text: "text-amber-400", ring: "ring-1 ring-amber-800/40" },
    approved: { bg: "bg-emerald-900/30", text: "text-emerald-400" },
    rejected: { bg: "bg-red-900/30", text: "text-red-400" },
  };
  const c = cfg[status] || cfg.none;
  return (
    <span className={`inline-flex items-center gap-1 rounded px-1 py-0.5 ${c.bg} ${c.ring || ""}`}>
      <span className={`w-1 h-1 rounded-full ${
        status === "approved" ? "bg-emerald-400" : status === "ready" ? "bg-amber-400" : status === "rejected" ? "bg-red-400" : "bg-neutral-700"
      }`} />
      <span className={`text-[7px] uppercase font-medium ${c.text}`}>{label}</span>
    </span>
  );
}

/* ── Cut row ────────────────────────────────────────── */

function CutRow({ cut, isSelected, onSelect }: { cut: CutItem; isSelected: boolean; onSelect: () => void }) {
  const durationSec = (cut.durationMs / 1000).toFixed(1);

  const imgLabel = cut.imageStatus === "approved" ? "승인" : cut.imageStatus === "ready" ? "대기" : cut.imageStatus === "rejected" ? "거절" : "없음";
  const vidLabel = cut.videoStatus === "ready" ? "완료" : "없음";

  return (
    <button
      onClick={onSelect}
      className={`w-full text-left rounded-lg border transition-all duration-150 group ${
        isSelected
          ? "border-blue-600/60 bg-blue-950/30 ring-1 ring-blue-500/20"
          : "border-neutral-800/60 bg-neutral-900/30 hover:border-neutral-700 hover:bg-neutral-800/40"
      }`}
    >
      <div className="flex gap-2 p-2">
        {/* Thumbnail */}
        <div className="w-12 h-16 rounded-md bg-neutral-800 overflow-hidden shrink-0 relative">
          {cut.thumbnailUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={cut.thumbnailUrl} alt={`Cut ${cut.cutIndex + 1}`} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-neutral-600 text-[8px]">없음</div>
          )}
          <span className={`absolute top-0.5 left-0.5 rounded px-1 py-0.5 text-[7px] font-bold ${
            isSelected ? "bg-blue-600 text-white" : "bg-neutral-900/80 text-neutral-400"
          }`}>
            {cut.cutIndex + 1}
          </span>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-[9px] font-medium text-neutral-400">S{cut.sceneIndex + 1}.{cut.shotIndex + 1}</span>
            <span className={`text-[8px] px-1 rounded ${
              cut.frameRole === "start"
                ? "bg-emerald-900/50 text-emerald-400"
                : cut.frameRole === "end"
                  ? "bg-rose-900/50 text-rose-400"
                  : "bg-neutral-800 text-neutral-500"
            }`}>
              {cut.frameRole}
            </span>
            <span className="text-[9px] text-neutral-600 ml-auto">{durationSec}s</span>
          </div>
          <p className="text-[10px] text-neutral-400 line-clamp-2 leading-snug">
            {cut.narration || "(내레이션 없음)"}
          </p>

          {/* Status row */}
          <div className="flex gap-1.5 mt-1 flex-wrap">
            <StatusBadge status={cut.imageStatus} label={`IMG ${imgLabel}`} />
            <StatusBadge status={cut.videoStatus} label={`VID ${vidLabel}`} />
            {!cut.hasPrompt ? (
              <span className="text-[7px] rounded px-1 py-0.5 bg-amber-900/20 text-amber-500 font-medium">프롬프트 없음</span>
            ) : null}
          </div>
        </div>
      </div>
    </button>
  );
}

/* ── Main panel ─────────────────────────────────────── */

export default function CutListPanel({ cuts, selectedIndex, onSelect }: CutListPanelProps) {
  const totalDuration = cuts.reduce((s, c) => s + c.durationMs, 0);
  const totalSec = (totalDuration / 1000).toFixed(1);

  const approvedCount = cuts.filter(c => c.imageStatus === "approved").length;
  const readyCount = cuts.filter(c => c.imageStatus === "ready").length;
  const noneCount = cuts.filter(c => c.imageStatus === "none").length;

  const handleKeyNav = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown" && selectedIndex < cuts.length - 1) { e.preventDefault(); onSelect(selectedIndex + 1); }
      else if (e.key === "ArrowUp" && selectedIndex > 0) { e.preventDefault(); onSelect(selectedIndex - 1); }
    },
    [selectedIndex, cuts.length, onSelect],
  );

  return (
    <div className="h-full flex flex-col" onKeyDown={handleKeyNav} tabIndex={0}>
      {/* Header */}
      <div className="px-3 py-2 border-b border-neutral-800">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-xs font-bold text-neutral-300">컷 리스트</h3>
          <span className="text-[9px] text-neutral-600">{cuts.length}컷 · {totalSec}s</span>
        </div>
        {/* Mini status bar */}
        {cuts.length > 0 ? (
          <div className="h-1.5 rounded-full bg-neutral-800 overflow-hidden flex">
            <div className="bg-emerald-500 transition-all" style={{ width: `${(approvedCount / cuts.length) * 100}%` }} />
            <div className="bg-amber-500 transition-all" style={{ width: `${(readyCount / cuts.length) * 100}%` }} />
            <div className="bg-neutral-700 transition-all" style={{ width: `${(noneCount / cuts.length) * 100}%` }} />
          </div>
        ) : null}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5 scrollbar-thin">
        {cuts.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-xs text-neutral-600">해당 필터에 컷이 없습니다</p>
          </div>
        ) : (
          cuts.map((cut, i) => (
            <CutRow key={cut.frameId} cut={cut} isSelected={i === selectedIndex} onSelect={() => onSelect(i)} />
          ))
        )}
      </div>

      {/* Summary footer */}
      {cuts.length > 0 ? (
        <div className="px-3 py-2 border-t border-neutral-800">
          <div className="flex gap-3 text-[9px] text-neutral-600">
            <span className="text-emerald-500">{approvedCount} 승인</span>
            <span className="text-amber-500">{readyCount} 대기</span>
            <span>{noneCount} 미생성</span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
