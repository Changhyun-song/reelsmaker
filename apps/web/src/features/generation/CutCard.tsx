"use client";

import type { ShotData, AssetData } from "@/lib/types";
import Badge from "@/components/ui/badge";

export type CutStatus = "pending" | "generating_image" | "image_done" | "generating_video" | "complete" | "error";

export interface CutInfo {
  index: number;
  shot: ShotData;
  imageAsset: AssetData | null;
  videoAsset: AssetData | null;
  status: CutStatus;
  imageProgress: number;
  videoProgress: number;
  prompt: string;
}

interface CutCardProps {
  cut: CutInfo;
  selected: boolean;
  onClick: () => void;
}

function statusLabel(s: CutStatus): string {
  switch (s) {
    case "pending": return "대기";
    case "generating_image": return "이미지 생성 중";
    case "image_done": return "이미지 완료";
    case "generating_video": return "비디오 생성 중";
    case "complete": return "완료";
    case "error": return "오류";
  }
}

function statusBadge(s: CutStatus): string {
  switch (s) {
    case "pending": return "pending";
    case "generating_image": return "generating";
    case "image_done": return "ready";
    case "generating_video": return "generating";
    case "complete": return "completed";
    case "error": return "failed";
  }
}

export default function CutCard({ cut, selected, onClick }: CutCardProps) {
  const durationStr = cut.shot.duration_sec
    ? `${cut.shot.duration_sec.toFixed(1)}s`
    : "—";

  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-xl border p-3 transition-all ${
        selected
          ? "border-violet-500/60 bg-violet-950/30 ring-1 ring-violet-500/30"
          : "border-neutral-800 bg-neutral-900/40 hover:border-neutral-600 hover:bg-neutral-900/70"
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Thumbnail */}
        <div className="w-16 h-16 rounded-lg bg-neutral-800 overflow-hidden shrink-0">
          {cut.imageAsset?.url ? (
            <img
              src={cut.imageAsset.url}
              alt={`Cut ${cut.index + 1}`}
              className="w-full h-full object-cover"
            />
          ) : cut.status === "generating_image" ? (
            <div className="w-full h-full flex items-center justify-center">
              <div className="w-5 h-5 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="w-full h-full flex items-center justify-center text-neutral-600 text-xs">
              {cut.index + 1}
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold text-neutral-400">Cut {cut.index + 1}</span>
            <Badge status={statusBadge(cut.status)} label={statusLabel(cut.status)} />
          </div>
          <p className="text-xs text-neutral-300 line-clamp-2 leading-relaxed">
            {cut.shot.narration_segment || cut.shot.description || "—"}
          </p>
          <div className="flex items-center gap-2 mt-1.5 text-[10px] text-neutral-500">
            <span>{durationStr}</span>
            {cut.shot.camera_movement && (
              <span className="text-violet-400/70">{cut.shot.camera_movement}</span>
            )}
          </div>
        </div>
      </div>

      {/* Progress bar for generating states */}
      {(cut.status === "generating_image" || cut.status === "generating_video") && (
        <div className="mt-2 h-1 rounded-full bg-neutral-800 overflow-hidden">
          <div
            className="h-full rounded-full bg-violet-500 transition-all duration-500"
            style={{
              width: `${cut.status === "generating_image" ? cut.imageProgress : cut.videoProgress}%`,
            }}
          />
        </div>
      )}
    </button>
  );
}
