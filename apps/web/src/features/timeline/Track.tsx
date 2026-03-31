"use client";

import { type ReactNode } from "react";

export interface Segment {
  id: string;
  startMs: number;
  endMs: number;
  label: string;
  color: string;
}

interface TrackProps {
  name: string;
  icon: ReactNode;
  segments: Segment[];
  pixelsPerSec: number;
  onSegmentClick?: (segId: string) => void;
}

export default function Track({ name, icon, segments, pixelsPerSec, onSegmentClick }: TrackProps) {
  return (
    <div className="flex items-stretch h-10 border-b border-neutral-800/50">
      {/* Label */}
      <div className="w-24 shrink-0 flex items-center gap-1.5 px-3 bg-neutral-900/60 border-r border-neutral-800">
        <span className="text-[10px] text-neutral-500">{icon}</span>
        <span className="text-[11px] font-medium text-neutral-400">{name}</span>
      </div>

      {/* Timeline area */}
      <div className="relative flex-1">
        {segments.map((seg) => {
          const left = (seg.startMs / 1000) * pixelsPerSec;
          const width = ((seg.endMs - seg.startMs) / 1000) * pixelsPerSec;

          return (
            <button
              key={seg.id}
              onClick={() => onSegmentClick?.(seg.id)}
              className="absolute top-1 h-8 rounded-md flex items-center px-2 text-[10px] font-medium text-white/90 transition hover:brightness-110 overflow-hidden"
              style={{
                left,
                width: Math.max(width, 20),
                backgroundColor: seg.color,
              }}
              title={seg.label}
            >
              <span className="truncate">{seg.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
