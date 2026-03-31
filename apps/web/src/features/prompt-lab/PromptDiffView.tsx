"use client";

/* ── Types ──────────────────────────────────────── */

interface PromptVersion {
  id: string;
  version: number;
  prompt_text: string;
  negative_prompt: string | null;
  prompt_source: string;
  quality_mode: string | null;
  provider: string | null;
  model: string | null;
  is_current: boolean;
  created_at: string;
  thumbnail_url: string | null;
}

interface DiffItem {
  type: "added" | "removed" | "unchanged";
  text: string;
}

interface Props {
  versionA: PromptVersion;
  versionB: PromptVersion;
  diff: DiffItem[];
}

const SOURCE_LABELS: Record<string, string> = {
  compiler: "자동 컴파일",
  story_prompt: "스토리 프롬프트",
  manual: "수동 편집",
  restored: "복원됨",
};

/* ── Diff token component ───────────────────────── */

function DiffToken({ item }: { item: DiffItem }) {
  if (item.type === "unchanged") {
    return <span className="text-neutral-400">{item.text} </span>;
  }
  if (item.type === "removed") {
    return (
      <span className="bg-red-900/30 text-red-300 line-through rounded-sm px-0.5 mx-0.5">
        {item.text}
      </span>
    );
  }
  return (
    <span className="bg-emerald-900/30 text-emerald-300 rounded-sm px-0.5 mx-0.5">
      {item.text}
    </span>
  );
}

/* ── Version column ─────────────────────────────── */

function VersionColumn({ v, label }: { v: PromptVersion; label: string }) {
  const time = v.created_at ? new Date(v.created_at).toLocaleString("ko-KR", { dateStyle: "short", timeStyle: "short" }) : "";

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-bold text-neutral-200">{label}: v{v.version}</span>
        {v.is_current && (
          <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-emerald-700/20 text-emerald-400 font-medium">
            현재
          </span>
        )}
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-500">
          {SOURCE_LABELS[v.prompt_source] || v.prompt_source}
        </span>
      </div>

      {/* Thumbnail */}
      <div className="w-full h-28 rounded-md bg-neutral-800 overflow-hidden flex items-center justify-center">
        {v.thumbnail_url ? (
          <img src={v.thumbnail_url} alt="" className="w-full h-full object-contain" />
        ) : (
          <span className="text-[9px] text-neutral-600">이미지 없음</span>
        )}
      </div>

      <div className="flex items-center gap-2 text-[9px] text-neutral-600 flex-wrap">
        <span>{time}</span>
        {v.provider && <span>· {v.provider}</span>}
        {v.model && <span>· {v.model}</span>}
        {v.quality_mode && <span>· {v.quality_mode}</span>}
      </div>
    </div>
  );
}

/* ── Main component ─────────────────────────────── */

export default function PromptDiffView({ versionA, versionB, diff }: Props) {
  const added = diff.filter(d => d.type === "added").length;
  const removed = diff.filter(d => d.type === "removed").length;
  const unchanged = diff.filter(d => d.type === "unchanged").length;

  return (
    <div className="rounded-xl border border-violet-800/30 bg-neutral-900/40 p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-violet-400">프롬프트 비교</h4>
        <div className="flex items-center gap-3 text-[9px]">
          <span className="text-emerald-400">+{added} 추가</span>
          <span className="text-red-400">−{removed} 삭제</span>
          <span className="text-neutral-600">{unchanged} 유지</span>
        </div>
      </div>

      {/* Side-by-side version info */}
      <div className="grid grid-cols-2 gap-4">
        <VersionColumn v={versionA} label="이전" />
        <VersionColumn v={versionB} label="이후" />
      </div>

      {/* Diff view */}
      <div className="space-y-1.5">
        <label className="text-[10px] font-bold text-neutral-500">변경 내용 (문장 단위)</label>
        <div className="rounded-lg bg-neutral-950/50 border border-neutral-800/50 p-3 text-[10px] leading-relaxed max-h-52 overflow-y-auto">
          {diff.map((item, i) => (
            <DiffToken key={`${item.type}-${i}`} item={item} />
          ))}
          {diff.length === 0 && (
            <span className="text-neutral-600">변경 사항이 없습니다.</span>
          )}
        </div>
      </div>

      {/* Side-by-side full text */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-[9px] font-bold text-neutral-600">v{versionA.version} 전체 텍스트</label>
          <div className="rounded-lg bg-neutral-800/30 border border-neutral-800/50 p-2.5 text-[9px] text-neutral-500 leading-relaxed max-h-32 overflow-y-auto">
            {versionA.prompt_text || "—"}
          </div>
        </div>
        <div className="space-y-1">
          <label className="text-[9px] font-bold text-neutral-600">v{versionB.version} 전체 텍스트</label>
          <div className="rounded-lg bg-neutral-800/30 border border-neutral-800/50 p-2.5 text-[9px] text-neutral-500 leading-relaxed max-h-32 overflow-y-auto">
            {versionB.prompt_text || "—"}
          </div>
        </div>
      </div>

      {/* Negative diff */}
      {(versionA.negative_prompt || versionB.negative_prompt) && (
        <div className="space-y-1">
          <label className="text-[9px] font-bold text-neutral-600">네거티브 프롬프트 변경</label>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-neutral-800/30 border border-neutral-800/50 p-2 text-[9px] text-neutral-600 max-h-20 overflow-y-auto">
              {versionA.negative_prompt || "—"}
            </div>
            <div className="rounded-lg bg-neutral-800/30 border border-neutral-800/50 p-2 text-[9px] text-neutral-600 max-h-20 overflow-y-auto">
              {versionB.negative_prompt || "—"}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
