"use client";

import { useState } from "react";
import Button from "@/components/ui/button";

interface SubtitleStyle {
  fontFamily: string;
  fontSize: number;
  color: string;
  backgroundColor: string;
  position: "top" | "center" | "bottom";
  bold: boolean;
  italic: boolean;
  outline: boolean;
}

interface SubtitleSettingsProps {
  style: SubtitleStyle;
  onChange: (style: SubtitleStyle) => void;
}

const FONT_OPTIONS = [
  "Pretendard",
  "Noto Sans KR",
  "Nanum Gothic",
  "Nanum Myeongjo",
  "Black Han Sans",
];

const COLOR_PRESETS = [
  "#FFFFFF", "#FFD700", "#00FF88", "#FF6B6B", "#6B8AFF",
  "#FF88CC", "#88FFE0", "#FFA500",
];

export default function SubtitleSettings({ style, onChange }: SubtitleSettingsProps) {
  const update = (partial: Partial<SubtitleStyle>) => {
    onChange({ ...style, ...partial });
  };

  return (
    <div className="space-y-4">
      <h4 className="text-xs font-bold text-neutral-400">자막 스타일</h4>

      {/* Font */}
      <div>
        <label className="text-[11px] text-neutral-500 mb-1 block">폰트</label>
        <select
          value={style.fontFamily}
          onChange={(e) => update({ fontFamily: e.target.value })}
          className="w-full rounded-lg bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm text-neutral-200 focus:outline-none focus:border-violet-500"
        >
          {FONT_OPTIONS.map((f) => (
            <option key={f} value={f}>{f}</option>
          ))}
        </select>
      </div>

      {/* Font size */}
      <div>
        <label className="text-[11px] text-neutral-500 mb-1 block">
          크기 <span className="text-neutral-600">{style.fontSize}px</span>
        </label>
        <input
          type="range"
          min={12}
          max={48}
          value={style.fontSize}
          onChange={(e) => update({ fontSize: Number(e.target.value) })}
          className="w-full accent-violet-500"
        />
      </div>

      {/* Text color */}
      <div>
        <label className="text-[11px] text-neutral-500 mb-1.5 block">글자 색상</label>
        <div className="flex gap-2 flex-wrap">
          {COLOR_PRESETS.map((c) => (
            <button
              key={c}
              onClick={() => update({ color: c })}
              className={`w-7 h-7 rounded-full border-2 transition ${
                style.color === c ? "border-violet-500 scale-110" : "border-neutral-700"
              }`}
              style={{ backgroundColor: c }}
            />
          ))}
        </div>
      </div>

      {/* Position */}
      <div>
        <label className="text-[11px] text-neutral-500 mb-1.5 block">위치</label>
        <div className="flex gap-2">
          {(["top", "center", "bottom"] as const).map((pos) => (
            <button
              key={pos}
              onClick={() => update({ position: pos })}
              className={`flex-1 rounded-lg py-2 text-xs font-medium transition ${
                style.position === pos
                  ? "bg-violet-600 text-white"
                  : "bg-neutral-800 text-neutral-400 hover:text-neutral-200"
              }`}
            >
              {pos === "top" ? "상단" : pos === "center" ? "중앙" : "하단"}
            </button>
          ))}
        </div>
      </div>

      {/* Text style toggles */}
      <div className="flex gap-2">
        <button
          onClick={() => update({ bold: !style.bold })}
          className={`flex-1 rounded-lg py-2 text-xs font-bold transition ${
            style.bold ? "bg-violet-600 text-white" : "bg-neutral-800 text-neutral-400"
          }`}
        >
          B
        </button>
        <button
          onClick={() => update({ italic: !style.italic })}
          className={`flex-1 rounded-lg py-2 text-xs italic transition ${
            style.italic ? "bg-violet-600 text-white" : "bg-neutral-800 text-neutral-400"
          }`}
        >
          I
        </button>
        <button
          onClick={() => update({ outline: !style.outline })}
          className={`flex-1 rounded-lg py-2 text-xs transition ${
            style.outline ? "bg-violet-600 text-white" : "bg-neutral-800 text-neutral-400"
          }`}
        >
          외곽선
        </button>
      </div>
    </div>
  );
}
