"use client";

import { useState, useEffect, useCallback } from "react";
import { apiUrl } from "@/lib/api";
import PromptDiffView from "./PromptDiffView";

/* ── Types ──────────────────────────────────────── */

interface PromptVersion {
  id: string;
  version: number;
  prompt_text: string;
  negative_prompt: string | null;
  prompt_source: string;
  quality_mode: string | null;
  generation_batch: string | null;
  asset_id: string | null;
  provider: string | null;
  model: string | null;
  is_current: boolean;
  created_at: string;
  thumbnail_url: string | null;
  asset_status: string | null;
  metadata_: Record<string, unknown> | null;
}

interface Props {
  projectId: string;
  frameId: string;
  onRestore?: () => void;
}

const SOURCE_LABELS: Record<string, string> = {
  compiler: "자동 컴파일",
  story_prompt: "스토리 프롬프트",
  manual: "수동 편집",
  restored: "복원됨",
};

/* ── API helper ─────────────────────────────────── */

async function api<T = unknown>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.json();
}

/* ── Version card ───────────────────────────────── */

function VersionCard({
  v,
  isSelected,
  onSelect,
  onCompare,
  compareMode,
}: {
  v: PromptVersion;
  isSelected: boolean;
  onSelect: () => void;
  onCompare: () => void;
  compareMode: boolean;
}) {
  const time = v.created_at ? new Date(v.created_at).toLocaleString("ko-KR", { dateStyle: "short", timeStyle: "short" }) : "";

  return (
    <button
      onClick={compareMode ? onCompare : onSelect}
      className={`w-full text-left rounded-lg border p-3 transition ${
        isSelected
          ? "border-blue-600/50 bg-blue-950/20"
          : "border-neutral-800 bg-neutral-900/40 hover:border-neutral-700"
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Thumbnail */}
        <div className="w-12 h-12 rounded-md bg-neutral-800 overflow-hidden shrink-0 flex items-center justify-center">
          {v.thumbnail_url ? (
            <img src={v.thumbnail_url} alt="" className="w-full h-full object-cover" />
          ) : (
            <span className="text-[9px] text-neutral-600">
              {v.asset_id ? "불러오기 실패" : "이미지 없음"}
            </span>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-[11px] font-bold text-neutral-200">v{v.version}</span>
            {v.is_current && (
              <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-emerald-700/20 text-emerald-400 font-medium">
                현재
              </span>
            )}
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-500">
              {SOURCE_LABELS[v.prompt_source] || v.prompt_source}
            </span>
          </div>

          <p className="text-[10px] text-neutral-400 line-clamp-2 leading-relaxed mb-1">
            {v.prompt_text}
          </p>

          <div className="flex items-center gap-2 text-[9px] text-neutral-600">
            <span>{time}</span>
            {v.provider && <span>· {v.provider}</span>}
            {v.model && <span>· {v.model}</span>}
            {v.quality_mode && <span>· {v.quality_mode}</span>}
          </div>
        </div>
      </div>
    </button>
  );
}

/* ── Detail panel ───────────────────────────────── */

function NegPromptBlock({ text }: { text: string }) {
  return (
    <div className="space-y-1.5">
      <label className="text-[10px] font-bold text-neutral-500">네거티브 프롬프트</label>
      <div className="rounded-lg bg-neutral-800/50 border border-neutral-700/30 p-3 text-[9px] text-neutral-500 leading-relaxed max-h-24 overflow-y-auto">
        {text}
      </div>
    </div>
  );
}

function MetaLine({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-neutral-600">{label}: </span>
      <span className="text-neutral-400">{value}</span>
    </div>
  );
}

function VersionDetail({
  v,
  onRestore,
  onClone,
  restoring,
  cloning,
}: {
  v: PromptVersion;
  onRestore: () => void;
  onClone: () => void;
  restoring: boolean;
  cloning: boolean;
}) {
  const negPrompt = v.negative_prompt ?? "";
  const restoredFrom = v.metadata_?.restored_from_version;
  const clonedFrom = v.metadata_?.cloned_from_version;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-neutral-200">
          v{v.version} — {SOURCE_LABELS[v.prompt_source] || v.prompt_source}
        </h4>
        <div className="flex items-center gap-2">
          {!v.is_current && (
            <button
              onClick={onRestore}
              disabled={restoring}
              className="rounded-md bg-blue-600/20 border border-blue-700/40 px-2.5 py-1 text-[10px] font-medium text-blue-400 hover:bg-blue-600/30 transition disabled:opacity-40"
            >
              {restoring ? "복원 중..." : "이 버전으로 복원"}
            </button>
          )}
          <button
            onClick={onClone}
            disabled={cloning}
            className="rounded-md bg-neutral-800 border border-neutral-700/50 px-2.5 py-1 text-[10px] font-medium text-neutral-400 hover:text-neutral-200 transition disabled:opacity-40"
          >
            {cloning ? "복제 중..." : "복제"}
          </button>
        </div>
      </div>

      {v.thumbnail_url ? (
        <div className="rounded-lg overflow-hidden border border-neutral-800 max-h-48">
          <img src={v.thumbnail_url} alt="" className="w-full h-full object-contain bg-neutral-950" />
        </div>
      ) : null}

      <div className="space-y-1.5">
        <label className="text-[10px] font-bold text-neutral-500">프롬프트</label>
        <div className="rounded-lg bg-neutral-800/50 border border-neutral-700/30 p-3 text-[10px] text-neutral-300 leading-relaxed max-h-40 overflow-y-auto">
          {v.prompt_text}
        </div>
      </div>

      {negPrompt.length > 0 ? <NegPromptBlock text={negPrompt} /> : null}

      <div className="grid grid-cols-2 gap-2 text-[9px]">
        {v.provider ? <MetaLine label="Provider" value={v.provider} /> : null}
        {v.model ? <MetaLine label="Model" value={v.model} /> : null}
        {v.quality_mode ? <MetaLine label="Quality" value={v.quality_mode} /> : null}
        {v.generation_batch ? (
          <div>
            <span className="text-neutral-600">Batch: </span>
            <span className="text-neutral-400 font-mono">{v.generation_batch}</span>
          </div>
        ) : null}
      </div>

      {restoredFrom ? (
        <p className="text-[9px] text-amber-500">v{String(restoredFrom)}에서 복원됨</p>
      ) : null}
      {clonedFrom ? (
        <p className="text-[9px] text-violet-500">v{String(clonedFrom)}에서 복제됨</p>
      ) : null}
    </div>
  );
}

/* ── Main component ─────────────────────────────── */

export default function PromptHistoryPanel({ projectId, frameId, onRestore }: Props) {
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [cloning, setCloning] = useState(false);

  // Compare mode
  const [compareMode, setCompareMode] = useState(false);
  const [compareA, setCompareA] = useState<string | null>(null);
  const [compareB, setCompareB] = useState<string | null>(null);
  interface DiffItem { type: "added" | "removed" | "unchanged"; text: string; }
  const [diffData, setDiffData] = useState<{ version_a: PromptVersion; version_b: PromptVersion; diff: DiffItem[] } | null>(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api<{ versions: PromptVersion[] }>(
        `/api/projects/${projectId}/frames/${frameId}/prompt-history`
      );
      setVersions(data.versions || []);
      if (data.versions?.length && !selectedId) {
        setSelectedId(data.versions[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "로딩 실패");
    } finally {
      setLoading(false);
    }
  }, [projectId, frameId, selectedId]);

  useEffect(() => { fetchHistory(); }, [projectId, frameId]);

  const selected = versions.find(v => v.id === selectedId);

  const handleRestore = async () => {
    if (!selectedId) return;
    setRestoring(true);
    try {
      await api(`/api/projects/${projectId}/frames/${frameId}/prompt-history/restore`, {
        method: "POST",
        body: JSON.stringify({ version_id: selectedId }),
      });
      await fetchHistory();
      onRestore?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "복원 실패");
    } finally {
      setRestoring(false);
    }
  };

  const handleClone = async () => {
    if (!selectedId) return;
    setCloning(true);
    try {
      await api(`/api/projects/${projectId}/frames/${frameId}/prompt-history/clone`, {
        method: "POST",
        body: JSON.stringify({ version_id: selectedId }),
      });
      await fetchHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : "복제 실패");
    } finally {
      setCloning(false);
    }
  };

  const handleCompareSelect = (id: string) => {
    if (!compareA) {
      setCompareA(id);
    } else if (!compareB && id !== compareA) {
      setCompareB(id);
    } else {
      setCompareA(id);
      setCompareB(null);
      setDiffData(null);
    }
  };

  const runCompare = async () => {
    if (!compareA || !compareB) return;
    try {
      const data = await api<{ version_a: PromptVersion; version_b: PromptVersion; diff: DiffItem[] }>(
        `/api/projects/${projectId}/frames/${frameId}/prompt-history/compare?version_a=${compareA}&version_b=${compareB}`
      );
      setDiffData(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "비교 실패");
    }
  };

  useEffect(() => {
    if (compareA && compareB) runCompare();
  }, [compareA, compareB]);

  if (loading) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-6 text-center">
        <div className="w-5 h-5 border-2 border-neutral-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
        <p className="text-xs text-neutral-500">프롬프트 히스토리 로딩 중...</p>
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-6 text-center">
        <p className="text-xs text-neutral-500">아직 프롬프트 히스토리가 없습니다.</p>
        <p className="text-[10px] text-neutral-600 mt-1">이미지를 생성하면 프롬프트가 자동으로 기록됩니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-neutral-200">프롬프트 히스토리</h3>
          <p className="text-[10px] text-neutral-500">{versions.length}개 버전</p>
        </div>
        <button
          onClick={() => {
            setCompareMode(!compareMode);
            setCompareA(null);
            setCompareB(null);
            setDiffData(null);
          }}
          className={`rounded-md px-2.5 py-1 text-[10px] font-medium border transition ${
            compareMode
              ? "bg-violet-600/20 border-violet-700/40 text-violet-400"
              : "bg-neutral-800 border-neutral-700/50 text-neutral-400 hover:text-neutral-200"
          }`}
        >
          {compareMode ? "비교 모드 종료" : "비교"}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-800/50 bg-red-950/20 p-2 flex items-center justify-between">
          <p className="text-[10px] text-red-400">{error}</p>
          <button onClick={() => setError(null)} className="text-neutral-600 hover:text-neutral-400 text-[10px]">✕</button>
        </div>
      )}

      {compareMode && (
        <div className="rounded-lg bg-violet-950/10 border border-violet-800/30 p-2 text-[10px] text-violet-400">
          두 버전을 선택하세요: {compareA ? `v${versions.find(v => v.id === compareA)?.version}` : "?"} vs {compareB ? `v${versions.find(v => v.id === compareB)?.version}` : "?"}
        </div>
      )}

      {/* Compare diff view */}
      {compareMode && diffData && (
        <PromptDiffView
          versionA={diffData.version_a}
          versionB={diffData.version_b}
          diff={diffData.diff}
        />
      )}

      {/* Layout: version list + detail */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {/* Version list */}
        <div className="md:col-span-2 space-y-2 max-h-[500px] overflow-y-auto pr-1">
          {versions.map((v) => (
            <VersionCard
              key={v.id}
              v={v}
              isSelected={compareMode ? (v.id === compareA || v.id === compareB) : v.id === selectedId}
              onSelect={() => setSelectedId(v.id)}
              onCompare={() => handleCompareSelect(v.id)}
              compareMode={compareMode}
            />
          ))}
        </div>

        {/* Detail */}
        {!compareMode && selected && (
          <div className="md:col-span-3 rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
            <VersionDetail
              v={selected}
              onRestore={handleRestore}
              onClone={handleClone}
              restoring={restoring}
              cloning={cloning}
            />
          </div>
        )}
      </div>
    </div>
  );
}
