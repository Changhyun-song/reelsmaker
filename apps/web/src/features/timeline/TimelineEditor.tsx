"use client";

import { useState, useMemo, useRef } from "react";
import TimeRuler from "./TimeRuler";
import Track, { type Segment } from "./Track";
import SubtitleSettings from "./SubtitleSettings";
import type { ShotData, SubtitleTrackData, AssetData } from "@/lib/types";

interface TimelineEditorProps {
  shots: ShotData[];
  subtitleTrack: SubtitleTrackData | null;
  assets: AssetData[];
  totalDurationMs: number;
  onSubtitleStyleChange?: (style: Record<string, unknown>) => void;
}

const TRACK_COLORS = {
  subtitle: "#8B5CF6",
  visual: "#3B82F6",
  audio: "#10B981",
  music: "#F59E0B",
};

export default function TimelineEditor({
  shots,
  subtitleTrack,
  assets,
  totalDurationMs,
  onSubtitleStyleChange,
}: TimelineEditorProps) {
  const [pixelsPerSec, setPixelsPerSec] = useState(50);
  const [showSubtitlePanel, setShowSubtitlePanel] = useState(false);
  const [subtitleStyle, setSubtitleStyle] = useState<{
    fontFamily: string;
    fontSize: number;
    color: string;
    backgroundColor: string;
    position: "top" | "center" | "bottom";
    bold: boolean;
    italic: boolean;
    outline: boolean;
  }>({
    fontFamily: "Pretendard",
    fontSize: 24,
    color: "#FFFFFF",
    backgroundColor: "rgba(0,0,0,0.5)",
    position: "bottom",
    bold: true,
    italic: false,
    outline: true,
  });
  const scrollRef = useRef<HTMLDivElement>(null);

  // Build visual track segments from shots
  const visualSegments: Segment[] = useMemo(() => {
    let offset = 0;
    return shots.map((shot, i) => {
      const dur = (shot.duration_sec || 3) * 1000;
      const seg: Segment = {
        id: shot.id,
        startMs: offset,
        endMs: offset + dur,
        label: `Cut ${i + 1}`,
        color: TRACK_COLORS.visual,
      };
      offset += dur;
      return seg;
    });
  }, [shots]);

  // Build subtitle segments
  const subtitleSegments: Segment[] = useMemo(() => {
    if (!subtitleTrack?.segments) return [];
    return subtitleTrack.segments.map((seg, i) => ({
      id: `sub-${i}`,
      startMs: seg.start_ms,
      endMs: seg.end_ms,
      label: seg.text.slice(0, 30),
      color: TRACK_COLORS.subtitle,
    }));
  }, [subtitleTrack]);

  // Build audio segments from voice assets
  const audioSegments: Segment[] = useMemo(() => {
    let offset = 0;
    return shots.map((shot, i) => {
      const dur = (shot.duration_sec || 3) * 1000;
      const hasVoice = assets.some(
        (a) => a.parent_id === shot.id && a.asset_type === "voice",
      );
      const seg: Segment = {
        id: `audio-${shot.id}`,
        startMs: offset,
        endMs: offset + dur,
        label: hasVoice ? `Voice ${i + 1}` : `—`,
        color: hasVoice ? TRACK_COLORS.audio : "#374151",
      };
      offset += dur;
      return seg;
    });
  }, [shots, assets]);

  const totalWidth = (totalDurationMs / 1000) * pixelsPerSec + 100;

  return (
    <div className="flex flex-col rounded-xl border border-neutral-800 bg-neutral-950/80 overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-neutral-800 bg-neutral-900/60">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-neutral-300">타임라인</span>
          <span className="text-[10px] text-neutral-500">
            {(totalDurationMs / 1000).toFixed(1)}s
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSubtitlePanel(!showSubtitlePanel)}
            className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition ${
              showSubtitlePanel
                ? "bg-violet-600 text-white"
                : "bg-neutral-800 text-neutral-400 hover:text-neutral-200"
            }`}
          >
            자막 설정
          </button>
          <div className="flex items-center gap-1 ml-2">
            <button
              onClick={() => setPixelsPerSec(Math.max(10, pixelsPerSec - 10))}
              className="w-6 h-6 rounded flex items-center justify-center bg-neutral-800 text-neutral-400 hover:text-neutral-200 text-xs"
            >
              −
            </button>
            <span className="text-[10px] text-neutral-500 w-8 text-center">
              {pixelsPerSec}
            </span>
            <button
              onClick={() => setPixelsPerSec(Math.min(120, pixelsPerSec + 10))}
              className="w-6 h-6 rounded flex items-center justify-center bg-neutral-800 text-neutral-400 hover:text-neutral-200 text-xs"
            >
              +
            </button>
          </div>
        </div>
      </div>

      <div className="flex">
        {/* Timeline tracks */}
        <div className="flex-1 overflow-x-auto" ref={scrollRef}>
          <div style={{ width: totalWidth, minWidth: "100%" }}>
            <TimeRuler totalMs={totalDurationMs} pixelsPerSec={pixelsPerSec} />

            <Track
              name="T1 자막"
              icon={<span>Aa</span>}
              segments={subtitleSegments}
              pixelsPerSec={pixelsPerSec}
            />

            <Track
              name="V1 영상"
              icon={<span>▶</span>}
              segments={visualSegments}
              pixelsPerSec={pixelsPerSec}
            />

            <Track
              name="A1 음성"
              icon={<span>♪</span>}
              segments={audioSegments}
              pixelsPerSec={pixelsPerSec}
            />

            <Track
              name="M1 음악"
              icon={<span>♫</span>}
              segments={[]}
              pixelsPerSec={pixelsPerSec}
            />
          </div>
        </div>

        {/* Subtitle settings panel */}
        {showSubtitlePanel && (
          <div className="w-60 shrink-0 border-l border-neutral-800 p-4 bg-neutral-900/60">
            <SubtitleSettings
              style={subtitleStyle}
              onChange={(s) => {
                setSubtitleStyle(s);
                onSubtitleStyleChange?.(s as unknown as Record<string, unknown>);
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
