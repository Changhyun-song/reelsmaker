"use client";

interface TimeRulerProps {
  totalMs: number;
  pixelsPerSec: number;
}

function formatTime(ms: number): string {
  const totalSec = ms / 1000;
  const m = Math.floor(totalSec / 60);
  const s = Math.floor(totalSec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function TimeRuler({ totalMs, pixelsPerSec }: TimeRulerProps) {
  const totalSec = Math.ceil(totalMs / 1000);
  const marks: number[] = [];

  const stepSec = pixelsPerSec >= 60 ? 1 : pixelsPerSec >= 30 ? 2 : 5;
  for (let s = 0; s <= totalSec; s += stepSec) {
    marks.push(s);
  }

  return (
    <div className="relative h-6 bg-neutral-900 border-b border-neutral-800 select-none">
      {marks.map((sec) => (
        <div
          key={sec}
          className="absolute top-0 h-full flex flex-col items-center"
          style={{ left: sec * pixelsPerSec }}
        >
          <div className="w-px h-2.5 bg-neutral-700" />
          <span className="text-[9px] text-neutral-600 mt-0.5">{formatTime(sec * 1000)}</span>
        </div>
      ))}
    </div>
  );
}
