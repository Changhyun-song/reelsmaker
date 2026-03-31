"use client";

import type { CutInfo } from "./CutCard";
import { CircularProgress } from "@/components/ui/progress";
import Badge from "@/components/ui/badge";
import Button from "@/components/ui/button";

interface CutDetailProps {
  cut: CutInfo;
  onRegenerateImage?: () => void;
  onRegenerateVideo?: () => void;
}

export default function CutDetail({ cut, onRegenerateImage, onRegenerateVideo }: CutDetailProps) {
  const isGenerating =
    cut.status === "generating_image" || cut.status === "generating_video";
  const progress =
    cut.status === "generating_image"
      ? cut.imageProgress
      : cut.status === "generating_video"
        ? cut.videoProgress
        : cut.status === "complete"
          ? 100
          : 0;

  return (
    <div className="flex flex-col h-full">
      {/* Media preview */}
      <div className="relative rounded-xl overflow-hidden bg-neutral-950 aspect-video mb-4">
        {cut.videoAsset?.url ? (
          <video
            src={cut.videoAsset.url}
            controls
            className="w-full h-full object-contain"
          />
        ) : cut.imageAsset?.url ? (
          <img
            src={cut.imageAsset.url}
            alt={`Cut ${cut.index + 1}`}
            className="w-full h-full object-contain"
          />
        ) : isGenerating ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
            <CircularProgress value={progress} size={100} strokeWidth={7}>
              <span className="text-lg font-bold text-neutral-100">
                {Math.round(progress)}
              </span>
            </CircularProgress>
            <p className="text-sm text-neutral-400">
              {cut.status === "generating_image"
                ? "이미지 생성 중..."
                : "영상 생성 중..."}
            </p>
          </div>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-neutral-600">
            Cut {cut.index + 1} 미리보기
          </div>
        )}

        {/* Top-left: Cut badge */}
        <div className="absolute top-3 left-3">
          <span className="rounded-lg bg-black/60 backdrop-blur-sm px-2.5 py-1 text-[11px] font-bold text-white">
            Cut {cut.index + 1}
          </span>
        </div>

        {/* Top-right: Actions */}
        {cut.status === "complete" && (
          <div className="absolute top-3 right-3 flex gap-2">
            {onRegenerateVideo && (
              <Button variant="secondary" size="xs" onClick={onRegenerateVideo}>
                영상 재생성
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Shot info */}
      <div className="space-y-3 flex-1 overflow-y-auto">
        {/* Narration */}
        {cut.shot.narration_segment && (
          <div className="rounded-lg bg-neutral-900/60 border border-neutral-800 p-3">
            <p className="text-[11px] font-semibold text-neutral-500 mb-1">나레이션</p>
            <p className="text-sm text-neutral-200 leading-relaxed">
              {cut.shot.narration_segment}
            </p>
          </div>
        )}

        {/* Prompt */}
        <div className="rounded-lg bg-neutral-900/60 border border-neutral-800 p-3">
          <p className="text-[11px] font-semibold text-neutral-500 mb-1">영상 프롬프트</p>
          <p className="text-xs text-neutral-300 leading-relaxed line-clamp-4">
            {cut.prompt || cut.shot.description || "—"}
          </p>
        </div>

        {/* Metadata row */}
        <div className="flex flex-wrap gap-2">
          {cut.shot.duration_sec && (
            <span className="rounded-md bg-neutral-800 px-2 py-1 text-[10px] text-neutral-400">
              {cut.shot.duration_sec.toFixed(1)}s
            </span>
          )}
          {cut.shot.camera_movement && (
            <span className="rounded-md bg-violet-900/40 px-2 py-1 text-[10px] text-violet-300">
              {cut.shot.camera_movement}
            </span>
          )}
          {cut.shot.shot_type && (
            <span className="rounded-md bg-neutral-800 px-2 py-1 text-[10px] text-neutral-400">
              {cut.shot.shot_type}
            </span>
          )}
          {cut.shot.asset_strategy && (
            <Badge
              status={cut.shot.asset_strategy === "image_to_video" ? "running" : "pending"}
              label={cut.shot.asset_strategy}
            />
          )}
        </div>

        {/* Image regeneration */}
        {cut.imageAsset && onRegenerateImage && (
          <Button variant="ghost" size="sm" onClick={onRegenerateImage} className="w-full">
            이미지 재생성
          </Button>
        )}
      </div>
    </div>
  );
}
