"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { CutItem } from "./CutListPanel";

/* ── Types ──────────────────────────────────────────── */

interface DirtyFields {
  narration?: boolean;
  visual_prompt?: boolean;
  duration_ms?: boolean;
  dialogue?: boolean;
  mood?: boolean;
  negative_prompt?: boolean;
}

interface CutInspectorProps {
  cut: CutItem | null;
  projectId: string;
  frameDetail: FrameDetail | null;
  shotDetail: ShotDetail | null;
  onSave: (updates: FrameSavePayload) => Promise<void>;
  onShotSave: (updates: ShotSavePayload) => Promise<void>;
  onRegenerateImage: (frameId: string) => void;
  saving: boolean;
}

export interface FrameDetail {
  id: string;
  visual_prompt: string | null;
  negative_prompt: string | null;
  dialogue: string | null;
  duration_ms: number;
  composition: string | null;
  mood: string | null;
  action_pose: string | null;
  background_description: string | null;
  continuity_notes: string | null;
  forbidden_elements: string | null;
}

export interface ShotDetail {
  id: string;
  narration_segment: string | null;
  description: string | null;
  duration_sec: number | null;
  camera_movement: string | null;
  emotion: string | null;
}

export interface FrameSavePayload {
  frameId: string;
  visual_prompt?: string;
  negative_prompt?: string;
  dialogue?: string;
  duration_ms?: number;
  mood?: string;
}

export interface ShotSavePayload {
  shotId: string;
  narration_segment?: string;
  description?: string;
  duration_sec?: number;
}

/* ── Impact indicators ──────────────────────────────── */

function ImpactBadge({ impacts }: { impacts: string[] }) {
  if (impacts.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {impacts.map((imp) => (
        <span
          key={imp}
          className="rounded px-1.5 py-0.5 text-[8px] font-medium bg-amber-900/30 text-amber-400 border border-amber-800/30"
        >
          {imp} 재생성 필요
        </span>
      ))}
    </div>
  );
}

/* ── Field editor ───────────────────────────────────── */

