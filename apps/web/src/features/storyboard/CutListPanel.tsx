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

/* ── Status dot ─────────────────────────────────────── */

function StatusDot({ status, label }: { status: string; label: string }) {
  const colors: Record<string, string> = {
    none: "bg-neutral-700",
    ready: "bg-amber-400",
    approved: "bg-emerald-400",
    rejected: "bg-red-400",
  };
  return (
    <div className="flex items-center gap-1" title={`${label}: ${status}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${colors[status] || colors.none}`} />
      <span className="text-[8px] text-neutral-500 uppercase">{label}</span>
    </div>
  );
}

/* ── Cut row ────────────────────────────────────────── */

function CutRow({
  cut,
  isSelected,
  onSelect,
}: {
  cut: CutItem;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const durationSec = (cut.durationMs / 1000).toFixed(1);

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
            <img
              src={cut.thumbnailUrl}
              alt={`Cut ${cut.cutIndex + 1}`}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-neutral-600 text-[8px]">
              없음
            </div>
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
            <span className="text-[9px] font-medium text-neutral-400">
              S{cut.sceneIndex + 1}.{cut.shotIndex + 1}
            </span>
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
          <div className="flex gap-2 mt-1">
            <StatusDot status={cut.imageStatus} label="IMG" />
            <StatusDot status={cut.videoStatus} label="VID" />
            {!cut.hasPrompt && (
              <span className="text-[8px] text-amber-500">프롬프트 없음</span>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}

/* ── Main panel ─────────────────────────────────────── */

export default function CutListPanel({
  cuts,
  selectedIndex,
  onSelect,
}: CutListPanelProps) {
  const totalDuration = cuts.reduce((s, c) => s + c.durationMs, 0);
  const totalSec = (totalDuration / 1000).toFixed(1);

  const handleKeyNav = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown" && selectedIndex < cuts.length - 1) {
        e.preventDefault();
        onSelect(selectedIndex + 1);
      } else if (e.key === "ArrowUp" && selectedIndex > 0) {
        e.preventDefault();
        onSelect(selectedIndex - 1);
      }
    },
    [selectedIndex, cuts.length, onSelect],
  );

  return (
    <div
      className="h-full flex flex-col"
      onKeyDown={handleKeyNav}
      tabIndex={0}
    >
      {/* Header */}
      <div className="px-3 py-2 border-b border-neutral-800">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-neutral-300">컷 리스트</h3>
          <span className="text-[9px] text-neutral-600">{cuts.length}컷 · {totalSec}s</span>
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5 scrollbar-thin">
        {cuts.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-xs text-neutral-600">프레임이 없습니다</p>
            <p className="text-[10px] text-neutral-700 mt-1">장면 구성을 먼저 실행하세요</p>
          </div>
        ) : (
          cuts.map((cut, i) => (
            <CutRow
              key={cut.frameId}
              cut={cut}
              isSelected={i === selectedIndex}
              onSelect={() => onSelect(i)}
            />
          ))
        )}
      </div>

      {/* Summary footer */}
      {cuts.length > 0 && (
        <div className="px-3 py-2 border-t border-neutral-800 flex gap-3 text-[9px] text-neutral-600">
          <span>IMG: {cuts.filter(c => c.imageStatus === "approved").length}/{cuts.length}</span>
          <span>VID: {cuts.filter(c => c.videoStatus === "ready").length}/{cuts.length}</span>
          <span>프롬프트: {cuts.filter(c => c.hasPrompt).length}/{cuts.length}</span>
        </div>
      )}
    </div>
  );
}
