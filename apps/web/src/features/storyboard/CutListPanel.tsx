"use client";

import { useCallback, useState, useMemo } from "react";

/* ── Types ──────────────────────────────────────────── */

export type ShotImportance = "key" | "normal" | "filler";

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
  importance: ShotImportance;
  importanceReasons: string[];
  needsManualReview: boolean;
}

interface CutListPanelProps {
  cuts: CutItem[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  onReorder: (from: number, to: number) => void;
}

/* ── Importance config ──────────────────────────────── */

const IMPORTANCE_STYLES: Record<ShotImportance, { dot: string; label: string; border: string; bg: string }> = {
  key: { dot: "bg-violet-400", label: "핵심", border: "border-violet-700/40", bg: "bg-violet-900/20" },
  normal: { dot: "bg-blue-400", label: "일반", border: "border-blue-800/30", bg: "bg-blue-950/10" },
  filler: { dot: "bg-neutral-600", label: "연결", border: "border-neutral-800/40", bg: "bg-neutral-900/20" },
};

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
  const impStyle = IMPORTANCE_STYLES[cut.importance];
  const imgLabel = cut.imageStatus === "approved" ? "승인" : cut.imageStatus === "ready" ? "대기" : cut.imageStatus === "rejected" ? "거절" : "없음";
  const vidLabel = cut.videoStatus === "ready" ? "완료" : "없음";

  return (
    <button
      onClick={onSelect}
      className={`w-full text-left rounded-lg border transition-all duration-150 group ${
        isSelected
          ? "border-blue-600/60 bg-blue-950/30 ring-1 ring-blue-500/20"
          : `${impStyle.border} ${impStyle.bg} hover:border-neutral-700 hover:bg-neutral-800/40`
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
          {/* Importance dot */}
          <span className={`absolute bottom-0.5 right-0.5 w-2 h-2 rounded-full ${impStyle.dot}`} title={impStyle.label} />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-[9px] font-medium text-neutral-400">S{cut.sceneIndex + 1}.{cut.shotIndex + 1}</span>
            <span className={`text-[7px] px-1 rounded font-medium ${impStyle.bg} ${
              cut.importance === "key" ? "text-violet-400" : cut.importance === "normal" ? "text-blue-400" : "text-neutral-500"
            }`}>
              {impStyle.label}
            </span>
            {cut.needsManualReview ? (
              <span className="text-[7px] px-1 rounded bg-orange-900/30 text-orange-400 font-medium">검토</span>
            ) : null}
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

/* ── Collapsible group ─────────────────────────────── */

function ImportanceGroup({
  importance,
  cuts,
  selectedIndex,
  onSelect,
  globalOffset,
  defaultExpanded,
}: {
  importance: ShotImportance;
  cuts: CutItem[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  globalOffset: number;
  defaultExpanded: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const style = IMPORTANCE_STYLES[importance];
  const hasSelected = cuts.some((_, i) => globalOffset + i === selectedIndex);

  if (cuts.length === 0) return null;

  return (
    <div className="space-y-1">
      <button
        onClick={() => setExpanded(!expanded)}
        className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition ${
          hasSelected ? "bg-blue-950/20" : "hover:bg-neutral-800/30"
        }`}
      >
        <span className={`w-2 h-2 rounded-full ${style.dot}`} />
        <span className="text-[10px] font-bold text-neutral-400 flex-1">
          {style.label} ({cuts.length})
        </span>
        <span className="text-[9px] text-neutral-600">
          {expanded ? "▾" : "▸"}
        </span>
      </button>
      {expanded ? (
        <div className="space-y-1">
          {cuts.map((cut, i) => (
            <CutRow
              key={cut.frameId}
              cut={cut}
              isSelected={globalOffset + i === selectedIndex}
              onSelect={() => onSelect(globalOffset + i)}
            />
          ))}
        </div>
      ) : (
        <div className="px-2 pb-1">
          <p className="text-[9px] text-neutral-600">
            {cuts.filter(c => c.imageStatus === "approved").length}/{cuts.length} 승인 ·
            {" "}{cuts.filter(c => c.imageStatus === "none").length} 미생성
          </p>
        </div>
      )}
    </div>
  );
}

/* ── Main panel ─────────────────────────────────────── */

