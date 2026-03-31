"use client";

import { useState, useEffect, useCallback } from "react";
import { apiUrl } from "@/lib/api";

/* ── Types ──────────────────────────────────────────── */

interface BibleField {
  key: string;
  label: string;
  hint: string;
}

interface BibleData {
  [key: string]: string;
}

interface ContinuityBiblePanelProps {
  projectId: string;
  onSave?: () => void;
}

/* ── API helper ─────────────────────────────────────── */

async function api(path: string, opts?: RequestInit) {
  const res = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.json();
}

/* ── Bible field editor ─────────────────────────────── */

function BibleFieldEditor({
  field,
  value,
  onChange,
  dirty,
}: {
  field: BibleField;
  value: string;
  onChange: (v: string) => void;
  dirty: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <label className="text-[11px] font-bold text-neutral-300">{field.label}</label>
        {dirty && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" title="수정됨" />}
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={2}
        placeholder={field.hint}
        className="w-full rounded-lg bg-neutral-800/60 border border-neutral-700/50 px-3 py-2 text-[11px] text-neutral-200 placeholder-neutral-600 resize-y focus:border-blue-700/50 focus:ring-1 focus:ring-blue-600/20 transition leading-relaxed"
      />
      <p className="text-[9px] text-neutral-600 leading-snug">{field.hint}</p>
    </div>
  );
}

/* ── Main component ─────────────────────────────────── */

export default function ContinuityBiblePanel({
  projectId,
  onSave,
}: ContinuityBiblePanelProps) {
  const [fields, setFields] = useState<BibleField[]>([]);
  const [bible, setBible] = useState<BibleData>({});
  const [original, setOriginal] = useState<BibleData>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const fetchBible = useCallback(async () => {
    try {
      setError(null);
      const data = await api(`/api/projects/${projectId}/bible`);
      setFields(data.fields || []);
      setBible(data.bible || {});
      setOriginal(data.bible || {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "로딩 실패");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetchBible(); }, [fetchBible]);

  const isDirty = (key: string) => (bible[key] || "") !== (original[key] || "");
  const hasAnyChanges = fields.some(f => isDirty(f.key));
  const filledCount = fields.filter(f => (bible[f.key] || "").trim()).length;

  const handleSave = async () => {
    setSaving(true);
    setSaveSuccess(false);
    setError(null);
    try {
      await api(`/api/projects/${projectId}/bible`, {
        method: "PUT",
        body: JSON.stringify({ bible }),
      });
      setOriginal({ ...bible });
      setSaveSuccess(true);
      onSave?.();
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장 실패");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setBible({ ...original });
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-6 text-center">
        <div className="w-5 h-5 border-2 border-neutral-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
        <p className="text-xs text-neutral-500">Continuity Bible 로딩 중...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-bold text-neutral-200 flex items-center gap-2">
              Continuity Bible
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-900/30 text-blue-400 font-medium">
                {filledCount}/{fields.length} 설정됨
              </span>
            </h3>
            <p className="text-xs text-neutral-500 mt-0.5">
              전체 영상에서 유지해야 할 시각적 규칙을 정의합니다. 여기에 설정한 규칙은 모든 씬의 이미지 프롬프트에 자동 반영됩니다.
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {hasAnyChanges && (
              <button
                onClick={handleReset}
                className="rounded-md bg-neutral-800 border border-neutral-700/50 px-2.5 py-1.5 text-[10px] font-medium text-neutral-400 hover:text-neutral-200 transition"
              >
                되돌리기
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={!hasAnyChanges || saving}
              className="rounded-md bg-blue-600/20 border border-blue-700/40 px-3 py-1.5 text-[10px] font-medium text-blue-400 hover:bg-blue-600/30 transition disabled:opacity-40"
            >
              {saving ? "저장 중..." : saveSuccess ? "✓ 저장 완료" : "저장"}
            </button>
          </div>
        </div>

        {/* Progress */}
        <div className="h-1 rounded-full bg-neutral-800">
          <div
            className="h-full rounded-full bg-blue-500 transition-all duration-500"
            style={{ width: `${Math.round((filledCount / Math.max(fields.length, 1)) * 100)}%` }}
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-800/50 bg-red-950/20 p-3 flex items-center justify-between">
          <p className="text-xs text-red-400">{error}</p>
          <button onClick={() => setError(null)} className="text-neutral-600 hover:text-neutral-400 text-xs">✕</button>
        </div>
      )}

      {/* Bible fields */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {fields.map((field) => (
          <BibleFieldEditor
            key={field.key}
            field={field}
            value={bible[field.key] || ""}
            onChange={(v) => setBible(prev => ({ ...prev, [field.key]: v }))}
            dirty={isDirty(field.key)}
          />
        ))}
      </div>

      {/* How it works */}
      <div className="rounded-xl border border-neutral-800/50 bg-neutral-900/30 p-4">
        <p className="text-[10px] font-bold text-neutral-500 uppercase mb-2">작동 방식</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[10px] text-neutral-500">
          <div className="flex gap-2">
            <span className="text-blue-400 shrink-0">1.</span>
            <p>Bible 규칙을 작성하면 <strong className="text-neutral-400">스토리 프롬프트 생성</strong> 시 AI에게 전달됩니다.</p>
          </div>
          <div className="flex gap-2">
            <span className="text-blue-400 shrink-0">2.</span>
            <p>이미지 생성 시 <strong className="text-neutral-400">프롬프트 컴파일러</strong>가 Bible 규칙을 continuity block으로 주입합니다.</p>
          </div>
          <div className="flex gap-2">
            <span className="text-blue-400 shrink-0">3.</span>
            <p>씬별 차별성은 유지하되, <strong className="text-neutral-400">캐릭터·색감·조명·렌즈 톤</strong>이 전체에서 일관됩니다.</p>
          </div>
        </div>
      </div>

      {/* Prompt impact preview */}
      {filledCount > 0 && (
        <div className="rounded-xl border border-emerald-800/30 bg-emerald-950/10 p-4">
          <p className="text-[10px] font-bold text-emerald-400 mb-2">프롬프트 반영 미리보기</p>
          <div className="space-y-1">
            {fields.filter(f => (bible[f.key] || "").trim()).map(f => (
              <div key={f.key} className="flex items-start gap-2 text-[10px]">
                <span className="text-emerald-500 shrink-0">✓</span>
                <span className="text-neutral-500">{f.label}:</span>
                <span className="text-neutral-300 line-clamp-1">{bible[f.key]}</span>
              </div>
            ))}
          </div>
          <p className="text-[9px] text-neutral-600 mt-2">
            위 규칙이 모든 이미지/비디오 프롬프트의 [CONTINUITY BLOCK]에 포함됩니다.
          </p>
        </div>
      )}
    </div>
  );
}