function FieldEditor({
  label,
  value,
  onChange,
  multiline,
  placeholder,
  dirty,
  type,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  multiline?: boolean;
  placeholder?: string;
  dirty?: boolean;
  type?: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5">
        <label className="text-[10px] font-medium text-neutral-400">{label}</label>
        {dirty && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" title="수정됨" />}
      </div>
      {multiline ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          placeholder={placeholder}
          className="w-full rounded-md bg-neutral-800/60 border border-neutral-700/50 px-2.5 py-1.5 text-[11px] text-neutral-200 placeholder-neutral-600 resize-y focus:border-blue-700/50 focus:ring-1 focus:ring-blue-600/20 transition"
        />
      ) : (
        <input
          type={type || "text"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-md bg-neutral-800/60 border border-neutral-700/50 px-2.5 py-1.5 text-[11px] text-neutral-200 placeholder-neutral-600 focus:border-blue-700/50 focus:ring-1 focus:ring-blue-600/20 transition"
        />
      )}
    </div>
  );
}

/* ── Main component ─────────────────────────────────── */

export default function CutInspector({
  cut,
  projectId,
  frameDetail,
  shotDetail,
  onSave,
  onShotSave,
  onRegenerateImage,
  saving,
}: CutInspectorProps) {
  const [narration, setNarration] = useState("");
  const [visualPrompt, setVisualPrompt] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [dialogue, setDialogue] = useState("");
  const [durationMs, setDurationMs] = useState(3000);
  const [moodVal, setMoodVal] = useState("");
  const [dirty, setDirty] = useState<DirtyFields>({});
  const [saveError, setSaveError] = useState<string | null>(null);

  const prevFrameId = useRef<string | null>(null);

  useEffect(() => {
    if (!frameDetail || frameDetail.id === prevFrameId.current) return;
    prevFrameId.current = frameDetail.id;
    setVisualPrompt(frameDetail.visual_prompt || "");
    setNegativePrompt(frameDetail.negative_prompt || "");
    setDialogue(frameDetail.dialogue || "");
    setDurationMs(frameDetail.duration_ms || 3000);
    setMoodVal(frameDetail.mood || "");
    setDirty({});
    setSaveError(null);
  }, [frameDetail]);

  useEffect(() => {
    if (!shotDetail) return;
    setNarration(shotDetail.narration_segment || "");
  }, [shotDetail]);

  const impacts: string[] = [];
  if (dirty.narration) impacts.push("자막/타이밍");
  if (dirty.visual_prompt) impacts.push("이미지");
  if (dirty.duration_ms) impacts.push("타임라인");

  const hasChanges = Object.values(dirty).some(Boolean);

  const handleSave = useCallback(async () => {
    if (!frameDetail || !cut) return;
    setSaveError(null);
    try {
      const framePayload: FrameSavePayload = { frameId: frameDetail.id };
      if (dirty.visual_prompt) framePayload.visual_prompt = visualPrompt;
      if (dirty.negative_prompt) framePayload.negative_prompt = negativePrompt;
      if (dirty.dialogue) framePayload.dialogue = dialogue;
      if (dirty.duration_ms) framePayload.duration_ms = durationMs;
      if (dirty.mood) framePayload.mood = moodVal;
      await onSave(framePayload);

      if (dirty.narration && shotDetail) {
        await onShotSave({
          shotId: shotDetail.id,
          narration_segment: narration,
        });
      }
      setDirty({});
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "저장 실패");
    }
  }, [
    frameDetail, shotDetail, cut, dirty, visualPrompt, negativePrompt,
    dialogue, durationMs, moodVal, narration, onSave, onShotSave,
  ]);

  if (!cut || !frameDetail) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-xs text-neutral-600">컷을 선택하세요</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-3 py-2 border-b border-neutral-800 flex items-center justify-between">
        <div>
          <h3 className="text-xs font-bold text-neutral-300">
            컷 {cut.cutIndex + 1} 인스펙터
          </h3>
          <p className="text-[9px] text-neutral-600">
            S{cut.sceneIndex + 1}.{cut.shotIndex + 1} · {cut.frameRole}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          {hasChanges && (
            <span className="text-[9px] text-amber-400">수정됨</span>
          )}
          <button
            onClick={handleSave}
            disabled={!hasChanges || saving}
            className="rounded-md bg-blue-600/20 border border-blue-700/40 px-2.5 py-1 text-[10px] font-medium text-blue-400 hover:bg-blue-600/30 transition disabled:opacity-40"
          >
            {saving ? "저장 중..." : "저장"}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4 scrollbar-thin">
        {/* Save error */}
        {saveError && (
          <div className="rounded-lg border border-red-800/50 bg-red-950/20 p-2">
            <p className="text-[10px] text-red-400">{saveError}</p>
            <p className="text-[9px] text-neutral-600 mt-0.5">변경 사항은 유지됩니다. 다시 저장해 주세요.</p>
          </div>
        )}

        {/* Impact badges */}
        <ImpactBadge impacts={impacts} />

        {/* Narration */}
        <FieldEditor
          label="내레이션"
          value={narration}
          onChange={(v) => { setNarration(v); setDirty(d => ({ ...d, narration: true })); }}
          multiline
          placeholder="이 컷의 내레이션 텍스트"
          dirty={dirty.narration}
        />

        {/* Duration */}
        <div className="space-y-1">
          <div className="flex items-center gap-1.5">
            <label className="text-[10px] font-medium text-neutral-400">길이</label>
            {dirty.duration_ms && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />}
          </div>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={500}
              max={15000}
              step={250}
              value={durationMs}
              onChange={(e) => { setDurationMs(+e.target.value); setDirty(d => ({ ...d, duration_ms: true })); }}
              className="flex-1 accent-blue-600"
            />
            <span className="text-[10px] text-neutral-400 w-10 text-right">
              {(durationMs / 1000).toFixed(1)}s
            </span>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-neutral-800 pt-3">
          <p className="text-[9px] font-bold text-neutral-500 uppercase mb-2">이미지 프롬프트</p>
        </div>

        {/* Visual prompt */}
        <FieldEditor
          label="Visual Prompt"
          value={visualPrompt}
          onChange={(v) => { setVisualPrompt(v); setDirty(d => ({ ...d, visual_prompt: true })); }}
          multiline
          placeholder="이미지 생성에 사용될 프롬프트를 직접 수정하세요"
          dirty={dirty.visual_prompt}
        />

        {/* Negative prompt */}
        <FieldEditor
          label="Negative Prompt"
          value={negativePrompt}
          onChange={(v) => { setNegativePrompt(v); setDirty(d => ({ ...d, negative_prompt: true })); }}
          multiline
          placeholder="생성에서 제외할 요소"
          dirty={dirty.negative_prompt}
        />

        {/* Mood */}
        <FieldEditor
          label="분위기"
          value={moodVal}
          onChange={(v) => { setMoodVal(v); setDirty(d => ({ ...d, mood: true })); }}
          placeholder="예: mysterious, warm, dramatic"
          dirty={dirty.mood}
        />

        {/* Dialogue */}
        <FieldEditor
          label="대사/캡션"
          value={dialogue}
          onChange={(v) => { setDialogue(v); setDirty(d => ({ ...d, dialogue: true })); }}
          multiline
          placeholder="이 컷에 표시될 대사"
          dirty={dirty.dialogue}
        />

        {/* Divider */}
        <div className="border-t border-neutral-800 pt-3">
          <p className="text-[9px] font-bold text-neutral-500 uppercase mb-2">대표 이미지</p>
        </div>

        {/* Representative image */}
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-2">
          {cut.thumbnailUrl ? (
            <div className="space-y-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={cut.thumbnailUrl}
                alt={`Cut ${cut.cutIndex + 1}`}
                className="w-full aspect-[9/16] object-cover rounded-md"
              />
              <div className="flex items-center gap-1.5">
                <span className={`text-[9px] px-1.5 py-0.5 rounded-md font-medium ${
                  cut.imageStatus === "approved"
                    ? "bg-emerald-900/30 text-emerald-400"
                    : cut.imageStatus === "ready"
                      ? "bg-amber-900/30 text-amber-400"
                      : "bg-neutral-800 text-neutral-500"
                }`}>
                  {cut.imageStatus === "approved" ? "승인됨" : cut.imageStatus === "ready" ? "검토 대기" : cut.imageStatus}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <p className="text-[10px] text-neutral-600">이미지 없음</p>
            </div>
          )}
          <button
            onClick={() => onRegenerateImage(frameDetail.id)}
            className="mt-2 w-full rounded-md bg-neutral-800 border border-neutral-700/50 py-1.5 text-[10px] font-medium text-neutral-400 hover:text-neutral-200 transition"
          >
            이미지 재생성
          </button>
          {cut.imageStatus !== "approved" && cut.imageStatus !== "none" && (
            <p className="text-[9px] text-amber-500 mt-1 text-center">
              승인되지 않은 이미지는 비디오 품질에 영향을 줄 수 있습니다
            </p>
          )}
        </div>

        {/* Read-only metadata */}
        {frameDetail.composition && (
          <div className="space-y-1">
            <p className="text-[9px] font-medium text-neutral-500">구도</p>
            <p className="text-[10px] text-neutral-400 bg-neutral-800/40 rounded p-2 leading-relaxed">
              {frameDetail.composition}
            </p>
          </div>
        )}
        {frameDetail.continuity_notes && (
          <div className="space-y-1">
            <p className="text-[9px] font-medium text-neutral-500">연속성 노트</p>
            <p className="text-[10px] text-neutral-400 bg-neutral-800/40 rounded p-2 leading-relaxed">
              {frameDetail.continuity_notes}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