export default function CutListPanel({ cuts, selectedIndex, onSelect }: CutListPanelProps) {
  const [viewMode, setViewMode] = useState<"flat" | "grouped">("grouped");

  const totalDuration = cuts.reduce((s, c) => s + c.durationMs, 0);
  const totalSec = (totalDuration / 1000).toFixed(1);

  const approvedCount = cuts.filter(c => c.imageStatus === "approved").length;
  const readyCount = cuts.filter(c => c.imageStatus === "ready").length;
  const noneCount = cuts.filter(c => c.imageStatus === "none").length;

  const keyCuts = useMemo(() => cuts.filter(c => c.importance === "key"), [cuts]);
  const normalCuts = useMemo(() => cuts.filter(c => c.importance === "normal"), [cuts]);
  const fillerCuts = useMemo(() => cuts.filter(c => c.importance === "filler"), [cuts]);

  const keyOffset = 0;
  const normalOffset = keyCuts.length;
  const fillerOffset = keyCuts.length + normalCuts.length;

  const groupedOrder = useMemo(() => [...keyCuts, ...normalCuts, ...fillerCuts], [keyCuts, normalCuts, fillerCuts]);
  const flatToGrouped = useMemo(() => {
    const map = new Map<number, number>();
    groupedOrder.forEach((c, gi) => {
      const fi = cuts.indexOf(c);
      if (fi !== -1) map.set(fi, gi);
    });
    return map;
  }, [groupedOrder, cuts]);
  const groupedToFlat = useMemo(() => {
    const map = new Map<number, number>();
    groupedOrder.forEach((c, gi) => {
      const fi = cuts.indexOf(c);
      if (fi !== -1) map.set(gi, fi);
    });
    return map;
  }, [groupedOrder, cuts]);

  const handleGroupedSelect = useCallback((groupedIdx: number) => {
    const flatIdx = groupedToFlat.get(groupedIdx);
    if (flatIdx !== undefined) onSelect(flatIdx);
  }, [groupedToFlat, onSelect]);

  const groupedSelectedIndex = useMemo(() => {
    return flatToGrouped.get(selectedIndex) ?? -1;
  }, [flatToGrouped, selectedIndex]);

  const handleKeyNav = useCallback(
    (e: React.KeyboardEvent) => {
      if (viewMode === "flat") {
        if (e.key === "ArrowDown" && selectedIndex < cuts.length - 1) { e.preventDefault(); onSelect(selectedIndex + 1); }
        else if (e.key === "ArrowUp" && selectedIndex > 0) { e.preventDefault(); onSelect(selectedIndex - 1); }
      }
    },
    [selectedIndex, cuts.length, onSelect, viewMode],
  );

  const manualReviewCount = cuts.filter(c => c.needsManualReview).length;
  const manualRatio = cuts.length > 0 ? Math.round((manualReviewCount / cuts.length) * 100) : 0;

  return (
    <div className="h-full flex flex-col" onKeyDown={handleKeyNav} tabIndex={0}>
      {/* Header */}
      <div className="px-3 py-2 border-b border-neutral-800 space-y-1.5">
        <div className="flex items-center justify-between">
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
        {/* View toggle + review ratio */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setViewMode("grouped")}
              className={`rounded px-1.5 py-0.5 text-[8px] font-medium transition ${
                viewMode === "grouped" ? "bg-violet-900/30 text-violet-400" : "text-neutral-600 hover:text-neutral-400"
              }`}
            >
              중요도순
            </button>
            <button
              onClick={() => setViewMode("flat")}
              className={`rounded px-1.5 py-0.5 text-[8px] font-medium transition ${
                viewMode === "flat" ? "bg-blue-900/30 text-blue-400" : "text-neutral-600 hover:text-neutral-400"
              }`}
            >
              순서대로
            </button>
          </div>
          <span className={`text-[8px] font-medium ${
            manualRatio <= 30 ? "text-emerald-500" : manualRatio <= 50 ? "text-amber-500" : "text-red-400"
          }`}>
            수동 검토 {manualRatio}%
          </span>
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5 scrollbar-thin">
        {cuts.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-xs text-neutral-600">해당 필터에 컷이 없습니다</p>
          </div>
        ) : viewMode === "grouped" ? (
          <div className="space-y-2">
            <ImportanceGroup
              importance="key"
              cuts={keyCuts}
              selectedIndex={groupedSelectedIndex}
              onSelect={handleGroupedSelect}
              globalOffset={keyOffset}
              defaultExpanded={true}
            />
            <ImportanceGroup
              importance="normal"
              cuts={normalCuts}
              selectedIndex={groupedSelectedIndex}
              onSelect={handleGroupedSelect}
              globalOffset={normalOffset}
              defaultExpanded={false}
            />
            <ImportanceGroup
              importance="filler"
              cuts={fillerCuts}
              selectedIndex={groupedSelectedIndex}
              onSelect={handleGroupedSelect}
              globalOffset={fillerOffset}
              defaultExpanded={false}
            />
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
          <div className="flex gap-3 text-[9px] text-neutral-600 flex-wrap">
            <span className="text-violet-400">{keyCuts.length} 핵심</span>
            <span className="text-blue-400">{normalCuts.length} 일반</span>
            <span>{fillerCuts.length} 연결</span>
            <span className="ml-auto text-emerald-500">{approvedCount} 승인</span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
